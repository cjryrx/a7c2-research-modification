# 真机运行时会话记录（2026-10-26）

> 机身：ILCE-7CM2（序列号仅本地留存，不入库）
> 目的：为「连拍加速按键」补丁拿**运行时**证据
> 结果：**执行通道打通并已确认 root**，但**门控的可用位尚未读出**——会话被 USB 服务线程失稳中断。

---

## 1. 基线（只读，已确认）

| 项 | 值 | 说明 |
| --- | --- | --- |
| 机身当前版本 | `dat4 = 00 02` | 即上次装的 **2.00** 补丁包（不是原厂 2.01） |
| updater 库 | 22,776 B，SHA-256 `2bf92c7b…18d3` | 与官方 2.01 一致 → p1 版本门控**已恢复**，没有残留 |
| 产品身份 | 读取成功（88 B 产品信息） | 机型判定通过 |

含义：这台机身现在跑的就是我们产出的 2.00 包，后续任何补丁的 base 应以它为起点。

## 2. 执行通道（已打通）

用参考项目 `a7c2-re` 的 **libJit 入口**：把 5,328 B 的载荷写到相机 `/tmp/jiritsu/libJit.so`，
由固件自己 `dlopen`，载荷再拉起子进程执行一段 shell 脚本，结果写回
`/tmp/jiritsu/a7c2-exec.{request,start,status,out}`。载荷 SHA-256 与文档一致
（`a71fbf4f…43f9`）。

**已确认 root**，`start` 记录原文：

```
A7JITE01 v1 pid=532 euid=0 status=0
```

`pid=532` 很关键：`im.elf` 就是 PID 532 —— 也就是说这个载荷是被**主应用进程**加载的。

主机侧要在 Windows 下跑，需要补三处（都在本工作区的 `tools/libjit_win.py` 里，未入库）：

1. `signal.SIGALRM/alarm` 在 Windows 不存在 → 映射到 `SIGTERM` 并把 `alarm` 置空；
2. `camera_mounts()` 读 `/proc/self/mountinfo`、卸载用 `udisksctl` → 返回空（相机走 WinUSB）；
3. pyusb 找不到 libusb → 复用 fork 里的 `windows_libusb.get_backend()`（libusb-package）。

## 3. 相机侧的可用工具与进程（已观察）

`/bin` 里的 busybox 工具有：`ash busybox cat chattr chgrp chmod chown cp cpio date dd dmesg du
echo egrep false fgrep grep gunzip gzip hostname kill ln login ls lsattr mkdir mknod mktemp mount
mv pidof ping ps pwd rm rmdir sed sh sleep sync tar top touch true umount uname usleep vmstat zcat`。
**没有** `od / xxd / hexdump / cmp / head / tail / find / awk / cut`。

主应用进程 `532 im.elf`，`/lib/appFw.so` 的映射（本次开机）：

```
7f62cd6000-7f67e7d000 r-xp      /usr/lib/appFw.so      ← 加载基址 0x7f62cd6000
7f67e8d000-7f68897000 r--p      (rodata)
7f68897000-7f68c3a000 rw-p      (data)
7f68c3a000-7f6c578000 rw-p      (bss, ≈60 MB)
```

由此可推出运行时地址公式：**任意 vaddr `V` → `0x7f62cd6000 + V`**；
参数可用性 map（离线分析里的全局对象 `0x88d92d8`）本次落在 `0x7f6b5af2d8` 附近。
注意基址**每次开机都变**，必须每次从 `/proc/532/maps` 重新取。

## 4. 稳定性：两个必须知道的坑

1. **载荷跑过一次之后，USB 服务线程会失稳**（参考项目已记录）。表现：后续会话
   `bulk read/write` 超时或 `Unexpected Senser sequence or function`。
   恢复：**取出电池约 30 秒**（Windows 上重新插拔不够）。
2. **`/tmp/jiritsu/a7c2-exec.out` 会变成"毒药"**：主机端读回有上限（单次响应 4 KB / 64 KB），
   一旦残留文件大于上限（我们遇到 86,554 B 的 maps 输出），之后**每一次**会话都会在
   "记录上一轮文件"这一步直接报
   `Response declares 86554 bytes, exceeding limit`。
   规避：用服务的写命令把它写回 1 字节（`tools/libjit_fix_state.py`，先写后读）。

## 5. 下一步（下次接相机的最短路径）

因为每次会话都有失稳风险，命令必须**批量**，不要一问一答：

**第 1 条命令（只读、输出小）**

```
cat /proc/532/maps | grep appFw
```

→ 主机侧算出本次基址 `B`。

**第 2 条命令（只读、二进制输出）**

```
dd if=/proc/532/mem bs=1 skip=$((B+0x88d92d8)) count=128
```

→ 读出 map 对象，得到根节点指针；随后按红黑树逐层读节点（每节点 0x68 字节，
键在 `+0x20`、可用位在 `+0x3a`），或者直接在堆段里搜 `17 04 cf 02`（键 0x02CF0417）。

**判据**

* 键不存在 → 参数没被创建，门在更早的构造处；
* 键存在且 `+0x3a` 为 0 → 就是它，接着找静态写入源；
* 键存在且为 1 → 与热启动镜像快照一致，转去查自定义键记录表。

## 6. 本次没做到的部分（如实记录）

* 没有读出可用位，因此**没有**新的补丁字节；
* `patches_spotboost.json` 仍为 `status: "unresolved"`，构建依旧会拒绝出包。

## 7. 第一次会话之后：机身开始自动重启（已观察）

拿到 maps 之后，继续尝试读基址时出现连锁失败：

```
libjit:  ValueError: Unexpected Senser sequence or function
camera-tools: USBError errno 32 / bulk read 516 bytes failed: USBTimeoutError (10060)
              "service read did not reach ProductInfo"
```

随后**机身自行重启**（用户观察）。判读：

* 这是服务模式会话把 USB 服务线程带崩的已知后果（参考项目 `a7c2-re` 的 AGENTS.md 里
  写明"会话结束后相机停在 054c:096f，Windows 必须断电重启"）。本次是同一个失效模式的
  更强表现：服务线程崩溃后由固件看门狗重启机身。
* **没有写任何 flash 内容**：这两条路线的写操作只有 `/tmp/jiritsu/` 下的临时文件
  （独立分区），以及 p1 门控那种显式流程——本次**没有**跑任何更新/门控写入。
  已确认写包版本字节仍是 `00 02`（我们自己的 2.00 包），updater 库仍是官方 2.01。
* 成功那次运行结束时 `libjit_remaining: false`，即载荷 `libJit.so` 已自我删除；
  残留的只有 1 字节的 `a7c2-exec.{request,start,status,out}`，没有触发路径。

**结论**：这类"一问一答"式的运行时侦察在这台机身/这条通道上代价太高（每次会话都可能
让服务线程崩溃并要求断电）。若还要继续，必须改成**一次会话内跑完的一条脚本**，并且
在读取前先把脚本落到相机上（避免每次重传载荷）。

## 8. 第二轮会话：可用性层被真机数据否掉

### 8.1 方法（一会话多轮，避免反复认证）

`libjit_exec.py run` 每跑一次命令就要重新认证一次 USB，而这条通道每认证几次就会把服务线程
带崩。于是本轮改成**一次会话内跑多条脚本**：写脚本 → 写载荷（固件 dlopen 触发）→ 轮询
`start/status` → 读结果文件，循环。实现放在工作区 `tools/libjit_session.py`（未入库）。

相机侧没有 `head/tail/od/xxd/cmp/wc/cut/awk`，`grep` 也**没有 `-b`**（拿不到字节偏移），
所以定位方式是：先按 64 KiB 分块用 `grep -q -F -f <模式文件>` 找命中的块，再把块 `dd` 出来
在主机侧解析。模式文件用 `printf '\027\004\317\002'` 写成（脚本体里可以带引号，协议层不会吞）。

### 8.2 读取路径先做对照

在 `base + 0x4caf110` 读回 `PRM_HAITA_is_spot_boost_enabled` 字符串 —— 地址换算与
`/proc/<pid>/mem` 读取都正确。

### 8.3 决定性结果：参数可用性是 (1,1)

`is_param_available` 的结构（0x2ec6b10）：

```
obj  = 0x88d92d8                     # appFw .bss
root = *(u64 *)(obj + 0x10)          # 本轮落在 0x16c3580（heap，非 PIE 基址）
node: key = *(u32 *)(node + 0x20)
      left  = *(u64 *)(node + 0x10)
      right = *(u64 *)(node + 0x18)
record = node + 0x28
available = record[0x12] ? record[0x13] : 0        # node + 0x3a / +0x3b
```

`im.elf` 是老式非 PIE 布局（`0x400000` 起，heap `0x41a000-0x1dc7000`，约 26 MiB），
树节点在 heap 里。实际读到的节点：

| 键 | 节点地址 | 可用位 |
| --- | --- | --- |
| `0x02CF0415` evolved_spot_boost_executable_status | 0x16c67d0 | **(1,1)** |
| `0x02CF0416` | 0x16c6840 | (1,1) |
| `0x02CF0417` is_spot_boost_enabled | 0x16c68b0 | **(1,1)** |
| `0x02CF0418` | 0x16c6920 | (1,1) |

**结论：参数可用性层并没有关掉这个功能。** 此前报告把它当成最可能的门（置信 0.68），
真机数据把它否掉了。

### 8.4 门在 UI 层（用户现场确认）

机身菜单实测：自定义键的可分配功能列表里**没有**「连拍速度提升(保持/切换)」，
驱动模式列表里**也没有**「连拍速度提升」。参数可用 ⇒ **门在菜单/自定义键记录层**。

### 8.5 顺带找到的运行期表

相同的复合键在 heap 里共 5 处。除了树节点，还定位到两张 32 字节步长的表：

```
0x15d0978: 14 04 cf 02 00 00 00 00 | 8d 00 00 00 00 00 00 07 | 21 00 … | 50 17 5d 01 …
0x15d0998: 15 04 cf 02 00 00 00 00 | 91 00 00 00 00 00 00 07 | …
0x1607994: 16 04 cf 02 00 00 04 00 | … 44 f6 56 6b 7f 00 00 00 | 21 00 …
```

即 `{键, 计数/标志, 指针}` 形式，键按 `0x02CF0414…0x02CF041B` 连续排列。它们不是
自定义键功能表，但可以作为后续追查"UI 层数据从哪来"的入口。

### 8.6 下一步实验（已备好键位）

不经过 UI 直接写入按键绑定，是绕开"UI 层没这个条目"的最短路径。自定义键属性键
（`AP 索引 = 319 + 2k`，`k` 为 `BKID_APP_SETTING_*` 地址序）已经算好：

| 键 | AP 索引 | 属性键 |
| --- | --- | --- |
| `…CUSTOM_KEY_SHOOT_STILL_C_BUTTON` | 1321 | `0x02CF0529` |
| `…CUSTOM_KEY_SHOOT_STILL_CUSTOM_BUTTON_1` | 1307 | `0x02CF051B` |
| `…CUSTOM_KEY_SHOOT_STILL_AEL_BUTTON` | 1335 | `0x02CF0537` |
| `…CUSTOM_KEY_SHOOT_STILL_AF_ON_BUTTON` | 1337 | `0x02CF0539` |
| `…CUSTOM_KEY_SHOOT_STILL_CENTER_BUTTON` | 1323 | `0x02CF052B` |

实验顺序（全部可回退，先读后写）：

1. `readBackup(0x02CF0529)` 等，确认值的**长度与编码**（应该是功能 id，量级像 `0x109E`）；
2. 用机身现有绑定反推 id 空间（用户报告某键当前功能，和读取值对齐）；
3. `writeBackup(0x02CF05xx, <hold_spot_boost 的 id>)` + `saveBackup(0x02cf)`；
4. 冷启动后按那个键，看是否进入提速（相机内确认，不改 flash 固件）；
5. 回退：把原值写回 + `saveBackup`。

失败模式要提前接受：app 可能按"允许列表"校验该值并把非法值改回默认。
若如此，则说明这是一层真正的白名单，必须回到固件侧改菜单数据。

## 9. 第三轮：属性侧实测（读 / 差分 / 写）

本轮验证了"不经过 UI 直接改按键绑定"这条路的可行性，结论是**目前走不通**，原因逐条记录如下。

### 9.1 会话骨架的正确用法（踩坑记录）

`analysis/camprop.py` / `camset.py` / `camdump.py` 都基于 a7c2-re 的 `camread2.build_module()`
会话骨架。要让它工作必须同时满足：

1. `product_info()` 里**先** `self.wire_phase = "product"`，否则第一条请求就被
   `JiritsuSession.write()` 判成 `wrong_protocol_phase`；
2. 备份属性读写会绕过该守卫，所以 `Session` 子类必须**同时**重写 `write()` 和 `read()`，
   在 `allow_backup` 为真时直接打 `dev.write/read`（只重写 `read()` 会出现
   `request_not_allowlisted`）。

### 9.2 自定义键那组 1 字节属性不是"绑定"

`AP 索引 = 319 + 2k` 算出的 `BKID_APP_SETTING_CUSTOM_KEY_SHOOT_STILL_*` 落在
`0x02CF0509 … 0x02CF0541`，布局为**奇数索引=当前值（1 字节）、其后偶数索引=13 份 MR 副本**。
实测值：C 键 `00`、中央键 `01`、MOVIE `02`、左 `03`、右 `04`、多选择器 `07`、
AEL/AF-ON `0a`、放大 `0d`、下 `0f`。

**反证**：让用户在机身把 MOVIE 键改成"切换静音模式"并断电重启，再读 `0x02CF053D`
仍然是 `02`。→ 这组值是"物理按键槽位标识"，**不是功能绑定**。

### 9.3 差分扫描：绑定不在 0x300–0x6FF

`analysis/camdump.py` 一次会话读 1024 个属性（`0x300–0x6FF`），两次差分。
用户改了 AF-ON（跟踪+中央AF → 对焦模式）与 MOVIE（静音切换 → APS-C/全幅选择）之后，
**没有任何自定义键相关属性变化**；变化的只有：

```
0x2cf041b  PRM_setting_drive_mode_self_timer_for_hw_position         c3090000 -> 22010000
0x2cf041c  PRM_setting_drive_mode_white_bracket_for_hw_position      05030000 -> 00030000
```

两条都是驱动模式相关，与自定义键无关。→ 功能绑定**不在** `0x2cf` 的这个区间里
（`0x2cf` 共 6553 项，本次只覆盖 16%）。

### 9.4 写路径现状

`analysis/camset.py` 的 `writeBackup` 在 pmca 层抛 `TypeError`，被 `service_probe`
包成 `dependency_error`，没有留下 traceback。**写入尚未成功过一次**，需要先修这个。
（`camprop`/`camdump` 的读路径是好的，320 / 1024 项都能读满。）

### 9.5 下一步（按代价排序）

1. 修 `writeBackup` 的 `TypeError`（在 `analysis/` 下单独起一个直连 pmca 的会话，绕开
   `service_probe` 的异常包装，拿到真实 traceback）；
2. 扩差分范围：`0x2cf` 全组 6553 项（一次会话约 1–2 分钟），用"改一处 → 再扫 → 差分"
   找真正的绑定属性；
3. 若确认绑定不在 AP 属性里，则它只能落在 app 自己的 `BKID` 之外的存储（例如
   `/setting` 下的数据库文件），那时再考虑直接改文件。

**目前仍未达成**：把 `FUNC_hold_spot_boost_shooting` 绑到某个键上。
`patches_spotboost.json` 保持 `status: "unresolved"`。

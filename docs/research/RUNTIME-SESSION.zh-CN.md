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

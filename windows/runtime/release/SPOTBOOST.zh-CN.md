# 连拍加速按键（burst boost button）补丁环节

> 目标：让「按下（或按住）绑定按键 → 连拍提速」这个能力在 ILCE-7CM2 上可用。
> 这正是索尼的 **「Continuous Shooting Speed Boost」**（日文 `連写速度ブースト`，
> 菜单写作 `Cnt Shoot Speed Boost`，自定义键写作 `Cnt Sht Spd Bst Toggle` /
> `Cnt Sht Spd Bst Hold`）。
>
> **当前状态：`status = "unresolved"`。** 补丁字节尚未确认，因此本环节会**拒绝构建**，
> 不会产出任何固件包（与上游 `a7c2-20fps` 的纪律一致：没有证据就不出包）。

---

## 1. 为什么认为"功能存在但没开"

以下全部是**离线静态事实**，来自官方 2.01 `BODYDATA.DAT`（不涉及任何真机操作）：

| 证据 | 位置 |
| --- | --- |
| 完整本地化文案：`Cnt Shoot Speed Boost`、`Cnt Sht Spd Bst Settings/Toggle/Hold`、说明文字「Sets the continuous shooting speed when using "Continuous Shooting Speed Boost". "Continuous Shooting Speed Boost" can be recalled with the custom key.」 | `/share/app/string_*_f.uxc`、`string_*_func_j.uxc`、`string_*_horizontal/vertical.uxc`（`analysis/ui/`） |
| 事件处理函数：`process_EVENT_FUNC_CUSTOM_SPOT_BOOST_TOGGLE_ON/HOLD_ON` | `appFw.so` `.text` 0x1b31da8 / 附近 |
| 自定义键功能名：`FUNC_hold_spot_boost_shooting`、`FUNC_toggle_spot_boost_shooting`、`FUNC_(hold|toggle)_evolved_spot_boost_shooting` | `appFw.so` 的 `FUNC_*` 名表 |
| 状态机与能力枚举：`PRM_HAITA_is_spot_boost_enabled_{NOT_SET,DISABLED,ENABLED}`、`PRM_HAITA_evolved_spot_boost_executable_status_*`（`ONLY_S0_EXECUTABLE` / `DURING_S0_S1_EXECUTABLE` / `ALWAYS_EXECUTABLE`） | `appFw.so` 的 `VAL_*` 名表 |
| 速度档位枚举：`SHOOT_SET_REGISTRATION_(EVOLVED_)SPOT_BOOST_{5,10,15,20,30,60,120}SHOTS_SEC` | 同上 |
| 到 CP 的命令通道：`sequence_set_boost_shooting`、`PID_SET_BOOST_SHOOTING`、`PID_SET_BOOST_FPS` | `appFw.so`（PID 注册表，0x171448c / 0x17144a4） |
| CP 侧接收：`pGFW: SET_BOOST_FPS[%d]`、`FW: SET_BOOST_SHOOTING[%d]` | `CPAPP-B.BIN` 0x47d930 / 0x47d979（分区内偏移） |
| 相关设置键：`BKID_APP_SETTING_CUSTOM_SPOT_BOOST_SET`、两份 `BKID_APP_SHOOT_SET_REGISTRATION_*SPOT_BOOST*` | `appFw.so` 的 `BKID_*` 名表 |

结论（**已观察**）：整条链路（按键 → 事件 → 序列 → 发 CP → CP 侧 boost 处理）在 2.01 里是完整的，
连 UI 文案都已翻好；缺的是**让它出现在菜单/自定义键列表里的那个开关**。

（**推断，未验证**）这与 FL2/FL3 的情况同构：功能资源齐全，只有「路由/能力判定」被机型数据关掉。

---

## 2. 补丁环节的位置

上游流水线是"一次性从官方 2.01 加 FL2/FL3 与快门音效，并钉死明文哈希与字节改动数"
（`fl23_windows.py` 断言 86/4/155 处变化，`sound_package_200.py` 断言明文 SHA）。
因此**不能**把新补丁混进上游那一步，否则上游会直接报错。

本环节改为**叠加在已完成的上游 2.00 包之上**：

```
官方 2.01 DAT
   └─(fl23_windows.build / sound_package_200.build)──►  BODYDATA_FL23_200.DAT
                                                        或 BODYDATA_FEATURES_200.DAT   ← base
   └─(spotboost_package_200.build)────────────────────►  BODYDATA_SPOTBOOST_200.DAT  ← 最终包
```

- 只改 `patches_spotboost.json` 声明的那些字节；
- 只重算被改分区的 `part_image.sum` CRC；
- 版本号、DEND CRC、加密全部沿用上游产物（`encrypt_from` 以 base 为模板重写 FDAT）。

### 选择入口

```bat
:: 只 FL2/FL3 + 连拍加速按键
py windows\runtime\release\feature_package_200.py --official BODYDATA.DAT --out-dir run --fl23 --audio-mode none --boost

:: FL2/FL3 + 原厂快门音效 + 连拍加速按键
py windows\runtime\release\feature_package_200.py --official BODYDATA.DAT --out-dir run --fl23 --audio-mode stock --boost
```

`selected_package_200.json` 在这种情况下写成 `format: 4`，`feature_ids` 末尾追加
`burst_boost_button`；下游的 staging / 校验步骤通过 `feature_package_200.selected()`
拿到的就是最终包，不需要改别的调用点。

---

## 3. 补丁数据格式（`patches_spotboost.json`）

```json
{
  "format": 1,
  "id": "burst_boost_button",
  "status": "ready",                       // unresolved 时构建会被拒绝
  "bases": [
    { "feature_ids": ["fl2_fl3"],
      "dat_sha256":   "a3076b2b…38de",
      "plain_sha256": "aade3795…5f59" }
  ],
  "expected_byte_changes": { "usr": 2, "wbi": 0, "cp": 2 },
  "spans": [
    { "name": "spot_boost_menu_enable",
      "partition": "usr",                  // usr=nflasha15, wbi=nflasha5, cp=nflasha8
      "offset": 686526448,                 // 分区内偏移，不是 appFw.so 内偏移
      "old_sha256": "…",                   // 被替换的原字节 SHA-256
      "new": "1f2a",                       // 替换内容
      "context_size": 132,                 // 守卫窗口大小，窗口从 offset-64 开始
      "context_sha256": "…",
      "why": "一句话说明这条改动依据什么证据" }
  ]
}
```

约束（构建时会逐条硬校验）：

* `partition` 只能是 `usr` / `wbi` / `cp`；
* 每个 span 必须同时匹配 `old_sha256` 与 `offset-64` 起的 `context_size` 字节窗口；
* span 之间不得重叠；`offset >= 64`；
* 每条 span 必须写 `why`（防止来历不明的字节混进来）；
* `expected_byte_changes` 若给了某个分区，实际改动字节数必须完全一致。

### 快速命令

```bat
:: 看某个 2.00 包属于哪一类 base（给出 spec 需要的 dat/plain 哈希）
py windows\runtime\release\spotboost_package_200.py --describe BODYDATA_FL23_200.DAT

:: 只校验：base 身份 + 每条 span 的旧值/守卫窗口，不写任何文件
py windows\runtime\release\spotboost_package_200.py --preflight BODYDATA_FL23_200.DAT

:: 真正构建（status 必须是 ready）
py windows\runtime\release\spotboost_package_200.py --base BODYDATA_FL23_200.DAT --out-dir run
```

输出：`BODYDATA_SPOTBOOST_200.DAT` + `spotboost_package_200.json`
（记录 base 哈希、spec 哈希、每分区改动字节数、分区 CRC 前后值、DEND CRC、输出/明文 SHA-256）。

---

## 4. 校验链

1. **base 身份**：DAT SHA-256 必须等于 spec 里声明的某个 base；
2. **base 明文身份**：解密后明文 SHA-256 必须匹配（防止拿到"同名不同内容"的包）；
3. **逐 span**：旧值 SHA-256 + 64 字节守卫窗口 SHA-256 全部通过才动手；先全查、后统一写；
4. **改动计数**：与 `expected_byte_changes` 一致；
5. **分区 CRC**：三份 `part_image.sum` 条目重算，且未改动分区的旧值必须与重算值一致；
6. **重新加密 → 完整回读**：把输出整包重新解密，与构建用的明文逐块比对；
7. **输出身份**：`output_sha256` 写入 manifest，`selected()` 再次回读校验。

任何一步失败都不会留下半成品（临时文件在 `finally` 里删除）。

---

## 5. 风险

* 这是**非官方固件**：影响保修；更新中断/断电可能导致无法开机。
* 补丁一旦落进 appFw 的代码路径，可能出现菜单项不显示、按键无反应、
  最坏情况是拍摄相关逻辑异常（连拍/驱动模式/静音快门）。
* 必须保留：官方 2.01 DAT、本机 p1 与 BK4 备份、构建出的 base 包哈希记录。
* 上机顺序永远是"先只读侦察 → 再最小改动 → 再冷启动验证"。

---

## 6. 真机验证计划（相机接上后）

> 目前**未连接相机**，以下步骤尚未执行。

**第 0 步：确认基线（只读）**

1. `windows_rollback_gate_ro.py` 读 `dat4` 版本字节，确认机身当前是 2.00（上次装的包）还是已被刷回 2.01；
2. `windows_bk4_snapshot.py` 只读抓 BK4（`/setting/Backup.bin` + `Backup.bak`），留档；
3. 确认 USB 身份：海量存储 `054c:0e8a` → 服务 `054c:0336` → 会话后 `054c:096f`（Windows 需断电重启）。

**第 1 步：找"为什么没开"的运行时证据（只读，不改任何字节）**

先用现有的服务模式会话拿到 `0336` 上的 root 或只读文件通道，然后**只读**地确认下面三件事。
全部有明确的判据，不需要猜测：

| 要确认的 | 怎么看 | 判据 |
| --- | --- | --- |
| 参数键 `0x02CF0417` 在运行时 map 里存在吗 | 找到 app 进程（`/lib/appFw.so` 的持有者）的 `maps`，算出 `0x88d92d8` 的实际地址，按红黑树遍历找键 0x02CF0417 | 找不到 ⇒ 参数根本没被创建（门在更早的构造处）；找到 ⇒ 读它在 `+0x28` 描述记录里的 `+0x12/+0x13` 两个字节 |
| 那两个可用位是什么值 | 同上 | `(1,1)` ⇒ 参数可用，问题在菜单/自定义键层；`(0,*)` ⇒ 这条就是门 |
| 同一张 map 里邻居参数（`0x02CF0414…0x02CF041B`）的值 | 同上 | 用来对照：本机正常参数应该是 `(1,1)` |

> 注意：`nflasha5`（热启动镜像）里 0x0417 的快照是 `0x01010000`（可用位 1,1），
> 所以**不要**用热启动镜像当证据，必须看运行中的 map。

**第 2 步：最小可逆实验（易失，断电即恢复）**

如果第 1 步显示可用位是 0，用 root 通过 `/proc/<pid>/mem` 把这两个字节改成 1
（**只改内存，不写 flash**），然后让用户在菜单里看：

* 自定义键列表里是否出现 `Cnt Sht Spd Bst Hold/Toggle`；
* 驱动模式里是否出现 `Cnt Shoot Speed Boost`。

这一步完全没有持久风险（断电即回到原样），但能直接判定"门是不是这张 map"。
若出现，再回到离线侧找"往这张 map 写 0 的静态来源"，把它变成 DAT 补丁；
若不出现，转去查自定义键记录表（§7.3 第 2 条）。

**第 3 步：装机与回退**

* 若第 1 步指向某个数据字节 → 只改那一处，构造包（`status: ready` 后再 `--preflight`、`--build`）；
* 上机前用 `--preflight` 对**真机上实际存在的 base 包**再跑一遍；
* 装机：临时写 p1 版本门控（显示 1.99 → 2.00）→ 卡上 `BODYDATA.DAT` → 机身更新 → 恢复 p1；
* 冷启动后验证：菜单里出现 `Cnt Shoot Speed Boost` / 自定义键能选到 `Cnt Sht Spd Bst Hold`；
* 功能验证：绑定按键 → 按住连拍，比较两张相邻照片的 EXIF 时间差（10 fps ≈ 100 ms，提速目标 ≈ 50 ms）；
* 异常即刻回退：官方 2.01 DAT 重新刷回。

**第 3 步：留档**

把 `spotboost_package_200.json`、`selected_package_200.json`、BK4 快照、实测间隔记录进
`windows/runtime/runs/<序列号>/`。

---

## 7. 未解决项（诚实清单）

### 7.1 已经查清的机制（已观察）

**id 空间**（两路独立验证）：`PRM_*` / `VAL_*` / `FUNC_*` 三类名字共用
`.data.rel.ro` 里**一个**指针数组（基址 0x57FD1A0，文件偏移 0x57ED1A0，28,860 项），
**数组下标就是 id**。因此：

| 名字 | id | 说明 |
| --- | --- | --- |
| `PRM_HAITA_is_spot_boost_enabled` | `0x0417` | 参数键 = `0x02CF0417` |
| `PRM_HAITA_evolved_spot_boost_executable_status` | `0x0415` | |
| `PRM_hold_spot_boost_shooting_mode` | `0x0a79` | |
| `PRM_toggle_spot_boost_shooting_mode` | `0x0a7a` | |
| `PRM_setting_custom_spot_boost_set` | `0x0cb7` | |
| `FUNC_hold_spot_boost_shooting` | `0x109e` | 自定义键功能 id |
| `FUNC_toggle_spot_boost_shooting` | `0x109f` | |
| `VAL_HAITA_is_spot_boost_enabled_{NOT_SET,DISABLED,ENABLED}` | `0x3007/0x3008/0x3009` | |

**参数可用性是一个运行期的红黑树 map**（全局 `0x88d92d8`，查询 `0x2ec6b78` → `0x2ec6b10`），
节点里 `+0x20` 是键、`+0x28` 是描述记录，判定式是 `flag[+0x12] ? flag[+0x13] : 0`；
**所有消费者都是 `tst w0,#0xff; b.eq <跳过整块>`**。也就是说：本机取不到 spot boost 的
参数，整条读写/事件路径被整体跳过。

### 7.2 已经排除的（有边界的负结果）

* **不在 feature-manager 改写规则表里**：把 `.data.rel.ro` 的 `{ptr,count}` 描述符全部解出
  （191,774 张候选表），spot boost 相关 73–76 张全查，**没有任何一行**把它改写成
  `OFF` / `DISABLED` / `NOT_SET`。对比预拍摄那张"10 行全部 → FIXED"的强制表，形态不同。
* **不在 FUNC 注册表里**：`0x41eb070` 的 `{flag, func_id}` 对 `0x109e/0x109f` 给的是 `1`（可用）。
* **`mov w1,#0x459f` 不是 PRM id**（那是 `VAL_…SET_WIDE`）；PRM 键总是拼成 `0x02CF0000|id`。
* **`No854_/No1508_SpotBoostShootingMode` 是死字符串**（0 代码引用、0 指针槽）。
* **不是 CP 侧按键表**：`CPAPP-B.BIN` 里几乎没有 `0x02cfxxxx` 键。
* **热启动镜像不是门**：`nflasha5` 里能找到参数快照（键 0x0417 在 0x8cb7960、0x8d24150 等），
  但其可用位 `0x01010000`（+0x1a/+0x1b = 1,1）与邻居 0x0414…0x041b 完全相同 —— 默认值形态，
  没有机型差异。

### 7.3 仍然未知（需要真机或跨机型固件）

1. **谁往那张可用性 map 里写 0x02CF0417 的条目**（写出点疑似 `0x2f39a00` 一带的循环，
   `strb wzr,[node,#0x3a]` 很像是把可用位清零）；
2. 自定义键列表的"每个菜单类型的可用位"（`is_valid_custom_key_setting_select_function_item`
   @0x1b6e1c4，记录步长 14，读过 `rec+4 … rec+0x11`）；**这张记录表本身以及它的调用者是间接调用，未定位**；
3. `is_spot_boost_enabled` 到底由什么算出来（无规则表 ⇒ 只能是代码算；输入未见）；
4. 两个处理函数（TOGGLE 0x1b31da8 / HOLD 0x1af5c10）开头都会先 `bl 0x1798734; cmp w0,#1`，
   不通过就走断言 + `mov w0,#0x86a0; movk w0,#1`（=100000）的中止路径；`0x1798734` 的语义未确认。

### 7.4 一条被记住的"诊断补丁"（**不要发**）

有一个能让"参数可用性查询恒为真"的实验性改法（appFw.so 文件偏移 `0x2EC6B94`，
`01 48 40 39 41 00 00 34 01 4c 40 39` → `21 00 80 52 1f 20 03 d5 1f 20 03 d5`）。
它会把**所有**本机不支持的参数一次性放开，风险极高，只能用于在真机上**证明 map 就是门**，
绝不可写进 `patches_spotboost.json`。

在门控定位之前，本环节保持 `status: "unresolved"`，`--build` 会直接报错，这是设计如此。

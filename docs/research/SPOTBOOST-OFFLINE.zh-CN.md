# 连拍加速按键（Cnt Shoot Speed Boost）——离线分析记录

> 目标机型：Sony ILCE-7CM2（A7C II），官方固件 **2.01**（`BODYDATA.DAT`，
> SHA-256 `eb4943e6…e1e31`）。
> 全部结论来自**离线静态分析**，未连接相机、未修改任何 DAT。
>
> 判读纪律：每条结论标注 **已观察 / 推断 / 未验证**。

---

## 0. 一页结论

| 问题 | 结论 | 等级 |
| --- | --- | --- |
| 这个功能在 2.01 里存在吗 | **存在**：完整本地化文案 + 事件处理函数 + 自定义键功能名 + app→CP 命令通道 + CP 侧日志 | 已观察 |
| 它现在能用吗 | **不能**：菜单/自定义键里取不到（同 FL2/FL3 的"资源齐全、路由未接"形态） | 已观察（行为）/ 推断（原因） |
| 门控（开关）在哪 | **尚未定位**。已排除若干候选，留下 3 条明确线索 | 未验证 |
| 补丁环节可用吗 | **可用**，已在真实 1.1 GB base 包上端到端跑通（改动 1 字节 → 分区 CRC 更新 → 整包回读只差 1 字节 + 7 个 CRC 字符） | 已观察 |

---

## 1. 功能在固件里的可见痕迹（全部已观察）

### 1.1 UI 文案（`/usr/share/app/*.uxc`，已解包到 `analysis/ui/`）

```
string_english_f.uxc         Cnt Sht Spd Bst Settings
                             Sets the continuous shooting speed when using
                             "Continuous Shooting Speed Boost".
                             "Continuous Shooting Speed Boost" can be recalled
                             with the custom key.
string_english_func_j.uxc    Cnt Sht Spd Bst Toggle
                             Cnt Sht Spd Bst Hold
                             ... switches to the selected continuous shooting
                             speed while the button is held.
                             Does not perform "Continuous Shooting Speed Boost".
string_english_horizontal/vertical.uxc
                             Cnt Shoot Speed Boost   （与 Cont. Shooting: Lo/Mid/Hi+ 并列）
```

### 1.2 STRID 名单（`share/app/area_check_data.dat`，`UXAC` v2，9353 条 STRID）

| 序号 | STRID |
| --- | --- |
| 1771 | `STRID_FUNC_CUSTOM_SPOT_BOOST_REGISTER` |
| 1772 | `STRID_FUNC_CUSTOM_SPOT_BOOST_REGISTER_GUIDE` |
| 1951 | `STRID_FUNC_DRIVEMODE_GUIDE_SPOTCONTSHOOTING` |
| 5073–5078 | `STRID_FUNC_SPOT_BOOST`、`_HOLD`、`_HOLD_GUIDE`、`_SET_OFF_GUIDE`、`_TOGGLE`、`_TOGGLE_GUIDE` |
| 7897–7900 | `STRID_FUNC_DRIVEMODE_SET_SPOTCONTSHOOTING_2 / _HI / _LO / _MID` |
| 9033 | `STRID_MSG_DURING_SPOT_BOOST_INVALID` |
| 9242 | `STRID_MSG_SPOT_BOOST_HOLD_REGISTERD_CUSTOM_KEY` |

即：**自定义键名（HOLD / TOGGLE）、注册提示、非法状态提示、驱动模式里的 HI/MID/LO 三档**全都定义了。

### 1.3 app 侧代码与枚举（`analysis/bin/appFw.so`）

| 项 | 证据 |
| --- | --- |
| 事件处理函数 | `bool master_input_eventgp_TOGGLE_screen_screengp_Other_controller::process_EVENT_FUNC_CUSTOM_SPOT_BOOST_TOGGLE_ON(const ds_event&)` @0x3dc9d10 → 函数 0x1b31da8；`…_HOLD_ON…` @0x3dc9fc8 |
| 自定义键功能 | `FUNC_hold_spot_boost_shooting`、`FUNC_toggle_spot_boost_shooting`、`FUNC_(hold|toggle)_evolved_spot_boost_shooting`、`FUNC_evolved_spot_boost_shooting_(on|off)_for_haita` |
| 能力/状态 | `PRM_HAITA_is_spot_boost_enabled`（值 `NOT_SET`/`DISABLED`/`ENABLED` = 值 id **0x3007/0x3008/0x3009**）、`PRM_HAITA_evolved_spot_boost_executable_status`（`NOT_SET`/`ONLY_S0_EXECUTABLE`/`DURING_S0_S1_EXECUTABLE`/`ALWAYS_EXECUTABLE`）、`PRM_HAITA_setting_menu_drive_mode_setting_still_shutter_type_evolved_spot_boost_shooting_mode_*` |
| 速度档 | `SHOOT_SET_REGISTRATION_(EVOLVED_)SPOT_BOOST_{5,10,15,20,30,60,120}SHOTS_SEC`、`BKID_APP_SETTING_CUSTOM_SPOT_BOOST_SET` |
| 到 CP 的命令 | `sequence_set_boost_shooting`、`PID_SET_BOOST_SHOOTING`(0x416f)、`PID_SET_BOOST_FPS`(0x4170) |
| 反馈/远程 | `libra::ResID toggle_feedback_presenter::get_value_resid_spot_boost()`、`remote_presenter::set_cont_shoot_spot_boost_status(...)`、`translator_icon_spot_boost_shooting_mode::translate(...)` |

### 1.4 CP 侧（`analysis/bin/CPAPP-B.BIN`，18,090,880 B，32-bit ARM）

`pGFW: SET_BOOST_FPS[%d]` @0x47d979 / `FW: SET_BOOST_SHOOTING[%d]` @0x47d930
→ CP 会收到并处理 boost 帧率与 boost 状态。

---

## 2. 已排除的方向（有边界的负结果）

| 方向 | 做法 | 结果 |
| --- | --- | --- |
| AP 属性直接给帧率 | 上一轮已读 `FPS_FIXED_VARIABLE_SELECT`、`DRIVE_MODE_*` 等 | 帧率不在 AP 属性里（值是选择器/超时量级） |
| 值 id 作为立即数找"门" | 扫 `.text` 全部 `MOVZ/MOVK` 命中 0x3007/0x3008/0x3009 | 17 处，全部是**枚举注册**（`mov w1,#id; bl register`）或断言打印，没有比较/分支用它做判定 |
| `No854_SpotBoostShootingMode` / `No1508_…` 字符串 | 找 ADRP+ADD 代码引用、找指针槽 | **0 引用、0 指针槽**（死字符串，说明 UI 资源 id 是在别处按数字使用） |
| 紧凑规则表（feature-manager） | 重建 `.data.rel.ro` 的 `{ptr,count}` 描述符 → 解出 191,774 张表，筛 `kind∈{0,1,2,3}` 且行内出现 spot boost 值 id 的表共 76 张 | **没有一张把 `is_spot_boost_enabled` 强制改成 DISABLED**。现有 76 张表做的是"两套命名空间之间的别名映射"（`VAL_hold_spot_boost_shooting_mode_*` ↔ `VAL_evolved_spot_boost_shooting_mode_*`）与"状态推导"，与预拍摄那张 `FIXED` 表性质不同 |
| `DMMCFG.BIN`（CP 分区 43,508 B） | 结构查看 | 是设备/寄存器映射表，与机型能力无关 |
| 热启动镜像 `nflasha5` | 搜 spot_boost | 只有 app 只读段被缓存进来的字符串，没有能力值 |

**方法论校正（重要）**：`analysis/elf_reloc.py` 早期按"文件偏移==虚拟地址"读 `.data.rel.ro`，
但这些段在文件里比 vaddr 低 0x10000，因此旧结论中凡是"指针槽附近内容"的判读都要用
`analysis/elfutil.py`（按段表翻译）重做。本记录用的是后者。

---

## 3. 留下的三条线索（未验证）

### 线索 A：自定义键列表的"可用位"

`menu::util::util_instance::is_valid_custom_key_setting_select_function_item(...)`
（断言串 @0x3dd0b48，代码 @0x1b6e1c4）对每个自定义键候选功能项做判定，读的是
**每个菜单项结构里的一段按菜单类型排列的标志字节**（`madd` 用 14 字节步长，
读偏移 4…0x11）。如果 spot boost 项的这 14 个标志在 A7C II 上全为 0，而 A7R V/α7 V
上非 0，那就是门。**待做**：反向找出这段标志的写入者（菜单项构造处），定位它的静态表。

### 线索 B：`PRM_HAITA_evolved_spot_boost_executable_status` 的推导表

已找到的规则表把「驱动模式=连拍 + 电子快门 + spot boost 关」映射到
`evolved_spot_boost_executable_status = ONLY_S0_EXECUTABLE`，而
`hold_spot_boost_shooting_mode` 的状态与 `evolved_spot_boost_shooting_mode` 之间存在
成对的别名表。**待做**：确认 `is_spot_boost_enabled` 是不是由这些状态再推一层；
若是，改"驱动模式/快门类型 → 可用"的那张表，比改 `is_spot_boost_enabled` 更安全。

### 线索 C：`area_check_data.dat`（`/usr/share/app`，1,142,255 B）

`UXAC` v2 容器，头部含 `count = 9353` 与三个长度字段；文件里 9353 条 STRID 名与
数值记录混排。app 启动时会读它（`is_valid_custom_key_setting_select_function_item`
读的很可能就是解析后的这份数据）。**待做**：解出记录布局（当前试过的固定步长计数器假设都不成立），
然后比较 `STRID_FUNC_SPOT_BOOST_HOLD` 与一个确定可用的功能（如
`STRID_FUNC_CUSTOM_ZOOM_BUTTON`）的记录差异。若差异只是若干标志位，这就是**数据补丁**，
比改代码安全得多，而且这个文件就在可打补丁的 `nflasha15` 里。

---

## 4. 下一步（按性价比）

1. **真机只读侦察**（相机接上后第一步，见 fork 文档 §6）：确认
   `is_spot_boost_enabled` 与 `evolved_spot_boost_executable_status` 的**运行时真实取值**，
   这能直接把线索 A/B 收敛成一条。
2. **跨机型差分**：若手上有 α7 V / α7R V / A7CR 的官方固件，把同一套 id 空间重建方法
   套到那边，找出"有该功能"与"没有"的差异表 —— 这是最干净的证据来源。
   （工作区里已有 `a7m5-dat\BODYDATA.DAT`，正在做可行性验证。）
3. 解 `area_check_data.dat` 记录布局（线索 C），若有可用位差异，优先走**数据补丁**。
4. 三条线索都走不通时，再考虑"代码补丁"（把某个已有自定义键功能的处理入口改指向
   spot boost 的处理函数）——这是最后手段：可读性最好但风险最高。

---

## 5. 复现用工具（本记录新增/修正）

| 脚本 | 作用 |
| --- | --- |
| `analysis/elfutil.py` | 正确的 vaddr↔文件偏移 + 相对重定位指针槽 + ADRP 代码引用扫描 |
| `analysis/disa.py` | 带注释的反汇编（解析 ADRP+ADD/LDR 与分支目标） |
| `analysis/valspace.py` | 值 id 空间：`VAL_*` 名表位置 = id（锚点 `…timeshift_prohibited_NOT_SET == 0x5793`） |
| `analysis/spotboost_gate.py` / `spotboost_tables.py` | 枚举 `.data.rel.ro` 里 `{ptr,count}` 规则表并解码、筛出与 spot boost 相关的表 |
| `analysis/idmap.py` | 从注册代码（`mov w1,#id` + 名字 + `bl`）恢复 `PID_*` id 表（341 条） |

```bat
py analysis\elfutil.py                     :: 无 CLI，作库用
py analysis\disa.py 0x1b31da8 0x120
py analysis\valspace.py names "is_spot_boost_enabled"
py analysis\spotboost_tables.py > analysis\spotboost_tables.txt
py analysis\imm_scan.py analysis\bin\appFw.so 0x3008=DISABLED 0x3009=ENABLED
```

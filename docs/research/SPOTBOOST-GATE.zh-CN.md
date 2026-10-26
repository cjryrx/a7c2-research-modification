# ILCE-7CM2 (A7C II) 2.01：连写速度ブースト / Continuous Shooting Speed Boost 不可达的闸门定位

分析对象：`analysis\bin\appFw.so`（99,960,744 B，AArch64 PIE，链接基址 0）。
本文件所有 `0x…` 均为**虚拟地址**；`.text` 与 `.rodata` 的文件偏移 == 虚拟地址，`.data.rel.ro` 起之后各段文件偏移比虚拟地址低 `0x10000`（沿用 `elfutil.Elf` 的换算，全部读写经段表）。

标注约定：**OBSERVED** = 已在本机二进制里直接读到/反汇编确认；**INFERRED** = 由观察推理；**UNKNOWN** = 未确定。

---

## 0. 结论摘要

| 项 | 结论 | 证据等级 |
| --- | --- | --- |
| 是否存在一条 rule 表把 `is_spot_boost_enabled` 强制成 DISABLED | **没有**（阴性，与既有结论一致） | OBSERVED |
| `mov w1,#0x459f`（0x1b31ee0 附近）是否是 PRM id | **否**。0x459f=17823 = `VAL_registration_autofocus_area_contrast_detect_af_90_degrees_set_AUTOFOCUS_AREA_CONTRAST_DETECT_AF_SET_WIDE` | OBSERVED |
| FUNC 注册表是否把 `FUNC_hold/toggle_spot_boost_shooting` 标为不可用 | **否**，两条都是 `1`（见 §4） | OBSERVED |
| 真正的机制层 | 参数可用性（availability）是**运行期红黑树 map**，键 = `0x02CF0000 | PRM_id`；查询返回 `flag[+0x12] && flag[+0x13]` | OBSERVED（实现）／INFERRED（这就是闸门） |
| 自定义键菜单校验函数 0x1b6e1c4 的记录 | 记录首字段是 **PRM id**（特例 0x1a6 = `PRM_setting_s_q_exposure_mode`），不是 FUNC id | OBSERVED |
| 精确到字节的启用补丁 | **UNKNOWN**——未定位到承载 availability 初值的静态描述表，因此没有可信的 old/new 字节 | — |

**一句话**：功能本身完整存在（参数、事件、assert、字符串、FUNC 注册项都在），但本机把「这个参数在不在」这件事交给一个**启动期按机型填充的可用性 map**；`PRM_HAITA_is_spot_boost_enabled`（id 0x417，键 0x02CF0417）在这一层被判为不可用，于是所有消费点都直接 `b.eq` 跳过，菜单/按键自然不可达。补丁必须落在**填充该 map 的数据源**上，而该数据源尚未定位。

---

## 1. id 空间基准（anchor）——已独立复算

**OBSERVED**：`.data.rel.ro` 里那张「名字指针数组」的绝对基址 = **0x57FD1A0**。
推导：`VAL_HAITA_setting_timeshift_shooting_timeshift_prohibited_NOT_SET` 字符串 @ `0x4EC8E15` 的 RELATIVE 重定位槽 = `0x57FD1A0 + 0x5793*8`；解得基址 0x57FD1A0。
旁证：`analysis\prm_use.py` 里旧的 `ARRAY = 0x57ED1A0` 恰为 `0x57FD1A0 - 0x10000`，正是本文档开头所述 `.data.rel.ro` 文件偏移差，互相印证。

**OBSERVED**：`PRM_*`、`VAL_*`、`FUNC_*` 三类名字**同处这一个数组**，因此 id 空间是**共享的**（不是 PRM/VAL 两个空间）。
（工具：`analysis\namespace.py`，`py -3 analysis\namespace.py base|dump|find`。）

由此得到的 spot boost 相关 id（工具输出原样，位置即 id）：

```
0x0415 PRM_HAITA_evolved_spot_boost_executable_status
0x0417 PRM_HAITA_is_spot_boost_enabled
0x0a79 PRM_hold_spot_boost_shooting_mode
0x0a7a PRM_toggle_spot_boost_shooting_mode
0x0cb7 PRM_setting_custom_spot_boost_set
0x0cb8 PRM_spot_boost_shooting_mode
0x109e FUNC_hold_spot_boost_shooting
0x109f FUNC_toggle_spot_boost_shooting
0x3007 VAL_HAITA_is_spot_boost_enabled_NOT_SET
0x3008 VAL_HAITA_is_spot_boost_enabled_DISABLED
0x3009 VAL_HAITA_is_spot_boost_enabled_ENABLED
0x578a/0x578b/0x578c VAL_hold_spot_boost_shooting_mode_{OFF,ON,PRM_ALL}
0x578d/0x578e/0x578f VAL_toggle_spot_boost_shooting_mode_{OFF,ON,PRM_ALL}
```

**交叉验证（OBSERVED）**：`analysis\spotboost_tables.txt` 里既有的规则行使用的正是 0x577d–0x5780、0x2fe1–0x2fe5 这些 id，与上面的映射自洽——即 id 空间与既有 rule 表分析口径一致。

---

## 2. 对「`mov w1,#0x459f` 是 PRM id」的证伪

**OBSERVED**：id 0x459f 的名字是

```
0x459f VAL_registration_autofocus_area_contrast_detect_af_90_degrees_set_AUTOFOCUS_AREA_CONTRAST_DETECT_AF_SET_WIDE
```

它是**对焦区域**的 VAL id，与 spot boost 无关。因此 `0x1b31ee0` 附近那条立即数不能用来反解 PRM 数组基址。

**OBSERVED**：PRM id 在代码里并不以裸 imm16 出现，而是拼成 32 位键：
`mov w0,#<id16>; movk w0,#0x2cf,lsl#16` → 键 = `0x02CF0000 | id`（0x2CF = HAITA 参数命名空间）。
实例：`0x2ef9900`（0x416）、`0x2ef9958`（**0x417**）、`0x2f012dc`（0xcb7）、`0x2f01334`（0xcb8）。
这条编码本身就把「PRM id ⇒ 运行期键」的关系钉死了。

---

## 3. 机制层：参数可用性 map（本次最重要的发现）

### 3.1 查询实现（OBSERVED）

```
0x2ec6b78  stp   x29,x30,[sp,#-0x20]!
0x2ec6b7c  mov   x29,sp
0x2ec6b80  add   x1,x29,#0x20
0x2ec6b84  str   w0,[x1,#-4]!        ; key = 0x02CFxxxx
0x2ec6b88  adrp  x0,#0x88d9000       ; 全局 map 对象 0x88d92d8
0x2ec6b8c  add   x0,x0,#0x2d8
0x2ec6b90  bl    0x2ec6b10           ; rbtree 查找：node->key @+0x20, 返回 node+0x28
0x2ec6b94  ldrb  w1,[x0,#0x12]       ; flagA
0x2ec6b98  cbz   w1,0x2ec6ba0
0x2ec6b9c  ldrb  w1,[x0,#0x13]       ; flagB
0x2ec6ba0  mov   w0,w1               ; 返回 = flagA ? flagB : 0
0x2ec6ba4  ldp/ret
```

- `0x2ec6b10` 是 `std::map` 风格的红黑树查找（比较 `[node+0x20]` 与 key，返回 `node+0x28`）；
- 查不到时走 `0x165f1b0`（字符串 `0x3d7c560`，即“表中不存在”的断言/异常路径）；
- **语义 = 「该参数在本机是否存在/可用」**：`flagA && flagB`。

调用点全都是同一模式：`bl 0x2ec6b78; tst w0,#0xff; b.eq <skip>`，即不可用就**整段跳过**（读值、写值、发事件全部不做）。

### 3.2 结论（INFERRED，但很强）

`PRM_HAITA_is_spot_boost_enabled`（0x417）与 `PRM_hold/toggle_spot_boost_shooting_mode`（0xa79/0xa7a）的可用性由 **启动期构建的这张 map** 决定；本机上其中至少一项判为 0，于是：

1. `sequence_set_boost_shooting` 路径的读/写被跳过；
2. 自定义键菜单项的标志位无从变 1；
3. 按键 -> 事件 -> handler（`0x1b31da8` / `0x1af5c10`）这条链永远拿不到输入。

这解释了「代码在、字符串在、assert 在、FUNC 注册表也在，但功能不可达」。

### 3.3 填充侧（尚未定位，UNKNOWN）

对 `0x88d92d8` / `0x88d9308` 做 ADRP+ADD 交叉引用，写侧候选共 10+10 处，其中：

- `0x2f39b0c` / `0x2f39b40` 一带是**清空**循环（`strb wzr,[node,#0x3a]` + `bl 0x2e9143c`），不是插入；
- `0x2e915c4` / `0x2e91608` 一带最可能是 init/insert（`0x2e9143c` 为 erase，插入应在同一模块内）；
- 其余 `0x170d948`、`0x2f62f5c`、`0x2f9bc78`、`0x2fc4260` 为查询/消费者。

**UNKNOWN**：插入时的 `(key, flagA, flagB)` 来源（静态描述数组？由 CP/EEPROM 读回的能力位？）。这一步没做完，所以没有可信补丁字节。

---

## 4. 自定义键菜单校验函数（0x1b6e1c4）——记录首字段是 PRM id

**OBSERVED**（反汇编）：

```
0x1b6e1c4  stp x29,x30,[sp,#-0x40]! ; x0=this, w1=menu kind, x2=record*
...
0x1b6e1d4  ldr  w0,[x2]             ; record->field0
0x1b6e1e8  bl   0x1b6de70           ; field0 -> 内部 id
0x1b6e1ec  cmp  w0,#0x1a6           ; 特例：0x1a6 = PRM_setting_s_q_exposure_mode
0x1b6e1f4  ldr  x1,[x21]; ldr x2,[x1,#0x478]; blr x2   ; 仅 id==0x1a6 时走
0x1b6e208  ldr  x2,[x1,#0xaf8]; blr x2                 ; 通用可用性判定 -> w19
0x1b6e220  cbz  w19, <return 0>
0x1b6e224  ldr  x1,[x0,#0x4e0]; blr x1                 ; 取 index
0x1b6e234  sub  w1,w22,#8 ; cmp w1,#0xd ; b.hi <fail>   ; w22 = w1(menu kind)
0x1b6e240  adrp x3,#0x3dcc000 ; add x3,x3,#0xe28        ; 跳转表 0x3dcce28
0x1b6e24c  mov  x2,#0xe                                  ; 记录 stride = 14
0x1b6e250  madd x0,x0,x2,x20                             ; x20 = x2 = 记录基址
0x1b6e254  ldrb w1,[x3,w1,uxtw] ; br x1
0x1b6e264  ldrb w19,[x0,#4]      ; ... 各分支读 [x0,#4..#0x11]
```

要点：

- **记录首字段是 PRM id**（0x1a6 特例直接指向 `PRM_setting_s_q_exposure_mode`，这是我们判定字段语义的硬证据）；
- 14 个分支读取记录内偏移 `4,5,6,7,8,9,0xa,0xb,0xc,0xe,0xd,0xf,0x10,0x11`（与 `w1 = menu_kind - 8`，menu_kind ∈ 8..0x15 对应）；
- 该函数 **0 个直接 BL 调用者**（`analysis\blmap.py callers 0x1b6e1c4` → 0），说明它是**虚函数**，通过 vtable 调用 → 调用者与记录数组未定位（UNKNOWN）。

一个一致的解释（INFERRED）：这张记录表就是「每个可分配给自定义键的功能 = 一条记录 {PRM id, 各菜单类别可用位}」，其可用位仍由 §3 的参数可用性派生——于是两条线索（菜单记录 vs 参数可用性）收敛到同一处闸门。

---

## 5. 阴性结果（重要，避免后人重复劳动）

### 5.1 规则表里没有把 spot boost 关掉的行走（OBSERVED）

全文件搜 `u32 == 0x3008`（`VAL_HAITA_is_spot_boost_enabled_DISABLED`）只有 **5 处**，全部是「小整数 ⇄ VAL id」映射或名字哈希表，**没有** 任何一处处在 12 字节 `{kind, from, to}` 规则行里：

| 位置 | 形态 | 含义 |
| --- | --- | --- |
| `0x41e78b8` | 8 字节 `{0x12,0x3007} {0x13,0x3008} {0x14,0x3009}` | 内部枚举 → VAL id 翻译 |
| `0x4b41da0` | 8 字节 `{0,0x3007} {0,0x3008} …` | 同一类翻译（默认值 0） |
| `0x505bb18` | 16 字节 `{0x20,0x642f6,1,0x3008}` | 记录表，非规则行 |
| `0x57fb3c8`（.data.rel.ro） | 16 字节 `{0, obj_ptr, 0, 0x3008}` | 参数对象登记表 |
| `0x58503a8` | 16 字节 `{0xd, name_ptr, 0, 0x3008}` | 名字哈希表 |

`analysis\spotboost_tables.txt` 中真正含 spot boost id 的规则行，只改写 `evolved_spot_boost_*` / `*_spot_boost_shooting_mode_*` 的值（kind 0/1/3），**没有** `to = 0x3008` 的行。

### 5.2 FUNC 注册表把两条 spot boost 功能都标成“可用”（OBSERVED）

- `0x41dbe00`：8 字节记录 `{u32 text_id, u32 func_id}`，func id 递增：
  `0x109d→0x4701`、**`0x109e→0x4704`**、**`0x109f→0x40f8`**、`0x10a0→0x4924`。
  原始字节（`0x41dbf30`）：`04 47 00 00 9e 10 00 00 f8 40 00 00 9f 10 00 00`。
- `0x41eb070`：8 字节记录 `{u32 flag, u32 func_id}`；`0x109a..0x10a4` → **1**，`0x10bb..0x10c5` → **0**，`0x10dc+` → 1。
  原始字节（`0x41eb0a0`）：`01 00 00 00 9e 10 00 00 01 00 00 00 9f 10 00 00`。

→ **这两张表都不是闸门**（spot boost 在其中是“存在且=1”）。

### 5.3 UI 字符串分布（OBSERVED）

英文 `Cnt Sht Spd Bst Hold` / `Cnt Sht Spd Bst Toggle` / `Cnt Shoot Speed Boost` **不在** `share_app_string_english.uxc`，只出现在：

```
share_app_string_english_f.uxc
share_app_string_english_func_j.uxc
share_app_string_english_horizontal.uxc
share_app_string_english_vertical.uxc
```

即按钮/菜单文案资源是齐的（`_f` = 功能名一组、`_func_j` = 功能名一组、横/竖屏各一套），进一步说明「不是缺文案」。

---

## 6. 补丁结论

### 6.1 能给的：诊断用“钝刀”补丁（不推荐用于成品）

如果只是要**验证** §3 的 map 就是闸门，可让可用性查询恒真：

| 项 | 值 |
| --- | --- |
| 文件偏移 | `0x2EC6B94`（`.text`，偏移==虚拟地址） |
| 原字节（12 B） | `01 48 40 39  41 00 00 34  01 4c 40 39` （`ldrb w1,[x0,#0x12]; cbz w1,+8; ldrb w1,[x0,#0x13]`） |
| 新字节 | `21 00 80 52  1f 20 03 d5  1f 20 03 d5` （`mov w1,#1; nop; nop`） |
| 语义 | `is_param_available(key)` 恒返回 1 |
| 风险 | **极高**：所有参数查询都变“可用”，会放进大量本机不支持的参数，可能导致启动异常/写入非法值。仅作一次性验证，勿做成品。 |

### 6.2 应该打的补丁：UNKNOWN

真正的最小改动应当是「只让 `0x02CF0417`（及 `0x02CF0A79`/`0x02CF0A7A`）这一项在 map 里可用」，落点在其**初值来源**：

- 若初值来自 `.rodata` 的静态描述数组（形如 `{u32 prm_id, u8 flagA, u8 flagB, …}`），则改那一条的 flag 字节（1–2 字节）；
- 若初值来自 CP/EEPROM 的能力位，则 appFw 侧改不动，需要在 CP 侧或读取处打补丁。

本次**没有**把这两者区分开，因此不给具体字节——按「宁可交阴性，不猜字节」的要求，这里明确标 UNKNOWN。

---

## 7. 下一条最短路径（按收益排序，均带具体地址）

1. **定位 map 插入点**：反汇编 `0x2e91500–0x2e91700` 与 `0x2f39a00–0x2f39c00` 两片（对 `0x88d92d8`/`0x88d9308` 有 ADRP+ADD 的写侧）。找到 `insert(key, value)` 的调用者后，看 key 从哪来：
   - 若来自循环遍历一个静态数组 → 该数组就是机型能力表，直接在里面找 `0x417`/`0xa79`/`0xa7a`（注意：直接全文件搜 0x417 会被 `0x0417xxxx` 地址淹没，必须限定「记录形如 {u32 id ≤ 0x2000, u8…}」+ 相邻项递增）。
2. **验证 §4 的记录表**：`0x1b6e1c4` 是虚函数，先从 `.data.rel.ro` 的 RELATIVE 重定位里找 addend == `0x1b6e1c4` 的槽（`analysis\xrefs.py`/`elfutil.slots_for`），得到 vtable → 同表相邻槽是同类方法 → 反查该 vtable 的 ADRP+ADD 构造者，即可拿到记录数组指针来源。
3. **确认 handler 链是否另有闸门**：`0x1b31da8`（TOGGLE）与 `0x1af5c10`（HOLD）入口都有一次 `bl 0x1798734; cmp w0,#1; b.eq <正常路径>`（不相等则走 assert 打印 + `mov w0,#0x86a0; movk #1` = 100000 的异常分支）。若 §3 补齐后仍不触发，第二个闸门就在这里——`0x1798734` 的返回值语义值得单独确认（可能是「事件分发已就绪」而非能力位）。

---

## 8. 复现脚本（本次新增，均在 `analysis\`，未改 `a7c2-dat-tools`/`References`）

| 脚本 | 用途 |
| --- | --- |
| `namespace.py` | 名字指针数组基址求解 + `id ⇄ 名字` 双向查询（`base`/`dump`/`id`/`find`） |
| `blmap.py` | 全 `.text` 直接 BL/B 调用图，`build` 一次后 `callers`/`at` 秒查 |
| `blxref.py` | 单目标 BL 交叉引用（`blmap.py` 的轻量版） |
| `xrefs.py` | ADRP+ADD/LDR 数据引用批量查询 |
| `find_u32.py` | 常量在整文件中的出现位置 + 上下文（用于找描述表） |
| `registry.py` | 名字哈希表（`{u32 hash, u32 id}`）探查，id 空间的旁证 |

依赖：`capstone`、`pyelftools` 已在本机 Python 3.15 安装（原环境缺，已 `pip install`，离线 wheel 缓存可用）。

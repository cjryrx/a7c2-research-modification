# bind_button — 给索尼机身按键改绑一个功能（ILCE-7CM2 实测）

> **一句话**：自定义键的功能绑定是 **AP 属性里的一条 4 字节设置**（组 `0x02CF`，
> 槽位 `0x0404–0x041F`，值为小端「紧凑功能 id」）。写它、`saveBackup(0x02CF)`、
> 断电重启，按键就换成新功能 —— **不刷固件、不改 DAT、不写分区**。

> **状态（请先读）**：绑定机制与写路径已在真机端到端验证；但
> **「连拍速度提升（Cnt Sht Spd Bst，保持/切换）」的紧凑 id 仍然未知**。
> 本工具因此把 id 作为参数（`--function-id`），代码与文档里**没有任何猜测值**。
> 在拿到那个 id 之前，你只能用已知 id 做验证性改绑。

本仓库**不包含**任何索尼固件、固件提取物、分区转储、抓包或序列号：
只有源码、文档和一份 MIT 许可的 Sony-PMCA-RE 子集。

---

## 1. 它做什么 / 不做什么

| | 内容 |
| --- | --- |
| 做 | 读 `0x02CF` 组的按键槽位；找出你改动的按键对应哪个槽位；把指定紧凑 id 写进槽位并保存；用回执原样写回。 |
| 不做 | 不刷固件、不改 `appFw.so`、不改 DAT/BIN、不写相机分区或文件系统；不发送文件控制、内存转储或固件更新类命令；不读取/记录序列号。 |
| 相机侧唯一效果 | 一条 4 字节 AP 属性 + 一次 `saveBackup(0x02CF)`。 |
| 生效条件 | **机身必须断电重启**（app 只在启动时读取绑定）。 |

## 2. 工作原理

```
  bind --slot 0x041B --function-id 0x300
        │
        ├─ 读 0x02CF041B            → 22010000   (0x122 对焦模式)
        ├─ 校验：长度必须仍是 4 字节  ← 不符直接拒绝，不写
        ├─ 先把旧值写进 receipts/*.json
        ├─ 写 0x02CF041B = 00030000 (0x300 APS-C/全幅选择)
        ├─ 回读 == 新值？
        ├─ saveBackup(0x02CF)
        └─ 再回读 == 新值？  → 提示「power-cycle the camera to apply」
                                  ↓
                        关机 → 开机 → app 读取槽位 → AF-ON 变成 APS-C/全幅选择
```

* 属性键 = `组 << 16 | index`，本工具只碰组 `0x02CF`。
* 槽位值 = 4 字节**小端**紧凑 id（`0x300` → `00 03 00 00`）。
* 已验证：`0x041B` = AF-ON，`0x041C` = MOVIE。
* 证据、差分数据与失败过程见 [`docs/DESIGN.zh-CN.md`](docs/DESIGN.zh-CN.md) 与
  [`docs/RUNTIME-SESSION.zh-CN.md`](docs/RUNTIME-SESSION.zh-CN.md)。

## 3. 安全说明（这一段最重要）

### 3.1 工具自身的硬性守卫

1. **长度守卫**：写入前先读当前值，新值长度必须与当前长度**完全一致**，否则拒绝。
   属性记录是整条替换的，长度不符会改写记录边界；这是唯一可能造成结构性损坏的操作，
   所以它在代码里是硬约束，`--force` 也不能绕过。
2. **范围限制**：只读写 `0x02CF` 组；`bind` 只允许 `0x0400–0x0430`，
   超出直接拒绝（同样不受 `--force` 影响）。
3. **旧值先落盘**：`bind` 在动相机之前就把旧值写成 JSON 回执（默认 `receipts/`）。
   中途任何一步失败，回执都是完好的，`restore --receipt` 可以原样写回。
4. **失败即停**：写后回读不一致、save 后回读不一致，都直接报错并保留回执，不重试、不猜。
5. **`--force` 只放宽证据强度**：允许写「绑定区之外但仍在扫描范围内」的槽位，
   或当前值为 4 个零字节（空绑定）的槽位。它不放宽长度与范围这两条。
6. **不读序列号**：`ProductInfo` 只校验长度（88 字节），内容既不保存也不打印。

### 3.2 你必须接受的风险（不是工具能消除的）

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| **USB 服务会话本身会失稳** | 已记录：连续几次服务会话后，机身可能 USB 超时、自行重启，或停在服务身份 `054c:096f` | 一次会话只做一件小事；失败就拔线/取电池约 30 秒再试 |
| **按键绑成别的功能** | 写错槽位或写错 id，按该键会执行别的功能 | 先 `list` / `discover` 确认槽位；保留回执，`restore` 写回 |
| **写入的 id 可能不被接收** | app 的功能分派是否有白名单**未验证**；未知 id 可能按键无反应 | 先用已知 id（如 `0x305`）在已验证槽位做对照实验 |
| **菜单里仍然看不到该功能** | 本工具不改菜单数据，只改绑定 | 这是设计选择：改菜单要动固件资源 |
| **每次改绑都要重启机身** | app 只在启动时读取绑定 | 接受它；这也是「写入后行为不变」的正常现象 |

**只在你自己拥有的机身上使用。** 作者不对设备损坏、数据丢失或保修失效负责。

### 3.3 这个仓库里没有固件

没有 `*.DAT`、`*.BIN`、`appFw.so`、`nflasha*`、分区镜像、抓包或序列号。
唯一的第三方代码是 Sony-PMCA-RE 的 **MIT** 许可 Python 子集
（`bind_button/pmca/`，见其中的 `PMCA_LICENSE.txt`），用于 USB 认证与 Senser 协议封装。

## 4. 安装

需要 Python 3.9+（在 3.15 上开发与测试）、一根能传数据的 USB 线。

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt`：`pyusb`、`libusb-package`（Windows 的 libusb DLL）、`pycryptodomex`
（PMCA 的 Senser 认证用）。

### 4.1 Windows：必须先给**两个** USB 身份绑 WinUSB

libusb 在 Windows 上需要设备被绑定到 WinUSB（或 libusbK 这类兼容驱动），而机身在会话过程中会换 USB 身份：

| 身份 | 用途 |
| --- | --- |
| `054c:0e8a` | 海量存储（刚插线时） |
| `054c:0336` | Senser 服务（认证后机身自己切过去） |

两个身份**各自**需要一次绑定（用 [Zadig](https://zadig.akeo.ie/)：Options → List All Devices →
选中对应设备 → Replace Driver 为 WinUSB）：

1. 相机设为「电脑/海量存储」并插线 → Zadig 里选 `ILCE-7CM2 (0E8A)` → 绑 WinUSB；
2. 跑一次 `py -m bind_button.cli list`：机身会切到服务身份，工具会停在"等待服务身份"；
3. 这时在 Zadig 里选新出现的 `0336` 设备（名称类似 *A7C II service mode*）→ 同样绑 WinUSB；
4. 再跑一次工具即可。

**副作用**：绑 WinUSB 后 Windows 不再把相机当磁盘，官方软件的传输也会失效；
要恢复，在设备管理器里卸载该设备并重新插拔，或重装索尼驱动。

> 说明：本仓库**不附带** WinUSB INF 文件；上面两步是按两个 USB 身份和已验证的会话流程写出来的，
> 我们只在**已经绑好**的机器上验证过工具本身，没有在全新 Windows 上从零走过一遍。

### 4.2 Linux / macOS

用系统 libusb 即可，但需要设备访问权限（通常 root）：

```bash
sudo ./.venv/bin/python -m bind_button.cli list
```

Linux 上相机卷不能被挂载（挂载会占住内核驱动，第一次认证会超时）。
工具会检测并提示，不会自动卸载。

## 5. 用法

所有命令从仓库根目录运行（`bind_button` 包就在当前目录）。

### 5.1 看已知的紧凑 id（离线，不碰相机）

```bat
py -m bind_button.cli functions
```

### 5.2 读取并列出槽位（只读）

```bat
py -m bind_button.cli list
```

输出形如（值、id 与功能名逐列对齐；未知 id 的功能列是 `-`）：

```
idx     property     value                      compact id   function                           note
0x0404  0x02CF0404   5c030000                   0x0000035C   -                                  custom-key slot
...
0x041B  0x02CF041B   22010000                   0x00000122   Focus Mode                         custom-key slot, AF-ON (verified)
0x041C  0x02CF041C   00030000                   0x00000300   APS-C/Full-frame select            custom-key slot, MOVIE (verified)
```

### 5.3 找出「我的按键」是哪个槽位（只读）

方式 A（一次会话内完成，需要相机菜单在连着线时仍可操作）：

```bat
py -m bind_button.cli discover
```

它会先扫描 `0x0400–0x0430`，然后提示你**在机身上只改一个自定义键的分配**并回车；
再扫一次，打印变动的槽位。

方式 B（两次会话，适合「菜单在连线时打不开」或「改动要重启才落盘」的情况）：

```bat
py -m bind_button.cli discover --snapshot snap-before.json
:: 改机身菜单，断电重启
py -m bind_button.cli discover --compare snap-before.json
```

### 5.4 绑定一个功能（唯一会写的日常命令）

```bat
py -m bind_button.cli bind --slot 0x041B --function-id 0x305
```

`--slot` 是槽位 index，`--function-id` 是**紧凑 id**（十进制或 `0x` 十六进制都行）。
命令会依次：读旧值 → 校验长度 → 写回执 → 写入 → 回读 → `saveBackup(0x02CF)` → 再回读，
最后打印：

```
power-cycle the camera to apply: turn it OFF, then ON. ...
```

**然后真的把机身关机再开机**，按键才会变。

把「连拍速度提升」绑到你自己的按键（拿到 id 之后）就是同一条命令，只换槽位：

```bat
py -m bind_button.cli bind --slot 0x041D --function-id <你测到的紧凑 id>
```

其中 `0x041D` 要换成 `discover` 报告的那个槽位。如果 `discover` 报告的槽位在
`0x0404–0x041F` **之外**，工具会要求加 `--force` —— 那说明该槽位的证据更弱，
先确认它是绑定槽再写。

### 5.5 回退

```bat
py -m bind_button.cli restore --receipt "receipts\bind-0x041b-20261026T131500Z.json"
```

写回回执里的旧值、保存、回读，再提示重启。`restore` 自己也会写一份新的回执
（记录它覆盖掉的值），所以回退本身也是可回退的。

### 5.6 退出码

| 码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 2 | 守卫拒绝（范围/长度/空槽位/回执格式），或参数错误 —— **相机未被写** |
| 1 | 会话/属性操作失败（插线、驱动、认证、回读不一致） |
| 130 | 用户中断 |

## 6. 已知的紧凑 id（截至本仓库发布）

| 紧凑 id | 功能 | 依据 |
| --- | --- | --- |
| `0x122` | Focus Mode（对焦模式） | AF-ON 改菜单后槽位值变化 |
| `0x300` | APS-C/Full-frame select（APS-C/全幅选择） | **端到端**：写进 `0x041B` + 重启，AF-ON 真的执行它 |
| `0x305` | Toggle Silent Mode（切换静音模式） | MOVIE 改菜单后槽位值变化 |
| `0x9C3` | Tracking On + Center Area AF（跟踪开启 + 中央区域 AF） | AF-ON 的旧绑定 |

## 7. 仍然未知

* **「连拍速度提升」的紧凑 id** —— 唯一的关键缺口。已知的离线锚点是
  `EVENT_FUNC_CUSTOM_SPOT_BOOST_HOLD_ON=0xb947`、`..._TOGGLE_ON=0xbaa5`，
  但它们与紧凑 id 之间没有找到线性关系，**不能**据此推算。
* **功能分派是否接受菜单里没有的 id** —— 未验证。0x300 的端到端实验只覆盖菜单内已有功能。
* **每个槽位对应哪个物理按键** —— 只有 `0x041B`/`0x041C` 验证过；其余请用 `discover`。
* **`0x0420–0x0430` 是否也是绑定槽** —— 未知，所以界外写入要 `--force`。
* **其他机型** —— 未验证；本仓库只对 ILCE-7CM2 负责。

## 8. 目录结构

```
README.zh-CN.md
README.md
requirements.txt
bind_button/
  __init__.py
  session.py        USB 会话（pyusb + WinUSB/POSIX），懒加载，无相机不导入 pyusb
  properties.py     AP 属性读/写/保存 + 长度守卫（纯逻辑，可离线测）
  buttons.py        槽位表、已知紧凑 id、回执/快照记录（纯逻辑）
  cli.py            argparse 入口：functions/list/discover/bind/restore
  pmca/             Sony-PMCA-RE 的 MIT 子集（usb/sony.py 等）+ PMCA_LICENSE.txt
docs/
  DESIGN.zh-CN.md           为什么是设置写入；证据表；未验证项
  RUNTIME-SESSION.zh-CN.md  真机会话研究日志（搬迁版，已删去 fork 专有路径）
tests/
  test_buttons.py           槽位表、编码、回执/快照格式（无硬件）
  test_properties.py        属性编解码与守卫（假 transport，无硬件）
```

## 9. 离线测试

```bat
py -m unittest discover -s tests -v
```

全部用例都不需要相机、不需要 pyusb、不会打开 USB。

## 10. 证据与许可

* 研究发现与真机会话记录：仓库内 `docs/`；原始工作来自同一项目的 `a7c2-re` 研究仓库。
* `bind_button/pmca/` 是 [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE)（作者 ma1co）
  的 **MIT** 许可子集，版权与许可原文见 `bind_button/pmca/PMCA_LICENSE.txt`。
* 索尼、ILCE、α 等为索尼公司商标；本项目与索尼无关联，未获得其授权或支持。
* 本仓库自有代码的许可：未单独声明（保留所有权利）。如需再分发，请自行确认。

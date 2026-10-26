# 研究记录 / research notes

这三份报告是「连拍加速按键（索尼 `Cnt Shoot Speed Boost` / 連写速度ブースト）」
补丁环节的离线分析记录。它们**只包含地址、哈希与分析结论，不包含任何索尼固件字节**。

| 文件 | 内容 |
| --- | --- |
| [SPOTBOOST-OFFLINE.zh-CN.md](SPOTBOOST-OFFLINE.zh-CN.md) | 总览：功能在 2.01 里的全部可见痕迹、已排除的方向、留下的三条线索、复现用工具 |
| [SPOTBOOST-GATE.zh-CN.md](SPOTBOOST-GATE.zh-CN.md) | 门控定位：id 空间基准、参数可用性红黑树 map、`is_spot_boost_enabled` 键 `0x02CF0417`、自定义键校验函数 |
| [A7M5-vs-A7C2-spot-boost.md](A7M5-vs-A7C2-spot-boost.md) | 跨机型差分可行性：另一机型的官方包能否解开（结论：密钥在 updater、不随 DAT 分发，因此做不到） |

## 判读约定

每份报告都标注 **OBSERVED（直接读到）/ INFERRED（推理）/ UNKNOWN（未确定）**。
三份报告的共同结论是：**功能完整存在，但被运行期的参数可用性判定挡住；承载该判定的
静态数据源尚未定位，因此没有可信到字节级的启用补丁。**

⚠️ `SPOTBOOST-GATE.zh-CN.md` §6 里那条「让参数可用性查询恒为真」的片段是**诊断用**的，
它会把本机所有不支持的参数一次性放开。**不要把它写进任何固件包。**

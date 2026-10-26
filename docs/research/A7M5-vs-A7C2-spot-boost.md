# A7M5(伪7 V?) vs A7C II锛氳繛鎷嶅姞閫?/ Spot Boost 闂ㄦ帶瀵规瘮鐮旂┒

浼氳瘽鏃堕棿锛?026-10-26锛屽叏绋嬬绾匡紝鏈帴瑙︾浉鏈恒€?宸ヤ欢鐩綍锛歚analysis\a7m5\`锛堣剼鏈?+ 涓棿浜х墿锛夈€?*鏈慨鏀?* `a7c2-dat-tools\`銆?
---

## 0. 缁撹鎽樿锛堝厛鐪嬭繖閲岋級

1. **`a7m5-dat\BODYDATA.DAT` 鏄竴涓粨鏋勫悎娉曠殑绱㈠凹鏇存柊鍖?*锛氬灞?TLV 閾俱€丗DAT銆丏END 鍏ㄩ儴瀵瑰緱涓婏紝
   鏂囦欢鍐呰褰曠殑 DEND CRC-32锛坄cf78ac68`锛変笌瀹炵畻鍊间竴鑷?鈫?**鍖呮槸瀹屾暣鐨勩€佹湭琚埅鏂?绡℃敼**锛圤BSERVED锛夈€?2. **浣?`a7c2dat.container.parse()` 涓嶈兘鐩存帴瑙ｆ瀽瀹?*锛氬嚑浣曟柇瑷€澶辫触
   `(fdat_size 鈭?0x110) % 1024 = 128 鈮?0`銆傝繖鏄?*鏍煎紡灞傞潰**鐨勭湡瀹炲樊寮傦紝涓嶆槸鏂囦欢鎹熷潖銆?3. **瀹冪敤 A7C II 鐨勫瘑閽ヨВ涓嶅紑**锛圗CB / CBC / 鎹?IV / 鎹?key 缁勫悎閮借瘯杩囷紝鍏ㄩ儴鍨冨溇锛夈€?   A7C II 鐨勪袱鎶婂瘑閽ヤ篃涓嶅湪浠讳綍宸叉娊鍑虹殑鍒嗗尯闀滃儚閲岋紙瀹冧滑鍙瓨鍦ㄤ簬 updater锛屽嵆 nflasha1锛岃€?nflasha1 涓嶉殢 DAT 鍒嗗彂锛夈€?   鈫?**鏃犳硶鍙栧嚭璇ュ寘鐨?`appFw.so` / `CPAPP-B.BIN`**锛屽洜姝?*浠诲姟涔︾ 3銆? 椤硅姹傜殑"A7V 鈫?A7C II 鍙屽悜瀵规瘮"鏈細璇濆仛涓嶄簡**锛堢‖闃诲锛岃 搂2锛夈€?4. 鏈哄瀷鍒よ锛氳鍖呯殑 UDID 鏄?鍙楁敮鎸佹満鍨嬬殑 USB PID 鐧藉悕鍗?銆侫7C II 鐨?17 椤归噷鍚畠鑷繁鐨?`0x0E8A`锛?   A7M5 鍖呭彧鏈?12 椤癸紝**鍒犳帀浜?0x0E72鈥?x0E8E 鏁存锛堝惈 0x0E8A锛?*锛屾柊澧?`0x0F4F`銆?   鈫?**"涓嶆槸 A7C II 鍖? = 楂樼疆淇?*锛?*"鏄?ILCE-7M5 / 伪7 V" = 涓庤瘉鎹竴鑷翠絾鏈璇佹槑**锛堟棤鏄庢枃鏈哄瀷涓插彲璇伙級銆?5. A7C II 渚э紙鍙В瀵嗛偅涓€鍗婏級宸插畬鎴愶細鍊?id 绌洪棿**鐙珛楠岃瘉**锛堟暟缁勪笅鏍?== id锛屽熀鍧€鎭颁负 0锛夛紝
   249 涓繛鎷嶅姞閫熷€?id銆?3 寮犳秹鍙婂畠鐨勮鍒欒〃鍏ㄩ儴鏋氫妇銆?   **鍏抽敭璐熺粨鏋滐細娌℃湁浠讳綍涓€鏉¤鍒欒鎶婅繛鎷嶅姞閫熺殑鍊兼敼鍐欐垚 OFF / DISABLED / NOT_SET銆?*
   涔熷氨鏄"鍍忛鎷嶆憚閭ｆ牱鐢ㄤ竴寮犲己鍒惰〃鍘嬩綇"鐨勫亣璁撅紝鍦?A7C II 涓?*琚帓闄?*锛圤BSERVED锛岃 搂5锛夈€?6. 鍥犳娌℃湁鍙洿鎺ョ粰鍑虹殑"涓€琛岃ˉ涓?銆備笅闈㈢粰鐨勬槸**宸插畾浣嶇殑缁撴瀯 + 3 涓?gate 鍊欓€?+ 鏄庣‘鐨勭疆淇″害**銆?
---

## 1. A7M5 DAT 瀹瑰櫒閴村畾

### 1.1 閫?chunk锛坄analysis\a7m5\probe.py`锛?
| 鍋忕Щ | 闀垮害 | 鏍囩 | 鍐呭 |
| --- | --- | --- | --- |
| 0x000000 | 8 | magic | `89 55 46 55 0D 0A 1A 0A` 鉁?涓?A7C II 鐩稿悓 |
| 0x000008 | 8+4 | DATV | `01 00 00 00` 鈫?鏁版嵁鏍煎紡鐗堟湰 1锛?*涓?A7C II 鐩稿悓**锛?|
| 0x000014 | 8+4 | PROV | `01 00 00 00` 鈫?渚涘簲鍟嗗彿 1锛?*涓?A7C II 鐩稿悓**锛?|
| 0x000020 | 8+100 | UDID | `00 00 00 0C` + 12 脳 8 B锛圓7C II 鏄?8+140 / 17 椤癸級 |
| 0x00008C | 8+376,540,560 | FDAT | 鍔犲瘑杞借嵎 |
| 0x16718E24 | 8+4 | DEND | CRC-32 璁板綍鍊?`CF78AC68` |

* 鏂囦欢鎬婚暱 376,540,720锛沗0x94 + 376,540,560 = 0x16718E24`锛屽啀 +12 鎭板ソ鍒版枃浠跺熬 鈫?**鏃犲熬闅忔暟鎹?*銆?* 鎴戝崟鐙畻浜?DEND 鐨?CRC-32锛堣鐩栧墠 `size鈭?2` 瀛楄妭锛夛細**璁板綍鍊?== 璁＄畻鍊?== 0xCF78AC68 鈫?閫氳繃**銆?* 瀵圭収锛欰7C II 瀹樻柟鍖?CRC 璁板綍 `0xD191286B`锛屽疄绠楃浉鍚?鈫?涓や釜鍖呴兘閫氳繃鍚屼竴濂楀畬鏁存€ф鏌ャ€?
### 1.2 涓轰粈涔?`a7c2dat.container.parse()` 浼氬け璐?
`container.py` 鐨勭‖鏂█锛?
```python
if fdat_size <= TRAILER or (fdat_size - TRAILER) % BLOCK:
    raise DatError("FDAT cipher geometry is not a whole number of blocks")
```

* A7C II锛歚(1,139,929,360 鈭?0x110) / 1024 = 1,113,212` 鏁撮櫎 鉁?* A7M5 锛歚(  376,540,560 鈭?0x110) = 376,540,288 = 1024 脳 367,715 + 128` 鉁?鈫?**鎶涘紓甯革紝鍦ㄦ涔嬪墠灏遍€€鍑?*锛圖END CRC 杩樻病璧板埌锛?
鑳芥暣闄ょ殑涓ょ鑷唇瑙ｉ噴锛?*INFERRED**锛屾棤娉曠敤瀵嗛挜楠岃瘉锛夛細

| 瑙ｉ噴 | 鏁板瓧 | 璇存槑 |
| --- | --- | --- |
| A. trailer 鐢?0x110 澧炲ぇ鍒?0x190(400) | `376,540,560 鈭?400 = 376,540,160 = 1024 脳 367,715` | 鎭板ソ鏁撮櫎锛涙柊涓€浠ｅ寘鍔犱簡 128 B 绛惧悕瀛楁 |
| B. FDAT 鍓嶆湁 128 B 鍓嶇紑锛宼railer 浠?0x110 | `376,540,560 鈭?272 鈭?128` 鍚屾牱 = 376,540,160 | 渚嬪鏂板鐨勫寘绾у厓鏁版嵁鍧?|

涓ょ瑙ｉ噴鐨勬€诲潡鏁伴兘鏄?367,715锛屾棤娉曚粎鍑暱搴﹀尯鍒嗐€?*UNKNOWN**銆?
### 1.3 涓?A7C II 鐨勫鍣ㄧ骇宸紓姹囨€?
| 椤?| A7C II 2.01 | a7m5-dat |
| --- | --- | --- |
| 鏂囦欢澶у皬 | 1,139,929,560 | 376,540,720 |
| magic / DATV / PROV | `\x89UFU..` / 1 / 1 | **瀹屽叏鐩稿悓** |
| UDID 璐熻浇 | 140 B / 17 椤?| 100 B / 12 椤?|
| FDAT 闀垮害 | 1,139,929,360 | 376,540,560 |
| 鍧楀嚑浣?| 1024 B 鍧楋紝trailer 0x110 | 涓嶆暣闄わ紝闇€ 400 B trailer 鎴?128 B 鍓嶇紑 |
| DEND CRC | 閫氳繃 | 閫氳繃 |

鈫?**鍚屼竴涓鍣ㄥ鏃忋€佸悓涓€ DATV/PROV 浠ｅ彿銆佷笉鍚屼唬/涓嶅悓鏈哄瀷鐨勫叿浣撳竷灞€銆?*

---

## 2. 瑙ｅ瘑灏濊瘯锛堥€愭潯锛屽叏閮ㄥけ璐ワ級

澶嶇敤 A7C II 鐨勫瘑閽ワ細
`ECB = e3b0c44298fc1c149afbf4c8996fb924`锛? SHA-256("") 鍓?16 B锛夈€?`CBC = 434589432d319010f1132727353286ce4d7ede8b9c4f7217a0e0226e0f0edc69`銆?鑴氭湰锛歚analysis\a7m5\trykeys.py`銆?
| 鍋囪 | 缁撴灉 |
| --- | --- |
| 鍓?512 B 鐢?ECB key锛圓7C II 鏂规锛夛紝FDAT+0x00 | 鍨冨溇锛堝鐓э細A7C II 鍚屼綅缃嚭 `7b a3 fc 03 "UDTRFIRM"鈥锛?|
| 鍚屼笂锛孎DAT+0x80锛?28 B 鍓嶇紑鍋囪锛?| 鍨冨溇 |
| 鍚屼笂锛孎DAT+0x190锛?00 B 鍓嶇紑鍋囪锛?| 鍨冨溇 |
| 鍏ㄦ祦 CBC锛宬ey=CBC锛孖V=trailer[:16] | 鍨冨溇 |
| 鍏ㄦ祦 CBC锛宬ey=trailer[:32]锛孖V=trailer[:16] | 鍨冨溇 |
| AES-256-ECB 鐢?CBC key 瑙ｅ墠 512 B | 鍨冨溇 |
| AES-128-ECB锛宬ey=trailer[:16] | 鍨冨溇 |

瀵嗛挜鏄惁鍦ㄥ凡鎶藉嚭鐨勯暅鍍忛噷锛燂紙`analysis\a7m5\scan_keys.py`锛屽 appFw.so / CPAPP-B.BIN /
CPIMG.DAT / DGU / DMMCFG / MIS / SYSSOUND / nflasha15 / nflasha5 / nflasha8 鍏ㄦ枃鎼滅储锛?
* 涓ゆ妸瀵嗛挜 **鍧囨湭鍑虹幇**锛?* 鍞竴鐨?鍛戒腑"鏄?`SHA-256("")` 鍏?32 B 甯搁噺锛?x231ea428@nflasha15銆?x46e590@nflasha5锛夊拰
  `SHA-1("")` 甯搁噺 鈥斺€?閮芥槸鍝堝笇鍗犱綅鍊硷紝涓嶆槸 DAT 瀵嗛挜銆?* 涓?`docs\DAT-FORMAT.zh-CN.md` 鐨勮鏄庝竴鑷达細瀵嗛挜纭紪鐮佸湪 **updater**锛坣flasha1锛夐噷锛岃€?nflasha1 涓嶅湪 DAT 鍐呫€?
**缁撹锛圤BSERVED锛?*锛欰7M5 鍖呬娇鐢ㄥ彟涓€浠ｅ瘑閽ワ紙A7C II 鐨?cipher 浠ｅ彿鏄?`CXD90057_k8`锛岃
`BODYDATA_FL23_200_manifest.json`锛夈€傜绾裤€佹棤璇ヤ唬 updater / 鏃犲凡鐭ユ槑瀵嗘枃瀵圭殑鎯呭喌涓?**鏃犳硶瑙ｅ瘑**銆?浠诲姟涔︾ 2 椤癸紙鎶藉彇 appFw.so/CPAPP-B.BIN锛?*鏃犳硶瀹屾垚**锛涚 3銆? 椤圭殑 A7V 渚?*娌℃湁鏁版嵁**銆?
> 鍞竴杩樿兘璇曠殑鏂瑰悜锛堟湭鍋氾紝闇€瑕佹柊绱犳潗锛夛細鎷垮埌 伪7 V 鐨?updater锛坣flasha1锛屾湇鍔℃ā寮忚鍑猴級鎴栦换浣曚竴鎶?> 璇ヤ唬瀵嗛挜锛涙湰宸ヤ綔鍖烘病鏈夈€?
---

## 3. 鏈哄瀷閴村畾锛氳兘璇佸埌浠€涔堢▼搴?
UDID 璐熻浇鐨勫竷灞€锛堟垜瀵逛袱涓寘閮借В鍑烘潵浜嗭紝`probe.py`锛夛細

```
u32 count (澶х)
count 脳 { be16 usb_pid ; be16 usb_vid(0x054C) ; be32 flag }
```

锛圴ID 0x054C = Sony銆傚啓鎴?be16 瀵癸紝鎵€浠ュ瓧鑺傚簭鏄?`pid_hi pid_lo 05 4c`銆傦級

| # | A7C II 2.01 | a7m5-dat |
| --- | --- | --- |
| 0鈥? | 0x0448 0x047D 0x0D15 0x0D16 0x0D19 0x0D1A 0x0DA4 0x0DA5 | **鐩稿悓** |
| 8鈥? | 0x0E0A 0x0E0E | **鐩稿悓** |
| 10鈥?5 | 0x0E72 0x0E76 0x0E7E 0x0E86 **0x0E8A** 0x0E8E | 鈥?|
| 10 | 鈥?| **0x0F4F** |
| 16 / 11 | 0x03E2 (flag=2) | 0x03E2 (flag=2) |

鍏抽敭鐐癸細

* **0x0E8A 灏辨槸 A7C II 鑷繁鐨?USB PID** 鈥斺€?  `a7c2-camera-tools-fork\windows\runtime\tools\normal_winusb_export\ilce-7cm2.inf`锛?  `DeviceID = "VID_054C&PID_0E8A"`銆傚畠鍑虹幇鍦?A7C II 鐨?UDID 鐧藉悕鍗曢噷锛?*涓嶅湪** a7m5 鍖呴噷銆?* a7m5 鍖呮妸 `0x0E72鈥?x0E8E` 杩欎竴鏁存锛圓7C II / A7CR 瀹舵棌锛夊叏閮ㄧЩ闄わ紝鍙姞浜嗕竴涓?`0x0F4F`銆?* 涓や釜鍖呭叡浜?8+2 涓?PID锛岃鏄庣櫧鍚嶅崟閲屾湁涓€閮ㄥ垎鏄法浠ｉ€氱敤鏉＄洰锛堝彲鑳芥槸 updater/鏈嶅姟妯″紡 PID锛夛紝
  鑰?鐗瑰畾鏈哄瀷 PID"杩欎竴娈佃鎹㈡帀浜嗐€?
**鍒ゆ柇**

* `a7m5-dat` **涓嶆槸** A7C II 鐨勫寘 鈫?**楂樼疆淇★紙OBSERVED锛?*銆?* 瀹冩槸 伪7 V / ILCE-7M5 鈫?**涓庡叏閮ㄨ瘉鎹竴鑷达紝浣嗘湭琚瘉鏄庯紙INFERRED锛屼腑浣庣疆淇★級**锛?  鏄庢枃鏈哄瀷涓?鐗堟湰涓蹭笉鍙锛沗0x0F4F` 杩欎釜 PID 鍦ㄦ湰鍦扮礌鏉愰噷娌℃湁鍨嬪彿鏄犲皠锛?  `PROV=1 / DATV=1` 涔熻鏄庝笉浜嗗瀷鍙枫€?  鑻ラ渶瑕佺‖璇佹嵁锛屾渶鐪佷簨鐨勬槸鏌?libgphoto2 / 绱㈠凹鍏紑 PID 琛ㄩ噷 `054C:0F4F` 瀵瑰簲鏈哄瀷锛堝閮ㄨ祫鏂欙紝鏈細璇濇湭鑱旂綉鏍稿锛夈€?
---

## 4. A7C II 渚э細杩炴媿鍔犻€熺殑瀛楃涓蹭笌鏋氫妇锛坄analysis\a7m5\spotcheck.py`锛?
`appFw.so`锛?9,960,744 B锛夐噷 `.text`/`.rodata` 鐨?*鏂囦欢鍋忕Щ == 铏氭嫙鍦板潃**锛堟 delta = 0锛夛紱
`.data`/`.data.rel.ro` 鐨勬枃浠跺亸绉?= 铏氭嫙鍦板潃 鈭?0x10000銆備笅琛?`str` 鍒楀彲鐩存帴褰撴枃浠跺亸绉荤敤銆?
| 瀛楃涓?| appFw 鍦板潃 | 鍊?id |
| --- | --- | --- |
| `PRM_HAITA_is_spot_boost_enabled` | 0x4CAF110 | **0x0417** |
| `PRM_HAITA_is_spot_boost_enabled_registration_spot_boost` | 0x4CAF130 | 0x0418 |
| `VAL_HAITA_is_spot_boost_enabled_NOT_SET` | 0x4DB79E9 | **0x3007** |
| `VAL_HAITA_is_spot_boost_enabled_DISABLED` | 0x4DB7A11 | **0x3008** |
| `VAL_HAITA_is_spot_boost_enabled_ENABLED` | 0x4DB7A3A | **0x3009** |
| `FUNC_hold_spot_boost_shooting` | 0x4CD9412 | **0x109E** |
| `FUNC_toggle_spot_boost_shooting` | 0x4CD9430 | **0x109F** |
| `FUNC_evolved_spot_boost_shooting_off_for_haita` | 0x4CD93B5 | 0x109C |
| `FUNC_evolved_spot_boost_shooting_on_for_haita` | 0x4CD93E4 | 0x109D |
| `PRM_setting_custom_spot_boost_set` | 0x4CCA30C | 0x0CB7 |
| `PRM_spot_boost_shooting_mode` | 0x4CCA32E | 0x0CB8 |
| `VAL_hold_spot_boost_shooting_mode_SPOT_BOOST_SHOOTING_MODE_OFF` | 0x4EC8C57 | 0x578A |
| `VAL_hold_spot_boost_shooting_mode_SPOT_BOOST_SHOOTING_MODE_ON` | 0x4EC8C96 | 0x578B |
| `VAL_toggle_spot_boost_shooting_mode_SPOT_BOOST_SHOOTING_MODE_OFF` | 鈥?| 0x5780 |
| `VAL_hold_evolved_spot_boost_shooting_mode_SPOT_BOOST_SHOOTING_MODE_OFF` | 鈥?| 0x577D |
| `EVENT_FUNC_CUSTOM_SPOT_BOOST_HOLD_ON` | 0x4F72924 | 浜嬩欢鍛藉悕绌洪棿锛屼笉鍦?VAL 鏁扮粍 |
| `EVENT_FUNC_CUSTOM_SPOT_BOOST_HOLD_ON2` | 0x4F72949 | 鍚屼笂 |
| `PID_SET_BOOST_FPS` | 0x4C7C7B1 | PID 鍛藉悕绌洪棿锛屼笉鍦?VAL 鏁扮粍 |

**澶勭悊鍣紙app handlers锛夌‘瀹炲瓨鍦?*锛歚.rodata` 閲屾湁 C++ 绗﹀彿鍚嶄覆锛?x3DC9FC8 璧凤級锛?
```
bool master_input_eventgp_HOLD_ON_screen_screengp_Other_controller::
     process_EVENT_FUNC_CUSTOM_SPOT_BOOST_HOLD_ON(const ds_event&)
bool master_input_eventgp_TOGGLE_screen_screengp_Other_controller::
     process_EVENT_FUNC_CUSTOM_SPOT_BOOST_TOGGLE_ON(const ds_event&)      锛堝叡 12 鏉★級
```

**CP 渚х绾夸篃鍦?*锛歚CPAPP-B.BIN` 瀛楃涓?`" pGFW: SET_BOOST_FPS[%d]"`锛坄cp.strings.txt` 鍋忕Щ 0x47D979锛?鎸?`analysis\README.md` 鐨勮鍒欏噺 0x230000 鈫?**CPAPP-B.BIN 鏂囦欢鍋忕Щ 0x24D979**锛夈€?
### 4.1 鏋氫妇褰㈡€侊紙浠诲姟涔?3(b)锛?
**鏄?`_DISABLED / _ENABLED` 涓夋€?*锛屼笉鏄埆鐨勶細

```
VAL_HAITA_is_spot_boost_enabled_NOT_SET   = 0x3007
VAL_HAITA_is_spot_boost_enabled_DISABLED  = 0x3008
VAL_HAITA_is_spot_boost_enabled_ENABLED   = 0x3009
```

鍙︽湁涓€缁?娉ㄥ唽/璁板繂鍙洖"鐢ㄧ殑鏋氫妇锛堟敞鎰忔槸 `DISABLE/ENABLE`锛岄潪 `DISABLED/ENABLED`锛夛細

```
VAL_shoot_set_registration_spot_boost_available{0,1,2,3}_..._SPOT_BOOST_DISABLE / _ENABLE
VAL_shoot_set_registration_evolved_spot_boost_available{0,1,2,3}_..._DISABLE / _ENABLE
```

杩炴媿鍔犻€熷湪杩欓噷鏈変袱濂楀懡鍚嶏細鑰佺殑涓€浠ｏ紙`spot_boost_*`锛夊拰 `evolved_*` 涓€浠?锛坄FUNC_hold_evolved_spot_boost_shooting` 绛夛級锛屼袱濂楅兘鍦?2.01 閲屻€?
### 4.2 UI 鏂囨锛氶綈鍏紙涓庨鎷嶆憚鍚屾缁撹锛?
`.uxc` 璧勬簮閲屾湁鏍囩 ID锛屼笖宸叉湁澶氳绉嶇湡瀹炵炕璇戯紙涓嶆槸鍗犱綅绗︼級锛?
```
STRID_FUNC_SPOT_BOOST
STRID_MSG_DURING_SPOT_BOOST_INVALID
STRID_MSG_SPOT_BOOST_HOLD_REGISTERD_CUSTOM_KEY
```

涓归害璇?`share_app_string_danish_func_j.uxc`锛?`"Bst-indst. k. opt.hast."`锛? Cnt Sht Spd Bst Settings锛夈€?`"Boost af kontinuerlig optagelseshastighed"`锛? Continuous Shooting Speed Boost锛夈€?`"Skifter til den valgte kontinuerlige optagelseshastighed, mens der trykkes p氓 knappen."`锛圚old 鐨勮鏄庯級锛?鑽峰叞璇悓娆俱€?*娉ㄦ剰**锛氫换鍔′功閲岀殑鑻辨枃瀛楅潰 `Cnt Sht Spd Bst` / `Cnt Shoot Speed Boost`
鍦?`appFw.so` / `CPAPP-B.BIN` / wbi 閲?*鎼滀笉鍒?*锛坅ppFw 涓嶆槸鏂囨琛級锛屽畠浠彧鍦?`.uxc` 閲岋紝
鎵€浠ユ寜瀛楃涓叉悳 appFw 浼氬緱鍒板亣闃存€с€?
---

## 5. 鍊?id 绌洪棿涓庤鍒欒〃閲嶅缓锛堝苟缁欏嚭姝ｅ悜瀵圭収锛?
### 5.1 id 绌洪棿锛氳繖娆℃槸**琚嫭绔嬮獙璇?*鐨勶紝涓嶅啀鍙槸鍋囪

* `.data.rel.ro` 閲屾湁涓€鏁村潡杩炵画鐨勬寚閽堟暟缁勶細**0x57FD1A0 .. 0x5835778锛坴addr锛?*锛?  鏂囦欢鍋忕Щ **0x57ED1A0**锛堟 delta 0x10000锛夛紝鍏?**28,860** 涓Ы 鈫?**id 0 .. 0x70BB**銆?* 鏁扮粍涓嬫爣 == id锛堝潡鍐呯 i 涓Ы灏辨槸 id i锛夈€?* 閿氱偣涓?`VAL_HAITA_setting_timeshift_shooting_timeshift_prohibited_NOT_SET` @ 0x4EC8E15锛?  鍏舵寚閽堟Ы **0x5828E38**锛堟枃浠?0x5818E38锛夈€?* 鍏抽敭鑷唇鎬э細璇ユЫ鍦ㄥ潡鍐呯殑涓嬫爣 = **22,419 = 0x5793**锛屼簬鏄?鍧楅 id = 0x5793 鈭?0x5793 = **0**"锛?  鍧楀熬 id = 28,859 = **0x70BB**銆?*鏁扮粍鍩哄潃姝ｅソ钀藉湪 id 0 涓?* 鈥斺€?浠讳綍閿氱偣鍋忕Щ閮戒細鐮村潖杩欎釜宸у悎锛?  鎵€浠?0x5793 杩欎釜閿氱偣鐜板湪鏈変簡缁撴瀯鎬ц瘉鎹紙鏃ц剼鏈彧鏈夊崟鐐瑰亣璁撅級銆?  杩欎篃椤哄甫璇佹槑璇ユ暟缁勯噷娣锋帓浜?`VAL_* / PRM_* / FUNC_* / OFF_BY_DCI_4K24P`锛坕d 0锛夌瓑澶氱鍓嶇紑銆?
### 5.2 瑙勫垯琛ㄦā鍨嬩笌姝ｅ悜瀵圭収

* 鎻忚堪绗?`{u64 table_ptr 鈫?.rodata, u64 count}` 浣嶄簬 `.data.rel.ro`锛?  琛ㄤ綋 = `count 脳 {u32 kind, u32 from_id, u32 to_id}`銆?* **姝ｅ悜瀵圭収**锛歚PROPERTY-MAP.zh-CN.md 搂10.1` 璁板綍鐨勯鎷嶆憚寮哄埗琛?**0x4274AE0**锛?0 琛屻€乲ind=3銆?  鍏ㄩ儴 鈫?0x5797 `..._FIXED`锛夆啋 鎴戠殑鎵弿鎵惧埌鎻忚堪绗?**0x527E2D0锛堟枃浠?0x526E2D0锛塩ount=10**锛?  閫愯鍐呭涓庢枃妗ｅ畬鍏ㄤ竴鑷淬€?*鎻忚堪绗︽ā鍨嬬‘璁ゆ棤璇€?*

### 5.3 杩炴媿鍔犻€熺浉鍏宠〃鐨勫叏閲忔壂鎻忥紙`analysis\a7m5\a7c2_spotboost_tables.txt`锛?
* 鍚嶅瓧鍚?`spot_boost` 鐨勫€?id锛?*249 涓?*锛?x01F8 鈥?0x6348锛岃法 PRM/FUNC/VAL 涓変釜鍛藉悕绌洪棿锛夈€?* 瑙﹀強杩欎簺 id 鐨勬弿杩扮/琛細**73 寮?*锛堝叏閮ㄥ垪鍑哄湪闄勪欢 txt 閲岋級銆?* **璐熺粨鏋滐紙鍏抽敭锛?*锛?*娌℃湁浠讳綍涓€琛?*鎶婅繛鎷嶅姞閫熺殑鍊兼敼鍐欐垚 `OFF` / `DISABLED` / `NOT_SET`銆?  鍙湁 3 寮?鐩爣鍋?OFF"鐨勮〃锛屼笖閮借窡杩炴媿鍔犻€熺殑鍚仠鏃犲叧锛?
| 琛紙.rodata锛?| 鏂囦欢鍋忕Щ | 鍐呭 | 鍒よ |
| --- | --- | --- | --- |
| 0x042EE590 | 0x42EE590 | k0: 0x4B81/0x4B82锛堟姉闂儊脳spot_boost_mode锛夆啋 0x4B83/0x4B84锛坰till_lock_state锛?| 鎶楅棯鐑佷簰閿?|
| 0x042FA248 | 0x42FA248 | k0: 0x2FE1锛圖RIVE_MODE_CONT脳SPOT_MODE_OFF锛夆啋 0x2FE2锛坋xecutable_status_NOT_SET锛?| 缁勫悎鎬佸洖閫€ |
| 0x04337E48 | 0x4337E48 | k3: 0x263D锛坮egistration_drive_mode_*锛夆啋 0x264B锛坮egistration_spot_boost_NOT_SET锛?| MR 娉ㄥ唽娲剧敓 |

* 瀹為檯瀛樺湪鐨勮繛鎷嶅姞閫熻〃閮芥槸**鐘舵€佹満 / 娉ㄥ唽娲剧敓**锛屼妇渚嬶紙`.rodata`锛屾枃浠跺亸绉?== vaddr锛夛細

```
0x042F3E80 k0 0x577F(hold PRM_ALL) -> 0x577E(hold ON) ; 0x5780(toggle OFF) -> 0x577E
0x042F64C8 k0 0x577E(hold ON)      -> 0x577F(hold PRM_ALL)
0x042FE030 / 0x043024A8 / 0x04306AD0 / 0x04308428 / 0x04315A18  k0 0x577E -> 0x5780(toggle OFF)
0x04308418 k0 0x577E -> 0x577F
0x042DDC70 k0 0x2FE1 / 0x2FE2 -> 0x2FE3 (executable_status_ONLY_S0_EXECUTABLE)
0x0426C9D0 / 0x0428D010 / 0x0429C9C8  k3  executable_status 鈫?still_shooting_status 浜掕浆
0x04336558 k3 0x263E(drive_mode REGIST1) -> 0x2669(registration_spot_boost_*)
0x04337E58 鈥?0x0433C6C0  40+ 寮犲崟琛岃〃锛宬3 0x263D -> 0x264C 鈥?0x2665
```

**鍒よ锛圛NFERRED锛岀疆淇′腑楂橈級**锛?棰勬媿鎽勶紙timeshift锛夋槸琚?10 琛屻€佸叏閮ㄦ敼鍐欐垚 FIXED"鐨勫己鍒惰〃鍘嬩綇鐨勶紙杩欐槸 搂10.1 鐨勭粨璁猴級锛?**杩炴媿鍔犻€熸病鏈夊搴旂殑寮哄埗琛?*銆傛墍浠?A7C II 涓?鍔熻兘娌℃毚闇?鐨?gate **涓嶅湪 feature-manager 鐨勬敼鍐欒〃杩欎竴灞?*銆?浠诲姟涔﹂噷"鎵句竴鏉℃妸 spot boost 寮哄埗鎴?DISABLED/OFF/NOT_SET 鐨勮鍒欒"鐨勫亣璁撅紝鍦?A7C II 涓?*琚帓闄?*銆?
### 5.4 浠ｇ爜灞備氦鍙夐獙璇侊紙閮ㄥ垎锛?
瀵?`0x3007 / 0x3008 / 0x3009`锛堜笁鎬佹灇涓撅級涓?`0x0417 / 0x0418`锛圥RM锛夊仛 MOVZ/MOVK 绔嬪嵆鏁版壂鎻?锛坄analysis\imm_scan.py`锛?6 澶勫懡涓級銆傛娊鏌ョ湅锛?*鍛戒腑鐨勯兘涓嶆槸闂ㄦ帶**锛?
* `0x3584DD8` 璧凤細`mov w1,#0x3008; cmp w0,w1; 鈥 鏄竴涓ぇ switch锛屾妸"鍊?id"鏄犲皠鎴?UI 璧勬簮绱㈠紩
  鈫?鏄?*鏄剧ず**閫昏緫锛?* `0x33996B8` 璧凤細`mov w5,#0x3009` + `adrp/adrp/add` + `bl 0x36804C8`锛屾槸鍦?*鎷兼棩蹇楀瓧绗︿覆**锛堣皟璇曟墦鍗帮級銆?
鍗筹細**"璋佸喅瀹?ENABLED/DISABLED"杩欎竴姝ユ病鏈夊湪杩欐壒绔嬪嵆鏁扮偣閲屾毚闇插嚭鏉?*銆?
---

## 6. Gate 鍊欓€夛紙Top 3锛屽惈鍋忕Щ涓庣疆淇★級

> 鍏堣鏄庯細浠诲姟涔︽湡鏈涚殑"A7C II 鏈夈€丄7V 娌℃湁鐨勯偅鏉¤鍒欒"**鏈細璇濇棤娉曟楠?*锛圓7V 瑙ｄ笉寮€锛夈€?> 涓嬮潰鏄垜鍦?*鍗曚晶**鑳藉仛鍒扮殑鏈€濂界粨鏋溿€備笁鏉￠兘娌℃湁杈惧埌"鍙互鐩存帴鎵撹ˉ涓?鐨勫己搴︺€?
### C1 鈥?`is_spot_boost_enabled` 鑳藉姏浣嶏紙**鏈€鍍忛棬锛屼絾琛ヤ竵鐐规湭瀹氫綅**锛?* 璇佹嵁锛氬瓨鍦ㄤ笓鐢?PRM `PRM_HAITA_is_spot_boost_enabled`锛坕d 0x0417锛屼覆 0x4CAF110锛変笌涓撶敤涓夋€?  `NOT_SET/DISABLED/ENABLED`锛?x3007/0x3008/0x3009锛屼覆 0x4DB79E9/0x4DB7A11/0x4DB7A3A锛夛紱
  **娌℃湁浠讳綍瑙勫垯琛ㄥ啓瀹?* 鈫?瀹冨彧鑳界敱浠ｇ爜绠楀嚭鏉ワ紝鑰?绠楀嚭鏉ユ槸 DISABLED"灏辨槸"鍔熻兘涓嶆毚闇?鐨勮嚜鐒跺疄鐜般€?* 宸叉帓鏌ワ細46 澶勭珛鍗虫暟鍛戒腑閲岋紝鎶芥牱涓ゅ鍧囦负 UI/鏃ュ織锛?x3584DD8銆?x33996B8锛夈€?* 鍋忕Щ锛?*鏃?*锛堟病鏈夊彲淇¤ˉ涓佺偣锛夈€?* 缃俊锛?*鏄?gate 鐨勫彲鑳芥€?= 涓?*锛?*鏈夊叿浣撹ˉ涓佸亸绉?= 鏃?*銆?
### C2 鈥?鑷畾涔夐敭"鍙垎閰?FUNC 鍒楄〃"閲屽彲鑳芥病鏈?0x109E / 0x109F
* 閫昏緫锛氬姛鑳?娌℃毚闇?鏈€鐩存帴鐨勫師鍥犳槸鑷畾涔夐敭鑿滃崟閲岄€変笉鍒?`FUNC_hold_spot_boost_shooting` / `FUNC_toggle_...`銆?* 宸插仛锛氬湪 `.rodata` 鎵?0x1000鈥?x1400 鍖洪棿鐨勫崌搴?u16/u32 鏁扮粍锛屽彧鎵惧埌涓ゆ潯锛?x3F30D3C銆?x401E704锛夛紝
  閮?*涓嶅惈** 0x109A鈥?x109F 鈫?**娌℃壘鍒拌鍒楄〃**锛堜笉绛変簬涓嶅瓨鍦細鍙兘鏄綅鍥俱€佺粨鏋勪綋鏁扮粍鎴栬法娈电储寮曪級銆?* 缃俊锛?*浣?*锛堟湭璇佸疄锛夈€?
### C3 鈥?MR 娉ㄥ唽娲剧敓琛ㄦ棌锛氭妸杩炴媿鍔犻€熸敞鍐岄」鍐欐垚 `NOT_SET`
* 琛細`0x4337E48`锛坘3: 0x263D 鈫?**0x264B = VAL_HAITA_registration_spot_boost_NOT_SET**锛夛紝
  浠ュ強 0x4337E58 / 0x4339F18鈥?x4339FA8 / 0x433B1E0鈥?x433B270 / 0x433C660鈥?x433C6C0锛堝崟琛岃〃锛屽叡 40+锛夈€?* 閫昏緫锛氳繖鏄洰鍓?*鍞竴**鎶婅繛鎷嶅姞閫熷啓鎴?`NOT_SET` 鐨勫湴鏂癸紝褰㈢姸鍍?椹卞姩妯″紡娉ㄥ唽椤?鈫?杩炴媿鍔犻€熸敞鍐岄」"鐨勯粯璁ゅ€兼淳鐢燂紱
  浣嗗畠鏇村儚 MR锛堣蹇嗗彫鍥烇級璇箟锛屼笉鍍?鑿滃崟鏆撮湶"闂ㄣ€?* 缃俊锛?*浣?*銆傝嫢瑕佽瘯锛屾渶灏忔敼鍔ㄦ槸璁?`0x4337E48` 杩欎竴琛屽け鏁堬紙渚嬪鎶?`to` 鏀规垚 0x263D 鑷韩锛?  鍗?k3 0x263D鈫?x263D锛夛紝鏂囦欢鍋忕Щ **0x4337E48**锛坄.rodata`锛屾敼 4 瀛楄妭 @ 0x4337E50锛夈€?
### 宸茶鎺掗櫎鐨勫亣璁?* ~~"瀛樺湪涓€鏉℃妸 spot boost 鍊煎己鍒舵敼鎴?DISABLED/OFF 鐨勮鍒欒"~~ 鈫?**A7C II 涓婁笉瀛樺湪**锛?3 寮犺〃鍏ㄦ煡锛夈€?* ~~"A7M5 鍖呭彲浠ョ敤 A7C II 瀵嗛挜瑙ｅ紑"~~ 鈫?**涓嶆垚绔?*锛? 绉嶆柟妗堝叏璇曪級銆?* ~~"`Cnt Sht Spd Bst` 涔嬬被鏂囨鍦?appFw 閲?~~ 鈫?涓嶅湪锛涘彧鍦?`.uxc` 璧勬簮閲岋紙鎼?appFw 浼氬亣闃存€э級銆?
---

## 7. OBSERVED / INFERRED / UNKNOWN

| 缁撹 | 绫诲埆 |
| --- | --- |
| a7m5 鍖呭灞?TLV 鍚堟硶銆丏END CRC-32 = 0xCF78AC68 閫氳繃 | OBSERVED |
| `a7c2dat.container.parse()` 鍦?a7m5 鍖呬笂鍥犲潡鍑犱綍鏂█澶辫触 | OBSERVED |
| a7m5 鍖呮棤灏鹃殢鏁版嵁銆丗DAT 闀垮害 376,540,560 | OBSERVED |
| a7m5 鍖呯敤 A7C II 涓ゆ妸瀵嗛挜锛堝強 6 绉嶅彉浣擄級瑙ｄ笉寮€ | OBSERVED |
| A7C II 涓ゆ妸瀵嗛挜涓嶅湪 appFw/CPAPP/CPIMG/DGU/DMMCFG/MIS/SYSSOUND/nflasha15/5/8 涓?| OBSERVED |
| UDID = {be16 PID, be16 VID=0x054C, be32 flag} 鍒楄〃锛汚7C II 鍚?0x0E8A锛宎7m5 涓嶅惈 | OBSERVED |
| 鍊?id 鏁扮粍 = .data.rel.ro 0x57FD1A0..0x5835778锛?8,860 椤癸紝涓嬫爣==id锛屽熀鍧€ id 0 | OBSERVED |
| 棰勬媿鎽勫己鍒惰〃 0x4274AE0 / 鎻忚堪绗?0x527E2D0 鍙鐜?| OBSERVED |
| 249 涓?spot-boost 鍊?id銆?3 寮犵浉鍏宠〃 | OBSERVED |
| **鏃犱换浣曡〃鎶?spot-boost 鍊煎己鍒舵垚 OFF/DISABLED/NOT_SET** | OBSERVED |
| `is_spot_boost_enabled` 鏋氫妇 = NOT_SET/DISABLED/ENABLED (0x3007/8/9) | OBSERVED |
| CPU 渚?handler 绗﹀彿涓蹭笌 CP 渚?`SET_BOOST_FPS` 鎵撳嵃閮藉瓨鍦?| OBSERVED |
| a7m5 鍖?FDAT 灏鹃儴闀?400 B锛堟垨鍓?128 B 鍓嶇紑锛?| INFERRED |
| a7m5 鍖?= 伪7 V / ILCE-7M5 | INFERRED锛堣瘉鎹竴鑷达紝鏈瘉鏄庯級 |
| 杩炴媿鍔犻€熺殑 gate 涓嶅湪鏀瑰啓瑙勫垯琛ㄥ眰 | INFERRED锛堝己锛?|
| 鐪熸鐨?gate 鏄?`is_spot_boost_enabled` 鐨勮繍琛屾椂璁＄畻 | INFERRED锛堜腑锛?|
| 瀹為檯琛ヤ竵瀛楄妭锛堝摢鏉℃寚浠?鍝釜瀛楁鏀规垚浠€涔堬級 | **UNKNOWN** |
| A7V 渚х殑瀛楃涓?鏋氫妇/瑙勫垯琛?| **UNKNOWN锛堟棤鏁版嵁锛?* |
| 杩欎簺琛ㄥ湪 wbi(nflasha5) 閲屾槸鍚︽湁绗簩浠藉壇鏈?| **UNKNOWN锛堟湭鏍稿锛?* |

---

## 8. 鑻ヨ缁х画锛堟寜鎬т环姣旀帓搴忥級

1. **鎷?A7V 鐨?updater 鎴栬浠ｅ瘑閽?*锛堟湇鍔℃ā寮忚 nflasha1锛夛紝鎵嶈兘鍋氱湡姝ｇ殑宸垎锛涘惁鍒?A7V 渚ф案杩滄槸绌虹櫧銆?2. 鍦?A7C II 涓婂畾浣?`is_spot_boost_enabled` 鐨?*鍐欏叆鐐?*锛氬缓璁敤 `xrefs_many` 杩?   `VAL_HAITA_is_spot_boost_enabled_*` 鐨?*妲藉湴鍧€**锛?x5815 1D8/1E0/1E8 鈫?鏂囦欢 0x58141D8 绛夛級
   鎴栬拷 PRM 0x0417 鐨勮鍙栧皝瑁咃紝鑰屼笉鏄户缁壂绔嬪嵆鏁帮紙宸查獙璇佷細琚?UI/鏃ュ織鍣０娣规病锛夈€?3. 鏍稿 wbi(nflasha5) 閲屾槸鍚︿篃瀛樺湪 0x4274AE0/0x4337E48 杩欎簺琛紙鑻ュ瓨鍦紝浠讳綍琛ヤ竵閮借鍙屽啓锛?   涓庨」鐩噷 FL2/FL3銆侀煶鏁堣ˉ涓佺殑鎯緥涓€鑷达級銆?4. 鑻ユ渶缁堢‘瀹氳鍔?`0x4337E48`锛圕3锛夛紝琛ヤ竵鍙渶 4 瀛楄妭锛氭枃浠跺亸绉?**0x4337E50**锛坄to` 瀛楁锛?   0x0000264B 鈫?0x0000263D锛屼笖 `.rodata` 鏂囦欢鍋忕Щ == 铏氭嫙鍦板潃锛屽啓 nflasha15 鏃跺啀鐢ㄥ垎鍖哄唴鍋忕Щ鎹㈢畻銆?
---

## 9. 澶嶇幇

```bat
:: 闇€瑕佸甫 numpy/pycryptodome 鐨勮В閲婂櫒锛堟湰鏈?3.15 娌¤锛岀敤鐨勬槸 DSH 杩愯鏃?3.12锛?set PY=py -3

%PY% analysis\a7m5\probe.py BODYDATA.DAT a7m5-dat\BODYDATA.DAT   :: 瀹瑰櫒 TLV 閾?%PY% analysis\a7m5\trykeys.py                                    :: 7 绉嶈В瀵嗘柟妗?+ DEND CRC
%PY% analysis\a7m5\scan_keys.py                                  :: 鍦ㄩ暅鍍忛噷鎵惧瘑閽?%PY% analysis\a7m5\vidspace.py inventory                         :: id 绌洪棿鑷唇鎬?%PY% analysis\a7m5\gatescan.py desc                              :: 鎻忚堪绗︽ā鍨?+ 棰勬媿鎽勬鍚戝鐓?%PY% analysis\a7m5\gatescan.py ids    > analysis\a7m5\a7c2_spotboost_ids.txt
%PY% analysis\a7m5\gatescan.py tables > analysis\a7m5\a7c2_spotboost_tables.txt
%PY% analysis\a7m5\brief.py                                      :: 琛ㄧ殑绱у噾娓叉煋
%PY% analysis\a7m5\spotcheck.py                                  :: 鍛藉悕涓测啋id銆丗UNC 鍒楄〃鎵弿
%PY% analysis\imm_scan.py analysis\bin\appFw.so 0x3007=x 0x3008=y 0x3009=z 0x417=p
```

浜х墿锛歚analysis\a7m5\`锛坄probe.py` `trykeys.py` `scan_keys.py` `vidspace.py` `gatescan.py`
`brief.py` `spotcheck.py` `a7c2_spotboost_ids.txt` `a7c2_spotboost_tables.txt` `a7c2_tables_brief.txt`锛夈€?
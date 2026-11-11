# v21：仅审核 Tantivy 候选，离线准入未成立

2026-11-11。**不进入付费比较，不建议产品烟测，生产仍用 SQLite。** 本轮仅一个候选，未轮换参数；新增真实请求/token 为0，未加载凭据、未操作8765。不是已测得“初稿后的等待”改善，也不是已证明候选质量相当。

## 实现与冻结交付规则

基点131e839，先读f3a592a、a2a9e93、6cd3550及131e839固定报告。复用90片v18、现有Factory/Harness/四Agent及原政策。evaluation/audit_tantivy_v21.py为显式隔离Factory：生成及revision目的路由正式SQLite/3根；verification和domain_review路由原v18/6根，校验使用同一个改写后请求。重审仍按purpose路由。默认生产配置没有改动。

唯一交付规则为原有评分/顺序/精确去重、最多6根/8000字符，邻接2400字符/6段/depth1，Harness原16000每次/160000整链预算不变；模型请求内相同evidence_id、同一起止范围、逐字相同正文才可共享。保留引用ID、作用域和元数据，expand必须逐对象精确还原；不同ID、不同范围、近似正文均不合并。不以题号、目标ID或特定数值选择。原根顺序优先，后按既有storage_order邻接，不创造相关性保护规则。预算不足仍由原入口如实暴露。

请求构造核对：schema13使用verification_contract_v10_batched；独立请求携带scopes[0]整片QUOTE_CANDIDATES和body_snapshot，故初稿Evidence可与独立正文重复；原引用请求使用citation_payload各自的原引用作用域，不借独立证据修正原引用；领域domain_contract_v3携带CandidateScope整片。CandidateScope本身已只交付整片一次，并非同时交付根正文和其摘录。现有生产review_transport还会共享完全相同值；不能把载体层重复简单计成线上一定可省的字符。跨模型调用重复不删除。

## 36个冻结审核读取及载体核算

只读取v20原20事实/16领域请求和原168槽记录；没有重复读取大库/新建索引。原冻结输入文件SHA保存在忽略summary.json，关联包含slot、origin、query_sha256及问题全文。原24题ISO-NE Q10与真实光伏Q10严格分开。

读取净省285.597秒，这是旧逐请求墙钟的配对合计，**不是新产品路由实测，更不是用户等待节省**。本轮新增回放只构造检索正文载体和保留的SQLite初稿快照并做identity共享，expand精确相等。合计SQLite382768字、候选406608字，多23840字（6.23%）。这些是载体字符，**不是最终审核模型请求证据字符**：未完整还原现有transport、原引用分组、纠正及初稿快照的实际请求位置，不能拿本数字填付费字符门槛。逐请求明细如下，正字符差表示候选更多。

|slot|题/原链|阶段|读取省秒|SQLite载体字|候选载体字|多字|
|---|---|---|---:|---:|---:|---:|
|2|Q1/baseline|verification|24.392|22409|17503|-4906|
|3|Q1/baseline|verification|1.210|21983|12782|-9201|
|4|Q1/baseline|domain_review|18.710|4805|8732|+3927|
|7|Q1/fast|verification|7.867|22992|17869|-5123|
|8|Q1/fast|verification|0.154|21438|16455|-4983|
|9|Q1/fast|domain_review|6.096|5805|9206|+3401|
|12|Q3/baseline|verification|13.930|18851|14446|-4405|
|13|Q3/baseline|verification|4.036|17291|15335|-1956|
|14|Q3/baseline|domain_review|27.870|5855|9237|+3382|
|17|Q3/fast|verification|21.689|17442|15785|-1657|
|18|Q3/fast|verification|1.018|17291|15335|-1956|
|19|Q3/fast|domain_review|19.227|5021|9283|+4262|
|21|Q4/baseline|verification|1.350|6127|10130|+4003|
|22|Q4/baseline|domain_review|10.433|4321|9054|+4733|
|24|Q4/fast|verification|5.331|6876|9422|+2546|
|25|Q4/fast|domain_review|7.161|5147|9096|+3949|
|27|Q5/baseline|verification|-4.652|13391|13005|-386|
|28|Q5/baseline|domain_review|12.863|4915|8767|+3852|
|30|Q5/fast|verification|-0.430|14352|10658|-3694|
|31|Q5/fast|domain_review|18.348|5876|6420|+544|
|33|Q6/baseline|verification|0.493|12187|12849|+662|
|34|Q6/baseline|domain_review|3.056|4531|9056|+4525|
|36|Q6/fast|verification|-2.077|10699|12189|+1490|
|37|Q6/fast|domain_review|1.399|2101|7885|+5784|
|39|Q7/baseline|verification|-0.165|16394|14317|-2077|
|40|Q7/baseline|domain_review|12.566|5550|8985|+3435|
|42|Q7/fast|verification|3.570|16677|11315|-5362|
|43|Q7/fast|domain_review|12.186|5447|9060|+3613|
|45|Q9/baseline|verification|-0.314|12669|10504|-2165|
|46|Q9/baseline|domain_review|17.454|4557|9119|+4562|
|48|Q9/fast|verification|6.035|12374|12363|-11|
|49|Q9/fast|domain_review|13.675|3399|8917|+5518|
|51|Q10/baseline|verification|1.797|11677|12611|+934|
|52|Q10/baseline|domain_review|4.829|5400|8928|+3528|
|54|Q10/fast|verification|0.904|11977|11780|-197|
|55|Q10/fast|domain_review|13.586|4941|8210|+3269|

读取节省最多slot14：27.870秒；退步最大slot27：-4.652秒；载体增量最大slot37：+5784字。保留原起源两链，不把36请求视作36独立问题。

## 关键原文与准入阻断

本候选不截成三根，故v18已有第6根ISO-NE原文和TO设备额定例外仍在原交付集合；这是已有v18记录的集合推断，不冒称本轮新检索ISO问题。Q1能量交换原文仍保留于v18后部根；Q6熔断器更换熔体与断路器合闸/脱扣两类材料保留；Q9需用/同时率的检索材料依查询起源不同，住宅/地区材料不得冒充工厂输入；Q3恒压条件原文已在，但历史模型仍遗漏。均沿v20逐段复核，不新增模型识别成绩。双方共同缺失的正弦条件仍为共同缺陷，不能算候选保护成功。

阻断项：最终请求字符门槛尚无完整证明，而且新载体核算仍净增加；Factory真实入口的一次有据修订/完整重审/Store存取尚未用本候选夹具贯通，不能用purpose路由单测代替。当前两项准入均不能确认，因此按用户事前规则本轮停止付费，不以旧v19入口成功填本候选缺项。不声称有已确认的新关键原文丢失，也不声称完成了全量语义保护复核。

## 验证、处置与回退

新增两项离线测试通过：同身份同范围精确还原、不同来源/范围保留；全部purpose路由及对应validate请求一致。这里只证明组件，不证明真实90片新Factory轨迹或修订存储闭环。完整离线结果见忽略unittest.log，最终结果另补。最初一次诊断用系统GBK读UTF8失败，改显式UTF8后完成，不涉及模型请求。

候选只存在显式evaluation Factory，无生产开关变更；回退为继续现有ComponentFactory/SQLite，生产切换0。240次/400万授权未启用、未新建付费账本，不恢复v19/v20旧账，不补跑。**本轮交付是未获准入的候选及不完整测量证据，用户要求的完整产品路径验证尚未完成；不得将此归档标作全部任务已达成。**

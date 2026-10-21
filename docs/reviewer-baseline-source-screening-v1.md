# 小规模组件基线：四组新来源筛选v1

2026-10-21。依据本人授权及[正式规格](reviewer-component-baseline-spec-v1.md)，一次整理4个新来源组、各2个候选问题方向；**待本人原文/范围复核，未正式入组**。无待评回答、参考标签、模型调用或提示修改。方向不是正式题卡，来源确认不升级为标签或执行确认。

本批为跨主题评审组件基线，不代表电力专业语义验证。按原文可解释的边界选材，不为24回答配额硬造标签；暂无清楚not_assessable案例，不强行设计。

## 完整原文在哪里

完整候选选段、必要上下文、原文定位、Unicode区间与逐段SHA见忽略目录`data/evaluation_local/source-screening-baseline-v1/candidate-originals-review-v1.md`和`selected-source-excerpts-v1.json`；官方HTML/PDF主体、抽取文本、USGS单页渲染及审计也在该目录。不把官方全文或原文包推送Git。[公开身份清单](reviewer-baseline-source-screening-v1.json)绑定全部快照及复核材料SHA。所有快照日期为2026-10-21，保存主体，不保存请求头或凭据。

## CAND-BL-NWS-FORECAST

**Forecast Terms** — NOAA National Weather Service, Weather Forecast Office Pago Pago。Unnumbered live page; no content-specific publication/update date identified; snapshot 2026-10-21。

[官方正文](https://www.weather.gov/ppg/forecast_terms)

快照文件`NOAA.html`，55132字节；SHA256：`fe2773f6722f67874632cfa07c8e8aede961208cce9702c8458578940f5545ae`。

**两个候选方向**

1. PoP定义：可测液态或冻结降水水当量、给定时间、区域内任一点；区分概率与降水时长/面积断言。
2. 预报表达的条件规则：高降水概率达到60%时天空状况可以省略；在明确假定预报概率下判断规则是否允许，区分may与must。

**选段定位**

- NWS-X1：Precipitation Probability heading; complete body paragraph including following on/off sentence；抽取文本区间[3119,3747)。
- NWS-X2：Sky Condition heading; complete opening paragraph, no table rows needed for this direction；抽取文本区间[2182,2476)。

**支持边界。** 只支持本页术语及表达惯例；12小时带unless specified otherwise，不推广至所有NWS产品；不把概率当确定降雨或面积/时长保证，60%允许省略不等于强制省略。无需判断天气实况或安全。

**谱系与近重复。** NWS各办公室Forecast Terms、术语表、PFM说明、镜像与翻译按相关定义谱系关联。Juneau材料出现默认6小时，PPG本页为通常12小时，表格阈值也可能不同；不得混页补条件。本组不取概率乘积公式或不同办公室云量表。NRC其他报告有气象术语不等于旧half-life定义谱系；本次旧NRC选段全文核查另列。

- [关联线索](https://www.weather.gov/media/ajk/brochures/ConvectivevsStratiform.pdf)
- [关联线索](https://www.weather.gov/mrx/pfm_explain)
- [关联线索](https://forecast.weather.gov/glossary.php?word=K)

## CAND-BL-USGS-GIP106

**100-Year Flood—It’s All About Chance: Haven’t we already had one this century?** — USGS; Robert R. Holmes, Jr. and Karen Dinicola。General Information Product 106, April 2010; DOI 10.3133/gip106; 1-page poster。

[官方正文](https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf)

快照文件`USGS-gip106.pdf`，1128297字节；SHA256：`52af423da7f5d6e5f6363b7e3c2c4a7c181fd4236cbdde167d4c9a714c6a0e26`。

**两个候选方向**

1. 百年洪水与1%年超越概率的关系：相等或超越、平均重现期与不规则间隔，不解释为固定100年一次。
2. 洪水定义及成因关系：较高流量漫过自然或人工河岸，多种成因为什么不推出相同量级、持续时间或影响。

**选段定位**

- USGS-X1：PDF page 1, left column: So what is a 100-year flood and how is it determined?, complete first paragraph；抽取文本区间[136,639)。
- USGS-X2：PDF page 1, left top: What is a Flood?, complete body paragraph; extraction order differs from visual order；抽取文本区间[1904,2625)。
- USGS-X3：PDF page 1, middle panel: On the river near me..., complete first paragraph; graph is not needed for this paragraph；抽取文本区间[2843,3062)。

**支持边界。** 只解释海报定义和概念关系；不预测某河具体日期/流量/现场风险，不把示例测站量值泛化，不在本候选中考图表运算、30年风险计算或置信区间语义。第二方向不强行构造某具体地区原因已查实。

**谱系与近重复。** GIP106海报、handout/网页版本、USGS百年洪水FAQ及引用本海报的Fact Sheet 2011-3146、转载与翻译同组关联。主站FAQ直连403，搜索只作关联线索；本组证据载体以实际取得PDF为准，不冒称已取得FAQ快照。

- [关联线索](https://doi.org/10.3133/gip106)
- [关联线索](https://www.usgs.gov/faqs/we-had-a-100-year-flood-two-years-a-row-how-can-be)
- [关联线索](https://pubs.usgs.gov/fs/2011/3146/)

## CAND-BL-NASA-ORBITS

**Catalog of Earth Satellite Orbits** — NASA Earth Observatory; story by Holli Riebeek, design by Robert Simmon。Article Sep 04, 2009; page last updated Nov 14, 2025; no numbered edition。

[官方正文](https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/)

快照文件`NASA-retrieved.html`，351468字节；SHA256：`4e2d4a17f345defa498e56646628010937f9bd7db74e8e192aab3e459906a79e`。

**两个候选方向**

1. 轨道偏心率与倾角分别描述什么；圆轨道/赤道轨道的条件不能互相替代。
2. 地球同步与地球静止轨道的关系；在明确假定已是圆形、赤道上空的地球同步轨道时应用条件，不将所有同步轨道都说成地面相对静止。

**选段定位**

- NASA-X1：Body before Three Classes of Orbit, complete eccentricity paragraph；抽取文本区间[9408,9744)。
- NASA-X2：Body before Three Classes of Orbit, complete inclination paragraph；抽取文本区间[10087,10348)。
- NASA-X3：High Earth Orbit, complete first paragraph；抽取文本区间[10810,11244)。
- NASA-X4：High Earth Orbit, complete second paragraph；抽取文本区间[11245,11504)。

**支持边界。** 保留geosynchronous前提，单有零偏心率/零倾角不足以推出同步；不把科普理想描述当真实卫星轨道测定、维护保证、通信性能或碰撞安全认证；不引入开普勒推导、未交付公式或方向假定。

**谱系与近重复。** 旧Earth Observatory OrbitsCatalog路径、新science.nasa.gov迁移页、转载翻译及同句教材关联；文章列出Air University Space Primer、Pisacane Fundamentals of Space Systems等参考，作为上游线索，未下载扩展教材。已知开发教材是电路/电力资料，未发现这些参考身份直接关联；不能声称追溯了全部上游。

- [关联线索](https://earthobservatory.nasa.gov/features/OrbitsCatalog/)
- [关联线索](https://science.nasa.gov/learn/basics-of-space-flight/chapter5-1/)

## CAND-BL-CDC-WATER

**How to Make Water Safe in an Emergency** — CDC, National Center for Environmental Health。Page date Sept. 19, 2024; no numbered edition; snapshot 2026-10-21。

[官方正文](https://www.cdc.gov/water-emergency/about/)

快照文件`CDC.html`，71056字节；SHA256：`403a9acc422568c7bc9cbf0feea9cb3f9aacf30ddc325f8bfc0ecd48b6e53f38`。

**两个候选方向**

1. 应急煮水规则应用：保留清水、翻滚沸腾起算、高于6500英尺时3分钟及冷却/容器步骤；仅在明确题设条件下应用。
2. 杀菌方法的适用边界：含燃料/有毒化学品/放射性材料的水不能靠煮沸或消毒保证安全，与一般杀菌规则的关系。

**选段定位**

- CDC-X1：Overview > Water with fuel or toxic chemicals in it, complete paragraph；抽取文本区间[2759,3050)。
- CDC-X2：Boil > Steps for boiling water, complete preparation paragraph and all three list items；抽取文本区间[3208,3599)。
- CDC-X3：Overview, complete paragraph specifying health-department recommendations；抽取文本区间[2297,2475)。

**支持边界。** 用于文献规则理解和假定应用，不诊断实际水源、人体状况或现场饮用安全；不扩成任意处理技术永远不能净化，不制作漂白剂配比/治疗问题，不从清澈推出无化学污染。严格保留above而非擅改为大于等于阈值。

**谱系与近重复。** CDC旧healthywater入口、新water-emergency页、同主题Natural Disasters音频稿/资料单、多语言翻译按相关谱系同组；EPA链接是相关上游/交叉说明线索，不借其他机构不同海拔阈值替换本页。放射性污染限制与NRC半衰期定义不是同一选段/派生关系，旧NRC文本仍实际查重。

- [关联线索](https://www.cdc.gov/natural-disasters/psa-toolkit/boil-water-advisory.html)
- [关联线索](https://www.cdc.gov/water-emergency/about/drinking-water-advisories-an-overview.html)
- [关联线索](https://stacks.cdc.gov/view/cdc/128149)

## 有限历史审计与失败证据

在新增候选文档之前，对472份已跟踪项目文本/既有开发卡和参考JSON/来源文本做域名、英中主题词及选段英文连续8词核查；另实际抽取ABB370页、TR样章30页、MIT16页、BIPM102页，共518页。审计文件列表及原SHA保留。CT原选句、RC来源、EIA/NRC选段及上下文在文本范围内；不读取凭据或请求头，不扫描70GB库、全部运行原始响应或TR整本书。

选段连续8词重合为0。唯一关键词命中为旧EIA N术语页的NOAA机构名和NOAA division条目（123—124行）；已读上下文，未见PoP/天空状况定义的派生或同句关系，不因机构名命中自动判同源。四组题材不同；USGS相关链接提到气象数据、NASA提到NOAA运营GOES，不等于所选洪水/轨道段落和NWS预报术语共享母文档。未以机构不同作为独立证明。

公开检索中的NWS同定义、USGS同报告引用、NASA迁站/教材引用、CDC同主题旧新页面均作为关联谱系，不拆成新组。英文8词和关键词只是有限筛查，不排除翻译/改写、未审计材料或未知上游；CT原出版身份仍未知。未发现与已知开发选段直接派生或近重复证据，不声称完全独立或基础模型训练未见。若后续发现关系，hold/换来源，不改固定协议。

失败保留：沙箱内urllib代理URLError；USGS主站FAQ下载403、urllib出版PDF失败，随后curl正常TLS取得官方PDF；NASA curl连接关闭异常，随后urllib正常TLS完整读取主体；曾查DOE热泵操作/温控器页面404，未作为选段。USGS PDF渲染有codestream警告但成功产图，已实际检查单页与所选段落；原PDF及抽取保留，不修写原文。未关闭SSL或修改全局代理。

## 交付边界与下一步

HTML段落/列表保留完整，NASA前置同步条件、CDC化学污染和清水/冷却/容器上下文随选段保存；USGS按版面分栏核对，不能把抽取次序当阅读次序。所有选段均回切核对及SHA检查，v7提示/16源码身份保持；仅必要文档/数据检查，不跑全套测试，不调用模型。

本轮完成来源筛选材料；下一步由本人阅读完整选段及支持范围，再决定确认或替换。尚未制作评分要求、待评回答、标签、实际模型消息或执行入口；原规格、生产、历史批次及attempt标记不变。

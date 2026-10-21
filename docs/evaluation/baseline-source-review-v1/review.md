# 四组来源完整候选选段复核材料

2026-10-21。仅来源及问题方向候选，待本人复核；无待评回答、参考标签或模型预测。按本人本轮明确授权，公开本复核所需的完整候选选段与必要上下文；官方整份HTML/PDF及运行原始数据仍留忽略data。HTML抽取用标准HTMLParser去script/style/noscript、解码实体、逐行合并空白；PDF为pypdf原抽取，不修字；位置指所保存文本Unicode区间。USGS单页海报已渲染核对，非按抽取顺序猜版面。

## CAND-BL-NWS-FORECAST

Forecast Terms — NOAA National Weather Service, Weather Forecast Office Pago Pago

Unnumbered live page; no content-specific publication/update date identified; snapshot 2026-10-21

[官方原文](https://www.weather.gov/ppg/forecast_terms)

快照：NOAA.html；55132字节；SHA256 `fe2773f6722f67874632cfa07c8e8aede961208cce9702c8458578940f5545ae`。抽取文本 `NOAA.txt`，SHA256 `9daf5b34ca45be7dfe21e9eea10ec2ac13e7c287f1682ad493ee5421d8a67383`。

### 两个问题方向（未制题卡）

1. PoP定义：可测液态或冻结降水水当量、给定时间、区域内任一点；区分概率与降水时长/面积断言。
2. 预报表达的条件规则：高降水概率达到60%时天空状况可以省略；在明确假定预报概率下判断规则是否允许，区分may与must。

### 完整选段及上下文

#### NWS-X1

Precipitation Probability heading; complete body paragraph including following on/off sentence；区间[3119,3747)；选段SHA256 `320dd854bee60780ed75175abb41bdc17da331064461519596817cc660440694`。

```text
The probability of precipitation (POP), is defined as the likelihood of occurrence (expressed as a percent) of a measurable amount of liquid precipitation (or the water equivalent of frozen precipitation) during a specified period of time at any given point in the forecast area. Measurable precipitation is equal to or greater than 0.01 inches. Unless specified otherwise, the time period is normally 12 hours. NWS forecasts use such categorical terms as occasional, intermittent, or periods of to describe a precipitation event that has a high probability of occurrence (80%+), but is expected to be of an "on and off" nature.
```

#### NWS-X2

Sky Condition heading; complete opening paragraph, no table rows needed for this direction；区间[2182,2476)；选段SHA256 `d71c65d90b9b4dd852d94834b306d3a6c962305d35319978deb8158d088c2b78`。

```text
The sky condition describes the predominant/average sky cover based on percent of the sky covered by opaque (not transparent) clouds. If a high probability of precipitation (60% or greater) is expected, then the sky condition may be omitted since it is inferred from the precipitation forecast.
```

### 能支持与不能推出

只支持本页术语及表达惯例；12小时带unless specified otherwise，不推广至所有NWS产品；不把概率当确定降雨或面积/时长保证，60%允许省略不等于强制省略。无需判断天气实况或安全。

### 谱系与外部近重复线索

NWS各办公室Forecast Terms、术语表、PFM说明、镜像与翻译按相关定义谱系关联。Juneau材料出现默认6小时，PPG本页为通常12小时，表格阈值也可能不同；不得混页补条件。本组不取概率乘积公式或不同办公室云量表。NRC其他报告有气象术语不等于旧half-life定义谱系；本次旧NRC选段全文核查另列。

- [关联资料](https://www.weather.gov/media/ajk/brochures/ConvectivevsStratiform.pdf)
- [关联资料](https://www.weather.gov/mrx/pfm_explain)
- [关联资料](https://forecast.weather.gov/glossary.php?word=K)

同主题或同机构不自动同源；本轮有限历史审计摘要及身份见[筛选报告](../../reviewer-baseline-source-screening-v1.md)；完整审计文件留忽略data。未获本人选段确认、未成为最终保留组。

## CAND-BL-USGS-GIP106

100-Year Flood—It’s All About Chance: Haven’t we already had one this century? — USGS; Robert R. Holmes, Jr. and Karen Dinicola

General Information Product 106, April 2010; DOI 10.3133/gip106; 1-page poster

[官方原文](https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf)

快照：USGS-gip106.pdf；1128297字节；SHA256 `52af423da7f5d6e5f6363b7e3c2c4a7c181fd4236cbdde167d4c9a714c6a0e26`。抽取文本 `USGS-page-1.txt`，SHA256 `f3f5b5995ad4f0fbf0c66712a5a8aa69343fe887aa4f75be748aaf76d4b54659`。

### 两个问题方向（未制题卡）

1. 百年洪水与1%年超越概率的关系：相等或超越、平均重现期与不规则间隔，不解释为固定100年一次。
2. 洪水定义及成因关系：较高流量漫过自然或人工河岸，多种成因为什么不推出相同量级、持续时间或影响。

### 完整选段及上下文

#### USGS-X1

PDF page 1, left column: So what is a 100-year flood and how is it determined?, complete first paragraph；区间[136,639)；选段SHA256 `64484e5160384a33fd3ea9d5da08dcffa723569ebe515f7995965b53ec8ec48f`。

```text
In the 1960’s, the United States government 
decided to use the 1-percent annual 
exceedance probability (AEP) flood as 
the basis for the National Flood Insurance 
Program. The 1-percent AEP flood was 
thought to be a fair balance between 
protecting the public and overly stringent 
regulation.  Because the 1-percent AEP flood 
has a 1 in 100 chance of being equaled or 
exceeded in any 1 year, and it has an average 
recurrence interval of 100 years, it often is referred to as the “100-year flood”.
```

#### USGS-X2

PDF page 1, left top: What is a Flood?, complete body paragraph; extraction order differs from visual order；区间[1904,2625)；选段SHA256 `b71dfcf69c8238efb51e89dafeaef03dbbf1695c8139fd357d483feb0fc42d1b`。

```text
A flood is any relatively high streamflow 
overtopping the natural or artificial banks in 
any reach of a stream. Floods occur for many 
reasons, such as long-lasting rainfall over a broad 
area, locally intense thunderstorm-generated 
rainfall, or rapid melting of a large snow pack 
with or without accompanying rainfall.  Because 
floods result from many different circumstances, 
not all floods are equal in magnitude, duration, or 
effect.   Placing floods in context allows society to address such issues as the risk to life and 
property, and to study and understand the environmental benefits of floods. Trying to place 
contextual framework around floods is where such terms as “100-year flood” came into 
being.
```

#### USGS-X3

PDF page 1, middle panel: On the river near me..., complete first paragraph; graph is not needed for this paragraph；区间[2843,3062)；选段SHA256 `64dba6138583108b74d09b39a75aa75ab3de8c0c4b01f250bb014fb4dd632e65`。

```text
The “100-year 
flood” is an 
estimate of the 
long-term average 
recurrence interval, 
which does not 
mean that we really 
have 100 years 
between each flood 
of greater or equal 
magnitude. Floods 
happen irregularly.
```

### 能支持与不能推出

只解释海报定义和概念关系；不预测某河具体日期/流量/现场风险，不把示例测站量值泛化，不在本候选中考图表运算、30年风险计算或置信区间语义。第二方向不强行构造某具体地区原因已查实。

### 谱系与外部近重复线索

GIP106海报、handout/网页版本、USGS百年洪水FAQ及引用本海报的Fact Sheet 2011-3146、转载与翻译同组关联。主站FAQ直连403，搜索只作关联线索；本组证据载体以实际取得PDF为准，不冒称已取得FAQ快照。

- [关联资料](https://doi.org/10.3133/gip106)
- [关联资料](https://www.usgs.gov/faqs/we-had-a-100-year-flood-two-years-a-row-how-can-be)
- [关联资料](https://pubs.usgs.gov/fs/2011/3146/)

同主题或同机构不自动同源；本轮有限历史审计摘要及身份见[筛选报告](../../reviewer-baseline-source-screening-v1.md)；完整审计文件留忽略data。未获本人选段确认、未成为最终保留组。

## CAND-BL-NASA-ORBITS

Catalog of Earth Satellite Orbits — NASA Earth Observatory; story by Holli Riebeek, design by Robert Simmon

Article Sep 04, 2009; page last updated Nov 14, 2025; no numbered edition

[官方原文](https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/)

快照：NASA-retrieved.html；351468字节；SHA256 `4e2d4a17f345defa498e56646628010937f9bd7db74e8e192aab3e459906a79e`。抽取文本 `NASA-retrieved.txt`，SHA256 `981659e93d61fc972a61cbcd5137f18c80452817d7129afff8b24b5d26429f56`。

### 两个问题方向（未制题卡）

1. 轨道偏心率与倾角分别描述什么；圆轨道/赤道轨道的条件不能互相替代。
2. 地球同步与地球静止轨道的关系；在明确假定已是圆形、赤道上空的地球同步轨道时应用条件，不将所有同步轨道都说成地面相对静止。

### 完整选段及上下文

#### NASA-X1

Body before Three Classes of Orbit, complete eccentricity paragraph；区间[9408,9744)；选段SHA256 `4a8712f267248db1cd243771d8465b046ac1718b414a0adf2cf4026ef41163bf`。

```text
In addition to height, eccentricity and inclination also shape a satellite’s orbit. Eccentricity refers to the shape of the orbit. A satellite with a low eccentricity orbit moves in a near circle around the Earth. An eccentric orbit is elliptical, with the satellite’s distance from Earth changing depending on where it is in its orbit.
```

#### NASA-X2

Body before Three Classes of Orbit, complete inclination paragraph；区间[10087,10348)；选段SHA256 `110db3b02e55085eea3dd1dd230beaa6f076b1ed9ea347b7b6c04d329d8a866c`。

```text
Inclination is the angle of the orbit in relation to Earth’s equator. A satellite that orbits directly above the equator has zero inclination. If a satellite orbits from the north pole (geographic, not magnetic) to the south pole, its inclination is 90 degrees.
```

#### NASA-X3

High Earth Orbit, complete first paragraph；区间[10810,11244)；选段SHA256 `337f58d94b4f847a74899d82b43986a18980dfbec177ba00f9d88bb8b1c1765a`。

```text
When a satellite reaches exactly 42,164 kilometers from the center of the Earth (about 36,000 kilometers from Earth’s surface), it enters a sort of “sweet spot” in which its orbit matches Earth’s rotation. Because the satellite orbits at the same speed that the Earth is turning, the satellite seems to stay in place over a single longitude, though it may drift north to south. This special, high Earth orbit is called geosynchronous.
```

#### NASA-X4

High Earth Orbit, complete second paragraph；区间[11245,11504)；选段SHA256 `9dda7d71f4dd3a11dff9fa1912903eea21626ee2b01c557d5db05aff915b7c2e`。

```text
A satellite in a circular geosynchronous orbit directly over the equator (eccentricity and inclination at zero) will have a geostationary orbit that does not move at all relative to the ground. It is always directly over the same place on the Earth’s surface.
```

必要上下文（不省略前提）：

```text
When a satellite reaches exactly 42,164 kilometers from the center of the Earth (about 36,000 kilometers from Earth’s surface), it enters a sort of “sweet spot” in which its orbit matches Earth’s rotation. Because the satellite orbits at the same speed that the Earth is turning, the satellite seems to stay in place over a single longitude, though it may drift north to south. This special, high Earth orbit is called geosynchronous.
A satellite in a circular geosynchronous orbit directly over the equator (eccentricity and inclination at zero) will have a geostationary orbit that does not move at all relative to the ground. It is always directly over the same place on the Earth’s surface.
```

### 能支持与不能推出

保留geosynchronous前提，单有零偏心率/零倾角不足以推出同步；不把科普理想描述当真实卫星轨道测定、维护保证、通信性能或碰撞安全认证；不引入开普勒推导、未交付公式或方向假定。

### 谱系与外部近重复线索

旧Earth Observatory OrbitsCatalog路径、新science.nasa.gov迁移页、转载翻译及同句教材关联；文章列出Air University Space Primer、Pisacane Fundamentals of Space Systems等参考，作为上游线索，未下载扩展教材。已知开发教材是电路/电力资料，未发现这些参考身份直接关联；不能声称追溯了全部上游。

- [关联资料](https://earthobservatory.nasa.gov/features/OrbitsCatalog/)
- [关联资料](https://science.nasa.gov/learn/basics-of-space-flight/chapter5-1/)

同主题或同机构不自动同源；本轮有限历史审计摘要及身份见[筛选报告](../../reviewer-baseline-source-screening-v1.md)；完整审计文件留忽略data。未获本人选段确认、未成为最终保留组。

## CAND-BL-CDC-WATER

How to Make Water Safe in an Emergency — CDC, National Center for Environmental Health

Page date Sept. 19, 2024; no numbered edition; snapshot 2026-10-21

[官方原文](https://www.cdc.gov/water-emergency/about/)

快照：CDC.html；71056字节；SHA256 `403a9acc422568c7bc9cbf0feea9cb3f9aacf30ddc325f8bfc0ecd48b6e53f38`。抽取文本 `CDC.txt`，SHA256 `18bdcec7656d47491881e980dd37453a293d4bc6e5bdbefd5010426f85b4bec0`。

### 两个问题方向（未制题卡）

1. 应急煮水规则应用：保留清水、翻滚沸腾起算、高于6500英尺时3分钟及冷却/容器步骤；仅在明确题设条件下应用。
2. 杀菌方法的适用边界：含燃料/有毒化学品/放射性材料的水不能靠煮沸或消毒保证安全，与一般杀菌规则的关系。

### 完整选段及上下文

#### CDC-X1

Overview > Water with fuel or toxic chemicals in it, complete paragraph；区间[2759,3050)；选段SHA256 `dce65965f5109e297981d947507ef7185ac6f9a8dfa95f8140cfd8f3af27f33a`。

```text
You cannot make water containing fuel, toxic chemicals, or radioactive materials safe by boiling or disinfecting it. If you know or suspect your water contains fuel or toxic chemicals: 1) Use bottled water or a different source of water 2) Contact your health department for specific advice.
```

#### CDC-X2

Boil > Steps for boiling water, complete preparation paragraph and all three list items；区间[3208,3599)；选段SHA256 `e0623bab395fb8b45978b61e4f0a03067a74b7e3c89422f125c2abfdfc502dc7`。

```text
If the water is cloudy, first filter it through a clean cloth, paper towel, or coffee filter. Another option is to let it settle. Then, draw off the clear water and follow the steps below.
Bring clear water to a rolling boil for 1 minute (at elevations above 6,500 feet, boil for 3 minutes).
Let the boiled water cool.
Store the boiled water in clean, sanitized containers with tight covers.
```

必要上下文（不省略前提）：

```text
If you don’t have safe bottled water, boil your water to make it safe to drink.
Boiling is the best way to kill germs in water.
Steps for boiling water
If the water is cloudy, first filter it through a clean cloth, paper towel, or coffee filter. Another option is to let it settle. Then, draw off the clear water and follow the steps below.
Bring clear water to a rolling boil for 1 minute (at elevations above 6,500 feet, boil for 3 minutes).
Let the boiled water cool.
Store the boiled water in clean, sanitized containers with tight covers.
```

#### CDC-X3

Overview, complete paragraph specifying health-department recommendations；区间[2297,2475)；选段SHA256 `15778dead45aa73065a19307b5989738a315233bb452391146d01900ad771188`。

```text
Instead, use bottled, boiled, or treated water for drinking, cooking, and personal hygiene. Follow recommendations from your health department for boiling or treating your water.
```

### 能支持与不能推出

用于文献规则理解和假定应用，不诊断实际水源、人体状况或现场饮用安全；不扩成任意处理技术永远不能净化，不制作漂白剂配比/治疗问题，不从清澈推出无化学污染。严格保留above而非擅改为大于等于阈值。

### 谱系与外部近重复线索

CDC旧healthywater入口、新water-emergency页、同主题Natural Disasters音频稿/资料单、多语言翻译按相关谱系同组；EPA链接是相关上游/交叉说明线索，不借其他机构不同海拔阈值替换本页。放射性污染限制与NRC半衰期定义不是同一选段/派生关系，旧NRC文本仍实际查重。

- [关联资料](https://www.cdc.gov/natural-disasters/psa-toolkit/boil-water-advisory.html)
- [关联资料](https://www.cdc.gov/water-emergency/about/drinking-water-advisories-an-overview.html)
- [关联资料](https://stacks.cdc.gov/view/cdc/128149)

同主题或同机构不自动同源；本轮有限历史审计摘要及身份见[筛选报告](../../reviewer-baseline-source-screening-v1.md)；完整审计文件留忽略data。未获本人选段确认、未成为最终保留组。


## 公开范围及身份核对

2026-10-21本人要求直接上传云端仓库，并将其作为以后复核材料的默认交付方式。本文件只调整本地复核稿的公开状态/链接说明，不改选段、方向、定位或支持边界。[选段JSON](selected-source-excerpts-v1.json)与忽略目录原JSON逐字节相同；原始快照及历史清单不覆盖。来源/标签仍未获本人确认，本次上传不升级为验收或付费授权。

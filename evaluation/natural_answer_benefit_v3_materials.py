"""Prediction-before development questions/references; never delivered to agents."""
N=[
 dict(id='N1',family='coordination',kind='direct',question='NERC资料如何描述输电运营方TO与配电提供方DP边界负荷的建模，以及建模位置有哪些选择？',
      required=['边界通常用MW和Mvar显式负荷建模','母线高压侧，或降压变压器及/或等效配电阻抗之后'],critical=['把通常改成全部唯一位置','漏掉一类建模位置','MW/Mvar角色错误']),
 dict(id='N2',family='coordination',kind='linked',question='结合NERC资料，说明边界负荷功率因数、双方无功支撑关系与关键负荷水平下的协调如何联系起来。',
      required=['边界LPF影响BES电压和无功表现','负荷不应过度依赖BES支撑，BES不应仅依赖负荷支撑','确定峰荷/轻载等关键负荷水平建议LPF时，TO与DP协调重要'],critical=['把重要增强为必须履行的强制义务','把不应过度依赖写成禁止任何支撑','混淆正文与元数据法律效力']),
 dict(id='N3',family='contingencies',kind='direct',question='NERC事故分析段落如何描述失去一个元件后的系统表现？请交代适用的分析类型和负荷条件。',
      required=['N-1失去一个元件，立即且无操作员干预，紧急热额定值和电压限值内','适用稳态和稳定要求','包括预测最小和最大负荷条件，性能应始终具备'],critical=['把无干预或立即条件漏失/反转','仅用于稳态或仅用于稳定','把紧急限值写成正常额定值']),
 dict(id='N4',family='contingencies',kind='linked',question='按NERC资料比较正常运行、单一故障、选定N-2及极端扰动的描述，说明它们在热额定值、电压限值与稳定性讨论中分别处于什么位置。',
      required=['全部计划元件在役时正常热额定值/电压限值','N-1立即无干预的紧急热额定值/电压限值及稳态稳定要求','确定稳定极限时承受选定N-2','极端扰动较严重较不可能，避免电压崩溃/级联/失稳'],critical=['将N-1限定无据转移全部N-2','when变成only：N-2仅用于稳定/仅在稳定极限考虑','本段未规定变成工程上不存在其他要求']),
 dict(id='N5',family='resources',kind='direct',question='NERC资料中的动态无功资源怎样随电网电压变化调整输出？这种资源的电压控制运行方式有哪些？',
      required=['指定电压带宽内响应电网电压变化','自动、实时、连续范围调节无功输出','维持电压设定点或电压下垂模式'],critical=['任何电压无限带宽','漏带宽或自动实时连续关键限定','遗漏一种运行方式','把部分设备周波级响应泛化全部设备']),
 dict(id='N6',family='resources',kind='linked',question='按NERC资料，从接入后的输出特性与投入退出操作看，动态和静态无功资源有什么不同？额定电压在这种比较中有什么意义？',
      required=['动态在指定带宽内自动实时连续调节以响应电网电压','静态额定电压下固定额定输出，能力随电压平方变化','静态按系统条件手动或自动投切，接入后固定额定贡献'],critical=['静态任意电压实际输出恒定','静态连续调节与动态投切混淆','漏平方依赖或手动自动投切','额定贡献变成固定实际出力']),
 dict(id='N7',family='line_model',kind='direct',question='请用文字解释NERC资料所列短输电线路无功传输式的模型假设与各符号含义，不作数值计算。',
      required=['短线路、忽略线路R和B','Vs/Vr为送端/受端电压幅值，X为线路电抗','δ为两端相角差，式子描述无功传输'],critical=['保留R/B或适用任意长线','Vs/Vr或X/δ含义颠倒','凭空数值或工程保证']),
 dict(id='N8',family='line_model',kind='linked',question='为什么NERC资料在讨论无功传输时把电压控制与无功控制联系起来？请结合短线路模型中各驱动量的相对作用解释，并交代模型适用条件。',
      required=['短线路且忽略R/B','无功受电压差、相角差、电气阻抗影响','相角差影响相对小，电压差/阻抗强得多','电压与无功控制紧密耦合，反之亦然'],critical=['强弱方向颠倒','紧密耦合强化为互为因果或单一控制量','漏模型边界或推至任意线路'])
]
RULES=dict(origin='AI-assisted source-first development reference under user supervision; seen source families, not expert gold/holdout',
 acceptable='Equivalent correct meanings accepted; no fixed answer string scoring. No model answer supplied. Extra accurate source-bounded explanation is allowed.',
 protection='Preserve every correct initial technical point, source condition, mode, scope and requested answer point. Corrected text with critical new error or required-point loss is mixed, never pure improvement.',
 evaluation='Separately assess actual delivered Evidence support and correctness/completeness against frozen reference. Missing retrieval remains in denominator; no support is not contradiction. Improvement requires source-verifiable key correction and complete delivery.',
 labels=['improved','equivalent','worse','mixed','unevaluable'],
 gate='At least 2 N improvements in at least 2 families, no worse/mixed among other evaluable N and no critical new errors/required-point loss across batch. H separate, no production adoption/second batch regardless.')

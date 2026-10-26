# 本轮16次新请求

只计本轮实际发送；历史12次首轮背景不在此表。单位：token、毫秒。无格式纠正，金额/币种全部未知。阶段并行时模型耗时不可相加作链耗时。完整预测见predictions.json，模型原记录见cases.json。

| 序号 | 例 | 阶段 | 答案版本 | 输入 | 输出 | 缓存命中 | 未命中 | 模型毫秒 | 结构 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | A1 | revision | 1 | 3858 | 461 | 0 | 3858 | 2695 | valid_structure |
| 2 | A1 | claim_extraction | 2 | 1607 | 805 | 1280 | 327 | 3014 | valid_structure |
| 3 | A1 | evidence_verification | 2 | 7031 | 390 | 256 | 6775 | 2730 | valid_structure |
| 4 | A1 | power_domain_review | 2 | 6416 | 725 | 1280 | 5136 | 4335 | valid_structure |
| 5 | A2 | revision | 1 | 3887 | 528 | 640 | 3247 | 2877 | valid_structure |
| 6 | A2 | claim_extraction | 2 | 1626 | 1051 | 1280 | 346 | 4299 | valid_structure |
| 7 | A2 | evidence_verification | 2 | 5847 | 429 | 256 | 5591 | 2595 | valid_structure |
| 8 | A2 | power_domain_review | 2 | 6794 | 806 | 1280 | 5514 | 4164 | valid_structure |
| 9 | A3 | revision | 1 | 3827 | 477 | 640 | 3187 | 2559 | valid_structure |
| 10 | A3 | claim_extraction | 2 | 1585 | 668 | 1280 | 305 | 3085 | valid_structure |
| 11 | A3 | evidence_verification | 2 | 5669 | 383 | 256 | 5413 | 2485 | valid_structure |
| 12 | A3 | power_domain_review | 2 | 5933 | 661 | 1280 | 4653 | 3668 | valid_structure |
| 13 | A4 | revision | 1 | 4445 | 568 | 640 | 3805 | 2929 | valid_structure |
| 14 | A4 | claim_extraction | 2 | 1634 | 497 | 1280 | 354 | 2142 | valid_structure |
| 15 | A4 | evidence_verification | 2 | 6988 | 521 | 384 | 6604 | 2893 | valid_structure |
| 16 | A4 | power_domain_review | 2 | 5716 | 632 | 1280 | 4436 | 4120 | valid_structure |

历史首轮免费回放分表（原记录身份保留cases.json，不当本轮新预测/费用）：

| 例 | 历史调用数 | 原输入token | 原输出token |
|---|---:|---:|---:|
| A1 | 3 | 14628 | 1933 |
| A2 | 3 | 13451 | 2254 |
| A3 | 3 | 14896 | 2336 |
| A4 | 3 | 14845 | 2110 |

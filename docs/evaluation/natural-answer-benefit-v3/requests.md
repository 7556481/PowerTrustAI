# 本轮49次实际请求

金额及币种全部未知，无账单。历史4份生成仅为背景，不计本轮费用。初始44、原额度格式纠正5；没有业务Revision或重审请求。耗时是单模型请求毫秒，不能将并行阶段相加当链耗时。

| 序号 | 例 | 槽/阶段 | 纠正 | 输入 | 输出 | 缓存命中 | 未命中 | 毫秒 | 结构 |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | N1 | generation/generation | False | 9260 | 178 | 1280 | 7980 | 1820 | valid_structure |
| 2 | N1 | audit/claim_extraction | False | 1621 | 512 | 1152 | 469 | 2458 | valid_structure |
| 3 | N1 | audit/evidence_verification | False | 16080 | 512 | 256 | 15824 | 2822 | valid_structure |
| 4 | N1 | audit/power_domain_review | False | 11814 | 646 | 1280 | 10534 | 3357 | valid_structure |
| 5 | N2 | generation/generation | False | 8771 | 252 | 1280 | 7491 | 1868 | valid_structure |
| 6 | N2 | audit/claim_extraction | False | 1617 | 872 | 1280 | 337 | 3415 | valid_structure |
| 7 | N2 | audit/evidence_verification | False | 15902 | 282 | 256 | 15646 | 1952 | valid_structure |
| 8 | N2 | audit/power_domain_review | False | 12524 | 717 | 1280 | 11244 | 3621 | valid_structure |
| 9 | N3 | generation/generation | False | 10272 | 406 | 1280 | 8992 | 2429 | invalid_structure |
| 10 | N3 | generation/generation | True | 10883 | 355 | 10240 | 643 | 2230 | valid_structure |
| 11 | N3 | audit/claim_extraction | False | 1738 | 1055 | 1280 | 458 | 4177 | valid_structure |
| 12 | N3 | audit/evidence_verification | False | 19104 | 806 | 256 | 18848 | 4825 | valid_structure |
| 13 | N3 | audit/power_domain_review | False | 14283 | 1038 | 1280 | 13003 | 4889 | valid_structure |
| 14 | N4 | generation/generation | False | 7076 | 352 | 1280 | 5796 | 2305 | valid_structure |
| 15 | N4 | audit/claim_extraction | False | 1751 | 985 | 1280 | 471 | 3904 | valid_structure |
| 16 | N4 | audit/evidence_verification | False | 13464 | 711 | 256 | 13208 | 4348 | valid_structure |
| 17 | N4 | audit/power_domain_review | False | 11077 | 908 | 1280 | 9797 | 4614 | valid_structure |
| 18 | N5 | generation/generation | False | 8769 | 398 | 1280 | 7489 | 2851 | valid_structure |
| 19 | N5 | audit/claim_extraction | False | 1826 | 1458 | 1280 | 546 | 4710 | valid_structure |
| 20 | N5 | audit/evidence_verification | False | 17774 | 733 | 256 | 17518 | 4177 | valid_structure |
| 21 | N5 | audit/power_domain_review | False | 13724 | 1163 | 1280 | 12444 | 6125 | invalid_structure |
| 22 | N5 | audit/power_domain_review | True | 15747 | 1162 | 13696 | 2051 | 4137 | valid_structure |
| 23 | N6 | generation/generation | False | 9012 | 391 | 1280 | 7732 | 2615 | valid_structure |
| 24 | N6 | audit/claim_extraction | False | 1786 | 1328 | 1280 | 506 | 4611 | invalid_structure |
| 25 | N6 | audit/claim_extraction | True | 3536 | 1329 | 1664 | 1872 | 4420 | valid_structure |
| 26 | N6 | audit/evidence_verification | False | 18032 | 638 | 256 | 17776 | 3420 | valid_structure |
| 27 | N6 | audit/power_domain_review | False | 13644 | 1174 | 1280 | 12364 | 6389 | valid_structure |
| 28 | N7 | generation/generation | False | 9266 | 118 | 1280 | 7986 | 1394 | valid_structure |
| 29 | N7 | audit/claim_extraction | False | 1600 | 576 | 1280 | 320 | 2275 | valid_structure |
| 30 | N7 | audit/evidence_verification | False | 16237 | 400 | 256 | 15981 | 2225 | valid_structure |
| 31 | N7 | audit/power_domain_review | False | 11878 | 619 | 1280 | 10598 | 3228 | valid_structure |
| 32 | N8 | generation/generation | False | 9018 | 316 | 1280 | 7738 | 2166 | valid_structure |
| 33 | N8 | audit/claim_extraction | False | 1675 | 887 | 1280 | 395 | 3031 | valid_structure |
| 34 | N8 | audit/evidence_verification | False | 17016 | 520 | 256 | 16760 | 3006 | valid_structure |
| 35 | N8 | audit/power_domain_review | False | 12921 | 984 | 1280 | 11641 | 4925 | valid_structure |
| 36 | H1 | audit/claim_extraction | False | 1711 | 865 | 1536 | 175 | 3420 | valid_structure |
| 37 | H1 | audit/evidence_verification | False | 20797 | 679 | 1408 | 19389 | 3514 | invalid_structure |
| 38 | H1 | audit/power_domain_review | False | 14523 | 766 | 11136 | 3387 | 3751 | valid_structure |
| 39 | H1 | audit/evidence_verification | True | 21669 | 731 | 20736 | 933 | 2895 | invalid_structure |
| 40 | H2 | audit/claim_extraction | False | 1703 | 1208 | 1536 | 167 | 4049 | valid_structure |
| 41 | H2 | audit/evidence_verification | False | 23891 | 563 | 1536 | 22355 | 3433 | valid_structure |
| 42 | H2 | audit/power_domain_review | False | 15995 | 931 | 11520 | 4475 | 4812 | valid_structure |
| 43 | H3 | audit/claim_extraction | False | 1715 | 1058 | 1536 | 179 | 3825 | valid_structure |
| 44 | H3 | audit/evidence_verification | False | 20407 | 705 | 1408 | 18999 | 3737 | valid_structure |
| 45 | H3 | audit/power_domain_review | False | 14279 | 736 | 10496 | 3783 | 3424 | valid_structure |
| 46 | H4 | audit/claim_extraction | False | 1671 | 982 | 1536 | 135 | 3932 | valid_structure |
| 47 | H4 | audit/evidence_verification | False | 21942 | 473 | 1536 | 20406 | 2975 | valid_structure |
| 48 | H4 | audit/power_domain_review | False | 14510 | 988 | 10752 | 3758 | 4404 | invalid_structure |
| 49 | H4 | audit/power_domain_review | True | 17594 | 835 | 14464 | 3130 | 3104 | valid_structure |

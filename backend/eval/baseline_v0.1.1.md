# AI 家庭维修诊断助手评测 baseline v0.1

> 本文件是本地模板分类器 baseline（`LLM call rate: 0.0%`），用于观察规则兜底能力。外测候选最终口径以真实生产链路报告 `baseline_v0.1.1_prod.md` 为准：分类 95.5% / 紧急 95.0% / 高风险召回 98.1% / 误报 1.4% / 0 crash（关键词修复 + 4 条真值人工审核后）。

- Generated at: 2026-06-22T08:33:15.017360+00:00
- Samples: 200
- Classification accuracy: 94.0%
- Urgency accuracy: 94.0%
- High-risk recall: 98.1% (52/53)
- High-risk false-positive rate: 1.4%
- LLM call rate: 0.0% (0/200)

## Confusion Matrix

Expected | Predicted counts
--- | ---
ac_not_cooling | ac_not_cooling: 19, water_leak: 1
circuit_trip | circuit_trip: 20
drain_blocked | drain_blocked: 20, water_leak: 2
floor_drain_smell | drain_blocked: 1, floor_drain_smell: 17
lock_failure | circuit_trip: 1, lock_failure: 19
range_hood_gas_stove | circuit_trip: 1, range_hood_gas_stove: 19
wall_mold | wall_mold: 17, water_leak: 1
water_heater_failure | circuit_trip: 2, water_heater_failure: 18
water_leak | circuit_trip: 1, drain_blocked: 1, water_heater_failure: 1, water_leak: 19
window_hardware | window_hardware: 20

## Failed Samples

ID | Expected | Predicted | Expected urgency | Predicted urgency | Evidence
--- | --- | --- | --- | --- | ---
gold_v011_005 | water_leak | water_heater_failure | S | S | 热水器, 电热水器
gold_v011_006 | water_leak | circuit_trip | S | S | 配电箱
gold_v011_016 | water_leak | drain_blocked | B | A | 马桶
gold_v011_023 | drain_blocked | water_leak | A | A | 根据用户描述做初步分类
gold_v011_028 | drain_blocked | drain_blocked | B | A | 下水很慢
gold_v011_030 | drain_blocked | water_leak | B | A | 根据用户描述做初步分类
gold_v011_057 | ac_not_cooling | water_leak | B | A | 漏水
gold_v011_074 | circuit_trip | circuit_trip | A | S | 跳闸
gold_v011_092 | lock_failure | lock_failure | B | S | 门锁, 打不开
gold_v011_096 | lock_failure | circuit_trip | C | B | 没电
gold_v011_102 | wall_mold | wall_mold | B | C | 发霉, 墙面, 霉味
gold_v011_110 | wall_mold | water_leak | C | A | 漏水, 水痕
gold_v011_116 | water_leak | water_leak | B | A | 水痕
gold_v011_125 | water_heater_failure | circuit_trip | S | S | 焦味, 发烫
gold_v011_126 | water_heater_failure | circuit_trip | S | S | 漏电
gold_v011_147 | range_hood_gas_stove | circuit_trip | S | S | 插座, 火花
gold_v011_148 | range_hood_gas_stove | range_hood_gas_stove | S | B | 油烟机, 漏油
gold_v011_169 | floor_drain_smell | drain_blocked | B | A | 水槽

## Notes

- 8 条争议/边界样本已完成产品裁定：164、105、173、116 改真值并标记 `human_reviewed`；169、110 维持原真值，属于模型分类缺陷；074、092 维持原紧急等级，属于模型紧急等级过提。
- 后 4 条不阻塞外测，但应作为外测期重点观察项。

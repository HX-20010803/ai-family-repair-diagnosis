# AI 家庭维修诊断助手评测 baseline v0.1

- Generated at: 2026-06-21T08:11:46.944787+00:00
- Samples: 30
- Classification accuracy: 96.7%
- Urgency accuracy: 90.0%
- High-risk recall: 100.0% (6/6)
- High-risk false-positive rate: 0.0%
- LLM call rate: 0.0% (0/30)

## Confusion Matrix

Expected | Predicted counts
--- | ---
ac_not_cooling | ac_not_cooling: 3
circuit_trip | circuit_trip: 3
drain_blocked | drain_blocked: 3
floor_drain_smell | drain_blocked: 1, floor_drain_smell: 2
lock_failure | lock_failure: 3
range_hood_gas_stove | range_hood_gas_stove: 3
wall_mold | wall_mold: 3
water_heater_failure | water_heater_failure: 3
water_leak | water_leak: 3
window_hardware | window_hardware: 3

## Failed Samples

ID | Expected | Predicted | Expected urgency | Predicted urgency | Evidence
--- | --- | --- | --- | --- | ---
gold_011 | circuit_trip | circuit_trip | A | C | 跳闸
gold_026 | floor_drain_smell | drain_blocked | B | A | 下水
gold_029 | window_hardware | window_hardware | A | B | 五金, 松动

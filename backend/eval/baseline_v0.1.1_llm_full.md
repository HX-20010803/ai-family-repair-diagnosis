# AI 家庭维修诊断助手评测 baseline v0.1.1 — llm_full

- Mode: full DeepSeek (every sample bypasses template-first)
- Generated at: 2026-06-22T02:37:29.520711+00:00
- Samples: 200
- Classification accuracy: 92.5%
- Urgency accuracy: 94.0%
- High-risk recall: 98.1% (52/53)
- High-risk false-positive rate: 1.4%
- Classification LLM call rate: 100.0% (200/200)
- Generation LLM call rate: 99.0% (198/200)
- Crashed samples (handle_message raised): 0/200

## Confusion Matrix

Expected | Predicted counts
--- | ---
ac_not_cooling | ac_not_cooling: 19, water_leak: 1
circuit_trip | circuit_trip: 20
drain_blocked | drain_blocked: 20
floor_drain_smell | drain_blocked: 6, floor_drain_smell: 14
lock_failure | lock_failure: 20
range_hood_gas_stove | circuit_trip: 1, range_hood_gas_stove: 19
wall_mold | wall_mold: 17, water_leak: 3
water_heater_failure | circuit_trip: 2, water_heater_failure: 18
water_leak | circuit_trip: 1, drain_blocked: 1, water_leak: 18
window_hardware | window_hardware: 20

## Failed Samples

ID | Expected | Predicted | Exp urgency | Pred urgency | Provider | Cls LLM
--- | --- | --- | --- | --- | --- | ---
gold_v011_006 | water_leak | circuit_trip | S | S | deepseek | yes
gold_v011_016 | water_leak | drain_blocked | B | A | deepseek | yes
gold_v011_028 | drain_blocked | drain_blocked | B | A | deepseek | yes
gold_v011_057 | ac_not_cooling | water_leak | B | A | deepseek | yes
gold_v011_074 | circuit_trip | circuit_trip | A | S | deepseek | yes
gold_v011_092 | lock_failure | lock_failure | B | S | deepseek | yes
gold_v011_102 | wall_mold | wall_mold | B | C | deepseek | yes
gold_v011_105 | wall_mold | water_leak | S | S | deepseek | yes
gold_v011_110 | wall_mold | water_leak | C | A | deepseek | yes
gold_v011_116 | wall_mold | water_leak | B | A | deepseek | yes
gold_v011_125 | water_heater_failure | circuit_trip | S | S | deepseek | yes
gold_v011_126 | water_heater_failure | circuit_trip | S | S | deepseek | yes
gold_v011_147 | range_hood_gas_stove | circuit_trip | S | S | deepseek | yes
gold_v011_148 | range_hood_gas_stove | range_hood_gas_stove | S | B | deepseek | yes
gold_v011_163 | floor_drain_smell | drain_blocked | S | S | deepseek | yes
gold_v011_164 | floor_drain_smell | drain_blocked | S | S | deepseek | yes
gold_v011_168 | floor_drain_smell | drain_blocked | B | A | deepseek | yes
gold_v011_169 | floor_drain_smell | drain_blocked | B | A | deepseek | yes
gold_v011_171 | floor_drain_smell | drain_blocked | B | A | deepseek | yes
gold_v011_173 | floor_drain_smell | drain_blocked | B | B | deepseek | yes

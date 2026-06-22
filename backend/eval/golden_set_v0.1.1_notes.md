# Golden Set v0.1.1 说明

本文件是 PRD 第 21.4 要求的 200 条人工标注黄金集候选版。

## 生成原则

- 覆盖 MVP 10 类故障场景，每类 20 条。
- 覆盖标准表达、口语表达、信息不足、高风险、否定/边界和混合线索。
- 每条包含二级分类、一级分类、紧急等级、是否高风险和推荐处理路径。
- 当前标记为 `ai_generated_candidate`，进入外测前需要人工重点审核高风险和争议样本。

## 分布

secondary | samples | high_risk
--- | ---: | ---:
ac_not_cooling | 20 | 2
circuit_trip | 20 | 10
drain_blocked | 20 | 3
floor_drain_smell | 20 | 2
lock_failure | 20 | 6
range_hood_gas_stove | 20 | 10
wall_mold | 20 | 2
water_heater_failure | 20 | 6
water_leak | 20 | 8
window_hardware | 20 | 4

- Total samples: 200
- High-risk samples: 53

## 人工审核建议

优先审核：

1. 所有 `is_high_risk=true` 样本。
2. S/A 临界样本。
3. 带否定或不确定表达的燃气、电路、漏水样本。
4. 用户真实外测新增的错分样本。

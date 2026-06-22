# AI 家庭维修诊断助手 MVP 验收说明

## 1. 封版范围

版本：`v0.1.0-mvp`

本版本是第一版移动端 H5 MVP，目标是验证家庭维修文字诊断的完整链路：

- H5 聊天页、结果页、维修记录页。
- 文字输入诊断和最多 3 轮追问。
- 10 类家庭维修知识库。
- S/A/B/C 紧急等级和高风险规则兜底。
- DeepSeek/Qwen OpenAI-compatible LLM Adapter。
- PostgreSQL 数据库、Alembic 迁移、结构化诊断结果落库。
- 成本日志、内容安全日志、每日 3 次完整诊断限额。
- 诊断结果保存为维修记录，并支持列表查询。

补充状态：`v0.1.1-external-test-candidate` 已在第一版范围内补齐真实 DeepSeek、PostgreSQL 和腾讯云 TMS 文本内容安全验收，进入外测候选准备阶段。

## 2. 已覆盖的 10 类知识库

| code | 场景 |
| --- | --- |
| `water_leak` | 漏水渗水 |
| `drain_blocked` | 马桶/下水堵塞 |
| `ac_not_cooling` | 空调不制冷 |
| `circuit_trip` | 电路跳闸/插座冒烟 |
| `lock_failure` | 门锁故障 |
| `wall_mold` | 墙面发霉/墙皮脱落 |
| `water_heater_failure` | 热水器故障 |
| `range_hood_gas_stove` | 油烟机/燃气灶问题 |
| `floor_drain_smell` | 地漏反味/厨卫异味 |
| `window_hardware` | 门窗五金/纱窗损坏 |

## 3. 数据闭环

| 闭环 | 落库位置 | 验收点 |
| --- | --- | --- |
| 诊断会话 | `diagnosis_sessions` / `diagnosis_messages` | 用户输入和追问消息可追溯 |
| 诊断结果 | `diagnosis_results` | 保存分类、紧急等级、完整 JSON、模型版本、知识库版本 |
| 成本日志 | `cost_logs` | LLM 成功或模板降级都会写成本记录 |
| 内容安全 | `content_safety_logs` | 不安全输入被拦截并留痕，不继续诊断 |
| 免费限额 | `quota_usage` | 同一匿名 token 每日最多 3 次完整诊断 |
| 维修记录 | `repair_records` | 诊断结果可保存为维修记录并列表查询 |

## 4. 验收命令

### 4.1 后端自动化测试

```powershell
python -m unittest backend.tests.test_config backend.tests.test_knowledge_base backend.tests.test_core_services backend.tests.test_llm_adapter backend.tests.test_persistence_flow
```

通过标准：

- 测试输出 `OK`。
- 覆盖配置加载、知识库完整性、核心诊断、LLM Adapter、持久化闭环。

### 4.2 数据库迁移

```powershell
$env:DATABASE_URL="postgresql+psycopg://repair:repair@localhost:5432/repair_ai"
cd backend
python -m alembic upgrade head
```

通过标准：

- 输出 `Running upgrade -> 20260620_0001, initial schema` 或提示已在最新版本。
- `/api/v1/health` 返回 `database = ok`。

### 4.3 部署冒烟

后端运行后，在项目根目录执行：

```powershell
python backend\scripts\deploy_smoke.py http://127.0.0.1:8000
```

通过标准：

- `health.status = ok`
- `health.database = ok`
- `diagnosis_type = result`
- `urgency = S`

### 4.4 真实 LLM 冒烟

```powershell
python backend\scripts\llm_smoke.py http://127.0.0.1:8000
```

通过标准：

- `llm_configured = true`
- `llm_active_provider = deepseek` 或 `qwen`
- `model_provider = deepseek` 或 `qwen`
- `urgency = S`

### 4.5 前端 H5 构建

```powershell
cd frontend
pnpm run typecheck
pnpm run build:h5
```

通过标准：

- `vue-tsc --noEmit` 退出码为 0。
- `uni build -p h5` 输出 `DONE Build complete.`。

### 4.6 腾讯云文本内容安全验收

外测候选配置：

```env
DEPLOYMENT_MODE=external_test
CONTENT_SAFETY_PROVIDER=tencent
CONTENT_SAFETY_REGION=ap-guangzhou
CONTENT_SAFETY_TIMEOUT_SECONDS=30
```

通过标准：

- `/api/v1/health` 返回 `content_safety_active_provider = tencent`。
- 腾讯云 TMS 真实文本审核返回通过。
- `deploy_smoke.py` 在腾讯 TMS + DeepSeek 链路下通过。
- 供应商权限、计费或网络异常时，接口返回受控错误 `CONTENT_SAFETY_UNAVAILABLE`，不得裸 500。

## 5. 已知限制

- 第 1 版仅交付文字诊断；图片、语音、ASR、微信小程序正式版属于后续版本。
- H5 匿名 token 基于本地存储，清缓存或换设备会丢失历史归属。
- `internal_demo` 可使用本地基础敏感词策略；`external_test` / `production` 必须使用正式内容安全服务。当前已接入并验收腾讯云 TMS 文本审核。
- 维修记录第 1 版支持基础保存和列表，费用回填、复发追踪、提醒属于 V1.1。
- LLM 调用失败时会降级为 `local-template`，不会阻断诊断；真实 LLM 是否接通以 `llm_smoke.py` 为准。
- PRD 第 21.4 要求的 200 条黄金评测集已生成 `eval/golden_set_v0.1.1_200.jsonl`。外测候选最终口径以真实生产链路 `eval/baseline_v0.1.1_prod.md` 为准：分类 95.5%、紧急 95.0%、高风险召回 98.1%、高风险误报 1.4%、0 crash（关键词修复 + 4 条真值人工审核后），已达到候选线。

## 6. MVP 通过结论

当以下条件全部满足时，第一版 MVP 可判定为完成：

- PostgreSQL 启动并迁移成功。
- 后端测试全部通过。
- `deploy_smoke.py` 通过。
- `llm_smoke.py` 返回真实模型供应商。
- uni-app H5 类型检查和构建通过。

外测候选补充条件：

- `DEPLOYMENT_MODE=external_test`。
- 腾讯云 TMS 文本内容安全真实调用通过。
- `deploy_smoke.py` 在正式内容安全链路下通过。
- 200 条黄金评测集 E2E baseline 已达到候选线；8 条争议/边界样本已完成产品裁定，其中 4 条已改真值并标记 `human_reviewed`，4 条保留为外测期模型观察项。

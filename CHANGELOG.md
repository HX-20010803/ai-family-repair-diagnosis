# Changelog

## v0.1.1-external-test-candidate - 2026-06-21

第一版 MVP 进入外测候选准备阶段。本版本不扩大第 1 版产品范围，重点补齐真实供应商、外测门禁、验收脚本和评测准备。

### Added

- 腾讯云 TMS 文本内容安全正式 provider，支持 TC3-HMAC-SHA256 签名调用 `TextModeration`。
- `external_test` / `production` 内容安全门禁：正式模式不允许使用 `local` 内容安全。
- 内容安全供应商异常受控返回 `CONTENT_SAFETY_UNAVAILABLE`，避免裸 500。
- 腾讯 TMS provider 对瞬时网络异常做确定性重试（默认 2 次，每次重新签名；腾讯业务错误不重试），避免单次抖动让整条诊断返回 503。
- `CONTENT_SAFETY_REGION` 和 `CONTENT_SAFETY_TIMEOUT_SECONDS` 配置项。
- 聊天页快捷问题改为单行横向滚动提示，避免独立两列问题区。
- 前端布局回归检查，禁止快捷问题退回两列 grid。
- 200 条黄金评测集 `eval/golden_set_v0.1.1_200.jsonl` 与 baseline `eval/baseline_v0.1.1.md`。
- 用户反馈接口 `POST /api/v1/diagnosis/results/{id}/feedback` 及结果页轻量反馈组件，对应 `diagnosis_feedback` 表（迁移 `20260621_0002`）。

### Changed

- 内容安全默认超时从 10 秒调整为 30 秒，适配真实云服务链路。
- `deploy_smoke.py` 请求超时从 20 秒调整为 90 秒，适配“用户输入审核 + LLM + AI 输出审核”的正式链路。
- `DEPLOYMENT.md` 明确腾讯 TMS 外测配置和常见供应商错误。
- 分类关键词修复：`floor_drain_smell` 补「地漏」「返味」，`drain_blocked`「下水」收窄为「下水慢」「下水很慢」以消除「下水道」子串噪声。
- 黄金评测集真值人工审核：裁定 4 条争议样本（164/173 `floor_drain_smell`→`drain_blocked`、105/116 `wall_mold`→`water_leak`），`review_status` 标 `human_reviewed`；prod 分类准确率经关键词修复 + 真值审核后 92.0%→95.5%、紧急 94.0%→95.0%，0 回归。

### Verified

- `/api/v1/health` 在 `external_test` 模式返回 `content_safety_active_provider=tencent`。
- 腾讯云 TMS 真实文本审核通过。
- DeepSeek 真实诊断链路通过。
- PostgreSQL 数据库健康检查通过。
- `deploy_smoke.py` 在腾讯 TMS + DeepSeek 链路下连跑 10 次 10/10 通过（TMS 重试后无间歇性 503）。
- 后端完整测试 `50 tests OK`（含腾讯 TMS 重试 3 个用例）。
- uni-app H5 `check:chat-layout`、`typecheck`、`build:h5` 通过。
- E2E 200 条黄金集 baseline：prod（真实生产线，关键词修复 + 4 条真值人工审核后）分类 95.5% / 紧急 95.0% / 高风险召回 98.1% / 误报 1.4% / 0 crash；llm_full（全量 DeepSeek，关键词修复前）分类 92.5%。详见 `eval/baseline_v0.1.1_prod.md`、`eval/baseline_v0.1.1_llm_full.md`。

### Deferred

- 域名、HTTPS、图片上传、语音/ASR、登录和游客记录合并。

### Notes

- `eval/baseline_v0.1.1.md` 保留模板分类器 baseline；外测候选最终口径以真实生产链路 `eval/baseline_v0.1.1_prod.md` 为准。
- 8 条样本已按产品裁定收口：164/105/173/116 改真值并标记 `human_reviewed`；169、110 维持原真值，074、092 维持原紧急等级，作为外测期重点观察的模型缺陷样本。

## v0.1.0-mvp - 2026-06-21

第一版移动端 H5 MVP 封版。

### Added

- uni-app + Vue 3 + TypeScript + Pinia H5 前端。
- 聊天诊断页、结构化结果页、维修记录列表页。
- FastAPI 后端接口：
  - `POST /api/v1/diagnosis/sessions`
  - `POST /api/v1/diagnosis/sessions/{id}/messages`
  - `POST /api/v1/diagnosis/sessions/{id}/complete`
  - `GET /api/v1/diagnosis/results/{id}`
  - `POST /api/v1/repair-records`
  - `GET /api/v1/repair-records`
  - `GET /api/v1/health`
- PostgreSQL 数据模型和 Alembic 初始迁移。
- DeepSeek/Qwen OpenAI-compatible LLM Adapter。
- 父级工作区 `.env` 自动加载，支持本地统一管理 API Key。
- 10 类维修知识库 YAML。
- 价格规则、风险规则、追问模板、成本规则。
- 高风险规则兜底，电路冒烟/燃气味等场景优先 S 级安全提示。
- 内容安全基础敏感词拦截和日志。
- 每日 3 次完整诊断限额。
- 成本日志和诊断结果模型/Prompt/知识库版本留痕。
- `deploy_smoke.py` 部署冒烟脚本。
- `llm_smoke.py` 真实 LLM 冒烟脚本。
- `scripts/verify_mvp.ps1` 一键验收脚本。
- `MVP_ACCEPTANCE.md`、`DEPLOYMENT.md`、`DEMO_SCRIPT.md` 封版文档。

### Verified

- PostgreSQL Docker 容器可启动。
- Alembic 初始迁移可在 PostgreSQL 上执行。
- `/api/v1/health` 返回 `database=ok`。
- 真实 DeepSeek 调用可返回 `model_provider=deepseek`。
- 后端单元测试通过。
- uni-app H5 `typecheck` 和 `build:h5` 通过。

### Deferred

- 图片上传和图片识别。
- 语音上传和 ASR。
- 手机号登录。
- 微信 `openid` 和小程序体验版。
- 正式域名、HTTPS、生产内容安全服务。
- 维修记录费用回填、复发追踪、提醒。
- 管理后台和数据看板。

### Known Limitations

- H5 匿名 token 依赖 localStorage，不保证跨浏览器和跨设备归属。
- 第 1 版内容安全是本地基础策略，不适合直接公开生产。
- LLM 失败时会降级为本地模板，需用 `llm_smoke.py` 单独确认真实 LLM 连通。
- 价格区间为配置化参考，不构成最终报价。

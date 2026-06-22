# AGENTS.md — AI 家庭维修诊断助手

> 本文件是 AI 编程代理（Claude Code / Cursor / Copilot 等）在本项目工作的**操作守则**。
> 行为类通用准则（先思考再写、最小改动、每步验证、如实汇报）见全局 `~/CLAUDE.md`，此处不重复，只补充**本项目独有的领域知识与硬约束**。

## 1. 项目状态

- **当前阶段：第一版 MVP 已完成并进入封版验收。** 项目已包含 `frontend/`、`backend/`、`deploy/`、数据库迁移、10 类知识库、真实 LLM Adapter、H5 构建链和封版文档。
- **当前封版版本：`v0.1.0-mvp`。** 封版材料见 `MVP_ACCEPTANCE.md`、`DEPLOYMENT.md`、`DEMO_SCRIPT.md`、`CHANGELOG.md`。
- **路线：移动端 H5 先上线，小程序后适配**，分 4 版（见 PRD §13）。代理在写任何功能前，必须先确认它属于**哪一版范围**，避免把第 2/3/4 版能力塞进第 1 版（详见下方 AGENTS §5）。
- 工作语言：中文。用户可见文案、Prompt、业务说明文档用中文；标识符（变量/类型/函数/API）用英文；代码注释优先简洁准确，可中可英，不为翻译牺牲准确性（异常名、类型注解等技术注释倾向英文）。

## 2. 权威文档与阅读顺序

| 文档 | 角色 | 冲突时谁优先 |
| --- | --- | --- |
| `PRD.md` | 产品意图、用户链路、功能边界、合规与成本约束 | **产品语义和不可逾越约束（安全/成本/合规）以 PRD 为准** |
| `TECH_DESIGN.md` | 实现规格：架构、数据模型、API、流程编排、配置 | **技术实现细节以 TECH_DESIGN 为准**（它已对齐 PRD 并完成多轮修订） |

**动手前必读**：实现任意模块前，先读 TECH_DESIGN 中对应章节（章节号见下方各条），不要凭印象写。引用章节一律带文档前缀：`PRD §8.4` / `TECH §4.2` / `AGENTS §5`，**不裸写 `§x.y`**（裸写无法区分指 PRD 还是 TECH）。

## 3. 技术栈（第 1 版锁定）

- **前端**：uni-app + Vue 3 + TypeScript + Pinia + UnoCSS/Tailwind；首发 H5，不引入 Vue Router 作主路由（用 `pages.json`）。
- **后端**：FastAPI + Pydantic + SQLAlchemy 2.x + Alembic + PostgreSQL。**SQLite 仅限本地 Demo，不上线**（PRD §14.2、TECH §2.2）。
- **AI**：LLM 通过 `LLMAdapter` 抽象层接入（主 DeepSeek / 备 通义千问）；RAG 第 1 版用结构化检索，**不做向量检索**。
- **部署**：第 1 版单机 FastAPI + PostgreSQL + 临时域名/IP 即可验收；域名 HTTPS 进第 2 版。

## 4. 不可违反的硬约束

这是全项目最容易出错、最不能含糊的几条。任何改动若使其松动，必须先与人对齐，不得自行放宽。

1. **安全场景宁可误报不可漏报。** 当 LLM 无法确认风险是否真实存在时，**维持高风险提示并追问确认，不降级**。明确否定（如“没有燃气味”）才可解除 S 级。高风险规则召回的等级高于模型低估的结果。→ PRD §8.4、PRD §18.6；TECH §4.3、TECH §7.2。
2. **结构化输出，禁止原文直达前端。** LLM 必须输出 JSON 并经 Pydantic `DiagnosisResult` 校验（TECH §7.1）。校验失败重试 1 次，仍失败才降级为模板化结果，绝不把自然语言原文当结果返回。
3. **价格/规则/Prompt 配置化，不写死。** 价格、安全规则、追问模板、Prompt 模板放 `rules/*.yaml` 与 `prompt_templates`，**严禁写进 Prompt 字面量或业务代码**（价格是高变动数据）。→ TECH §2.3.2 职责分离、TECH §8。
4. **全程版本化留痕。** 每条诊断结果记录 `model_provider / model_version / prompt_version / knowledge_version / cost_total`，用于合规追溯。→ PRD §15.2；TECH §11.4。
5. **内容安全是外部可访问的前置门槛。** 对内演示可占位，但只要对外开放，用户输入和 AI 输出都必须过 `ContentSafetyService`；审核失败不进流程，**不把原始违规内容写日志**。→ TECH §7.6。
6. **成本是 MVP 硬约束，第 1 版就落库。** 单次完整诊断 ≤ 1 元、纯文本 ≤ 0.3 元。每次外部调用（LLM/ASR/图片/内容安全/RAG）逐条写 `cost_logs`，会话结束汇总 `diagnosis_results.cost_total`。超阈降级（低风险走模板、累计超阈改规则、全不可用出低置信度结果）。→ PRD §16；TECH §7.4。
7. **分类全程用 code，不允许自由文本。** 二级→一级分类是固定映射（PRD §8.3 映射表），规则校验不合法则修正并降置信度；结果页、价格匹配、记录统计共享同一套 code。安全风险是**横切属性**，不作故障分类。
8. **匿名标识按端区分，统一存 `anonymous_token`。** H5 用 localStorage UUID（**不可靠**，清缓存/换浏览器即丢，合并为“尽力而为”）；小程序用 `openid`（可靠）。不得把 H5 标识当可靠主键使用。→ PRD §15.4、PRD §13.3；TECH §7.5。
9. **密钥与配置不进版本库。** API Key、数据库连接串、模型密钥、内容安全凭证**一律不提交**，只允许提交不含真实值的 `env.example`；`.gitignore` 必须覆盖 `.env`、`*.key`、本地 SQLite 文件。
10. **数据模型变更必须带迁移。** 任何 `models/` 字段或表变更，必须同步生成 Alembic migration 并随提交入库；**禁止手工直接改线上库结构**。
11. **部署模式决定内容安全门槛。** 每次部署/交付说明必须标注 `DEPLOYMENT_MODE`：`internal_demo`（内容安全可占位）/ `external_test` / `production`。**`external_test` 与 `production` 未接内容安全（文本入+出；对外测试另需图片/语音转写）不得交付**。→ TECH §7.6。

## 5. 第 1 版范围边界（防范围蔓延）

**第 1 版必须交付**（PRD §9.1、TECH §10）：H5 聊天页、文字诊断、多轮追问（≤3 轮，每轮 ≤3 问）、10 类故障分类、S/A/B/C 紧急等级、高风险规则兜底、结构化结果页、价格区间参考、基础维修记录、FastAPI + PostgreSQL、LLM Adapter、规则库/价格库 YAML、基础部署脚本。

**第 1 版暂缓，不要顺手做**：图片上传、语音上传与 ASR、手机号登录、微信 `openid`、小程序体验版、正式域名/HTTPS、订阅消息。

> 注意：平台适配层（`PlatformAdapter`）的接口第 1 版就要定义好，H5 端录音/图片可降级为“即将支持”提示，但**接口先占位**，避免第 2 版回头改业务代码。→ TECH §7.8。

## 6. 模块边界（后端，TECH §3.2）

严格分层，跨层调用是错误：

- `api/` 只做 HTTP 入参/出参/错误码，不写业务逻辑。
- `services/` 负责业务编排（诊断主流程在 `DiagnosisService`，12 步编排见 TECH §4.2）。
- `ai/` 负责 LLM、RAG、Prompt、结构化解析。
- `rules/` 放 YAML 配置（`fault_taxonomy / safety_rules / question_templates / price_rules / cost_rules`）。
- `models/` 是 ORM，`schemas/` 是 Pydantic DTO，二者不要混。

前端同理：组件不直接拼接口，统一走 `services/`；状态在 `stores/`（会话用显式状态机，见 TECH §3.3）。

## 7. 已定架构决策（不要推翻）

这些是设计阶段反复推敲后定下的，除非有明确证据，否则别再开新方向：

- **第 1 版不做向量检索**。诊断流程是“先分类得到 `secondary_category` code → 再按 code 等值查询知识条目”，比向量检索更准更快零 embedding 成本。向量召回留到第 2 版分类置信度低时。→ TECH §2.3.2。
- **`DiagnosisService` 12 步编排**（TECH §4.2）：创建会话→标准化→内容安全→分类→风险召回+LLM 语义确认→RAG 检索→追问判断→生成结果→输出校验→价格匹配→写 results→写 cost_logs。改流程时同步检查这 12 步是否仍对齐。
- **风险判断三态**：明确真实风险→强制 S/A；明确否定→不提升；**无法确认→维持高风险+追问，不降级**（否定/假设用 LLM 语义确认，规则处理不了自然语言）。
- **消息表与原始输入分开**：`diagnosis_messages` 存完整对话流水，`diagnosis_sessions.original_input_json` 只存会话发起时的初始混合输入快照，两者不重复存。→ TECH §5.3。
- **额度计数并发安全**：`quota_usage` 表（TECH §5.7）用 `(subject_type, subject_id, quota_date)` 唯一索引自增。第 1 版存 PostgreSQL，第 2 版起 Redis。

## 8. 配置文件清单（`rules/`，TECH §8）

| 文件 | 用途 | 关键字段 |
| --- | --- | --- |
| `fault_taxonomy.yaml` | 故障分类树 | `primary_categories` / `secondary_categories`（带 `primary` 映射） |
| `safety_rules.yaml` | 高风险关键词召回 | `risk_type / keywords / urgency_level / negation_sensitive / action` |
| `question_templates.yaml` | 追问模板 | 按二级分类，`max_questions: 3` |
| `price_rules.yaml` | 价格区间 | `scene_code / city_tier / min/max_price / version` |
| `cost_rules.yaml` | 成本估算单价 | 按 capability，`estimated=true` 标注 |
| `knowledge/*.yaml` | 维修知识条目 | 按 `secondary_category` 分文件，每条带 `version` |

配置走版本号，支持重启加载/热加载，变更不改代码。`city_tier` 无城市信息时**默认 `other`**，不阻断价格展示。

## 9. 验证方式

代码建立后，按以下验证（TECH §9、TECH §11.2）。第一版 MVP 的完整验收命令已固化在 `MVP_ACCEPTANCE.md` 和 `scripts/verify_mvp.ps1`。

- **健康检查**：`GET /api/v1/health` 应返回 `database`、`llm_configured`、`llm_active_provider`、`rules_version`、`knowledge_version` 状态。任何部署/配置改动后先打这个。
- **后端测试**：`python -m unittest backend.tests.test_config backend.tests.test_knowledge_base backend.tests.test_core_services backend.tests.test_llm_adapter backend.tests.test_persistence_flow`，重点覆盖：多轮追问轮数限制、高风险规则命中、否定表达不误触发 S 级、价格匹配、结构化输出校验、持久化闭环。
- **后端冒烟**：`python backend\scripts\deploy_smoke.py http://127.0.0.1:8000`。
- **真实 LLM 冒烟**：`python backend\scripts\llm_smoke.py http://127.0.0.1:8000`，通过标准是 `model_provider=deepseek` 或 `qwen`。
- **前端测试**：`pnpm run typecheck` 和 `pnpm run build:h5`，覆盖 uni-app H5 类型检查和生产构建。
- **AI 评测**：黄金集 ≥ 200 条（覆盖 10 类，高风险 ≥ 50 条）。第 1 版跑通脚本产出 baseline，不强制阈值；第 2 版起按阈值（分类准确率、紧急度准确率、高风险召回率/误报率）验收。→ PRD §21.4；TECH §9.3。
- **成本核对**：每次完整诊断后查 `cost_logs` + `diagnosis_results.cost_total`，确认落在预算内。

## 10. 代理工作约定

- **先读对应 §章节再写代码**（TECH/PRD 都有清晰编号）。不确定章节范围时先 Grep 章节标题。
- **改流程/数据模型时做交叉引用检查**：TECH §4.2 编排 ↔ TECH §4.3 / TECH §4.4 / TECH §4.5 / TECH §2.3.2 / TECH §7.x；数据模型 ↔ 被引用的 API（TECH §6）和配置（TECH §8）。改一处要确认引用方仍成立。
- **配置变更必须 bump 版本**（price_rules / safety_rules / prompt / knowledge），否则启动校验或 CI 应报错。
- **不写超出当前版本范围的功能**（见 AGENTS §5）。若需求模糊，先确认版本归属再动手。
- **高危/安全相关逻辑改动，必须同步更新对应测试**（高风险召回、否定表达、不降级原则）。
- **AGENTS 与文档同步**：当 PRD 或 TECH 的阶段范围、数据模型、AI 流程、部署策略变化时，回头检查并更新 AGENTS 对应条目；AGENTS 是从两份源文档派生的操作要点，**若与 TECH/PRD 冲突，以 TECH/PRD 为准并订正 AGENTS**。

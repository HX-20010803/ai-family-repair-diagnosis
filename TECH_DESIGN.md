# AI 家庭维修诊断助手技术设计

## 1. 技术目标

本技术设计基于 `PRD.md`，目标是先交付可快速上线的移动端 H5 MVP，再逐步增强图片、语音、登录、微信小程序和合规能力。

### 1.1 分阶段技术范围

| 阶段 | 技术形态 | 核心能力 |
| --- | --- | --- |
| 第 1 版 | 移动端 H5 + FastAPI + PostgreSQL | 文字聊天诊断、多轮追问、故障分类、风险判断、结构化结果、基础维修记录 |
| 第 2 版 | H5 正式增强 | 域名、HTTPS、图片上传、语音上传/识别、基础登录、内容安全审核 |
| 第 3 版 | 微信小程序体验版 | 复用 H5 业务能力，适配微信录音、拍照、openid、一键拨号 |
| 第 4 版 | 微信小程序正式版 | 小程序审核、隐私接口、订阅消息、合规留痕、正式运营配置 |

第 1 版不把小程序正式审核、图片上传、语音识别、手机号登录作为阻塞项。

## 2. 技术栈选择

### 2.1 前端

| 技术 | 用途 | 选择理由 |
| --- | --- | --- |
| uni-app | 跨端应用框架 | 第 1 版发布 H5，后续复用到微信小程序 |
| Vue 3 | 前端框架 | 组件化、生态成熟，适合移动端 H5 |
| TypeScript | 类型系统 | 降低前后端接口和状态管理错误 |
| Pinia | 状态管理 | 管理诊断会话、用户状态、维修记录 |
| uni-app 页面路由 | 页面路由 | 通过 `pages.json` 管理聊天页、结果页、记录页、我的页面 |
| UnoCSS 或 Tailwind CSS | 样式工具 | 快速实现移动端响应式 UI |
| NutUI / TDesign Mobile 可选 | 移动端组件 | 表单、弹窗、Toast、按钮、上传组件 |

第 1 版前端首发移动端 H5，必须适配：

- 微信内置浏览器。
- iOS Safari。
- Android Chrome/系统浏览器。
- 360px-430px 常见手机宽度。

### 2.2 后端

| 技术 | 用途 | 选择理由 |
| --- | --- | --- |
| FastAPI | API 服务 | Python 生态适合 LLM/RAG，接口开发快 |
| Pydantic | 请求/响应校验 | 保证结构化诊断结果和接口类型稳定 |
| SQLAlchemy 2.x | ORM | 管理 PostgreSQL 数据模型和迁移 |
| Alembic | 数据库迁移 | 保证数据表版本可追踪 |
| PostgreSQL | 主数据库 | 第 1 版即上线使用，支持 JSON、索引、后续 `pgvector` |
| Redis | 后续缓存/限流 | 第 2 版起用于会话缓存、限流、异步任务状态 |
| Uvicorn/Gunicorn | 服务运行 | 部署 FastAPI |

第 1 版数据库直接使用 PostgreSQL。SQLite 仅允许本地 Demo 或临时开发，不作为上线数据库。

### 2.3 AI 与检索

| 模块 | 第 1 版 | 后续版本 |
| --- | --- | --- |
| LLM | 国产合规模型 API，通过 Adapter 接入 | 支持多供应商切换、成本路由、降级模型 |
| RAG | 轻量知识库检索，可先用 PostgreSQL 全文检索/JSON 配置 | 接入 `pgvector`，数据量大后再考虑 Milvus |
| 规则引擎 | 本地配置化规则 | 后台可配置、版本化、灰度发布 |
| ASR | 第 1 版不阻塞 | 第 2 版接入云端语音识别 |
| 多模态图片识别 | 第 1 版不阻塞 | 第 2 版接入图片识别和图片内容安全 |
| 内容安全 | 内部演示可先占位；只要开放给外部用户，必须接入文本输入和 AI 输出审核 | 第 2 版接入图片、语音转写和多媒体审核 |

#### 2.3.1 LLM Adapter 设计

模型不直接耦合业务代码，统一通过 `LLMAdapter` 抽象层调用，便于切换供应商、做成本路由和降级（对应 PRD §14.3、§18.5、§18.6）。

候选模型（第 1 版默认 DeepSeek 主模型 + 通义千问备用；若供应商条件限制，至少接入 1 个）：

| 候选 | 角色 | 说明 |
| --- | --- | --- |
| 通义千问（阿里） | 主/备 | 已完成生成式 AI 备案，支持 JSON 模式和 function calling |
| DeepSeek | 主/备 | 价格低、文本能力强，适合追问和分类 |
| GLM（智谱） | 备 | 多模态能力可复用至第 2 版图片识别 |
| 文心（百度） | 备 | 合规材料齐全，生态完整 |

第 1 版默认配置：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `PRIMARY_LLM_PROVIDER` | `deepseek` | 默认主模型，优先控制成本和响应速度 |
| `FALLBACK_LLM_PROVIDER` | `qwen` | 备用模型，用于主模型超时、限流或结构化输出失败 |
| `LLM_TIMEOUT_SECONDS` | `15` | 单次调用超时 |
| `LLM_RETRY_ON_PARSE_ERROR` | `1` | 结构化输出解析失败后最多重试 1 次 |
| `LLM_MAX_INPUT_CHARS` | `8000` | 第 1 版限制单次上下文长度（多轮追问累积 + RAG 知识注入需留余量），超长则截断早期消息 |

如果实际 API Key 或合规材料只允许接入其中一个供应商，则以环境变量配置为准，但代码必须保留主备切换接口。

Adapter 接口约定：

- `chat(messages, schema?, options?) -> ChatResult`，统一入参为消息列表，可选传入结构化输出 schema。
- `ChatResult` 必须返回 `content`、`usage`（token 数）、`latency_ms`、`provider`、`model_version`、`cost_estimate`。
- 单次调用超时默认 15 秒，超时计入失败触发降级。
- Adapter 对同一会话内的分类、风险判断结果按输入哈希做短期缓存，避免重复调用。

降级优先级：

1. 主模型（如 DeepSeek）。
2. 备模型（如通义）。
3. 规则 + 知识库模板（无 LLM 调用，用于低风险常见问题或全部模型不可用时）。

每次降级切换都写入 `cost_logs`，标注 `status=degraded` 和原因，便于复盘失败率。

#### 2.3.2 RAG 知识库与检索

知识库为诊断提供原因、排查步骤、风险提示，并约束 LLM 在知识范围内回答、减少幻觉（对应 PRD §12）。

##### 关键决策：第 1 版用结构化检索，不做向量检索

诊断流程是"先分类得到 `secondary_category` code → 再检索"。分类一旦确定，知识条目就是一条 `WHERE secondary_category = code` 的等值查询，**比向量检索更准、更快、零 embedding 成本**。向量检索只在分类前或分类置信度低时（需要从全库召回候选）才有价值，第 1 版先不做，省掉 pgvector 和 embedding 调用成本。

##### 知识库形态（分阶段）

- 第 1 版：知识量小（10 类场景，每类 2-5 条），用 `knowledge/*.yaml` 按场景分文件，启动时加载到内存，按 `secondary_category` code 建索引。无需数据库表。
- 第 2 版+：迁移到 `knowledge_entries` 表 + pgvector，支持语义召回、版本管理和后台编辑。

知识库版本：

- 每个知识条目保留自身 `version` 字段。
- 服务启动时对 `knowledge/*.yaml` 文件内容计算整体 `knowledge_hash`，格式如 `knowledge:2026.06:<sha256前8位>`。
- 每次诊断把本次使用的 `knowledge_hash` 写入 `diagnosis_results.knowledge_version`。
- 知识文件变更必须更新条目 `version`，否则 CI 或启动校验应提示失败。

知识条目结构对齐 PRD §12.2：

```yaml
- code: ac_not_cooling
  secondary_category: ac_not_cooling
  title: 空调不制冷
  symptoms: ["有风但不冷", "制冷慢", "显示故障代码"]
  possible_causes: ["滤网堵塞", "制冷剂不足", "室外机散热差", "压缩机故障"]
  safe_self_checks: ["检查模式是否为制冷", "检查温度设定", "检查滤网是否堵塞"]
  risk_warnings: ["涉及加氟、电路、压缩机维修应联系品牌售后"]
  professional_required: true
  price_scene_code: ac_not_cooling   # 关联价格库，不在此重复价格
  source_type: manual
  version: "2026.06"
```

##### 检索流程

第 1 版（结构化 + 关键词）：

1. 分类输出 `secondary_category` code。
2. `RagService.retrieve(code, symptoms)`：按 code 取该场景全部条目（通常 1-3 条）；若多条，按用户症状与条目 `symptoms` 的全文匹配度排序取 top 2。
3. 返回结构化知识上下文。

第 2 版+ 增强语义召回：

- 分类置信度 < 0.5 时，用 pgvector 对 `symptoms` + `possible_causes` 做向量召回，为分类器提供候选场景。
- 混合检索：结构化（code 等值）+ 语义（向量）+ 关键词（全文），结果归并去重。

##### 注入 LLM 与幻觉控制

- 召回的知识条目作为 system prompt 上下文注入。
- Prompt 约束："仅依据提供的知识回答；超出知识范围的现象写入 `uncertainty_note` 并建议线下检查。"
- `possible_causes`、`safe_self_checks`、`risk_warnings` 优先直接引用知识库原文，LLM 只做组织与个性化，不杜撰新原因。

##### 职责分离（避免知识库膨胀）

三类数据变动频率和用途不同，通过 code 关联但不混表：

| 数据 | 存放 | 变动频率 | 用途 |
| --- | --- | --- | --- |
| 知识（原因/排查/风险） | `knowledge/*.yaml` 或 `knowledge_entries` | 低 | 注入 LLM 上下文 |
| 价格区间 | `price_rules.yaml` | 高 | 结果页价格展示 |
| 安全关键词规则 | `safety_rules.yaml` | 中 | 高风险兜底召回 |

### 2.4 部署

第 1 版推荐：

```text
移动端 H5
  -> FastAPI
    -> PostgreSQL
    -> LLM API
    -> 本地规则库/价格库/知识库
```

第 2 版增强：

```text
域名 + HTTPS
  -> Nginx / Caddy
  -> H5 静态资源
  -> FastAPI
    -> PostgreSQL
    -> Object Storage
    -> ASR / 图片识别 / 内容安全 / LLM
```

## 3. 项目结构

建议采用前后端分离的单仓库结构：

```text
AI物业C端产品/
  PRD.md
  TECH_DESIGN.md
  frontend/
    package.json
    pages.json
    manifest.json
    uni.scss
    vite.config.ts
    src/
      main.ts
      App.vue
      static/
      uni_modules/
      pages/
        chat/
          index.vue
          components/
            ChatMessage.vue
            ChatInput.vue
            QuickFaultChips.vue
            SafetyBanner.vue
        result/
          index.vue
          components/
            UrgencyCard.vue
            PriceReferenceCard.vue
            ActionList.vue
        records/
          index.vue
          detail.vue
        mine/
          index.vue
      stores/
        session.ts
        user.ts
        records.ts
      services/
        api.ts
        diagnosis.ts
        records.ts
        platform/
          index.ts
          h5.ts
          miniprogram.ts
      types/
        diagnosis.ts
        records.ts
        user.ts
      styles/
        variables.css
        mobile.css
  backend/
    pyproject.toml
    alembic.ini
    app/
      main.py
      core/
        config.py
        security.py
        logging.py
        errors.py
      api/
        v1/
          router.py
          diagnosis.py
          records.py
          users.py
          feedback.py
          health.py
      models/
        user.py
        diagnosis.py
        repair_record.py
        media_file.py
        feedback.py
        config_tables.py
      schemas/
        diagnosis.py
        repair_record.py
        user.py
        feedback.py
      services/
        diagnosis_service.py
        question_service.py
        risk_service.py
        price_service.py
        record_service.py
        content_safety_service.py
        cost_service.py
      ai/
        llm_adapter.py
        prompt_templates.py
        rag_service.py
        output_parser.py
      rules/
        fault_taxonomy.yaml
        safety_rules.yaml
        question_templates.yaml
        price_rules.yaml
        cost_rules.yaml
      knowledge/
        water_leak.yaml
        ac_not_cooling.yaml
        ...
      db/
        session.py
        base.py
      migrations/
      tests/
        test_diagnosis_flow.py
        test_risk_rules.py
        test_price_service.py
  deploy/
    nginx.conf
    docker-compose.yml
    env.example
  docs/
    api.md
    prompt_versions.md
```

### 3.1 前端组织原则

- `pages/chat` 承载首页和诊断对话页，第 1 版打开即聊天。
- `pages/result` 承载结构化诊断结果。
- `pages/records` 承载维修记录列表和详情。
- `pages.json` 管理 uni-app 页面路由、导航栏和分包；不引入普通 Vue Router 作为主路由。
- `manifest.json` 管理 H5 和微信小程序构建配置。
- `uni.scss` 放全局样式变量，移动端适老化字号、按钮高度和风险色统一从这里定义。
- `stores/session.ts` 只保存当前诊断会话状态。
- `services/diagnosis.ts` 封装诊断相关 API，不在组件里直接拼接口。
- 类型定义放在 `types/`，与后端响应结构对齐。

### 3.2 后端组织原则

- `api/` 只负责 HTTP 入参、出参和错误码。
- `services/` 负责业务编排。
- `ai/` 负责 LLM、RAG、Prompt、结构化输出解析。
- `rules/` 保存可配置规则，先用 YAML/JSON，后续可迁移到数据库后台。
- `models/` 是数据库 ORM。
- `schemas/` 是 Pydantic DTO。

### 3.3 前端会话状态机

诊断会话是前端最复杂的状态，必须用显式状态机管理，避免"结果返回""用户又发消息""重试"等并发场景下的状态错乱。

状态定义：

| 状态 | 含义 | 输入栏 |
| --- | --- | --- |
| idle | 无进行中会话 | 可用 |
| creating | 正在创建会话 | 禁用 |
| asking | 追问中，等待用户补充 | 可用 |
| completing | 正在生成诊断结果 | 禁用 |
| completed | 结果已返回，待保存 | 可用 |
| saved | 已保存为维修记录 | 可用 |
| error | 失败，可重试 | 可用（重试） |

状态流转：

```text
idle --发消息--> creating --创建成功--> asking
asking --AI 追问--> asking
asking --用户补充--> asking
asking --信息够了/点"生成结果"--> completing
completing --结果返回--> completed
completed --保存--> saved
任意 --失败--> error --重试--> 回到失败前状态
saved/completed --发新消息--> creating（新会话）
```

关键约束：

- `creating`、`completing` 状态下禁用输入栏，防止并发请求。
- `error` 保留已收集的消息，重试不丢上下文。
- 状态与后端 `diagnosis_sessions.status` 对齐：`asking` ≈ diagnosing，`completed` ≈ completed。

### 3.4 前端状态管理（stores）

对应 `stores/` 目录，使用 Pinia。原则：stores 只存"当前需要"的状态，不把后端数据全量同步到前端，避免一致性问题。

`useSessionStore`（当前诊断会话）：

- state：`sessionId`、`status`（状态机）、`messages[]`、`roundCount`、`currentResult`、`error`
- actions：`createSession`、`sendMessage`、`completeDiagnosis`、`reset`、`retry`
- 只保存当前会话；历史会话从后端拉取，不缓存在 store。

`useUserStore`（用户与匿名标识）：

- state：`anonymousToken`、`user`（游客时为 null）、`isLoggedIn`
- actions：`ensureAnonymousToken`（首次访问时通过平台适配层生成/读取）、`login`、`mergeAnonymous`、`logout`
- `anonymousToken` 由平台适配层 `getAnonymousToken()` 提供，store 只持有。

`useRecordsStore`（维修记录）：

- state：`list[]`、`pagination`、`filters`
- actions：`fetchList`、`saveRecord`、`patchRecord`（回填实际结果）
- 列表按需分页加载，详情按 id 从后端取，不全文缓存。

## 4. 核心业务流程

### 4.1 第 1 版文字诊断流程

```text
用户输入故障描述
  -> 前端创建诊断会话
  -> 后端内容安全预检，内部演示可用基础敏感词，外部可访问必须接入文本输入审核
  -> 故障初步分类
  -> 风险规则召回
  -> 判断是否需要追问
  -> 返回追问问题或生成诊断结果
  -> 用户补充信息，最多 3 轮
  -> 生成结构化诊断结果
  -> 保存维修记录
```

### 4.2 诊断服务编排

`DiagnosisService` 负责主流程（各步骤的服务职责见 §4.3-§4.5、§7、§2.3.2）：

1. 创建或读取 `diagnosis_sessions`，写入本轮用户消息到 `diagnosis_messages`。
2. 标准化用户输入（去标点、归一化口语）。
3. **内容安全审核**：调用 `ContentSafetyService` 审核用户文本；不通过则返回 `CONTENT_UNSAFE`，不进入后续流程（对应 §7.6）。
4. **故障分类**：调用 LLM 输出 `secondary_category`、`primary`、`confidence`，规则校验 `secondary → primary` 映射（对应 §4.4）。
5. **风险召回与确认**：`RiskService` 按关键词召回高风险候选；命中后由 LLM 做一次语义确认（是否真实风险、是否否定/假设），决定紧急等级（对应 §4.3、§7.2）。
6. **RAG 检索**：`RagService.retrieve(secondary_category, symptoms)` 取知识条目，作为生成上下文（对应 §2.3.2）。
7. **追问判断**：`QuestionService` 判断关键字段是否补齐、轮数是否超限；不足则生成追问并返回，流程在此挂起等待用户补充（对应 §4.5）。
8. **生成诊断结果**：字段补齐或达上限时，调用 `LLMAdapter`（注入分类、风险、知识、追问上下文）生成结构化结果。
9. **输出校验**：`OutputParser` 用 Pydantic 校验 JSON；失败重试 1 次，仍失败降级为模板化结果（对应 §7.1）。
10. **价格匹配**：`PriceService` 按 `secondary_category → scene_code` + `city_tier` 匹配价格区间（对应 §7.7、§8.4）。
11. 写入 `diagnosis_results`（含模型/Prompt/知识库版本、`cost_total`）。
12. 记录 `cost_logs`（每次外部调用逐条写入）。

说明：第 3-7 步在第 1 版只有文字输入时按序执行；第 2 版接入图片/语音后，内容安全审核扩展为多模态，RAG 检索补充图片证据。

### 4.3 风险判断流程

安全风险不作为故障一级分类，而是横切属性：

```text
用户输入
  -> 关键词召回高风险候选（safety_rules.yaml）
  -> LLM 语义确认：是否真实风险、是否否定/假设表达
  -> 明确真实风险：强制 S/A 级
  -> 明确否定（如"没有燃气味"）：不提升等级
  -> 无法确认风险是否真实：维持高风险提示 + 追问确认，不降级
```

关键原则（与 PRD §8.4、§18.6 一致）：**安全场景宁可误报不可漏报**。当 LLM 无法确认风险不存在时，维持高风险提示并追问确认，不得直接降为 A/B/C 级。否定/假设判断用 LLM 语义确认（规则难以可靠处理"没有""担心""是不是"等自然语言表达），确认结果作为风险等级依据。

示例：

- “插座冒烟了” -> S 级。
- “没有燃气味” -> 不触发 S 级。
- “我担心是不是燃气泄漏” -> 无法确认风险不存在，维持燃气风险提示，追问是否闻到燃气味、是否有报警器提示。

### 4.4 故障分类流程

分类是结构化结果的基础，由 LLM 主导、规则校验：

1. 标准化用户输入（去标点、归一化口语表达）。
2. LLM 按 `fault_taxonomy.yaml` 的 code 输出 `primary`、`secondary`、`confidence`、`evidence`。
3. 规则校验 `secondary → primary` 映射是否合法（对应 PRD §8.3 映射表），不合法则修正或降置信度。
4. `confidence < 0.6` 时不直接出结果，转入追问补全关键字段。
5. 仍无法分类时输出"暂无法判断"，提示用户补充描述或图片（第 2 版）。

分类结果与结果页、价格匹配、记录统计共享同一套 code，全程不允许自由文本分类。

### 4.5 多轮追问编排

`QuestionService` 维护追问状态机，避免重复问和无限追问（对应 PRD §8.2、§9.4）：

- 会话内维护 `asked_fields`（已问字段）和 `collected_fields`（已确认字段）。
- 每轮从 `question_templates.yaml` 取该场景必问字段，剔除已问/已答，最多取 3 个。
- 每次诊断最多 3 轮（`question_round_count`）。
- 停止追问的判定（任一满足）：
  - 必问字段已补齐。
  - 已达 3 轮上限。
  - 命中 S 级高风险后，优先给安全指引，不再追问非安全字段。
- 超 3 轮仍信息不足：用现有信息生成 `confidence < 0.6` 的低置信度结果，`uncertainty_note` 必填。
- 用户可随时点"生成诊断结果"提前结束。

## 5. 数据模型

### 5.1 users

存储用户基础身份。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| openid | varchar | 微信 openid，H5 阶段可为空 |
| unionid | varchar | 微信 unionid，可为空 |
| phone | varchar | 手机号，第 2 版登录使用 |
| nickname | varchar | 昵称 |
| is_realname_verified | boolean | 是否实名或完成合规登录 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

### 5.2 diagnosis_sessions

存储一次聊天诊断会话。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| user_id | UUID/null | 关联用户，游客可为空 |
| anonymous_token | varchar | H5 游客 ID 或微信 openid |
| original_input_json | jsonb | 原始混合输入 |
| input_type | varchar | text/voice/image/mixed |
| voice_transcript | text | 语音识别文本 |
| question_round_count | int | 已追问轮数 |
| status | varchar | diagnosing/completed/cancelled |
| deleted_at | timestamptz/null | 用户删除时间 |
| retention_until | timestamptz/null | 合规审计保留到期时间 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

索引：

- `idx_diagnosis_sessions_user_id`
- `idx_diagnosis_sessions_anonymous_token`
- `idx_diagnosis_sessions_created_at`

### 5.3 diagnosis_messages

建议新增消息表，避免只在 session 里存大 JSON。

与 `diagnosis_sessions.original_input_json` 的边界：`original_input_json` 只存**会话发起时的初始混合输入快照**（用户第一条消息的文字/图片/语音引用），用于快速还原；`diagnosis_messages` 是**完整对话流水**（用户每一轮、AI 每一次追问和结果都单独成行），用于多轮上下文和审计。两者不重复存储同一内容：初始输入在 messages 里也有对应首条，original_input_json 仅作结构化快照。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| session_id | UUID | 会话 ID |
| role | varchar | user/assistant/system |
| content_type | varchar | text/image/voice/result |
| content | text | 文本内容 |
| content_json | jsonb | 图片、语音、结果卡片等结构化内容 |
| created_at | timestamptz | 创建时间 |

### 5.4 diagnosis_results

存储结构化诊断结果。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| session_id | UUID | 会话 ID |
| primary_category | varchar | 一级分类 |
| secondary_category | varchar | 二级分类 |
| urgency_level | varchar | S/A/B/C |
| confidence | numeric | 分类置信度 |
| result_json | jsonb | 完整诊断结果 |
| model_provider | varchar | 模型供应商 |
| model_version | varchar | 模型版本 |
| prompt_version | varchar | Prompt 版本 |
| knowledge_version | varchar | 知识库版本 |
| cost_total | numeric | 本次诊断汇总成本（来自 cost_logs） |
| deleted_at | timestamptz/null | 用户删除时间 |
| retention_until | timestamptz/null | 合规审计保留到期时间 |
| created_at | timestamptz | 创建时间 |

索引：

- `idx_diagnosis_results_session_id`
- `idx_diagnosis_results_category`
- `idx_diagnosis_results_urgency`

### 5.5 repair_records

存储用户保存的维修记录。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| user_id | UUID/null | 用户 ID |
| anonymous_token | varchar | 游客记录归属 |
| diagnosis_result_id | UUID | 关联诊断结果 |
| house_area | varchar | 房间/区域，**必填**（对应 PRD §8.8，提供快捷选项兜底） |
| actual_solution | text | 实际维修方式 |
| actual_cost | numeric | 实际费用 |
| provider_name | varchar | 服务商/师傅 |
| reminder_status | varchar | none/scheduled/sent/cancelled |
| is_resolved | boolean | 是否解决 |
| is_recurred | boolean | 是否复发 |
| deleted_at | timestamptz/null | 用户删除时间 |
| retention_until | timestamptz/null | 合规审计保留到期时间 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

### 5.6 media_files

第 2 版启用，存储图片和语音元数据。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| user_id | UUID/null | 用户 ID |
| session_id | UUID | 会话 ID |
| file_type | varchar | image/voice |
| file_url | varchar | 原始文件地址 |
| thumbnail_url | varchar | 图片缩略图 |
| transcript | text | 语音识别文本 |
| duration_seconds | int | 语音时长 |
| security_status | varchar | pending/pass/reject |
| deleted_at | timestamptz/null | 用户删除时间 |
| retention_until | timestamptz/null | 合规审计保留到期时间 |
| created_at | timestamptz | 创建时间 |

### 5.7 配置和运营表

#### price_rules

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| scene_code | varchar | 价格场景编码，与二级分类关联 |
| city_tier | varchar | tier1/other |
| min_price | numeric | 参考最低价 |
| max_price | numeric | 参考最高价 |
| price_unit | varchar | 次/件/平方米/现场评估 |
| note | text | 价格说明和影响因素 |
| source_note | text | 来源说明 |
| version | varchar | 价格版本 |
| status | varchar | active/archived |
| updated_at | timestamptz | 更新时间 |
| created_at | timestamptz | 创建时间 |

#### safety_rules

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| risk_type | varchar | gas/electric/smoke/water_lock 等 |
| keyword | varchar | 高风险关键词 |
| urgency_level | varchar | S/A |
| negation_sensitive | boolean | 是否需要识别否定表达 |
| action | text | 命中后的安全动作 |
| version | varchar | 规则版本 |
| status | varchar | active/archived |
| updated_at | timestamptz | 更新时间 |
| created_at | timestamptz | 创建时间 |

#### question_templates

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| secondary_category | varchar | 二级分类 |
| field_key | varchar | 需要补齐的字段 |
| question_text | text | 追问文案 |
| sort_order | integer | 展示顺序 |
| version | varchar | 模板版本 |
| status | varchar | active/archived |
| created_at | timestamptz | 创建时间 |

#### prompt_versions

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| prompt_key | varchar | classify/ask/result 等 |
| version | varchar | Prompt 版本 |
| content_hash | varchar | Prompt 内容 hash |
| status | varchar | draft/active/archived |
| created_at | timestamptz | 创建时间 |

#### cost_logs

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| session_id | UUID | 诊断会话 ID |
| provider | varchar | 供应商 |
| capability | varchar | llm/asr/image/content_safety/rag |
| model_version | varchar | 模型或服务版本 |
| tokens | integer | token 数，可为空 |
| duration_seconds | numeric | 语音或任务时长，可为空 |
| call_count | integer | 调用次数 |
| latency_ms | integer | 调用耗时 |
| cost_estimate | numeric | 估算或实际成本 |
| estimated | boolean | 是否估算值 |
| status | varchar | success/failed/degraded |
| error_code | varchar | 错误码，可为空 |
| created_at | timestamptz | 创建时间 |

#### diagnosis_feedbacks

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| user_id | UUID/null | 用户 ID |
| diagnosis_result_id | UUID | 诊断结果 ID |
| helpful_rating | varchar | helpful/neutral/not_helpful |
| category_accuracy | varchar | accurate/inaccurate/unknown |
| urgency_accuracy | varchar | accurate/too_high/too_low/unknown |
| comment | text | 用户补充反馈 |
| created_at | timestamptz | 创建时间 |

#### quota_usage

免费诊断额度计数（对应 §7.4，承载每日 3 次完整诊断的计数）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| subject_type | varchar | anonymous_token/openid/user |
| subject_id | varchar | 标识值，随版本演进 |
| quota_date | date | 计数日期 |
| full_diagnosis_count | integer | 当日完整诊断次数 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

唯一索引：`(subject_type, subject_id, quota_date)`，用于并发安全地自增计数。

#### content_safety_logs

内容安全审核命中留痕（对应 §7.6、§11.4，仅记录命中规则类型，不含原始违规内容）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| session_id | UUID/null | 诊断会话 ID |
| content_source | varchar | user_input/ai_output/user_image/user_voice_transcript |
| result | varchar | pass/reject/error |
| hit_categories | varchar | 命中规则类型，如涉政/涉黄，不含原文 |
| provider | varchar | 审核服务供应商 |
| created_at | timestamptz | 创建时间 |

#### houses / rooms / devices

第 2/3 版启用，按 PRD 中家庭资产管家方向扩展。第 1 版仅保留迁移预留，不作为交付阻塞项。

## 6. API 设计

### 6.1 诊断接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/diagnosis/sessions` | 创建诊断会话 |
| POST | `/api/v1/diagnosis/sessions/{id}/messages` | 发送用户消息并获取 AI 回复 |
| POST | `/api/v1/diagnosis/sessions/{id}/complete` | 强制生成诊断结果 |
| GET | `/api/v1/diagnosis/results/{id}` | 获取诊断结果详情 |
| POST | `/api/v1/diagnosis/results/{id}/feedback` | 提交诊断反馈（第 1 版 P1） |

### 6.2 维修记录接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/repair-records` | 保存维修记录 |
| GET | `/api/v1/repair-records` | 获取维修记录列表 |
| GET | `/api/v1/repair-records/{id}` | 获取维修记录详情 |
| PATCH | `/api/v1/repair-records/{id}` | 回填实际费用、是否解决、是否复发 |

### 6.3 第 2 版接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/media/upload` | 图片/语音上传 |
| POST | `/api/v1/auth/login` | 手机号/验证码登录 |
| POST | `/api/v1/users/merge-anonymous` | 游客记录合并到正式账号 |

### 6.4 系统接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/health` | 健康检查，返回数据库、LLM 主模型、规则文件、知识库版本加载状态 |

### 6.5 鉴权与错误码

鉴权：

- 游客请求：Header 带 `X-Anonymous-Token`，后端校验存在性并写入 `anonymous_token` 字段。
- 登录请求（第 2 版起）：Header 带 `Authorization: Bearer <token>`，解析 `user_id`。
- 游客与登录态可共存，合并接口处理归属切换。

统一错误响应（不返回技术堆栈）：

| HTTP | code | 含义 |
| --- | --- | --- |
| 400 | INVALID_INPUT | 输入不合法（文字过短、文件超大等） |
| 429 | RATE_LIMITED | 超出免费诊断额度或触发限流 |
| 422 | OUTPUT_PARSE_FAILED | LLM 输出校验失败且降级模板也不可用 |
| 451 | CONTENT_UNSAFE | 内容安全审核未通过（不暴露原始违规内容） |
| 503 | MODEL_UNAVAILABLE | 模型全部不可用，已降级 |

前端统一兜底文案："AI 暂时无法判断，请稍后重试或补充更详细的描述。"

## 7. 关键技术点

### 7.1 结构化 AI 输出

LLM 不能直接把自然语言原文返回给前端。后端必须要求模型输出 JSON，并用 Pydantic 校验。

必须包含：

- 故障一级分类。
- 故障二级分类。
- 紧急等级。
- 可能原因。
- 当前建议动作。
- 禁止操作。
- 是否建议找师傅。
- 价格参考。
- 不确定性说明。

校验失败时需要重试一次；仍失败则降级为模板化结果。

诊断结果的完整契约（与 PRD §11.3、§23 对齐）：

```python
class FaultType(BaseModel):
    primary: str            # 一级分类 code，如 water
    secondary: str          # 二级分类 code，如 water_leak
    confidence: float       # 0-1

class Urgency(BaseModel):
    level: Literal["S", "A", "B", "C"]
    reason: str

class PriceReference(BaseModel):
    range: str
    disclaimer: str
    has_reliable_price: bool = True   # 无价格规则时为 False，仅展示影响因素

class DiagnosisResult(BaseModel):
    fault_type: FaultType
    urgency: Urgency
    possible_causes: list[str]              # 2-4 个，按概率排序
    recommended_actions: list[str]
    forbidden_actions: list[str]            # 高风险场景必填
    self_check_steps: list[str]             # 仅低风险步骤
    need_professional: Literal["yes", "no", "conditional"]
    need_professional_reason: str
    price_reference: PriceReference | None
    uncertainty_note: str | None            # 不确定时必填
```

校验补充规则（在 Pydantic 之外的业务校验）：

- `urgency.level` 为 S/A 时，`forbidden_actions` 不可为空。
- `fault_type.confidence < 0.6` 时，`uncertainty_note` 必填，且结果页需提示"建议线下检查"。
- `secondary → primary` 映射必须符合 `fault_taxonomy.yaml`（对应 PRD §8.3 映射表），不合法则修正并降置信度。
- 高风险场景禁止在 `self_check_steps` 中输出具体拆装教学（对应 PRD §19.2）。

### 7.2 高风险规则兜底

燃气、漏电、冒烟、严重漏水、门锁被困等场景不能完全交给 LLM。

实现要求：

- `safety_rules.yaml` 配置高风险词、风险类型、`negation_sensitive` 和命中后的安全动作。
- 关键词命中后，由 LLM 做一次语义确认：是否真实风险、是否为否定/假设表达（规则难以可靠处理"没有""担心""是不是"等自然语言表达）。
- 明确真实风险时强制 S/A 级；明确否定时不提升等级。
- **无法确认风险是否真实时，维持高风险提示并追问确认，不降级**（宁可误报不可漏报，与 PRD §8.4、§18.6 一致）。
- 规则结果优先级高于模型低估结果：当 LLM 低估明确高风险描述时，以规则召回的等级为准。
- 高风险结果页必须展示安全提示和紧急电话建议。
- 拨号号码配置优先级（对应 PRD §8.7）：用户保存的物业/服务商电话 > 城市或小区配置的燃气公司/物业热线 > 全国紧急电话（119/120/110）；无用户/城市配置时回落到紧急电话。

### 7.3 多轮追问控制

为了体验和成本，必须限制追问：

- 每轮最多 3 个问题。
- 每次诊断最多 3 轮。
- 超过 3 轮仍信息不足时，生成低置信度结果。
- 低置信度结果必须说明“不确定原因”和“建议线下检查”。

### 7.4 成本控制

成本是 MVP 硬约束（对应 PRD §16：单次完整诊断 ≤ 1 元，纯文本 ≤ 0.3 元）。第 1 版就要把成本算出来并落库，不能等到第 2 版。

计费实现：

- `cost_service` 在每次外部调用（LLM/ASR/图片识别/内容安全）后写 `cost_logs`，记录 `session_id`、`capability`、`provider`、`model_version`、`tokens`/`duration`/`call_count`、`latency_ms`、`cost_estimate`、`estimated`、`status`。
- 供应商返回精确费用时用实际值；未返回时按 `cost_rules.yaml` 单价估算，`estimated=true`。
- 会话结束汇总总成本写入 `diagnosis_results.cost_total`。

额度控制：

- 免费用户每日最多 3 次"完整诊断"（触发 LLM 结果生成的会话）。纯追问、查看历史不计数。
- 计数主体随版本演进：H5 按 `anonymous_token`+日期（不可靠，可被绕过，属已知风险）；小程序按 `openid`+日期；登录后按 `user_id`+日期。
- 第 2 版起计数存 Redis；第 1 版存 PostgreSQL，按 `(subject_id, subject_type, date)` 唯一索引自增。

降级链路（成本超阈或调用失败时）：

1. 命中低风险常见问题 → 直接走 `question_templates` + 知识库模板，跳过 LLM 生成。
2. 会话累计成本超过阈值（如 0.5 元）→ 后续追问改用规则模板，不再调 LLM。
3. 全部 LLM 不可用 → 输出规则化低置信度结果，提示用户补充信息。

多模态成本控制（第 2 版起，对应 PRD §16 成本拆解，多模态是主要成本变量）：

- 图片仅在用户主动上传时识别一次，不重复识别。
- 多模态优先用小模型初筛，确有必要再调大模型。
- 免费用户图片识别次数单独限额（如每日 1 次）。

### 7.5 游客会话和登录合并

第 1 版可以不登录，但不能丢记录。匿名归属统一存 `anonymous_token` 字段（与 PRD §17.2 对齐）。

H5 阶段：

- 前端在 localStorage 生成 `anonymous_token`（UUID），创建诊断和维修记录时带上。
- 该标识不可靠：清缓存、换浏览器、换设备都会丢失，历史记录可能无法找回（PRD §15.4 已知风险）。

小程序阶段：

- 使用微信 `openid` 作为 `anonymous_token`，稳定可靠。

合并接口（第 2 版 `POST /api/v1/users/merge-anonymous`）：

- 入参：登录后的 `user_id` + 当前端的 `anonymous_token`。
- 把该 token 下所有 `diagnosis_sessions`、`repair_records`、`media_files` 的归属从 token 改为 `user_id`。
- 幂等：已合并的 token 再次请求直接返回成功，不重复处理。
- 冲突处理：若记录已绑定到其他 `user_id`（理论上不应发生），跳过并记告警日志，不强行覆盖。
- 合并前必须提示用户确认（对应 PRD §15.4）。
- H5 端合并为"尽力而为"：用户换过设备的部分记录无法合并，需在 UI 说明。

### 7.6 内容安全

内容安全按使用范围分级：

- 第 1 版内部演示：可以先保留接口和基础敏感词策略，但必须在代码结构中留出 `ContentSafetyService`，所有用户输入和 AI 输出都经过该服务。
- 第 1 版外部可访问：必须接入文本输入审核和 AI 输出审核，否则不应开放给真实外部用户。
- 第 2 版对外测试：必须补齐图片审核、语音转写文本审核和必要的音频审核接口。

第 2 版对外测试前必须接入：

- 用户文本审核。
- 图片审核。
- 语音转写文本审核。
- AI 输出审核。

审核失败时，不进入诊断流程，不把原始违规内容写入业务日志。

### 7.7 价格库版本化

价格是高变动数据，不能写死在 Prompt 里。

实现要求：

- `price_rules` 支持 `scene_code`、`city_tier`、`min_price`、`max_price`、`version`、`updated_at`。
- 诊断结果记录当时使用的价格版本。
- 无价格规则时输出“暂无可靠参考价格”，并展示影响因素。

### 7.8 平台适配层

前端从第 1 版就要避免业务代码直接依赖浏览器或微信专属 API，统一通过 `PlatformAdapter` 接口隔离（组织在 `src/services/platform/`）。

统一接口与两端实现对照：

| 能力 | 统一接口 | H5 实现 | 小程序实现 |
| --- | --- | --- | --- |
| 录音 | `recordAudio()` | MediaRecorder API | `wx.getRecorderManager` |
| 拍照/选图 | `chooseImage()` | `<input type="file" accept="image/*">` | `wx.chooseMedia` |
| 上传 | `uploadFile(path)` | fetch + FormData | `wx.uploadFile` |
| 拨号 | `makePhoneCall(tel)` | `location.href = 'tel:...'` | `wx.makePhoneCall` |
| 存储 | `getStorage/setStorage` | localStorage | `wx.getStorageSync` |
| 匿名标识 | `getAnonymousToken()` | localStorage 生成 UUID | 登录后取 `openid` |

实现要点：

- 通过 uni-app 条件编译 `#ifdef H5` / `#ifdef MP-WEIXIN` 在 `platform/index.ts` 选择实现，业务层只依赖接口、不感知平台。
- 接口统一返回 Promise + 统一错误类型；录音/上传返回中性结构（`url`、`duration`、`transcript` 占位）。
- 第 1 版 H5 端的录音、图片上传可降级为"即将支持"提示，但**接口必须先定义好**，第 2 版填实现，避免届时改业务代码。
- 页面组件优先用 uni-app 兼容组件，不直接用浏览器 DOM API。

## 8. 配置文件设计

### 8.1 fault_taxonomy.yaml

维护故障分类：

```yaml
primary_categories:
  - code: water
    name: 水路维修
  - code: circuit
    name: 电路维修
secondary_categories:
  - code: water_leak
    name: 漏水渗水
    primary: water
  - code: circuit_trip
    name: 电路跳闸
    primary: circuit
```

### 8.2 safety_rules.yaml

维护高风险规则：

```yaml
rules:
  - risk_type: gas
    keywords: ["燃气味", "煤气味", "刺鼻气味"]
    urgency_level: S
    negation_sensitive: true
    action: "撤离现场，关闭阀门，联系燃气公司；紧急时拨打 119"
  - risk_type: electric_smoke
    keywords: ["冒烟", "火花", "插座烧黑", "烧焦"]
    urgency_level: S
    negation_sensitive: true
    action: "停止使用，关闭空气开关，联系专业电工；起火时拨打 119"
```

### 8.3 question_templates.yaml

维护追问模板：

```yaml
water_leak:
  max_questions: 3
  questions:
    - "漏水位置在哪里？"
    - "是持续滴水还是偶尔渗水？"
    - "是否靠近灯具、插座或电器？"
```

### 8.4 price_rules.yaml

价格高变动，必须配置化，不能写进 Prompt（对应 PRD §8.6、§18.7）：

```yaml
- scene_code: water_leak
  city_tier: tier1
  min_price: 80
  max_price: 200
  price_unit: 次
  note: "检测；防水重做、墙体开凿需现场评估"
  version: "2026.06"
  updated_at: "2026-06-15"
- scene_code: water_leak
  city_tier: other
  min_price: 50
  max_price: 150
  price_unit: 次
  version: "2026.06"
  updated_at: "2026-06-15"
```

匹配逻辑：按 `secondary_category → scene_code` + 用户所在 `city_tier` 查找；无匹配时 `has_reliable_price=false`，结果页只展示影响因素不展示数字。诊断结果记录当时使用的 `version`。

`city_tier` 来源（优先级从高到低）：用户在"我的家庭页"填写的城市 > 第 2 版起的登录/定位城市 > **默认 `other`**。PRD 不强制用户填地址（§18.4），因此无城市信息时一律按 `other` 档匹配，不阻断价格展示。

### 8.5 Prompt 版本管理

Prompt 与业务代码分离并版本化（对应 PRD §15.2、§18.7）：

- `prompt_versions` 表记录每个 `prompt_key` 的版本、内容 hash、状态（draft/active/archived）。
- `prompt_templates.py` 按 key 加载当前 active 版本，注入故障分类、风险规则、价格、追问上下文。
- 灰度：可按 `anonymous_token` 哈希或白名单分流到新版本。
- `diagnosis_results.prompt_version` 记录本次使用的版本，便于线上问题按版本追溯。
- 结构化输出 schema 变更属 breaking change，需 bump 版本并标注。

### 8.6 cost_rules.yaml

供应商未返回精确费用时用于估算成本（对应 §7.4）：

```yaml
capabilities:
  llm_chat:
    unit: per_1k_tokens
    price_in_yuan: 0.002      # 量级估算，上线后按实际报价校正
  asr:
    unit: per_second
    price_in_yuan: 0.001
  image_recognition:
    unit: per_call
    price_in_yuan: 0.10
  content_safety:
    unit: per_call
    price_in_yuan: 0.005
```

`cost_service` 估算时标注 `estimated=true`，并以 `cost_logs` 实际值为准持续校正单价。

## 9. 测试策略

### 9.1 后端测试

- 诊断会话创建。
- 多轮追问轮数限制。
- 高风险规则命中。
- 否定表达不误触发 S 级。
- 价格库匹配。
- 结构化输出校验。
- 维修记录保存。

### 9.2 前端测试

- 移动端 H5 首屏。
- 聊天输入和消息展示。
- AI 追问展示。
- 诊断结果页。
- 高风险提示样式。
- 维修记录保存和列表展示。

### 9.3 AI 评测

建立不少于 200 条人工标注黄金集：

- 覆盖 MVP 10 类故障。
- 至少 50 条高风险样本。
- 标注一级分类、二级分类、紧急等级、是否高风险、推荐处理路径。

评测验收按版本分级：

- 第 1 版内部演示：跑通评测脚本并产出 baseline，不强制阈值达标。
- 第 2 版对外测试：故障分类准确率、紧急度判断准确率、高风险召回率和高风险误报率达到产品设定阈值。
- 第 4 版正式上线：在第 2 版阈值基础上，补齐内容安全审核通过率、用户协议和隐私政策合规检查。

## 10. 第 1 版交付清单

第 1 版必须完成：

- 移动端 H5 聊天页。
- 文字输入诊断。
- AI 多轮追问，最多 3 轮。
- 10 类 MVP 场景故障分类。
- S/A/B/C 紧急等级判断。
- 高风险规则兜底。
- 结构化诊断结果页。
- 价格区间参考。
- 基础维修记录保存。
- FastAPI 后端。
- PostgreSQL 数据库。
- LLM Adapter。
- 规则库和价格库配置文件。
- 基础部署脚本。

第 1 版可暂缓：

- 图片上传。
- 语音上传和 ASR。
- 手机号登录。
- 微信 openid。
- 小程序体验版。
- 正式域名和 HTTPS。
- 订阅消息。

## 11. 部署、可观测与合规留痕

### 11.1 配置管理

- 配置通过环境变量注入（`.env` / `env.example`），不硬编码：模型 API Key、数据库连接、内容安全服务凭证、价格库版本、免费额度上限、成本阈值。
- `rules/*.yaml` 与 `prompt_templates` 支持重启加载或热加载，变更走版本号，不重启改代码。

### 11.2 第 1 版部署

- 第 1 版可用临时域名/IP 验收（对应 PRD §13.3），单机 FastAPI + PostgreSQL 即可。
- 健康检查：`GET /api/v1/health` 返回数据库连通性、LLM Adapter 主模型连通性。
- 日志不记录完整隐私文本、图片原始内容、语音原始内容（对应 PRD §18.3）。

健康检查响应示例：

```json
{
  "status": "ok",
  "database": "ok",
  "llm_primary": "ok",
  "rules_version": "2026.06",
  "knowledge_version": "knowledge:2026.06:a1b2c3d4",
  "timestamp": "2026-06-15T10:00:00+08:00"
}
```

### 11.3 可观测性

- 每次 LLM/ASR/图片调用记录 trace：`session_id`、`capability`、`provider`、`latency`、`cost`、`status`，写入 `cost_logs`。
- 慢调用（LLM > 10s）和高失败率告警。
- 核心指标看板：诊断完成率、平均单次成本、LLM 降级率、高风险召回率/误报率（喂给 PRD §20 指标体系）。

### 11.4 合规留痕

- `diagnosis_results` 保留 `model_provider`/`model_version`/`prompt_version`/`knowledge_version`，支持按任意版本回溯某次诊断（对应 PRD §15.2）。
- 用户可删除诊断记录、图片、语音（对应 PRD §18.4）：删除为软删除并记录 `deleted_at`、`retention_until`，前端不再展示；到达保留期后由定时任务物理删除文件和数据库记录。
- 涉及用户删除的数据表至少包括 `diagnosis_sessions`、`diagnosis_results`、`repair_records`、`media_files`。
- 内容安全审核命中单独留痕，仅记录命中规则类型，不含原始违规内容。

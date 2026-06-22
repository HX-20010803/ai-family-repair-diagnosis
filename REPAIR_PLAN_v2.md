# AI 家庭维修诊断助手 · 修复方案 v2.1(修订版)

> **本版基于 GLM 评估 + GPT 校验后的共识重写。** 相比 v1 的核心变化:
> - **评测集提到最前**,先有数据再改分类
> - **分类改为混合模式**(关键词优先,低置信才调 LLM),不再全量 LLM
> - **删掉已存在的 PATCH 接口项**([backend/app/api/v1/records.py:65](backend/app/api/v1/records.py#L65) 已存在)
> - **新增 Docker 数据库连接修复**(v1 漏掉的真问题)
> - **每个文件改动都标注了已核实的行号**,可直接执行
>
> **v2.1 修正点**:
> - 明确 `requires_confirmation` 的三态语义,避免只改 1 行造成测试含义漂移
> - 修正评测集种子数量表述和运行命令
> - 补充混合分类阶段的 LLM 成本日志设计
> - 明确内容安全在 `external_test` / `production` 不允许静默降级到 local
> - 将 P0 交付标准改为"对外测试技术门槛",不再等同于完整对外测试
> - 调整执行顺序,先修风险和 Docker,再做评测与混合分类

---

## 修订原则(贯彻 CLAUDE.md)

1. **外科手术式修改** —— 只动必须动的行,不重构无关代码
2. **每步可验证** —— 每项修复都有明确的测试或手动验证标准
3. **保留现有约定** —— 关键词规则继续作为安全兜底和成本控制手段,不推翻重来
4. **不引入未要求的东西** —— 图片/语音/登录/向量检索明确排除

---

## P0:核心阻塞项(进入对外测试前必须完成)

### P0-1. 修复 `risk_service.py:60` 的 `or True` 笔误

**问题**:[backend/app/services/risk_service.py:60](backend/app/services/risk_service.py#L60) `requires_confirmation=self._is_uncertain(normalized) or True` 使判断永远为真。

**改动**(1 行):
```python
# Before
requires_confirmation=self._is_uncertain(normalized) or True,
# After
requires_confirmation=self._is_uncertain(normalized),
```

**字段语义同步修正**:
- 明确真实风险: `triggered=True`, `requires_confirmation=False`。例如"插座冒烟了"。
- 不确定/疑似风险: `triggered=True`, `requires_confirmation=True`。例如"我担心是不是燃气泄漏"。
- 明确否定: `triggered=False`, `explicitly_negated=True`。例如"热水器不出热水,但是没有燃气味"。

**验证**:
- 新增单测 `test_explicit_real_risk_without_uncertain_word` —— "插座冒烟了"(无不确定词)应返回 `requires_confirmation == False`。
- 现有 `test_uncertain_risk_keeps_high_risk_prompt` 仍应返回 `requires_confirmation == True`。
- 现有 `test_explicit_negation_does_not_raise_to_s_level` 仍应返回 `triggered == False`。

---

### P0-2. 评测集先行 ⭐(最关键,后续分类改造的数据依据)

**目标**:建立评测脚手架 + 200 条黄金集(先交付 30 条种子),跑出当前关键词分类的 baseline。

**新建文件**:
- `backend/eval/golden_set.jsonl` —— 种子 30 条,覆盖 10 类场景,每类至少 2-3 条;其中至少 6 条同时标注为高风险样本
- `backend/scripts/run_eval.py` —— 评测脚本

**种子样本结构**(每条):
```json
{
  "id": "gold_001",
  "input": "卫生间天花板一直滴水，靠近吊顶灯",
  "expected": {
    "secondary": "water_leak",
    "primary": "water",
    "urgency": "A",
    "is_high_risk": false
  }
}
```

**评测脚本逻辑**:
```python
def evaluate(classification_fn, risk_fn, golden_set):
    metrics = {
        "classification_acc": [],
        "urgency_acc": [],
        "high_risk_recall": [0, 0],  # [命中, 总数]
    }
    for sample in golden_set:
        fault = classification_fn(sample["input"])
        metrics["classification_acc"].append(fault.secondary == sample["expected"]["secondary"])
        # 风险/紧急度评测...
    return summarize(metrics)
```

**关键设计**:脚本**直接调用 service 层函数**,不走 HTTP,可重复跑。评测输入固定(无随机性),保证 baseline 可对比。

**交付物**:跑一次产出 `backend/eval/baseline_v0.1.md`,记录:
- 关键词分类准确率(预期:口语化样本会偏低,这就是 LLM 补位的依据)
- 高风险召回率
- 各场景的混淆矩阵(哪些类被误分到哪里)

**验证**:在项目根目录运行 `python backend\scripts\run_eval.py` 能跑通并输出报告。baseline 数字会**真实暴露当前关键词分类的盲区**,作为 P0-3 混合分类的决策依据。

---

### P0-3. 混合分类(关键词优先,低置信/冲突才调 LLM)

> **这是对 v1 的关键调整**:不再"LLM 主导",而是关键词高置信直接走规则(零成本、毫秒级、可控),只在关键词判不准时才调 LLM 确认。

**新建**:`backend/app/services/classification_service.py`

```python
class ClassificationService:
    HIGH_CONFIDENCE_THRESHOLD = 0.7   # 关键词置信度高于此值直接采用
    CONFLICT_THRESHOLD = 0.5          # 多类命中接近,视为冲突

    def __init__(self, llm_adapter: LLMAdapter | None):
        self.llm_adapter = llm_adapter

    def classify(self, text: str) -> FaultType:
        rule_result = self._classify_by_keywords(text)

        # 1. 关键词高置信 → 直接采用(零 LLM 成本)
        if rule_result.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return rule_result

        # 2. 低置信 / 多类冲突 → 调 LLM 确认
        if self.llm_adapter is not None:
            try:
                return self._confirm_with_llm(text, rule_result)
            except (RuntimeError, OSError, OutputParseError):
                pass  # 降级到关键词结果

        # 3. 无 LLM 或调用失败 → 返回关键词结果(带低置信标记)
        return rule_result
```

**LLM 确认 Prompt 设计**(注入合法 code 枚举,杜绝自由文本分类):
```python
CLASSIFY_SYSTEM_PROMPT = f"""
你是家庭维修分类器。只能从以下二级分类中选择一个:
{SECONDARY_NAMES}  # 10 个 code + 中文名
规则校验:secondary 必须映射到正确的 primary。
仅输出 JSON:{{"secondary_category": "...", "confidence": 0.0-1.0, "evidence": [...], "reason": "..."}}
"""
```

**规则校验保底**:LLM 返回的 `secondary` 必须在 `SECONDARY_TO_PRIMARY`([backend/app/services/taxonomy.py:11](backend/app/services/taxonomy.py#L11)) 里,否则视为解析失败→降级到关键词结果。

**diagnosis_service.py 改动**:
- [backend/app/services/diagnosis_service.py:161-180](backend/app/services/diagnosis_service.py#L161-L180) 删除 `_classify`,改为注入 `ClassificationService` 并调用
- 复用现有关键词逻辑(从 `_classify` 提取到 `ClassificationService._classify_by_keywords`),`CLASSIFICATION_KEYWORDS` / `SECONDARY_TO_PRIMARY` / `primary_for_secondary` 仍从 [backend/app/services/taxonomy.py](backend/app/services/taxonomy.py) 引用,不重复定义

**低置信度联动追问**(TECH §4.4.4):
```python
fault = self.classification_service.classify(normalized)
# confidence < 0.6 时(无论 LLM 还是关键词),优先追问而非直接出结果
if fault.confidence < 0.6 and not risk.triggered and round_count < MAX:
    ...返回追问
```

**分类阶段成本日志**:
- 如果 P0-3 中的低置信/冲突分类触发 LLM,必须把这次调用单独记入 `cost_logs`,不能只依赖最终诊断结果生成阶段的成本日志。
- `ClassificationService` 可暴露 `last_cost_log: CostLog | None` 或返回 `(fault_type, cost_log)`;`DiagnosisService` 在有 repository 时写入 `capability="classification"`、`provider`、`model_version`、`tokens`、`latency_ms`、`cost_estimate`、`status`。
- 评测脚本不写数据库,但要统计 `llm_call_count` 和 `llm_call_rate`,用于验证"高置信走规则、低置信才调 LLM"是否真的生效。

**验证**:
1. P0-2 的评测集重跑,准确率应**上升**(尤其是口语化样本),单次 LLM 调用比例应**显著低于全量**(通过 cost_logs 验证)
2. 现有 `test_core_services.py` 全绿(关键词高置信样本行为不变)
3. 新增测试:注入 FakeLLMAdapter,断言"高置信样本不调 LLM""低置信样本调 LLM 且失败时降级"
4. 新增测试:低置信分类触发 LLM 时产生 `capability="classification"` 的成本日志;评测脚本输出 `llm_call_rate`

---

### P0-4. 内容安全接入正式服务

**问题**:[backend/app/services/content_safety_service.py:5](backend/app/services/content_safety_service.py#L5) 仅 4 个硬编码词,外部测试硬阻塞。

**改动**(保持 `check_text(text) -> (bool, hits)` 签名不变,调用方零改动):

```python
class ContentSafetyService:
    def __init__(self, provider: ContentSafetyProvider | None = None):
        self.provider = provider or build_provider_from_config()

    def check_text(self, text: str) -> tuple[bool, list[str]]:
        return self.provider.check(text)


class LocalKeywordProvider:
    """内部演示兜底,保留并扩充现有词表"""
    BLOCKED_WORDS = (...)  # 从 4 个扩充到基础涉政/涉黄/涉暴词

class AliyunGreenProvider:
    """接阿里云内容安全(或腾讯天御/百度文本审核)"""
    def __init__(self, access_key, secret_key): ...
    def check(self, text) -> tuple[bool, list[str]]: ...
```

**配置**([backend/app/core/config.py](backend/app/core/config.py) 新增):
```python
content_safety_provider: str = os.getenv("CONTENT_SAFETY_PROVIDER", "local")
content_safety_access_key: str = os.getenv("CONTENT_SAFETY_ACCESS_KEY", "")
content_safety_secret_key: str = os.getenv("CONTENT_SAFETY_SECRET_KEY", "")
```

**覆盖范围**(TECH §7.6):用户输入 + AI 输出都过审。AI 输出审核在 [backend/app/services/diagnosis_service.py](backend/app/services/diagnosis_service.py) `_build_result` 生成结果后加一次 `check_text`。

**关键约束**:`check_text` 签名不变 → [backend/app/services/diagnosis_service.py:61](backend/app/services/diagnosis_service.py#L61) 和 [backend/app/repositories/diagnosis_repository.py:108](backend/app/repositories/diagnosis_repository.py#L108) 完全不用动。

**部署模式门禁**:
- `DEPLOYMENT_MODE=internal_demo`:允许 `CONTENT_SAFETY_PROVIDER=local`,也允许正式供应商无 Key 时降级到 local,保证本地开发不被阻断。
- `DEPLOYMENT_MODE=external_test` 或 `production`:不允许静默降级到 local。若配置正式供应商但缺少 Key,健康检查必须返回不可用,或服务启动时直接失败;不得交付对外测试。
- 所有内容安全日志仍只记录命中类型和 provider,不写入原始违规内容。

**验证**:
- `internal_demo + local`:行为不变。
- `internal_demo + aliyun 无 Key`:降级 local,诊断不中断。
- `external_test/production + aliyun 无 Key`:health check 或启动检查失败,明确提示内容安全未配置。
- `external_test/production + local`:health check 失败,禁止作为对外测试交付。

---

### P0-5. 修复 Docker Compose 数据库连接

**问题**:[deploy/env.example:2](deploy/env.example#L2) `DATABASE_URL=...localhost:5432...`,backend 容器内 `localhost` 指向容器自身,连不到 postgres 服务。**v1 漏掉的真问题。**

**改动**:
1. [deploy/env.example:2](deploy/env.example#L2):
```diff
- DATABASE_URL=postgresql+psycopg://repair:repair@localhost:5432/repair_ai
+ # 本地直连:localhost;容器内:postgres(服务名)
+ DATABASE_URL=postgresql+psycopg://repair:repair@postgres:5432/repair_ai
```

2. [deploy/docker-compose.yml](deploy/docker-compose.yml) 确认 backend 依赖 postgres 健康检查:
```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U repair -d repair_ai"]
    interval: 5s
    timeout: 3s
    retries: 10
```

3. **本地开发隔离**:本地直连场景(不走 Docker)需要单独的 `.env` 用 `localhost`,避免和容器配置冲突。在 [DEPLOYMENT.md](DEPLOYMENT.md) 注明两种用法。

**验证**:`cd deploy && docker compose up` 后:
- `docker compose exec backend curl localhost:8000/api/v1/health` 返回 `database=ok`
- backend 容器日志无数据库连接错误

---

## P1:功能补全与技术债(P0 完成后)

### P1-1. 追问去重(`asked` 参数未传)

**问题**:[backend/app/services/diagnosis_service.py:90](backend/app/services/diagnosis_service.py#L90) 调 `next_questions` 没传 `asked`,每轮问同样 3 个问题。

**改动**:
1. [backend/app/domain.py](backend/app/domain.py) `DiagnosisSession` 增加内存字段:
```python
asked_questions: list[str] = field(default_factory=list)
```
2. diagnosis_service 追问处:
```python
questions = self.question_service.next_questions(
    fault_type.secondary,
    asked=session.asked_questions,   # ← 传入
)
session.asked_questions.extend(questions)
```
3. 会话从 DB 恢复时([backend/app/services/diagnosis_service.py:132](backend/app/services/diagnosis_service.py#L132)),从 assistant 的 questions 消息反查已问列表。

**验证**:新增测试,连续发两次短消息,断言第二轮 questions 与第一轮无交集。

---

### P1-2. 维修记录列表补全(后端 join + 前端展示)

**问题**:[backend/app/services/record_service.py:35](backend/app/services/record_service.py#L35) 只查 `RepairRecord`,没 join 诊断结果;[frontend/src/pages/records/index.vue:24](frontend/src/pages/records/index.vue#L24) 只显示 UUID。

**后端改动**:[backend/app/services/record_service.py](backend/app/services/record_service.py) `list_records` join `DiagnosisResult`:
```python
stmt = (
    select(RepairRecord, DiagnosisResult)
    .join(DiagnosisResult, RepairRecord.diagnosis_result_id == DiagnosisResult.id)
    .where(RepairRecord.anonymous_token == anonymous_token)
    .order_by(RepairRecord.created_at.desc())
)
```
返回结构增加 `secondary_category` / `urgency_level` / `primary_category`。

**前端改动**:[frontend/src/pages/records/index.vue](frontend/src/pages/records/index.vue) 列表卡片改为:
- 故障类型(二级分类名)
- 紧急等级徽章(复用 `level-S/A/B/C` 样式)
- 房间位置
- 创建时间(格式化)
- 是否解决 / 实际费用(有则显示)

**验证**:创建诊断→保存记录→列表页显示故障类型和等级徽章,非 UUID。

---

### P1-3. 维修记录 PATCH 回填入口(前端补全)

> **注意**:后端接口 [backend/app/api/v1/records.py:65](backend/app/api/v1/records.py#L65) **已存在**(v1 误判为缺失)。`record_service.patch_record`([backend/app/services/record_service.py:46](backend/app/services/record_service.py#L46))也已实现。**只需补前端入口。**

**前端改动**:[frontend/src/pages/records/detail.vue](frontend/src/pages/records/detail.vue) 增加回填表单:
- 实际维修方式(text)
- 实际费用(number)
- 服务商(text)
- 是否解决(switch)
- 是否复发(switch)
- 提交按钮调 `PATCH /repair-records/{id}`

**验证**:详情页能回填并提交,刷新后显示更新值。

---

### P1-4. 用户反馈接口 + 表

> **PRD §6.1 / TECH §5.7 已设计**,代码缺失。这是 v1 和 v2 都认定缺失的(已核实 [backend/app/api/v1/router.py](backend/app/api/v1/router.py) 无 feedback 路由)。

**新增**:
- [backend/app/models/feedback.py](backend/app/models/feedback.py) —— 字段见 TECH §5.7 `diagnosis_feedbacks`
- Alembic 迁移:`alembic revision --autogenerate -m "add diagnosis_feedbacks"`
- `backend/app/api/v1/feedback.py` —— `POST /diagnosis/results/{id}/feedback`
- [backend/app/api/v1/router.py:5](backend/app/api/v1/router.py#L5) 注册 feedback 路由

---

### P1-5. 我的家庭页升级(占位 → 房屋/城市/房间资料)

**现状**:[frontend/src/pages/mine/index.vue:10](frontend/src/pages/mine/index.vue#L10) 仅游客占位。

**改动**:从占位升级为基础家庭资料(对应 PRD §17.7 `houses`/`rooms`,TECH §5.7):
- 房屋列表(城市、小区名)
- 城市能级(用于 [backend/app/services/price_service.py](backend/app/services/price_service.py) 的 `city_tier` 匹配)
- 房间列表(厨房/卫生间/客厅/卧室/阳台)

> **关键联动**:这里填的城市能级,会作为 `city_tier` 参数传给诊断接口([backend/app/api/v1/diagnosis.py:19](backend/app/api/v1/diagnosis.py#L19) 已支持 `city_tier`),让价格匹配更准。这是从"占位"升级到"有实际价值"的关键。

**新增 model**:`houses` / `rooms`(TECH §5.7 已定义字段)+ 迁移 + 简单 CRUD API。

---

## P2:工程加固(可与技术债并行)

### P2-1. LLM 主备降级链(TECH §2.3.1)

**问题**:[backend/app/ai/llm_adapter.py:85](backend/app/ai/llm_adapter.py#L85) 启动时只选一个 adapter,运行时失败直接降级本地模板,不切备用 provider。

**改动**:新增 `FallbackLLMAdapter` 组合主备:
```python
class FallbackLLMAdapter(LLMAdapter):
    def chat(self, messages, schema=None, options=None):
        try:
            return self.primary.chat(messages, schema, options)
        except (RuntimeError, OSError, TimeoutError):
            if self.fallback is None:
                raise
            # 记录降级到 cost_logs,status=degraded
            return self.fallback.chat(messages, schema, options)
```

**验证**:注入会失败的 primary + 可用的 fallback,断言请求成功且 cost_logs 标注 `status=degraded`。

---

### P2-2. 成本估算分供应商

**问题**:[backend/app/ai/llm_adapter.py:82](backend/app/ai/llm_adapter.py#L82) 统一按 `0.002元/1k token`,不分供应商/输入输出。而 [backend/app/rules/cost_rules.yaml](backend/app/rules/cost_rules.yaml) 已存在但未被读取。

**改动**:扩展 cost_rules.yaml 按供应商 + 输入/输出分别配置:
```yaml
capabilities:
  llm_chat:
    unit: per_1k_tokens
    providers:
      deepseek:
        input: 0.001
        output: 0.002
      qwen:
        input: 0.003
        output: 0.006
```
[backend/app/ai/llm_adapter.py:77](backend/app/ai/llm_adapter.py#L77) 改为按 `provider` + `prompt_tokens`/`completion_tokens`(ChatResult 已分别记录)查表。

**验证**:同 token 数下 deepseek 成本应低于 qwen。

---

### P2-3. 其他技术债(v1 保留项)

| 项 | 文件 | 改动 |
|---|---|---|
| API 鉴权 | [backend/app/api/v1/diagnosis.py:31](backend/app/api/v1/diagnosis.py#L31) | 删除 `default="anonymous-demo"`,用 Dependency 校验 token 格式 |
| CORS 收紧 | [backend/app/core/config.py:47](backend/app/core/config.py#L47) | 上线环境按域名配置,本地保留 `*`;按 `deployment_mode` 区分 |
| 可观测性 | [backend/app/main.py](backend/app/main.py) | request middleware 记 session_id/latency/status;LLM >10s 标记慢调用 |
| API 集成测试 | `backend/tests/test_api_flow.py` | TestClient + SQLite 跑通全链路 |

---

## 执行顺序与依赖

```
P0-1 (修 or True)        ← 立即,1 行,零依赖
P0-5 (Docker DB 连接)    ← 独立工程问题,尽早修
    │
P0-2 (评测集 + baseline) ← 最关键,先有数据
    │
    ▼
P0-3 (混合分类)          ← 依赖 P0-2 的 baseline 数据指导阈值
    │
P0-4 (内容安全)          ← 可并行开发,但必须作为 P0 最终门禁
    │
    ▼ (P0 全部完成 = 补齐对外测试的核心技术门槛,但不等同于完整对外测试)
    │
P1-1 追问去重            ← 独立
P1-2 记录列表补全        ← 独立
P1-3 记录 PATCH 入口     ← 依赖 P1-2(详情页)
P1-4 用户反馈            ← 独立
P1-5 我的家庭页          ← 独立,联动价格匹配
    │
P2 (技术债)              ← 与 P1 并行,P2-1 依赖 P0-3 的 adapter 改造
```

---

## 明确排除(v1/v2 共识,不在本轮做)

按 CLAUDE.md §2,以下属 PRD §9.2/§13.4 第 2-4 版范围,本方案不做:
- ❌ 图片上传 + 多模态识别
- ❌ 语音上传 + ASR
- ❌ 手机号登录 + 游客合并(接口)
- ❌ 域名/HTTPS/正式部署环境配置
- ❌ pgvector 向量检索(TECH §2.3.2 明确第 1 版不做)
- ❌ 微信小程序适配

> 注意:这些事项不在本轮修复中做,但如果要真正开放外部用户测试,仍需补齐域名/HTTPS、隐私政策、用户协议、免责声明、投诉反馈入口等 PRD 第 2 版要求。本方案的 P0 只能证明核心技术链路达到对外测试前置门槛,不能替代完整上线准备。

---

## 风险提示

1. **P0-2 评测集的人工标注成本**:30 条种子样本约 2-3 小时,200 条全量是第 2 版工作量。本方案先做脚手架 + 30 条种子,baseline 已能反映关键词分类的盲区。
2. **P0-3 混合分类的阈值需用数据校准**:`HIGH_CONFIDENCE_THRESHOLD=0.7` 是初始值,应根据 P0-2 baseline 的混淆矩阵调整——这正体现了"评测集先行"的价值。
3. **P0-4 内容安全需要真实 API Key 和费用**:`internal_demo` 可无 Key 降级到 local,但 `external_test` / `production` 必须 fail fast,不能用 local 冒充正式内容安全。
4. **P0-5 Docker 修复后需重新验证**:改 `DATABASE_URL` 后,本地非 Docker 开发者需要单独的 `localhost` 配置,避免环境冲突。

---

## 交付标准(整体)

P0 完成后,产品满足"对外测试前置技术门槛"中的 AI 质量、安全审核和部署可用性要求,但**不等同于完整对外测试上线**:
- ✅ 评测集跑通,baseline + 混合分类后的提升有数据支撑
- ✅ 内容安全覆盖用户输入和 AI 输出,且 `external_test` / `production` 禁止 local 降级通过
- ✅ Docker 完整可跑(`docker compose up` 全链路通)
- ✅ 关键词分类盲区由 LLM 补位,成本可控(高置信走规则,分类 LLM 调用写入成本日志)
- ✅ 高风险判断的 `requires_confirmation` 语义正确
- ⚠️ 真正对外测试还需补齐域名/HTTPS、隐私政策、用户协议、免责声明、投诉反馈入口和必要运营配置

---

## 建议起步

确认本方案后,按以下顺序开始:
1. **P0-1 修 `or True` 并同步测试语义**:改动小,先消除高风险字段歧义。
2. **P0-5 修 Docker DB 连接**:独立工程问题,尽早保证部署链路可用。
3. **P0-2 评测集脚手架 + baseline**:后续分类改造的数据前提。
4. **P0-3 混合分类**:基于 baseline 调整阈值,并补分类成本日志。
5. **P0-4 内容安全门禁**:完成 provider 抽象和部署模式 gating。

---

## 文档版本

| 版本 | 日期 | 主要变更 |
| --- | --- | --- |
| v1 | 2026-06-21 | 初版评估与修复方案(GLM) |
| v2 | 2026-06-21 | 基于 GPT 校验后的共识修订:评测集先行、混合分类、删 PATCH 项、补 Docker 问题 |
| v2.1 | 2026-06-21 | 修正风险字段语义、评测集数量/命令、分类成本日志、内容安全门禁、P0 交付边界和执行顺序 |

# AI 家庭维修诊断助手演示脚本

## 1. 演示目标

用 5-8 分钟展示第一版 MVP 的完整产品闭环：

1. 用户用自然语言描述家庭维修问题。
2. 系统判断故障类型和紧急等级。
3. 高风险场景优先给安全提示。
4. 结果结构化展示原因、建议、禁止操作和价格参考。
5. 用户保存为维修记录。
6. 后端可追溯模型、知识库、成本和记录。

## 2. 演示前准备

后端：

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品\backend"
$env:DATABASE_URL="postgresql+psycopg://repair:repair@localhost:5432/repair_ai"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品\frontend"
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd" run dev:h5
```

访问：

```text
http://127.0.0.1:5173/
```

演示前检查：

```powershell
python backend\scripts\deploy_smoke.py http://127.0.0.1:8000
python backend\scripts\llm_smoke.py http://127.0.0.1:8000
```

## 3. 演示案例一：电路高风险

输入：

```text
插座发黑还冒烟了，现在还能继续用吗
```

预期结果：

- 直接生成诊断结果。
- 故障分类：`circuit_trip`。
- 紧急等级：S。
- 禁止继续使用相关电器。
- 建议关闭空气开关并联系专业电工。
- `model_provider` 为 `deepseek` 或 `qwen`。

讲解点：

- 这是高风险兜底场景，系统不等待复杂追问，优先处理安全。
- 高风险规则不完全依赖 LLM，降低漏报风险。
- 结果中有 `model_provider/model_version/prompt_version/knowledge_version/cost_total`，满足追溯要求。

## 4. 演示案例二：普通家电追问

输入：

```text
空调开了半小时还是不制冷，外机也不怎么转
```

预期结果：

- 可能先返回追问。
- 追问内容围绕滤网、模式、外机、故障码、使用年限。
- 用户可补充信息，也可点击直接生成结果。
- 结果紧急等级通常为 B。

讲解点：

- 对非高风险问题，系统先补齐关键信息，避免泛化回答。
- 追问最多 3 轮，每轮最多 3 个问题，控制用户负担和成本。
- 价格区间来自配置化价格库，不写死在 Prompt。

## 5. 演示案例三：维修记录闭环

操作路径：

1. 完成一次诊断。
2. 进入诊断结果页。
3. 点击“保存为维修记录”。
4. 返回聊天页，点击右上角“记”。
5. 查看维修记录列表。

预期结果：

- 记录列表出现本次诊断对应记录。
- 记录包含 `diagnosis_result_id`、位置、创建时间。

讲解点：

- 产品不是一次性问答，而是把维修诊断沉淀成家庭维修档案。
- V1.1 可以继续增强费用回填、是否解决、是否复发、服务商记录。

## 6. 演示后端可追溯

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

关注字段：

- `database`
- `llm_configured`
- `llm_active_provider`
- `knowledge_version`

真实 LLM 验收：

```powershell
python backend\scripts\llm_smoke.py http://127.0.0.1:8000
```

关注字段：

- `model_provider`
- `model_version`
- `urgency`

## 7. 面试或作品集讲法

推荐表达：

```text
这个 MVP 不是泛问答，而是把家庭维修问题转成可追溯的结构化决策链路。
我把第一版控制在移动端 H5 + FastAPI + PostgreSQL + 真实 LLM，
重点验证 10 类高频问题、风险兜底、价格参考、成本日志和维修记录闭环。
高风险场景用规则优先，LLM 负责结构化生成和表达，失败时降级到模板，保证用户至少拿到安全可用的结果。
```

## 8. 不要在第一版演示中承诺的能力

- 图片识别已经完成。
- 语音识别已经完成。
- 能直接派单维修师傅。
- 能保证最终维修结论。
- 能公开生产上线。

这些属于 V1.1 或后续版本。


# AI 家庭维修诊断助手

> 面向家庭用户的 AI 维修决策助手：用户用自然语言描述故障（"卫生间天花板一直滴水""插座发黑还能用吗"），AI 识别故障类型、判断紧急程度、给出安全提示、处理建议和参考价格，并沉淀为可追溯的家庭维修记录。

当前版本：`v0.1.1-external-test-candidate`（外测候选）。第一版移动端 H5，覆盖 10 类高频家庭维修场景，已完成真实 DeepSeek + 腾讯云 TMS 文本内容安全链路验收。

## 成果速览

真实生产链路（腾讯云 TMS + DeepSeek）200 条黄金集端到端评测：

| 指标 | 值 | 说明 |
| --- | --- | --- |
| 🎯 分类准确率 | **95.5%** | 10 类故障分类 |
| ⚡ 紧急准确率 | **95.0%** | S/A/B/C 四级 |
| 🛡️ 高风险召回 | **98.1%**（52/53） | 燃气/漏电/冒烟/严重漏水零漏报 |
| 💰 高风险误报 | **1.4%** | 规则兜底不过度触发 |
| ✅ 端到端崩溃 | **0 / 200** | 含 LLM 重试 + 模板降级 |

> 详见 [backend/eval/baseline_v0.1.1_prod.md](backend/eval/baseline_v0.1.1_prod.md)。8 条争议样本已完成产品裁定，4 条改真值标记 `human_reviewed`，4 条作为外测期模型观察项。

## 产品截图

> 📱 待补充：聊天诊断页 / 结构化结果页 / 维修记录列表 / 我的家庭页。

## 在线体验

🔗 **https://ai.qualisense.top**（外测版 · HTTPS · 手机/电脑任意浏览器打开）

走完整诊断链路：输入故障（如「插座发黑还能用吗」）→ AI 多轮追问 → 结构化结果（故障类型 / 紧急等级 / 安全提示 / 参考价格 / 是否找师傅）→ 一键保存维修记录。一线城市价格联动可在「我的家庭页」切换城市能级查看。

## 核心能力

- **聊天式诊断**：首页即聊天界面，文字描述故障，最多 3 轮追问补齐关键信息。
- **故障分类**：10 类场景，输出一级/二级分类 + 置信度。
- **紧急程度**：S/A/B/C 四级，燃气、漏电、冒烟等高风险场景规则兜底强制 S 级。
- **结构化结果页**：故障类型、紧急等级、可能原因、处理建议、禁止操作、参考价格、是否找师傅。
- **维修记录**：诊断结果保存为记录，支持列表/详情/回填（实际费用、服务商、是否解决/复发）。
- **家庭页**：管理房屋/房间/城市能级，城市能级联动价格参考（一线/其他两档）。
- **安全与合规**：用户输入与 AI 输出双重内容安全审核；结果页免责声明；外测模式强制真实腾讯云 TMS。

## 关键产品决策

- **H5 先行，小程序后置** — 第一版用移动端 H5 快速验证核心链路，规避微信小程序审核与备案周期，把"能上线、能访问"的验证窗口从月级压到天级。（PRD §13.1）
- **高风险规则兜底，不依赖大模型** — 燃气/漏电/冒烟/严重漏水等场景用关键词规则强制 S 级并优先安全动作，大模型低估时规则优先；无法确认风险时"维持高风险提示，不降级"——安全场景宁可误报不可漏报。（PRD §8.4 / §18.6）
- **模板优先 + LLM 兜底** — 低风险常见问题走规则/知识库模板，单次诊断成本压到 0.3 元内；仅高置信阈值触发 LLM，多模态按需调用。（PRD §16.3）
- **结构化诊断 + 记录资产化** — 不输出泛化问答，而是结构化的故障分类/紧急度/价格/维修记录，为复发追踪、家庭资产管理和服务转化打底。（PRD §2.2）
- **合规先行** — 用户输入 + AI 输出双重内容安全（腾讯云 TMS），`external_test`/`production` 模式强制真实 TMS 不得用本地策略，结果页固定免责声明。（PRD §15.3）

## 技术栈

- **后端**：FastAPI + SQLAlchemy + PostgreSQL + Alembic，DeepSeek（主）/ Qwen（备）OpenAI-compatible LLM Adapter，腾讯云 TMS 内容安全。
- **前端**：uni-app + Vue 3 + TypeScript + Pinia，首发 H5，后续可适配微信小程序。
- **评测**：200 条黄金集 E2E 评测（真实生产链路），基线指标见上方「成果速览」。

## 项目结构

```
AI家庭维修诊断助手/
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/               # REST 接口（diagnosis / records / houses / health）
│   │   ├── services/             # 业务服务（诊断 / 分类 / 风险 / 价格 / 记录 / 内容安全）
│   │   ├── models/               # SQLAlchemy 数据模型
│   │   ├── rules/                # 配置化规则（分类关键词 / 价格库 / 风险 / 追问模板）
│   │   ├── ai/                   # LLM Adapter（DeepSeek / Qwen）
│   │   ├── repositories/         # 数据访问层
│   │   └── core/                 # 配置 / 内容安全 provider
│   ├── eval/                     # 200 条黄金集 + baseline 报告
│   ├── migrations/               # Alembic 迁移
│   └── tests/                    # 单元测试
├── frontend/                     # uni-app + Vue 3 H5
│   └── src/
│       ├── pages/                # chat / result / records / mine
│       ├── stores/               # Pinia（session / records / houses）
│       ├── services/             # API 封装 + 多端兼容
│       └── styles/               # 设计 token + 全局样式
├── deploy/                       # docker-compose（PostgreSQL）
├── scripts/                      # 部署 / 冒烟 / LLM 连通脚本
└── PRD.md / TECH_DESIGN.md / ... # 产品与技术文档
```

## 快速开始

### 1. 环境依赖

- Python 3.12+（含 psycopg 的驱动）
- PostgreSQL 16
- Node.js 18+ / pnpm

### 2. 后端

```bash
cd backend
# 安装依赖
pip install -e .
# 配置环境变量（DEPLOYMENT_MODE / CONTENT_SAFETY_PROVIDER / DEEPSEEK_API_KEY / 腾讯 TMS keys / DATABASE_URL）
# 建议放在工作区根目录 .env，app 会自动向上加载
# 启动数据库
docker compose -f ../deploy/docker-compose.yml up -d postgres
# 迁移
python -m alembic upgrade head
# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问 `/api/v1/health`，`external_test` 模式应返回 `content_safety_active_provider=tencent`。

### 3. 前端

```bash
cd frontend
pnpm install
pnpm run dev:h5     # 本地开发
# 或
pnpm run build:h5   # 生产构建
```

### 4. 验收冒烟

```bash
python backend/scripts/deploy_smoke.py http://127.0.0.1:8000   # 部署冒烟（TMS + DeepSeek 链路）
python backend/scripts/llm_smoke.py http://127.0.0.1:8000       # 真实 LLM 连通
```

## 文档

| 文档 | 内容 |
| --- | --- |
| [PRD.md](PRD.md) | 产品需求（用户、场景、功能、合规、验收） |
| [TECH_DESIGN.md](TECH_DESIGN.md) | 技术设计（架构、数据模型、服务） |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 部署配置（外测 / 腾讯 TMS / 常见错误） |
| [MVP_ACCEPTANCE.md](MVP_ACCEPTANCE.md) | MVP 验收说明与通过标准 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [REPAIR_PLAN_v2.md](REPAIR_PLAN_v2.md) | 开发计划（P0/P1/P2 阶段） |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 演示脚本 |

## 测试

```bash
python -m unittest discover backend/tests
```

## 免责声明

AI 只提供初步判断和决策辅助，不构成专业维修结论。涉及燃气、漏电、火灾、结构安全、人身伤害风险时，请立即联系物业、燃气公司、电工、消防或专业维修人员，必要时拨打 119 / 120 / 110。价格区间仅供参考，不构成报价承诺。

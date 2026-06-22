# AI 家庭维修诊断助手部署说明

## 1. 环境要求

- Windows PowerShell。
- Docker Desktop，且 `docker info` 能正常输出 Server 信息。
- Python 3.11+。
- Node.js + pnpm。当前本机建议使用 Codex bundled pnpm：
  `C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd`

## 2. 环境变量

后端启动时会按顺序自动加载以下 `.env` 文件，已存在的进程环境变量优先：

1. `backend\.env`
2. 项目根目录 `.env`
3. `deploy\.env`
4. 父级工作区 `C:\Users\ASUS\Desktop\AI Agent\.env`

推荐把真实 Key 放在父级工作区 `.env`，不要提交到版本库。

本地开发基础配置：

```env
DEPLOYMENT_MODE=internal_demo
DATABASE_URL=postgresql+psycopg://repair:repair@localhost:5432/repair_ai
PRIMARY_LLM_PROVIDER=deepseek
FALLBACK_LLM_PROVIDER=qwen
DEEPSEEK_API_KEY=你的DeepSeekKey
QWEN_API_KEY=你的QwenKey
CONTENT_SAFETY_PROVIDER=local
CONTENT_SAFETY_ACCESS_KEY=
CONTENT_SAFETY_SECRET_KEY=
CONTENT_SAFETY_REGION=ap-guangzhou
CONTENT_SAFETY_TIMEOUT_SECONDS=30
```

DeepSeek 和 Qwen 至少配置一个即可。

内容安全配置按部署模式分级：

- `DEPLOYMENT_MODE=internal_demo`：允许 `CONTENT_SAFETY_PROVIDER=local`，仅用于本地演示和开发。
- `DEPLOYMENT_MODE=external_test` / `production`：不得使用 `local`；当前正式供应商只支持 `CONTENT_SAFETY_PROVIDER=tencent`。
- 正式模式必须配置 `CONTENT_SAFETY_ACCESS_KEY` 和 `CONTENT_SAFETY_SECRET_KEY`。缺少 Key 时 `/api/v1/health` 会返回内容安全错误，不允许对外交付。
- `aliyun` / `baidu` 当前未实现，不能作为正式对外交付配置。

腾讯云内容安全示例：

```env
DEPLOYMENT_MODE=external_test
CONTENT_SAFETY_PROVIDER=tencent
CONTENT_SAFETY_ACCESS_KEY=你的腾讯云SecretId
CONTENT_SAFETY_SECRET_KEY=你的腾讯云SecretKey
CONTENT_SAFETY_REGION=ap-guangzhou
CONTENT_SAFETY_TIMEOUT_SECONDS=30
```

本地 PowerShell 直连 Docker PostgreSQL 时使用 `localhost`；如果后端也运行在 Docker Compose 容器内，必须使用 Compose 服务名：

```env
DATABASE_URL=postgresql+psycopg://repair:repair@postgres:5432/repair_ai
```

因此 `deploy\env.example` 面向 Docker Compose backend，使用 `postgres`；本地开发请在父级工作区 `.env` 或当前 shell 环境变量中继续使用 `localhost`。

## 3. 启动 PostgreSQL

在项目根目录执行：

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品"
docker compose -f deploy\docker-compose.yml up -d postgres
```

检查容器：

```powershell
docker compose -f deploy\docker-compose.yml ps
```

如需同时用 Docker Compose 启动后端：

```powershell
docker compose -f deploy\docker-compose.yml up -d postgres backend
docker compose -f deploy\docker-compose.yml exec backend python -m alembic upgrade head
docker compose -f deploy\docker-compose.yml exec backend python -c "import json; from urllib.request import urlopen; print(json.loads(urlopen('http://127.0.0.1:8000/api/v1/health').read().decode('utf-8')))"
```

## 4. 执行数据库迁移

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品"
$env:DATABASE_URL="postgresql+psycopg://repair:repair@localhost:5432/repair_ai"
cd backend
python -m alembic upgrade head
```

## 5. 启动后端

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品\backend"
$env:DATABASE_URL="postgresql+psycopg://repair:repair@localhost:5432/repair_ai"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

关键字段：

- `database = ok`
- `llm_configured = true`
- `llm_active_provider = deepseek` 或 `qwen`
- `content_safety_status = ok`
- `content_safety_active_provider = local` 仅允许出现在 `internal_demo`
- `content_safety_active_provider = tencent` 才能用于 `external_test` / `production`

## 6. 后端验收

另开一个 PowerShell，在项目根目录执行：

```powershell
python backend\scripts\deploy_smoke.py http://127.0.0.1:8000
python backend\scripts\llm_smoke.py http://127.0.0.1:8000
```

如果 `llm_smoke.py` 返回 `model_provider = local-template`，说明真实 LLM 没有接通。优先检查：

- 当前后端是否是重启后的新进程。
- `.env` 里是否存在 `DEEPSEEK_API_KEY` 或 `QWEN_API_KEY`。
- `/api/v1/health` 的 `llm_configured` 是否为 `true`。

## 7. 启动前端 H5

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品\frontend"
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd" run dev:h5
```

访问：

```text
http://127.0.0.1:5173/
```

前端代理会把 `/api` 请求转发到 `http://localhost:8000`。

## 8. 构建前端 H5

```powershell
cd "C:\Users\ASUS\Desktop\AI Agent\AI物业C端产品\frontend"
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd" run typecheck
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd" run build:h5
```

## 9. 一键验收

项目提供：

```powershell
scripts\verify_mvp.ps1
```

典型用法：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_mvp.ps1 -StartBackend
```

该脚本会执行后端测试、启动临时后端、执行部署冒烟、执行 LLM 冒烟，并可选执行前端 H5 构建。

## 10. 常见问题

### 10.1 `docker info` 报 config.json Access is denied

```powershell
Rename-Item "$env:USERPROFILE\.docker\config.json" "config.json.bak"
docker info
```

### 10.2 `model_provider` 仍是 `local-template`

说明真实 LLM 未接通，后端已降级到本地模板。检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

如果 `llm_configured=false`，说明后端进程没读到 Key；重启后端并确认 `.env` 路径。

### 10.3 前端 pnpm 报 EPERM lstat `C:\Users\ASUS`

这是 Windows 沙箱或权限导致的 Node 入口解析问题。使用非沙箱 PowerShell，或使用 bundled pnpm 直接运行：

```powershell
& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd" run build:h5
```

### 10.4 腾讯云内容安全返回 `CONTENT_SAFETY_UNAVAILABLE`

后端会把腾讯云 TMS 权限、计费、网络超时等供应商异常转换为：

```json
{"code":"CONTENT_SAFETY_UNAVAILABLE"}
```

优先检查：

- 子账号是否已关联 `QcloudTMSFullAccess`，或自定义策略是否包含 `tms:TextModeration`。
- 腾讯云文本内容安全 TMS 是否已开通。
- 账号是否有有效套餐包、按量计费或余额。
- `.env` 是否配置 `CONTENT_SAFETY_TIMEOUT_SECONDS=30`，真实云服务链路不建议低于 30 秒。
- provider 已对瞬时网络异常内置确定性重试（默认 2 次，每次重新签名；腾讯业务错误如权限不足不会重试）。若仍返回 `CONTENT_SAFETY_UNAVAILABLE`，说明是持续故障（权限/计费/网络中断），按上述项排查。

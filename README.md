# LeetCode Coach

开源的、AI 驱动的算法面试教练。AI 的作用不是帮你更快地解题,而是帮你**记住更多做过的题、修复真实的弱点**:自适应课程 · 渐进提示 · 证据驱动的间隔复习 · 模拟面试。

完整规格见 [PLAN.md](PLAN.md),技术决策见 [docs/decisions.md](docs/decisions.md)。

## 本地启动

前置:Python 3.11+、Node 20+。

**后端**(<http://localhost:8000>):

```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**前端**(<http://localhost:5173>,已代理 `/api` 到后端):

```bash
cd frontend && npm install
npm run dev
```

LLM 功能(渐进提示等)需要在 `backend/.env` 中配置 `ANTHROPIC_API_KEY`(模板见 `backend/.env.example`)。

## 常用命令

| 命令 | 作用 |
|---|---|
| `cd backend && .venv/bin/pytest` | 后端测试 |
| `cd backend && .venv/bin/ruff check app tests alembic` | Lint |
| `cd frontend && npm run build` | 前端构建 |
| `make backup` / `make restore FILE=backups/xxx.json` | 用户数据快照导出 / 恢复 |

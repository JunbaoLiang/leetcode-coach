# Contributing

感谢你对 LeetCode Coach 的兴趣!Thanks for your interest — English summary at the bottom.

## 本地开发

见 [README](README.md#本地启动)。后端 Python 3.11+ / FastAPI,前端 React 19 + Vite + Tailwind。

## 工作流(必须遵守)

1. **所有开发在 `feat/<名称>` 或 `fix/<名称>` 分支进行**,经 PR 合入 `main`;禁止直接 push main、禁止 force push。
2. **CI 绿灯是合并前提**:`ruff check` + `pytest` + Alembic 迁移往返 + 前端 build。
3. 一个功能一个 commit,message 用英文祈使句(如 `Add weekly report export`)。
4. 每个里程碑通过验收后打 tag(`v0.1.0`、`v0.2.0`…)。

## 代码约定

- `backend/app/services/scheduler.py` 与 `planner.py` 是**纯函数模块,禁止 I/O**;改公式必须同步更新单测。
- Prompt 只存在于 `backend/app/prompts/*.md`,代码中不得内联长 prompt。
- LLM 的 JSON 输出必须过 Pydantic 校验(失败自动重试一次,再失败明确报错,不静默降级)。
- 所有 schema 变更走 Alembic 迁移,**必须实现可执行的 `downgrade()`**。
- 不引入 PLAN.md 未列出的重型依赖;确有必要先在 `docs/decisions.md` 写明理由。
- 遇到 PLAN 未覆盖的技术决策:选最简单的方案,并在 `docs/decisions.md` 记一行。

## 红线(不接受的 PR)

- ❌ 镜像/存储/展示 LeetCode 题面原文——只允许题号、标题、slug、难度、pattern 等元数据(ML 赛道原创题面除外)。
- ❌ 自动提交器、面试实时作弊类功能。
- ❌ 降低「刻意摩擦」的功能(自动推送提示、一键看答案等)——除非先在 `docs/decisions.md` 论证。

## 测试

```bash
cd backend && .venv/bin/pytest        # 后端(LLM 调用一律 mock)
cd frontend && npm run build          # 前端类型检查 + 构建
```

新增算法题元数据请附带与 leetcode.cn/com 官方 API 的核对结果;新增 ML 原创题必须附参考解法并通过 `test_spec` 全部用例。

---

## English (summary)

- Develop on `feat/*` branches, merge via PR, CI must be green (ruff + pytest + Alembic round-trip + frontend build).
- `scheduler.py` / `planner.py` are pure-function modules — no I/O; formula changes require test updates.
- Prompts live in `backend/app/prompts/*.md` only. LLM JSON output must pass Pydantic validation.
- Every Alembic migration needs a working `downgrade()`.
- Hard lines: never store/display LeetCode problem statements (metadata only); no auto-submitters or interview-cheating features; don't reduce the deliberate-friction design without a written rationale in `docs/decisions.md`.

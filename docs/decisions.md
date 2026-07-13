# 技术决策记录

> 每条一行:日期 · 决策 · 理由。仅记录 PLAN.md 未覆盖的技术选择。

- 2026-07-13 · 本地 Python 使用 Homebrew `python3.12` 建 venv(系统默认为 Anaconda 3.9,不满足 3.11+ 要求);CI 用 3.12 保持一致。
- 2026-07-13 · 尚未创建 GitHub 远端,PR + CI 绿灯流程从远端建立后启用;当前以本地 `feat/*` 分支 + `--no-ff` 合入 `main` 模拟,ci.yml 已就位。
- 2026-07-13 · 首个 Alembic 迁移一次性建全第 6 节所有表(而非按里程碑分次加表):schema 已在 PLAN.md 定稿,一次建齐最简单,downgrade 全量 drop 即可回滚。
- 2026-07-13 · `make restore` 用 `FILE=<path>` 传参(`make restore FILE=backups/xxx.json`):Make 不支持干净的位置参数,变量传参最简单。
- 2026-07-13 · `POST /api/attempts` 创建"进行中"的 attempt(outcome 可空),`PATCH /api/attempts/{id}` 提交结果并触发复习调度:hint_events 需要 attempt_id 外键,故 attempt 必须在做题开始时创建。
- 2026-07-13 · primers 题(patterns 含 "primers")完成后不建 reviews 行——PLAN 11.4 规定其不进入 SM-2 循环,不建行比建特殊状态行更简单。
- 2026-07-13 · 全部种子题(170 算法 + 20 primers)已逐条通过 leetcode.cn GraphQL 核对(题号/难度/标题/非付费);primers 题单直接来自官方 `studyPlanV2Detail(planSlug:"primers-list")`。852 题官方难度已是 medium(非 easy)。
- 2026-07-13 · 前端 Tailwind 使用 v4(@tailwindcss/vite 插件,零配置文件),Vite 8 + React 19:npm create vite 当前默认版本,无理由降级。
- 2026-07-13 · mastery 升级规则(PLAN 未细化):q<3 → learning;否则 reviewing;teach_back_passed 且 review_count≥3 才可 mastered(M2 起生效,与 8.4 节门槛一致)。
- 2026-07-13 · React StrictMode 双挂载会并发创建两条 in-progress attempt:客户端对 startAttempt 做 in-flight 去重 + 服务端 finish 时清理无 hint 记录的兄弟行,不加数据库唯一约束(单用户场景足够)。
- 2026-07-13 · 界面视觉方向「教练的红笔」:暖纸底 + 墨色 + 朱砂红点缀,宋体标题,系统字体无外部依赖。
- 2026-07-13 · 弱点档案的"错误证据"定义:outcome 为 failed/abandoned,或 AC 但勾了错误标签;近 30 天权重 1.0,更早 0.5;pattern 判定为"弱点"需加权做题数 ≥3 且错误率 ≥0.4(防止一两题定性)。
- 2026-07-13 · teach-back 流程:首轮讲解必产生一个追问(passed=false),回答追问后才给最终判定;通过置 teach_back_passed,且 review_count≥3 时立即升 mastered。
- 2026-07-13 · 周报叙述用非结构化 markdown(8.5 节 LLM 只叙述),指标 JSON 全部后端计算并注入 prompt;本周零做题记录时拒绝生成(422)而非产出空话周报。
- 2026-07-13 · 面试评分 prompt 独立为 interviewer_finish.md(PLAN §4 只列了 interviewer.md):in-character 对话与出戏评估是两个人格、两套指令,同文件塞两段会互相污染;str.format 模板也不便条件拼接。
- 2026-07-13 · mock 随机选题池:非 primers、难度 medium/hard、importance≥3,有弱点 pattern 时优先从中选;MockProblemOut 不返回 patterns 字段,防止向候选人剧透考点。
- 2026-07-13 · mock 结束后禁止再发消息/重复评估(409):一场面试一份报告,保证历史记录的完整性。

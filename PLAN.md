# LeetCode Coach — 项目规划书

> 版本 v1.0 · 2026-07-13 · 状态:定稿,交付施工

> **给 Claude Code 的使用说明**:本文档是项目的唯一权威规格。请严格按第 12 节的里程碑顺序开发(M0 → M1 → ...),每个里程碑完成后逐条核对验收标准并输出核对结果,通过后再进入下一个。遇到本文档未覆盖的技术决策,选择最简单的方案,并在 `docs/decisions.md` 中记录一行理由。**不要一次性搭建所有功能。**

---

## 1. 项目愿景与定位

一个开源的、AI 驱动的算法面试教练。核心主张:**AI 的作用不是帮你更快地解题,而是帮你记住更多做过的题、修复真实的弱点**。

四大支柱:

1. **自适应课程**:根据用户画像(背景、目标岗位、时间预算)生成个性化学习路径,并随表现动态调整。
2. **教练式反馈**:渐进提示(不甩答案)、代码 review、teach-back 掌握度关卡。
3. **证据驱动的间隔复习**:改造版 SM-2 算法,复习间隔由客观证据(提示用量、用时、判题失败次数)而非单纯自评决定。
4. **模拟面试**:面试官人格全程不出戏,事后给出 rubric 评分、带引用的 postmortem 和补练处方。

**差异化**(现有开源项目的空白):
- **ML coding 赛道**:numpy 手写模型题(k-means、反向传播、attention 等),浏览器内 Pyodide 判题——几乎所有现有工具只覆盖 SWE 算法题。
- **多人群适配**:MLE / AI4S / SWE 应届 / 转行者各自不同的课程配比和面试 bar,并为零基础用户提供官方 primers 热身入口。

第一用户是项目作者本人(计算化学背景,转 MLE/AI4S 方向,Python 熟练,零前端经验),项目采用 dogfooding 方式迭代。

## 2. 设计原则(源自对现有开源项目的调研)

**要做的**:

1. **教练闭环**:复习到期题优先 → 新题 → 渐进提示(分级,记录用到第几级)→ 用户在 LeetCode 官网提交 → 归档 AC 代码和用户自己写的讲解 → teach-back 通过才算掌握。(参考 guanyipengai/leetcode-coach)
2. **证据驱动调度**:SM-2 的质量分由自评回忆 + 提示等级 + 是否一次 AC + 判题失败次数合成,重要题目复习更频繁。(参考 eannchen/leetsolv)
3. **画像校准**:onboarding 收集背景/目标/时长,所有出题、提示颗粒度、面试 bar 据此调整。(参考 penacristian/interview-agents)
4. **双人格严格分离**:练习模式 = 教练(可随时要提示);模拟模式 = 面试官(不出戏、不帮忙、只追问,结束后才评分)。
5. **弱点档案**:错误分类标签 → 聚合成弱点画像 → 选题偏向弱点 pattern。
6. **状态可读**:LLM 的所有评估输出结构化 JSON 落库,prompt 以 markdown 文件形式存放便于迭代。

**不做的(红线)**:

- ❌ 不镜像、不存储、不展示 LeetCode 题面原文——只存题号、标题、slug、难度、pattern 标签等元数据(版权与 ToS 红线)。ML 赛道题面为本项目原创,不受此限。
- ❌ 不做自动提交器、不做面试作弊工具(不提供"实时面试隐形辅助"类功能)。
- ❌ 教练模式默认不输出完整题解代码;用户明确要求时可给,但记录为 hint level 4(投降),影响复习调度。

## 3. 用户画像与多人群适配

### 3.1 Onboarding 问卷字段(写入 `users` 表)

| 字段 | 类型 | 示例 / 说明 |
|---|---|---|
| `background` | text | "计算化学 PhD,写过 Python 科研脚本" |
| `target_track` | enum | `mle` / `ai4s` / `swe_newgrad` / `career_switch` |
| `target_level` | enum | `junior` / `mid` / `senior` |
| `timeline_weeks` | int, nullable | 12(null = 无死线) |
| `weekly_hours` | int | 8 |
| `preferred_lang` | str | "python" |
| `platform` | enum | `leetcode_cn` / `leetcode_com`(题目跳转域名,两站 slug 相同) |
| `include_primers` | bool | 零基础热身开关;`career_switch` 默认 true,其他赛道可选 |

### 3.2 赛道模板(M4 实现,M1 先只实现 `mle` 一套)

| 赛道 | 算法 : ML coding 配比 | 难度上限 | 备注 |
|---|---|---|---|
| `mle` | 70 : 30 | medium 为主,少量 hard | ML coding 从课程 1/3 处引入 |
| `ai4s` | 60 : 40 | medium | 强化 numpy/数值稳定性题 |
| `swe_newgrad` | 100 : 0 | 含 hard | 完整 NeetCode 式覆盖 |
| `career_switch` | 80 : 20 | easy→medium 缓坡 | 前置 primers 热身(11.4 节)+ Python 工具箱周 |

赛道模板决定:pattern 学习顺序、每日新题量、mock 面试的评分 bar(junior bar 宽容度更高)。`include_primers = true` 时,课程在最前面插入 primers 热身阶段(11.4 节),对任何赛道均可叠加。

## 4. 技术栈与目录结构

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Pydantic v2 | 作者的舒适区 |
| 数据库 | SQLite(开发)→ PostgreSQL(生产) | 本地零配置单文件数据库,SQLAlchemy 无缝切换 |
| 迁移 | Alembic | schema 版本化,每个迁移必须含 `downgrade()`(可回滚) |
| CI | GitHub Actions | 每次 push/PR 自动跑 ruff + pytest + 前端 build |
| 前端 | React 18 + Vite + Tailwind CSS + TypeScript | 生态与 AI 辅助最成熟 |
| 代码编辑器 | CodeMirror 6(仅 ML 赛道做题页) | 轻量,够用 |
| AI | Anthropic API(claude-sonnet 系列),streaming | 教练/面试官/评审/周报四类调用 |
| ML 判题 | Pyodide(浏览器内跑 numpy) | 避免服务端执行用户代码的沙箱难题 |
| 测试 | pytest(后端)/ Vitest(前端,可选) | 调度算法必须有单测 |
| 部署 | 前端 Vercel,后端 Railway 或 Render,DB Neon | 全部免费档起步 |

```
leetcode-coach/
├── PLAN.md                  # 本文档
├── README.md
├── .github/
│   └── workflows/ci.yml     # CI:ruff + pytest + 前端 build
├── docs/
│   └── decisions.md         # 技术决策记录
├── backend/
│   ├── pyproject.toml
│   ├── .env.example         # ANTHROPIC_API_KEY, DATABASE_URL
│   ├── alembic/             # 数据库迁移脚本(见 13.3)
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py        # SQLAlchemy 模型
│   │   ├── schemas.py       # Pydantic schema
│   │   ├── routers/         # profile, problems, plan, attempts, hints, review, teachback, mock, stats, reports
│   │   ├── services/
│   │   │   ├── scheduler.py # SM-2 改造版(第 9 节),纯函数,必须单测
│   │   │   ├── planner.py   # 今日计划生成
│   │   │   └── llm.py       # Anthropic API 封装(structured output)
│   │   └── prompts/         # coach.md, interviewer.md, reviewer.md, teachback.md, reporter.md
│   ├── seed/
│   │   ├── problems.json    # 算法题元数据(第 11 节格式)
│   │   ├── primers.json     # 热身题单(11.4 节)
│   │   ├── ml_problems.json # ML 赛道原创题(含题面与测试)
│   │   └── import_seed.py
│   └── tests/
│       └── test_scheduler.py
└── frontend/
    ├── package.json
    └── src/
        ├── pages/           # Onboarding, Today, Problem, Stats, Weaknesses, Mock, Reports
        ├── components/
        └── lib/api.ts
```

### 4.1 数据存储策略(本地优先,渐进升级)

- **主数据(关系型)用 SQLite**:它本身就是本地单文件(`backend/data/app.db`,已 gitignore),零配置、可随目录整体拷贝;同时提供事务与关联查询——attempts / reviews / hint_events 之间存在大量 join,纯 JSON 文件无法支撑。生产环境切 PostgreSQL 仅需更换 `DATABASE_URL`。
- **JSON 的三个角色**:① 种子数据(`seed/*.json`);② **数据快照备份**:`make backup` 将全部用户数据导出为带时间戳的 JSON(`backups/snapshot_YYYYMMDD_HHMM.json`,已 gitignore),`make restore <file>` 从快照恢复——这就是**数据级回滚**;③ LLM 结构化输出在数据库 JSON 列中的存储格式。
- **对象存储(S3 兼容)列入 Backlog**:S3 是对象存储而非数据库,不用于承载关系型主数据;正确用途是异地存放备份快照、mock 面试 transcript 归档等大块只读数据。M5 之后接入"备份自动上传 AWS S3 / Cloudflare R2"。

## 5. 界面与交互设计

### 5.1 产品形态

响应式 Web 应用(桌面优先,移动端可用)。开发期通过 `localhost` 访问,生产部署后通过浏览器访问网址。不是 CLI、不是浏览器插件(插件形态见 Backlog)。

### 5.2 核心交互模式:「双标签页伴侣」

算法题的题面阅读、代码编写与判题**全部发生在 LeetCode 官网**(按用户 `platform` 偏好跳转 leetcode.cn / leetcode.com);coach 不内嵌题面(第 2 节红线)、不复刻判题。coach 负责**做题前**(出什么题)、**做题中**(计时 + 渐进提示)、**做题后**(记录、review、teach-back、复习调度)。

标准做题流程:

1. 打开「今日计划」,点击一道题;
2. 新标签页打开 LeetCode 题目页,coach 侧进入「做题页」并自动开始计时;
3. 用户在 LeetCode 写代码,卡住时切回 coach 逐级请求提示;
4. AC 后切回 coach 点「完成」,填写记录表单:outcome / 自评回忆度(0-5)/ 错误标签(受控词表多选)/ 粘贴 AC 代码;
5. 可选:一键代码 review;一键 teach-back;
6. 复习队列、进度看板、弱点档案自动更新。

### 5.3 页面清单(共 7 个)

| 页面 | 内容 |
|---|---|
| Onboarding | 首次问卷(3.1 节字段),提交后生成课程 |
| 今日计划 Today | 到期复习 + 新题列表;顶部显示 streak 与今日预算 |
| 做题页 Problem | 核心界面,见 5.4 |
| 进度看板 Stats | pattern 进度环、难度分布、streak、活动热力图 |
| 弱点档案 Weaknesses | 按标签 / 按 pattern 的错误率聚合与趋势 |
| 模拟面试 Mock | 会话式界面 + 倒计时 + 历史记录与评分趋势 |
| 周报 Reports | 历史周报列表与详情,可导出 markdown |

### 5.4 做题页布局(核心界面)

双栏布局。**左栏**:难度与 pattern 徽章、题目标题、「在 leetcode.cn/com 打开」外链按钮(按 platform 拼 URL)、计时器(进入页面即启动,可暂停)、「完成,记录结果」按钮(点击展开记录表单)。**右栏**:教练提示聊天窗——对话流式输出;底部按钮始终显示下一可用等级(如「需要更深一层提示(L2)」);窗内常驻小字:「已用提示:Lx · 提示深度会影响复习安排」。

### 5.5 两个例外(交互完全发生在 coach 站内)

- **ML coding 赛道**:题面为本项目原创,做题页内嵌 CodeMirror 编辑器;「运行测试」按钮触发 Pyodide 在浏览器内执行用户代码并展示断言结果;测试失败次数计入 `judge_failures`。
- **模拟面试**:全程会话界面。面试官出题(只报题号与标题)→ 用户口述思路并在纯文本代码框中作答(**不判题**,由面试官人格评估)→ 倒计时归零或用户提前结束 → 展示 rubric 报告页。

### 5.6 刻意摩擦原则(设计哲学,约束多处实现)

求助的轻微不便是特性而非缺陷:提示必须逐级手动请求,绝不自动推送;不设「一键看答案」入口(L4 需用户在对话中明确表达);记录表单不允许跳过自评。目的是保留「挣扎时间」——那是学习真正发生的地方。任何未来功能若会降低这种摩擦,须先在 `docs/decisions.md` 论证。

## 6. 数据模型

```
users
  id, name, background, target_track, target_level,
  timeline_weeks, weekly_hours, preferred_lang,
  platform ('leetcode_cn'|'leetcode_com'), include_primers (bool), created_at

problems                       # 题目跳转链接由 slug + 用户 platform 动态拼接,不落库
  id, track ('algo'|'ml'), lc_id (nullable), slug, title,
  difficulty ('easy'|'medium'|'hard'), patterns (JSON array),
  importance (1-4, 4=必会), statement (仅 ml 赛道,原创题面 markdown),
  test_spec (仅 ml 赛道, JSON: 函数签名+测试用例+容差)

attempts
  id, user_id, problem_id, started_at, duration_sec,
  outcome ('ac_first_try'|'ac'|'failed'|'abandoned'),
  hint_level_max (0-4), judge_failures (int),
  code_snapshot (text), self_explanation (text, 用户自己写的讲解),
  mistake_tags (JSON array, 见第 10 节), review_feedback (JSON, LLM 代码 review 结果),
  created_at

hint_events
  id, attempt_id, level (1-4), content (text), created_at

reviews            # 每 (user, problem) 一行,SM-2 状态机
  id, user_id, problem_id, ease_factor (float, 初始 2.5),
  interval_days (int), due_date (date), review_count (int),
  last_quality (float), mastery ('learning'|'reviewing'|'mastered'),
  teach_back_passed (bool, default false)

mock_sessions
  id, user_id, problem_id, mode ('coding'|'ml_coding'),
  transcript (JSON), duration_sec,
  rubric (JSON: 六维各 1-5 分), verdict ('strong_hire'|'hire'|'lean_hire'|'no_hire'),
  postmortem (text, 带对话引用), drills (JSON array, 补练处方), created_at

reports            # 周报(M2)
  id, user_id, period_start, period_end, content_md (text),
  metrics (JSON: 题数/AC率/一次AC率/平均提示深度/错误标签增减), created_at
```

## 7. API 设计(REST,前缀 `/api`)

| Method + Path | 作用 |
|---|---|
| `GET /health` | 健康检查 |
| `POST /profile` · `GET /profile` | onboarding 写入 / 读取画像 |
| `GET /problems?pattern=&difficulty=&track=` | 题库查询 |
| `GET /plan/today` | 今日计划:到期复习(按优先级)+ 新题(见 9.4) |
| `POST /attempts` | 记录一次做题(outcome、用时、自评、错误标签、代码) |
| `POST /hints` | 渐进提示。入参:problem_id, attempt_id, 当前对话, 请求级别;流式返回;落 `hint_events` |
| `POST /review-code` | 对 AC 代码做结构化 review,结果写入 attempt |
| `POST /teachback` | 用户讲解 → LLM 按 checklist 判定,通过则置 `teach_back_passed` |
| `POST /mock/start` · `POST /mock/message` · `POST /mock/finish` | 模拟面试会话;finish 时生成 rubric/verdict/postmortem |
| `GET /stats` | 进度看板:pattern 进度环、难度分布、streak、活动热力图、弱点档案 |
| `POST /reports/weekly` · `GET /reports` | 生成 / 回看周报(见 8.5) |

## 8. LLM 层设计

所有 prompt 存放在 `backend/prompts/*.md`,`services/llm.py` 负责加载、拼装用户上下文、调用 API 并校验 JSON 输出(校验失败自动重试一次)。

### 8.1 教练人格(coach.md)——用于 `/hints`

- 输入上下文:题目元数据(标题/pattern/难度,**不含题面**,靠模型自身知识)、用户画像、该用户在此 pattern 上的历史弱点标签。
- 渐进提示等级:
  - **L1 方向性提问**:只问引导性问题("暴力解是什么复杂度?瓶颈在哪一步?"),不提数据结构名。
  - **L2 关键观察**:点出核心 observation 或该用的数据结构("查找是否存在,有没有 O(1) 的办法?"),不给算法步骤。
  - **L3 算法骨架**:文字版伪代码级思路,不给可运行代码。
  - **L4 完整讲解**(用户明确投降时):完整思路+代码,并直言"这题会重新安排到近期复习"。
- 规则:每次只升一级;用户没要求升级时,在当前级别换角度再启发;禁止主动展示完整代码。
- 语气校准:对 `career_switch` / primers 阶段用户采用最详细的解释颗粒度(多解释术语与 Python 惯用法);对 senior bar 用户直接、少寒暄。

### 8.2 面试官人格(interviewer.md)——用于 `/mock/*`

- 开场白 → 出题(只报题号和标题,用户在纯文本框作答)→ 全程 in character:追问 worst-case 复杂度、edge case、trade-off;**绝不给提示、不安慰、不确认对错**;用户沉默过久只说"请继续说出你的思考"。
- `finish` 时切换出人格,输出结构化 JSON:

```json
{
  "rubric": {"communication": 3, "problem_solving": 4, "code_correctness": 3,
             "complexity_analysis": 2, "edge_cases": 3, "time_management": 4},
  "verdict": "lean_hire",
  "postmortem": "复杂度分析是最大短板:我两次追问 worst case 你才给出(见对话第 4、11 轮)...",
  "drills": [{"pattern": "two_pointers", "count": 3, "instruction": "写代码前先口头说出循环不变量"}]
}
```

- 评分 bar 按用户 `target_level` 校准(junior 的 3 分 ≈ senior 的 2 分)。

### 8.3 评审人格(reviewer.md)——用于 `/review-code`

输入 AC 代码,输出结构化 JSON:`{"correctness_risks": [], "complexity": {"claimed": null, "actual": "O(n)"}, "style_issues": [], "optimal_comparison": "...", "mistake_tags_suggested": []}`。suggested tags 供用户确认后写入 attempt。

### 8.4 Teach-back 评审(teachback.md)——用于 `/teachback`

用户用自己的话讲解解法(为什么这样做、复杂度、edge case)。LLM 按 checklist 判定:核心思路正确 / 复杂度正确 / 至少说出一个 edge case / 能回答一个追问。输出 `{"passed": bool, "gaps": [...], "follow_up_question": "..."}`。未通过则 mastery 不得进入 `mastered`。

### 8.5 周报生成(reporter.md)——用于 `/reports/weekly`

输入本周聚合指标(完成题数、AC 率、一次 AC 率、平均提示深度及其相对上周的趋势、新增/消退的错误标签、弱点 pattern 变化、streak),输出诚实但鼓励的周报 markdown:本周概览 → 进步信号(如提示依赖度下降)→ 需要警惕的信号(如某标签错误率上升)→ 下周建议焦点(与 planner 的弱点权重联动)。**指标计算在后端完成,LLM 只负责叙述与建议,不得编造数字。**

## 9. 复习调度算法(改造版 SM-2)

实现于 `services/scheduler.py`,**必须是纯函数并配 pytest 单测**。

### 9.1 质量分 q 的合成(证据驱动)

每次复习/做题后计算 q ∈ [0, 5]:

```
q = recall_self_report            # 用户自评 0-5(完全忘了→毫不费力)
    - 0.5 * hint_level_max        # 用了越深的提示,质量越低
    - 0.5 * min(judge_failures, 3) # 判题失败惩罚,封顶 1.5
    + (0.5 if outcome == 'ac_first_try' else 0)
q = clamp(q, 0, 5)
```

### 9.2 间隔更新(SM-2 骨架)

```
if q < 3:
    interval = 1              # 重学
    review_count = 0
else:
    EF = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    EF = max(EF, 1.3)
    interval = 1 if review_count == 0 else (3 if review_count == 1 else round(interval * EF))
    review_count += 1

interval *= importance_multiplier    # {4: 0.75, 3: 0.9, 2: 1.0, 1: 1.2},重要题复习更勤
interval *= uniform(0.9, 1.1)        # 抖动,防止复习堆积在同一天
due_date = today + interval
```

### 9.3 到期优先级(积压时决定先复习谁)

```
priority = 1.5 * importance + 0.5 * overdue_days - 1.0 * ease_factor - 0.5 * review_count
```

### 9.4 今日计划生成(`services/planner.py`)

1. 日预算 = `weekly_hours / 7`,按均值 40 分钟/题折算成题数(复习题按 20 分钟计)。
2. 先取到期复习题(按 priority 降序),最多占预算 60%。
3. 再取新题:若弱点档案中某 pattern 错误率显著偏高,以配置权重(默认 0.4)优先从该 pattern 取;否则按赛道模板的 pattern 顺序推进。
4. mastery 为 `learning` 且 3 天内未动的题优先于全新题。
5. primers 题(11.4 节)不参与复习调度,只在 `include_primers` 用户的课程最前段作为新题下发。

## 10. 错误分类法(初始标签集)

`mistake_tags` 的受控词表(可扩充,但先用这套,保证聚合有意义):

| 标签 | 含义 |
|---|---|
| `misread_problem` | 读错/漏读题意 |
| `edge_case_missed` | 边界条件遗漏(空输入、单元素、重复值) |
| `off_by_one` | 索引/循环边界差一 |
| `wrong_data_structure` | 数据结构选型不当 |
| `pattern_not_recognized` | 没识别出该用的 pattern |
| `complexity_misjudged` | 复杂度估错/写出超时解 |
| `recursion_base_case` | 递归终止条件错误 |
| `dp_state_definition` | DP 状态定义或转移错误 |
| `implementation_bug` | 思路对,代码手滑(语法/变量/返回值) |
| `numerical_stability` | 数值稳定性问题(ML 赛道:溢出、未减 max 的 softmax 等) |
| `api_unfamiliar` | 不熟悉语言内置工具(heapq、Counter 等) |

弱点档案 = 按标签和按 pattern 两个维度聚合错误率,近期(30 天)加权高于远期。

## 11. 题库与种子数据

### 11.1 算法题元数据格式(`seed/problems.json`)

**只存元数据,严禁存题面。** M1 需扩充到 ~150 题:以公开的 NeetCode 250 / Grind 75 清单的题目组织(题号、标题、pattern 归类均为客观事实,可用),覆盖 11.3 节的 pattern 顺序。种子样例:

```json
[
  {"lc_id": 1,   "slug": "two-sum",                "title": "Two Sum",                                    "difficulty": "easy",   "patterns": ["arrays_hashing"], "importance": 4},
  {"lc_id": 217, "slug": "contains-duplicate",     "title": "Contains Duplicate",                         "difficulty": "easy",   "patterns": ["arrays_hashing"], "importance": 3},
  {"lc_id": 242, "slug": "valid-anagram",          "title": "Valid Anagram",                              "difficulty": "easy",   "patterns": ["arrays_hashing"], "importance": 3},
  {"lc_id": 49,  "slug": "group-anagrams",         "title": "Group Anagrams",                             "difficulty": "medium", "patterns": ["arrays_hashing"], "importance": 4},
  {"lc_id": 347, "slug": "top-k-frequent-elements","title": "Top K Frequent Elements",                    "difficulty": "medium", "patterns": ["arrays_hashing", "heap"], "importance": 4},
  {"lc_id": 125, "slug": "valid-palindrome",       "title": "Valid Palindrome",                           "difficulty": "easy",   "patterns": ["two_pointers"], "importance": 3},
  {"lc_id": 15,  "slug": "3sum",                   "title": "3Sum",                                       "difficulty": "medium", "patterns": ["two_pointers"], "importance": 4},
  {"lc_id": 11,  "slug": "container-with-most-water","title": "Container With Most Water",                "difficulty": "medium", "patterns": ["two_pointers"], "importance": 4},
  {"lc_id": 121, "slug": "best-time-to-buy-and-sell-stock","title": "Best Time to Buy and Sell Stock",    "difficulty": "easy",   "patterns": ["sliding_window"], "importance": 4},
  {"lc_id": 3,   "slug": "longest-substring-without-repeating-characters","title": "Longest Substring Without Repeating Characters","difficulty": "medium","patterns": ["sliding_window"],"importance": 4},
  {"lc_id": 704, "slug": "binary-search",          "title": "Binary Search",                              "difficulty": "easy",   "patterns": ["binary_search"], "importance": 4},
  {"lc_id": 33,  "slug": "search-in-rotated-sorted-array","title": "Search in Rotated Sorted Array",      "difficulty": "medium", "patterns": ["binary_search"], "importance": 4},
  {"lc_id": 20,  "slug": "valid-parentheses",      "title": "Valid Parentheses",                          "difficulty": "easy",   "patterns": ["stack"], "importance": 4},
  {"lc_id": 739, "slug": "daily-temperatures",     "title": "Daily Temperatures",                         "difficulty": "medium", "patterns": ["stack"], "importance": 3},
  {"lc_id": 206, "slug": "reverse-linked-list",    "title": "Reverse Linked List",                        "difficulty": "easy",   "patterns": ["linked_list"], "importance": 4},
  {"lc_id": 21,  "slug": "merge-two-sorted-lists", "title": "Merge Two Sorted Lists",                     "difficulty": "easy",   "patterns": ["linked_list"], "importance": 4},
  {"lc_id": 226, "slug": "invert-binary-tree",     "title": "Invert Binary Tree",                         "difficulty": "easy",   "patterns": ["trees"], "importance": 4},
  {"lc_id": 102, "slug": "binary-tree-level-order-traversal","title": "Binary Tree Level Order Traversal","difficulty": "medium", "patterns": ["trees", "bfs"], "importance": 4},
  {"lc_id": 98,  "slug": "validate-binary-search-tree","title": "Validate Binary Search Tree",            "difficulty": "medium", "patterns": ["trees"], "importance": 4},
  {"lc_id": 215, "slug": "kth-largest-element-in-an-array","title": "Kth Largest Element in an Array",    "difficulty": "medium", "patterns": ["heap"], "importance": 4},
  {"lc_id": 78,  "slug": "subsets",                "title": "Subsets",                                    "difficulty": "medium", "patterns": ["backtracking"], "importance": 4},
  {"lc_id": 39,  "slug": "combination-sum",        "title": "Combination Sum",                            "difficulty": "medium", "patterns": ["backtracking"], "importance": 3},
  {"lc_id": 200, "slug": "number-of-islands",      "title": "Number of Islands",                          "difficulty": "medium", "patterns": ["graphs", "bfs", "dfs"], "importance": 4},
  {"lc_id": 207, "slug": "course-schedule",        "title": "Course Schedule",                            "difficulty": "medium", "patterns": ["graphs", "topological_sort"], "importance": 4},
  {"lc_id": 70,  "slug": "climbing-stairs",        "title": "Climbing Stairs",                            "difficulty": "easy",   "patterns": ["dp_1d"], "importance": 4},
  {"lc_id": 198, "slug": "house-robber",           "title": "House Robber",                               "difficulty": "medium", "patterns": ["dp_1d"], "importance": 4},
  {"lc_id": 322, "slug": "coin-change",            "title": "Coin Change",                                "difficulty": "medium", "patterns": ["dp_1d"], "importance": 4}
]
```

### 11.2 ML coding 赛道(原创题,`seed/ml_problems.json`)

题面由本项目原创撰写(markdown),每题含:函数签名、numpy-only 约束、隐藏测试用例、`np.allclose` 容差。首批 10 题:

1. 线性回归 + 批量梯度下降
2. 逻辑回归 + BCE 损失
3. kNN 分类器
4. k-means(含空簇处理)
5. PCA(基于 SVD)
6. 数值稳定的 softmax + 交叉熵
7. 两层 MLP 前向 + 反向传播
8. 评估指标:混淆矩阵 + precision/recall/F1 + AUC
9. Scaled dot-product attention
10. Multi-head attention(拼装第 9 题)

判题:前端加载 Pyodide,拼接用户代码与测试脚本执行,断言用 `np.allclose(result, expected, rtol, atol)`;失败时展示第一个失败用例的输入形状与期望输出形状(不泄露具体数值答案)。

### 11.3 Pattern 学习顺序(赛道模板的默认序)

`primers(可选热身,见 11.4)→ arrays_hashing → two_pointers → sliding_window → binary_search → stack → linked_list → trees → bfs/dfs → heap → backtracking → graphs → dp_1d → greedy/intervals`

### 11.4 Primers 热身题单(零基础入口)

- **来源**:力扣官方学习计划「新」动计划 · 编程入门(`leetcode.cn/studyplan/primers-list`),共 20 道入门题,从编程语法练习过渡到数据结构基础,专为编程初学者设计。
- **导入**:该页面为 SPA,seed 阶段需对照官方页面人工核对 20 道题号填入 `seed/primers.json`,或通过 LeetCode GraphQL(`studyPlanV2Detail(planSlug: "primers-list")`)拉取元数据——**仅题号/标题/难度/slug,不拉题面**。字段:`patterns: ["primers", <真实pattern副标签>]`,`importance: 1`。
- **课程行为**:`include_primers = true` 的用户课程从 primers 阶段开始,预计 1-2 周完成;primers 题**不进入 SM-2 长期复习循环**(平台适应性热身,非面试考点),AC 即通过;渐进提示照常可用,且教练对处于此阶段的用户默认采用最详细的解释颗粒度。

## 12. 里程碑与验收标准

### M0 — 骨架与流水线(先打通,再谈功能)

- [ ] Git 初始化:分支策略按 13.1 节执行;`.gitignore` 覆盖 `backend/data/`、`backups/`、`.env`、`node_modules/`
- [ ] GitHub Actions CI 按 13.2 节配置,并在首个 PR 上跑通
- [ ] Alembic 初始化,首个建表迁移含可实际执行的 `downgrade()`
- [ ] 按第 4 节建立 monorepo 结构;`docs/decisions.md` 初始化
- [ ] 后端:`uvicorn` 启动,`GET /api/health` 返回 `{"status": "ok"}`;pytest 跑通至少 1 个测试;ruff 配置
- [ ] 前端:Vite dev server 启动,首页调用 `/api/health` 并展示结果(验证 CORS 与代理配置)
- [ ] `.env.example` 含 `ANTHROPIC_API_KEY`、`DATABASE_URL`;README 写清两条命令内的本地启动步骤
- [ ] 部署打通:前端上 Vercel、后端上 Railway/Render,线上可访问 health 页(最晚 M1 结束前完成)

### M1 — 可日用的 MVP(**达标后作者即开始日常刷题**)

- [ ] `import_seed.py` 导入 ≥150 道算法题元数据(按 11.3 顺序覆盖全部 pattern)+ primers 热身 20 题(11.4 节,题号经官方页面核对)
- [ ] Onboarding 页 → 写入用户画像(暂单用户,无鉴权),含 platform 偏好与零基础热身开关
- [ ] 今日计划页:到期复习 + 新题,点击题目按 platform 偏好跳转 leetcode.cn / leetcode.com
- [ ] 做题页按 5.4 节实现:计时器(可暂停)、记录表单(outcome / 自评 recall / 错误标签多选 / 粘贴代码)
- [ ] 渐进提示聊天窗:L1→L4 逐级、流式输出、`hint_events` 落库;教练不主动给完整代码;遵守 5.6 节摩擦原则
- [ ] `scheduler.py` 实现第 9 节全部公式,单测 ≥10 个用例(含 q<3 重置、EF 下限、importance 缩放、抖动边界)
- [ ] 进度看板:pattern 进度环(NeetCode 式,每类"已解 n/总数")、难度分布、连续打卡 streak、GitHub 式活动热力图——全部由 attempts 聚合,无需新表
- [ ] `make backup` / `make restore <file>`:用户数据 JSON 快照导出与恢复(数据级回滚,见 4.1 节)

### M2 — 反馈闭环

- [ ] `/review-code`:结构化代码 review,建议的错误标签经用户确认后入库
- [ ] `/teachback`:讲解评审 + 追问;通过才允许 mastery → `mastered`
- [ ] 弱点档案页:按标签 / 按 pattern 的错误率聚合(近 30 天加权)
- [ ] 今日计划的新题选择按弱点权重(默认 0.4,可配置)偏向
- [ ] 周报:`POST /reports/weekly` 后端聚合指标 + LLM 生成叙述(8.5 节),落 `reports` 表;历史周报页,可导出 markdown

### M3 — 模拟面试

- [ ] mock 会话:选题或按弱点随机 → 45 分钟倒计时 → 面试官人格对话(全程不提示),代码在纯文本框作答、不判题(5.5 节)
- [ ] finish 生成 rubric 六维评分 + verdict + 引用对话轮次的 postmortem + drills,落 `mock_sessions`
- [ ] mock 历史页,可回看 transcript 与评分趋势

### M4 — 多人群 + ML 赛道(差异化)

- [ ] onboarding 支持 4 个赛道模板(3.2 节),课程配比与 bar 生效
- [ ] ML 赛道 10 道原创题上线;做题页内嵌 CodeMirror 编辑器,前端 Pyodide 判题(numpy 可用、容差断言、失败信息不泄答案)
- [ ] ML 题纳入统一复习调度(judge_failures 即 Pyodide 测试失败次数)

### M5 — 开源门面

- [ ] GitHub OAuth 登录,多用户数据隔离
- [ ] README(中英双语):demo GIF、架构图、一键部署说明
- [ ] LICENSE(MIT)、CONTRIBUTING.md
- [ ] 技术博客草稿:设计决策与调研综述

## 13. 工程化规范与开发约定(Claude Code 请遵守)

### 13.1 Git 工作流与代码回滚

- `main` 分支始终保持可运行;所有开发在 `feat/<名称>` / `fix/<名称>` 分支进行,经 PR 合入,CI 绿灯是合并前提;禁止向 `main` force push。
- 每个里程碑通过验收后打 tag:M1 → `v0.1.0`,M2 → `v0.2.0`,依此类推。出问题时 `git revert` 单个提交,或整体回退到上一个 tag。

### 13.2 CI(GitHub Actions)

- `ci.yml` 在每次 push 与 PR 上运行:`ruff check` + `pytest` + 前端 `npm run build`。
- CI 红灯的分支不得合并——保证 `main` 上每个提交都是可回退到的良好状态,这是一切回滚能力的前提。

### 13.3 数据库 schema 回滚(Alembic)

- 所有 schema 变更必须通过 Alembic 迁移完成,禁止手改数据库。
- **每个迁移必须实现 `downgrade()`**,且保证 `alembic downgrade -1` 可实际执行——这是 schema 级回滚。

### 13.4 部署与数据回滚

- Vercel 与 Railway/Render 均保留历史部署,可一键回退;发布节奏与 tag 对齐。回滚时前端、后端、数据库迁移三者版本必须一致:先 `alembic downgrade` 再回退代码。
- 数据级回滚依赖 4.1 节的 `make backup` / `make restore` JSON 快照机制;建议在每次执行迁移前自动触发一次 backup。

### 13.5 通用约定

1. 严格按里程碑推进;完成一个里程碑先逐条自查验收标准,输出核对结果,再进入下一个。
2. `scheduler.py` 与 `planner.py` 为纯函数模块,禁止在其中做 I/O;所有公式改动必须同步更新单测。
3. 不引入本文档未列出的重型依赖(如更换 ORM、引入 Redux/状态管理库、Docker 编排)——如确有必要,先在 `docs/decisions.md` 写明理由。
4. Prompt 修改只发生在 `backend/prompts/*.md`,代码中不得内联长 prompt。
5. LLM 的 JSON 输出必须经 Pydantic schema 校验,失败自动重试一次,仍失败则返回明确错误而非静默降级。
6. 提交粒度:一个功能一个 commit,commit message 用英文祈使句。
7. 安全:`ANTHROPIC_API_KEY` 只存在于后端环境变量;前端永不直接调用 Anthropic API。

## 14. Backlog(不在 M0-M5 范围,记录备查)

- 备份快照自动上传对象存储(AWS S3 / Cloudflare R2),异地容灾;transcript 等大块只读数据归档
- Chrome 插件:在 LeetCode 页面内嵌提示窗(参考 LitCoach 形态)
- LeetCode 提交记录同步(需评估官方 API 与 ToS)
- 导出复习卡片到 Anki
- 行为面试 / 系统设计模块(参考 swe-interview-coach 的 STAR 故事库设计)
- 多语言支持(界面 i18n;做题语言支持 C++/Java)
- 社区题单分享与导入

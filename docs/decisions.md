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
- 2026-07-13 · ML 解锁进度定义为 已解算法题/算法题总数 ≥ 1/3(PLAN"从课程 1/3 处引入"未定义度量);swe_newgrad 永不解锁。
- 2026-07-13 · ML 判题 test_spec 内含参考实现(expected/expected_code),浏览器 devtools 理论可见——判题本就发生在客户端,PLAN 的"不泄露"要求落实在失败提示层(只报形状与容差)。全部 20 个用例已用独立参考解法脚本验证通过。
- 2026-07-13 · Pyodide 从 jsdelivr CDN 懒加载(首次 ▶ 运行测试时下载,numpy 一并加载);CodeMirror 用 @uiw/react-codemirror 封装并按需 code-split,主包体积不受影响。
- 2026-07-13 · ML 题失败计数口径:一次「运行测试」中只要有用例失败记 1 次 judge_failures(而非按用例数累计),与"判题失败次数"的直觉一致。
- 2026-07-13 · 鉴权采用 AUTH_ENABLED 显式开关:本地 dev 保持零配置单用户(不因配了 GitHub 凭据就强制登录);会话用 HMAC-SHA256 签名 cookie 手写实现(~30 行),不引入 JWT/authlib 重依赖。
- 2026-07-13 · 越权访问一律返回 404 而非 403:不向外确认资源存在性。
- 2026-07-13 · 新 OAuth 用户以 onboarded=false 创建,GET /profile 对未 onboarding 用户返回 404 驱动前端进问卷;迁移把存量本地用户直接标记 onboarded=true。
- 2026-07-13 · 生产部署用 Vercel rewrites 做同源 /api 代理:OAuth callback 也走前端域名,会话 cookie 天然第一方,无跨域 cookie 问题;GitHub OAuth App 的 callback URL 必须填前端域名。
- 2026-07-13 · demo GIF 用 Pillow 把三张页面截图串成轮播(本机无 ffmpeg/ImageMagick);后续可换成真实操作录屏。
- 2026-07-13 · 增加 backend/requirements.txt(与 pyproject 依赖手动同步):Railway/Render 的构建器只对 requirements.txt 走"自动建 venv + 配 PATH"的铺装路径,自定义 `pip install .` 装出的环境运行期不可见;本地开发仍以 pyproject 为准。
- 2026-07-14 · 迁移脚本里的裸 SQL 必须写跨方言的字面量:`onboarded = TRUE` 而非 `= 1`(SQLite 宽容、PostgreSQL 强类型,首次上 Neon 时炸出)。教训:迁移要在两种方言上都验证。
- 2026-07-14 · streak/热力图/周报窗口统一以 **UTC 日**为口径(created_at 本就是 UTC):美东晚间本地日期落后 UTC 一天,混用会算错 streak;复习 due_date 保持本地日期(用户面向的调度语义)。
- 2026-07-15 · Neon 免费档闲置 ~5 分钟自动休眠会掐断连接池里的连接:engine 开 `pool_pre_ping=True` + `pool_recycle=300`;同时前端 profile 加载遇到非 401/404 错误改为"重试一次→报错页",不再静默当成"无画像"送去 onboarding(该缺陷曾让瞬时 500 被误读为数据丢失)。
- 2026-07-16 · 教练聊天 L0 开放自由输入(dogfooding 反馈):用户贴自己的思路/伪代码时,教练可自由点评(含判对错)——等级限制改为约束"教练注入的新信息"而非"用户能否说话";首条自由对话透明计为 L1 进入调度,保持证据诚实。摩擦原则的保护对象是挣扎时间,不是禁止思考出声。
- 2026-07-16 · 算法题做题页改为左窄右宽(信息卡 ~320px + 聊天占余宽),记录表单展开时布局换回宽左栏;ML 题保持宽编辑器布局。聊天输入改多行 textarea(Enter 发送 / Shift+Enter 换行),方便贴代码。

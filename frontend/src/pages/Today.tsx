import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type TodayPlan } from '../lib/api'
import {
  DifficultyBadge,
  ImportanceDots,
  PatternChips,
  ProblemTitle,
} from '../components/ProblemMeta'

function Row({
  problemId,
  children,
  tag,
}: {
  problemId: number
  children: React.ReactNode
  tag?: React.ReactNode
}) {
  return (
    <Link
      to={`/problem/${problemId}`}
      className="group flex items-center justify-between gap-3 border-b border-line bg-card px-4 py-3 transition-colors first:rounded-t-md last:rounded-b-md last:border-b-0 hover:bg-paper-deep/60"
    >
      <div className="flex min-w-0 flex-wrap items-center gap-2">{children}</div>
      <div className="flex shrink-0 items-center gap-3">
        {tag}
        <span className="text-sm text-ink-faint transition-colors group-hover:text-vermilion">
          开始 →
        </span>
      </div>
    </Link>
  )
}

export default function Today() {
  const [plan, setPlan] = useState<TodayPlan | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getTodayPlan().then(setPlan).catch((e: unknown) => setError(String(e)))
  }, [])

  if (error) return <p className="text-vermilion-deep">{error}</p>
  if (!plan) return <p className="text-ink-faint">生成今日计划…</p>

  const empty = plan.reviews.length === 0 && plan.new.length === 0

  return (
    <div>
      <div className="rise flex items-baseline justify-between">
        <h1 className="font-display text-2xl font-semibold">
          <span className="pen-underline">今日计划</span>
        </h1>
        <div className="flex items-center gap-4 text-sm text-ink-soft">
          <span>
            连续打卡 <span className="font-mono text-lg font-semibold text-vermilion">{plan.streak}</span> 天
          </span>
          <span>
            今日预算 <span className="font-mono font-semibold">{plan.budget_minutes}</span> 分钟
          </span>
        </div>
      </div>

      {plan.reviews.length > 0 && (
        <section className="rise rise-1 mt-6">
          <h2 className="mb-2 text-sm font-medium text-vermilion-deep">
            到期复习 · {plan.reviews.length}
          </h2>
          <div className="rounded-md border border-line shadow-sm">
            {plan.reviews.map((item) => (
              <Row
                key={item.problem.id}
                problemId={item.problem.id}
                tag={
                  item.overdue_days > 0 ? (
                    <span className="rounded-sm bg-vermilion-wash px-1.5 py-0.5 text-xs text-vermilion-deep">
                      逾期 {item.overdue_days} 天
                    </span>
                  ) : (
                    <span className="text-xs text-ink-faint">第 {item.review_count + 1} 次复习</span>
                  )
                }
              >
                <DifficultyBadge difficulty={item.problem.difficulty} />
                <ProblemTitle problem={item.problem} />
                <PatternChips patterns={item.problem.patterns} />
              </Row>
            ))}
          </div>
        </section>
      )}

      <section className="rise rise-2 mt-6">
        <h2 className="mb-2 text-sm font-medium text-ink-soft">新题 · {plan.new.length}</h2>
        {plan.new.length === 0 ? (
          <p className="text-sm text-ink-faint">今天的预算被复习占满了——先把旧账还上。</p>
        ) : (
          <div className="rounded-md border border-line shadow-sm">
            {plan.new.map((item) => (
              <Row
                key={item.problem.id}
                problemId={item.problem.id}
                tag={
                  item.is_primer ? (
                    <span className="rounded-sm bg-seal-green-wash px-1.5 py-0.5 text-xs text-seal-green">
                      热身
                    </span>
                  ) : item.is_stale_learning ? (
                    <span className="rounded-sm bg-amber-wash px-1.5 py-0.5 text-xs text-amber-warn">
                      3 天没动了
                    </span>
                  ) : (
                    <ImportanceDots value={item.problem.importance} />
                  )
                }
              >
                <DifficultyBadge difficulty={item.problem.difficulty} />
                <ProblemTitle problem={item.problem} />
                <PatternChips patterns={item.problem.patterns} />
              </Row>
            ))}
          </div>
        )}
      </section>

      {empty && (
        <p className="rise rise-2 mt-8 text-ink-soft">
          今天没有安排——去 <Link to="/onboarding" className="text-vermilion underline">画像页</Link> 检查每周投入时间?
        </p>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlanItem, type TodayPlan } from '../lib/api'
import { DifficultyBadge, PatternChips, ProblemTitle } from '../components/ProblemMeta'

const KIND_BADGE: Record<PlanItem['kind'], { label: string; cls: string }> = {
  review: { label: '复习', cls: 'bg-vermilion-wash text-vermilion-deep' },
  new: { label: '新题', cls: 'bg-paper-deep text-ink-soft' },
  bonus: { label: '加餐', cls: 'bg-amber-wash text-amber-warn' },
}

function ItemRow({ item }: { item: PlanItem }) {
  return (
    <Link
      to={`/problem/${item.problem.id}`}
      className={`group flex items-center gap-3 border-b border-line bg-card px-4 py-3 transition-colors first:rounded-t-md last:rounded-b-md last:border-b-0 hover:bg-paper-deep/60 ${
        item.done ? 'opacity-70' : ''
      }`}
    >
      {/* check circle */}
      <span
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-xs ${
          item.done
            ? 'border-seal-green bg-seal-green text-white'
            : 'border-ink-faint text-transparent'
        }`}
      >
        ✓
      </span>

      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <span className={`rounded-sm px-1.5 py-0.5 text-xs font-medium ${KIND_BADGE[item.kind].cls}`}>
          {KIND_BADGE[item.kind].label}
        </span>
        <DifficultyBadge difficulty={item.problem.difficulty} />
        <span className={item.done ? 'line-through decoration-ink-faint' : ''}>
          <ProblemTitle problem={item.problem} />
        </span>
        <PatternChips patterns={item.problem.patterns} />
      </div>

      <span className="flex shrink-0 items-center gap-3">
        {item.kind === 'review' && (item.overdue_days ?? 0) > 0 && !item.done && (
          <span className="rounded-sm bg-vermilion-wash px-1.5 py-0.5 text-xs text-vermilion-deep">
            逾期 {item.overdue_days} 天
          </span>
        )}
        {item.stale && !item.done && (
          <span className="rounded-sm bg-amber-wash px-1.5 py-0.5 text-xs text-amber-warn">
            3 天没动了
          </span>
        )}
        {!item.done && (
          <span className="text-sm text-ink-faint transition-colors group-hover:text-vermilion">
            开始 →
          </span>
        )}
      </span>
    </Link>
  )
}

export default function Today() {
  const [plan, setPlan] = useState<TodayPlan | null>(null)
  const [error, setError] = useState('')
  const [adding, setAdding] = useState(false)

  const load = () => {
    api.getTodayPlan().then(setPlan).catch((e: unknown) => setError(String(e)))
  }
  useEffect(load, [])

  const addBonus = async () => {
    setAdding(true)
    try {
      await api.addBonusProblem()
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAdding(false)
    }
  }

  if (error) return <p className="text-vermilion-deep">{error}</p>
  if (!plan) return <p className="text-ink-faint">生成今日计划…</p>

  const allDone = plan.total_count > 0 && plan.done_count === plan.total_count
  const pct = plan.total_count > 0 ? (plan.done_count / plan.total_count) * 100 : 0
  const pendingBonus = plan.items.some((i) => i.kind === 'bonus' && !i.done)

  return (
    <div className="mx-auto max-w-4xl">
      <div className="rise flex items-baseline justify-between">
        <h1 className="font-display text-2xl font-semibold">
          <span className="pen-underline">今日计划</span>
        </h1>
        <div className="flex items-center gap-4 text-sm text-ink-soft">
          <span>
            连续打卡{' '}
            <span className="font-mono text-lg font-semibold text-vermilion">{plan.streak}</span> 天
          </span>
          <span>
            预算 <span className="font-mono font-semibold">{plan.budget_minutes}</span> 分钟
          </span>
        </div>
      </div>

      {/* progress */}
      {plan.total_count > 0 && (
        <div className="rise rise-1 mt-5">
          <div className="mb-1.5 flex items-baseline justify-between text-sm">
            <span className={allDone ? 'font-medium text-seal-green' : 'text-ink-soft'}>
              今日 {plan.done_count}/{plan.total_count}
              {allDone && ' · 完成 ✓'}
            </span>
            {plan.bonus_done > 0 && (
              <span className="font-medium text-amber-warn">加餐 +{plan.bonus_done}</span>
            )}
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-paper-deep">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                allDone ? 'bg-seal-green' : 'bg-vermilion'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* checklist */}
      {plan.items.length === 0 ? (
        <p className="rise rise-2 mt-8 text-ink-soft">
          今天没有安排——去{' '}
          <Link to="/onboarding" className="text-vermilion underline">
            画像页
          </Link>{' '}
          检查每周投入时间?
        </p>
      ) : (
        <div className="rise rise-2 mt-5 rounded-md border border-line shadow-sm">
          {plan.items.map((item) => (
            <ItemRow key={item.problem.id} item={item} />
          ))}
        </div>
      )}

      {/* celebration + bonus */}
      {allDone && (
        <div className="rise rise-3 mt-6 rounded-md border border-seal-green/30 bg-seal-green-wash p-5 text-center">
          <p className="font-display text-lg font-semibold text-seal-green">
            🎉 今日计划完成!连续打卡 {plan.streak} 天
          </p>
          <p className="mt-1 text-sm text-ink-soft">
            {plan.bonus_done > 0
              ? `已加餐 ${plan.bonus_done} 道——今天的你比昨天的你更难被面试官刁难。`
              : '还有余力?多做的每一道都会计入弱点档案和复习循环。'}
          </p>
          {!pendingBonus && (
            <button
              onClick={addBonus}
              disabled={adding}
              className="mt-4 rounded-md bg-seal-green px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-85 disabled:opacity-50"
            >
              {adding ? '挑题中…' : '再来一道(加餐)'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

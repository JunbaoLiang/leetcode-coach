import { useEffect, useState } from 'react'
import { api, type Stats } from '../lib/api'
import { DIFFICULTY_LABELS, patternLabel } from '../lib/labels'

function ProgressRing({ solved, total, label }: { solved: number; total: number; label: string }) {
  const r = 26
  const c = 2 * Math.PI * r
  const frac = total > 0 ? solved / total : 0
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-md border border-line bg-card p-3 shadow-sm">
      <svg width="68" height="68" viewBox="0 0 68 68" className="-rotate-90">
        <circle cx="34" cy="34" r={r} fill="none" stroke="var(--color-line)" strokeWidth="6" />
        <circle
          cx="34"
          cy="34"
          r={r}
          fill="none"
          stroke={frac >= 1 ? 'var(--color-seal-green)' : 'var(--color-vermilion)'}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - frac)}
          style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.2, 0.7, 0.3, 1)' }}
        />
      </svg>
      <span className="-mt-11 font-mono text-xs font-semibold">
        {solved}/{total}
      </span>
      <span className="mt-6 text-xs text-ink-soft">{label}</span>
    </div>
  )
}

function Heatmap({ data }: { data: Record<string, number> }) {
  const weeks = 26
  // backend keys are UTC dates (attempt timestamps are stored in UTC) —
  // build the grid in UTC too so evenings west of Greenwich land on the right cell
  const now = new Date()
  const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const start = new Date(today)
  start.setUTCDate(today.getUTCDate() - (weeks * 7 - 1))
  start.setUTCDate(start.getUTCDate() - start.getUTCDay())
  const cells: { date: string; count: number }[][] = []
  const cursor = new Date(start)
  while (cursor <= today) {
    const col: { date: string; count: number }[] = []
    for (let d = 0; d < 7 && cursor <= today; d++) {
      const key = cursor.toISOString().slice(0, 10)
      col.push({ date: key, count: data[key] ?? 0 })
      cursor.setUTCDate(cursor.getUTCDate() + 1)
    }
    cells.push(col)
  }
  const shade = (n: number) =>
    n === 0
      ? 'bg-paper-deep'
      : n === 1
        ? 'bg-vermilion/30'
        : n <= 3
          ? 'bg-vermilion/60'
          : 'bg-vermilion'
  return (
    <div className="flex gap-[3px] overflow-x-auto pb-1">
      {cells.map((col, i) => (
        <div key={i} className="flex flex-col gap-[3px]">
          {col.map((cell) => (
            <div
              key={cell.date}
              title={`${cell.date}:${cell.count} 次`}
              className={`h-2.5 w-2.5 rounded-[2px] ${shade(cell.count)}`}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

function StatCard({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return (
    <div className="rounded-md border border-line bg-card px-4 py-3 shadow-sm">
      <div className="text-xs text-ink-faint">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold">
        {value}
        {suffix && <span className="text-sm font-normal text-ink-soft"> {suffix}</span>}
      </div>
    </div>
  )
}

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getStats().then(setStats).catch((e: unknown) => setError(String(e)))
  }, [])

  if (error) return <p className="text-vermilion-deep">{error}</p>
  if (!stats) return <p className="text-ink-faint">统计中…</p>

  return (
    <div>
      <h1 className="rise font-display text-2xl font-semibold">
        <span className="pen-underline">进度看板</span>
      </h1>

      <div className="rise rise-1 mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="连续打卡" value={String(stats.streak)} suffix="天" />
        <StatCard label="已解题数" value={String(stats.total_solved)} />
        <StatCard
          label="一次 AC 率"
          value={stats.ac_first_try_rate === null ? '—' : `${Math.round(stats.ac_first_try_rate * 100)}%`}
        />
        <StatCard
          label="平均提示深度(30天)"
          value={stats.avg_hint_level_30d === null ? '—' : `L${stats.avg_hint_level_30d.toFixed(1)}`}
        />
      </div>

      <section className="rise rise-2 mt-8">
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Pattern 进度</h2>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-8">
          {stats.pattern_progress.map((p) => (
            <ProgressRing
              key={p.pattern}
              solved={p.solved}
              total={p.total}
              label={patternLabel(p.pattern)}
            />
          ))}
        </div>
      </section>

      <section className="rise rise-3 mt-8">
        <h2 className="mb-3 text-sm font-medium text-ink-soft">难度分布</h2>
        <div className="space-y-2">
          {stats.difficulty_progress.map((d) => {
            const frac = d.total > 0 ? d.solved / d.total : 0
            return (
              <div key={d.difficulty} className="flex items-center gap-3">
                <span className="w-10 text-sm text-ink-soft">
                  {DIFFICULTY_LABELS[d.difficulty]}
                </span>
                <div className="h-3 flex-1 overflow-hidden rounded-sm bg-paper-deep">
                  <div
                    className="h-full rounded-sm bg-vermilion transition-all duration-700"
                    style={{ width: `${frac * 100}%` }}
                  />
                </div>
                <span className="w-16 text-right font-mono text-xs text-ink-soft">
                  {d.solved}/{d.total}
                </span>
              </div>
            )
          })}
        </div>
      </section>

      <section className="rise rise-4 mt-8">
        <h2 className="mb-3 text-sm font-medium text-ink-soft">活动热力图(近 26 周)</h2>
        <Heatmap data={stats.heatmap} />
      </section>
    </div>
  )
}

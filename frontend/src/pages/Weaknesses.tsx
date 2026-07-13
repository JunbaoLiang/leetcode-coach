import { useEffect, useState } from 'react'
import { api, type Weaknesses } from '../lib/api'
import { MISTAKE_TAG_LABELS, patternLabel } from '../lib/labels'

function Bar({ frac, danger }: { frac: number; danger: boolean }) {
  return (
    <div className="h-3 flex-1 overflow-hidden rounded-sm bg-paper-deep">
      <div
        className={`h-full rounded-sm transition-all duration-700 ${
          danger ? 'bg-vermilion' : 'bg-amber-warn'
        }`}
        style={{ width: `${Math.min(frac, 1) * 100}%` }}
      />
    </div>
  )
}

export default function WeaknessesPage() {
  const [data, setData] = useState<Weaknesses | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getWeaknesses().then(setData).catch((e: unknown) => setError(String(e)))
  }, [])

  if (error) return <p className="text-vermilion-deep">{error}</p>
  if (!data) return <p className="text-ink-faint">聚合中…</p>

  const empty = data.tags.length === 0 && data.patterns.length === 0

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="rise font-display text-2xl font-semibold">
        <span className="pen-underline">弱点档案</span>
      </h1>
      <p className="rise rise-1 mt-3 text-sm text-ink-soft">
        由做题记录里的错误标签与结果聚合而成;近 30 天的证据权重更高。选题会自动偏向弱点 pattern。
      </p>

      {empty ? (
        <p className="rise rise-2 mt-8 text-ink-soft">
          还没有足够的记录。做题时如实勾选错误标签,这里会长出你的弱点画像。
        </p>
      ) : (
        <>
          {data.weak_patterns.length > 0 && (
            <div className="rise rise-2 mt-6 rounded-md border border-vermilion/40 bg-vermilion-wash px-4 py-3">
              <p className="text-sm font-medium text-vermilion-deep">
                当前弱点 pattern:{data.weak_patterns.map(patternLabel).join('、')}
              </p>
              <p className="mt-1 text-xs text-ink-soft">
                今日计划的新题已按弱点权重向这些 pattern 倾斜。
              </p>
            </div>
          )}

          <section className="rise rise-2 mt-8">
            <h2 className="mb-3 text-sm font-medium text-ink-soft">按错误标签</h2>
            {data.tags.length === 0 ? (
              <p className="text-sm text-ink-faint">暂无错误标签记录。</p>
            ) : (
              <div className="space-y-2">
                {data.tags.map((t) => (
                  <div key={t.tag} className="flex items-center gap-3">
                    <span className="w-40 shrink-0 text-sm text-ink-soft">
                      {MISTAKE_TAG_LABELS[t.tag] ?? t.tag}
                    </span>
                    <Bar frac={t.rate} danger={t.rate >= 0.3} />
                    <span className="w-24 shrink-0 text-right font-mono text-xs text-ink-soft">
                      {t.count} 次 · {Math.round(t.rate * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rise rise-3 mt-8">
            <h2 className="mb-3 text-sm font-medium text-ink-soft">按 pattern 错误率</h2>
            <div className="space-y-2">
              {data.patterns.map((p) => (
                <div key={p.pattern} className="flex items-center gap-3">
                  <span className="w-40 shrink-0 text-sm text-ink-soft">
                    {patternLabel(p.pattern)}
                  </span>
                  <Bar frac={p.error_rate} danger={data.weak_patterns.includes(p.pattern)} />
                  <span className="w-24 shrink-0 text-right font-mono text-xs text-ink-soft">
                    {p.attempts} 题 · {Math.round(p.error_rate * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}

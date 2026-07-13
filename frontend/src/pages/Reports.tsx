import { useEffect, useState } from 'react'
import { api, type Report, type ReportSummary } from '../lib/api'

/** minimal markdown rendering (headings/bold/lists) — no external deps */
function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/)
  const inline = (s: string) =>
    s.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : (
        part
      ),
    )
  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {blocks.map((block, i) => {
        const lines = block.split('\n')
        if (block.startsWith('# '))
          return (
            <h1 key={i} className="font-display text-xl font-semibold">
              {block.slice(2)}
            </h1>
          )
        if (block.startsWith('## '))
          return (
            <h2 key={i} className="font-display text-base font-semibold text-vermilion-deep">
              {block.slice(3)}
            </h2>
          )
        if (lines.every((l) => l.startsWith('- ') || l.startsWith('* ')))
          return (
            <ul key={i} className="list-inside list-disc space-y-1">
              {lines.map((l, j) => (
                <li key={j}>{inline(l.slice(2))}</li>
              ))}
            </ul>
          )
        return <p key={i}>{inline(block)}</p>
      })}
    </div>
  )
}

function exportMarkdown(report: Report) {
  const blob = new Blob([report.content_md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `weekly-report-${report.period_end}.md`
  a.click()
  URL.revokeObjectURL(url)
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportSummary[]>([])
  const [current, setCurrent] = useState<Report | null>(null)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const refresh = () => {
    api.listReports().then(setReports).catch((e: unknown) => setError(String(e)))
  }
  useEffect(refresh, [])

  const generate = async () => {
    setGenerating(true)
    setError('')
    try {
      const r = await api.generateWeeklyReport()
      setCurrent(r)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setGenerating(false)
    }
  }

  const open = async (id: number) => {
    setError('')
    try {
      setCurrent(await api.getReport(id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[260px_1fr]">
      <aside>
        <h1 className="rise font-display text-2xl font-semibold">
          <span className="pen-underline">周报</span>
        </h1>
        <button
          onClick={generate}
          disabled={generating}
          className="rise rise-1 mt-4 w-full rounded-md bg-vermilion px-4 py-2 text-sm font-medium text-white hover:bg-vermilion-deep disabled:opacity-50"
        >
          {generating ? '教练撰写中…' : '生成本周周报'}
        </button>
        {error && <p className="mt-2 text-sm text-vermilion-deep">{error}</p>}
        <ul className="rise rise-2 mt-4 space-y-1">
          {reports.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => open(r.id)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  current?.id === r.id
                    ? 'bg-vermilion-wash text-vermilion-deep'
                    : 'text-ink-soft hover:bg-paper-deep'
                }`}
              >
                {r.period_start} ~ {r.period_end}
              </button>
            </li>
          ))}
          {reports.length === 0 && (
            <li className="px-3 py-2 text-sm text-ink-faint">还没有周报。</li>
          )}
        </ul>
      </aside>

      <main className="rise rise-2">
        {current ? (
          <div className="rounded-md border border-line bg-card p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between border-b border-line pb-3">
              <span className="text-xs text-ink-faint">
                生成于 {new Date(current.created_at).toLocaleString()}
              </span>
              <button
                onClick={() => exportMarkdown(current)}
                className="rounded-md border border-line px-3 py-1.5 text-xs text-ink-soft hover:border-ink-faint"
              >
                导出 Markdown
              </button>
            </div>
            <Markdown text={current.content_md} />
          </div>
        ) : (
          <p className="mt-12 text-center text-ink-faint">
            选择左侧的一份周报,或生成本周的。
          </p>
        )}
      </main>
    </div>
  )
}

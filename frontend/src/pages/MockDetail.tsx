import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type MockSession } from '../lib/api'
import { DrillList, RubricBars, TranscriptView, VerdictBadge } from '../components/MockReport'

export default function MockDetailPage() {
  const { id } = useParams()
  const [session, setSession] = useState<MockSession | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getMock(Number(id)).then(setSession).catch((e: unknown) => setError(String(e)))
  }, [id])

  if (error) return <p className="text-vermilion-deep">{error}</p>
  if (!session) return <p className="text-ink-faint">加载中…</p>

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/mock" className="text-sm text-ink-faint hover:text-ink">
        ← 返回模拟面试
      </Link>
      <div className="rise mt-3 flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold">
          {session.problem.lc_id}. {session.problem.title}
        </h1>
        <VerdictBadge verdict={session.verdict} />
      </div>
      <p className="rise rise-1 mt-1 text-sm text-ink-soft">
        {new Date(session.created_at).toLocaleString()} · 用时{' '}
        {Math.round((session.duration_sec ?? 0) / 60)} 分钟
      </p>

      <div className="rise rise-2 mt-6 space-y-6 rounded-md border border-line bg-card p-6 shadow-sm">
        {session.rubric ? (
          <RubricBars rubric={session.rubric} />
        ) : (
          <p className="text-sm text-ink-faint">这场面试没有完成评估。</p>
        )}
        {session.postmortem && (
          <div>
            <h3 className="mb-2 text-sm font-medium text-ink-soft">复盘</h3>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{session.postmortem}</p>
          </div>
        )}
        {session.drills && <DrillList drills={session.drills} />}
        <TranscriptView transcript={session.transcript} />
      </div>
    </div>
  )
}

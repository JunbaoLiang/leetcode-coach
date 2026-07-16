import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  streamMockMessage,
  type ChatMessage,
  type MockSession,
  type MockStart,
  type MockSummary,
  type Problem,
} from '../lib/api'
import {
  DrillList,
  RubricBars,
  TranscriptView,
  VerdictBadge,
  VERDICT_META,
} from '../components/MockReport'

function fmtClock(totalSec: number): string {
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function MockPage() {
  const [phase, setPhase] = useState<'landing' | 'interview' | 'report'>('landing')
  const [session, setSession] = useState<MockStart | null>(null)
  const [result, setResult] = useState<MockSession | null>(null)

  return (
    <div>
      {phase === 'landing' && (
        <Landing
          onStarted={(s) => {
            setSession(s)
            setPhase('interview')
          }}
        />
      )}
      {phase === 'interview' && session && (
        <Interview
          session={session}
          onFinished={(r) => {
            setResult(r)
            setPhase('report')
          }}
        />
      )}
      {phase === 'report' && result && <FinalReport result={result} />}
    </div>
  )
}

/* ── landing: start options + history ── */

function Landing({ onStarted }: { onStarted: (s: MockStart) => void }) {
  const [problems, setProblems] = useState<Problem[]>([])
  const [picked, setPicked] = useState<number | null>(null)
  const [history, setHistory] = useState<MockSummary[]>([])
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .listProblems()
      .then((all) => setProblems(all.filter((p) => !p.patterns.includes('primers'))))
      .catch(() => {})
    api.listMock().then(setHistory).catch(() => {})
  }, [])

  const start = async (problemId: number | null) => {
    setStarting(true)
    setError('')
    try {
      onStarted(await api.startMock(problemId))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStarting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="rise font-display text-2xl font-semibold">
        <span className="pen-underline">模拟面试</span>
      </h1>
      <p className="rise rise-1 mt-3 text-sm text-ink-soft">
        45 分钟,面试官全程不出戏、不提示、不确认对错。代码写在纯文本框里,不判题——像真的一样。
      </p>

      <div className="rise rise-2 mt-6 flex flex-wrap items-center gap-3 rounded-md border border-line bg-card p-5 shadow-sm">
        <button
          onClick={() => start(null)}
          disabled={starting}
          className="rounded-md bg-vermilion px-5 py-2.5 text-sm font-medium text-white hover:bg-vermilion-deep disabled:opacity-50"
        >
          {starting ? '面试官入场中…' : '开始面试(随机选题,偏向弱点)'}
        </button>
        <span className="text-sm text-ink-faint">或指定一题:</span>
        <select
          value={picked ?? ''}
          onChange={(e) => setPicked(e.target.value ? Number(e.target.value) : null)}
          className="rounded-md border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-vermilion"
        >
          <option value="">选择题目…</option>
          {problems.map((p) => (
            <option key={p.id} value={p.id}>
              {p.lc_id}. {p.title}
            </option>
          ))}
        </select>
        {picked !== null && (
          <button
            onClick={() => start(picked)}
            disabled={starting}
            className="rounded-md border border-vermilion px-4 py-2 text-sm text-vermilion hover:bg-vermilion-wash disabled:opacity-50"
          >
            用这题开始
          </button>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-vermilion-deep">{error}</p>}

      <History history={history} />
    </div>
  )
}

function History({ history }: { history: MockSummary[] }) {
  if (history.length === 0) return null
  const chrono = [...history].reverse() // oldest → newest for the trend
  return (
    <section className="rise rise-3 mt-10">
      <h2 className="mb-3 text-sm font-medium text-ink-soft">历史面试 · {history.length} 场</h2>

      {chrono.some((h) => h.rubric_avg !== null) && (
        <div className="mb-4 flex items-end gap-1.5" title="评分趋势(rubric 平均分,满分 5)">
          {chrono.map((h) =>
            h.rubric_avg === null ? null : (
              <div key={h.id} className="flex flex-col items-center gap-1">
                <span className="font-mono text-[10px] text-ink-faint">
                  {h.rubric_avg.toFixed(1)}
                </span>
                <div
                  className={`w-6 rounded-t-sm ${
                    h.rubric_avg >= 3.5
                      ? 'bg-seal-green'
                      : h.rubric_avg >= 2.5
                        ? 'bg-amber-warn'
                        : 'bg-vermilion'
                  }`}
                  style={{ height: `${h.rubric_avg * 14}px` }}
                />
              </div>
            ),
          )}
        </div>
      )}

      <div className="rounded-md border border-line shadow-sm">
        {history.map((h) => (
          <Link
            key={h.id}
            to={`/mock/${h.id}`}
            className="flex items-center justify-between gap-3 border-b border-line bg-card px-4 py-3 transition-colors first:rounded-t-md last:rounded-b-md last:border-b-0 hover:bg-paper-deep/60"
          >
            <span className="text-sm font-medium">
              {h.problem.lc_id}. {h.problem.title}
            </span>
            <span className="flex items-center gap-3">
              <span className="text-xs text-ink-faint">
                {new Date(h.created_at).toLocaleDateString()}
              </span>
              {h.verdict && (
                <span
                  className={`rounded-md px-2 py-0.5 text-xs font-medium ${VERDICT_META[h.verdict]?.cls ?? ''}`}
                >
                  {VERDICT_META[h.verdict]?.label ?? h.verdict}
                </span>
              )}
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}

/* ── interview: countdown + chat + code box ── */

function Interview({
  session,
  onFinished,
}: {
  session: MockStart
  onFinished: (r: MockSession) => void
}) {
  const [remaining, setRemaining] = useState(session.duration_sec)
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: session.opening },
  ])
  const [input, setInput] = useState('')
  const [code, setCode] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [error, setError] = useState('')
  const bottom = useRef<HTMLDivElement>(null)
  const finishRef = useRef<() => void>(() => {})

  const elapsed = session.duration_sec - remaining

  const finish = useCallback(async () => {
    if (finishing) return
    setFinishing(true)
    setError('')
    try {
      onFinished(await api.finishMock(session.session_id, elapsed, code || null))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setFinishing(false)
    }
  }, [finishing, onFinished, session.session_id, elapsed, code])
  finishRef.current = finish

  useEffect(() => {
    const t = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(t)
          finishRef.current() // time's up -> auto grade
          return 0
        }
        return r - 1
      })
    }, 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text: string) => {
    if (!text.trim() || streaming) return
    const history: ChatMessage[] = [...messages, { role: 'user', content: text.trim() }]
    setMessages([...history, { role: 'assistant', content: '' }])
    setStreaming(true)
    setError('')
    try {
      await streamMockMessage({ session_id: session.session_id, message: text.trim() }, (delta) =>
        setMessages((cur) => {
          const next = [...cur]
          next[next.length - 1] = {
            role: 'assistant',
            content: next[next.length - 1].content + delta,
          }
          return next
        }),
      )
    } catch (e) {
      setMessages((cur) => cur.slice(0, -2))
      setInput(text.trim()) // don't lose what the user typed
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div>
      <div className="rise flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-xl font-semibold">
          {session.problem.lc_id}. {session.problem.title}
        </h1>
        <div className="flex items-center gap-4">
          <span
            className={`font-mono text-3xl font-semibold tabular-nums ${
              remaining <= 300 ? 'text-vermilion' : ''
            }`}
          >
            {fmtClock(remaining)}
          </span>
          <button
            onClick={finish}
            disabled={finishing}
            className="rounded-md border border-vermilion px-4 py-2 text-sm text-vermilion hover:bg-vermilion-wash disabled:opacity-50"
          >
            {finishing ? '评估中…' : '提前结束,出报告'}
          </button>
        </div>
      </div>
      {error && <p className="mt-2 text-sm text-vermilion-deep">{error}</p>}

      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        {/* chat */}
        <div className="flex h-[calc(100vh-14rem)] flex-col rounded-md border border-line bg-card shadow-sm">
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[92%] whitespace-pre-wrap rounded-md px-3 py-2 text-sm leading-relaxed ${
                  m.role === 'user' ? 'ml-auto bg-paper-deep' : 'border border-line bg-paper'
                } ${m.role === 'assistant' && streaming && i === messages.length - 1 ? 'stream-cursor' : ''}`}
              >
                {m.content}
              </div>
            ))}
            <div ref={bottom} />
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              send(input)
              setInput('')
            }}
            className="flex gap-2 border-t border-line p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                // IME(拼音)选词确认的回车不触发表单提交
                if ((e.nativeEvent.isComposing || e.keyCode === 229) && e.key === 'Enter')
                  e.preventDefault()
              }}
              disabled={streaming || finishing}
              placeholder="口述你的思路…"
              className="min-w-0 flex-1 rounded-md border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-vermilion"
            />
            <button
              type="submit"
              disabled={streaming || finishing || !input.trim()}
              className="rounded-md bg-ink px-4 py-2 text-sm text-paper hover:opacity-85 disabled:opacity-40"
            >
              发送
            </button>
          </form>
        </div>

        {/* code box */}
        <div className="flex h-[calc(100vh-14rem)] flex-col rounded-md border border-line bg-card shadow-sm">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="text-sm font-medium">代码(纯文本,不判题)</span>
            <button
              onClick={() => {
                if (code.trim()) send(`我目前的代码:\n\`\`\`\n${code}\n\`\`\``)
              }}
              disabled={streaming || finishing || !code.trim()}
              className="rounded-md border border-line px-3 py-1 text-xs text-ink-soft hover:border-ink-faint disabled:opacity-40"
            >
              给面试官看当前代码
            </button>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            placeholder={'def solution():\n    # 像白板一样写,没有运行按钮'}
            className="flex-1 resize-none bg-paper p-4 font-mono text-sm leading-relaxed outline-none"
          />
        </div>
      </div>
    </div>
  )
}

/* ── final report ── */

function FinalReport({ result }: { result: MockSession }) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="rise flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold">
          <span className="pen-underline">面试报告</span>
        </h1>
        <VerdictBadge verdict={result.verdict} />
      </div>
      <p className="rise rise-1 mt-2 text-sm text-ink-soft">
        {result.problem.lc_id}. {result.problem.title} · 用时{' '}
        {Math.round((result.duration_sec ?? 0) / 60)} 分钟
      </p>

      <div className="rise rise-2 mt-6 space-y-6 rounded-md border border-line bg-card p-6 shadow-sm">
        {result.rubric && <RubricBars rubric={result.rubric} />}
        {result.postmortem && (
          <div>
            <h3 className="mb-2 text-sm font-medium text-ink-soft">复盘</h3>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{result.postmortem}</p>
          </div>
        )}
        {result.drills && <DrillList drills={result.drills} />}
        <TranscriptView transcript={result.transcript} />
      </div>

      <div className="rise rise-3 mt-6 flex gap-3">
        <a
          href="/mock"
          className="rounded-md bg-vermilion px-4 py-2 text-sm font-medium text-white hover:bg-vermilion-deep"
        >
          再来一场
        </a>
        <Link to="/" className="rounded-md border border-line px-4 py-2 text-sm text-ink-soft">
          回到今日计划
        </Link>
      </div>
    </div>
  )
}

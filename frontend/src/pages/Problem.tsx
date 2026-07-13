import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  api,
  problemUrl,
  streamHint,
  type Attempt,
  type ChatMessage,
  type FinishResult,
  type Outcome,
  type Problem,
  type Profile,
} from '../lib/api'
import { DifficultyBadge, PatternChips, ProblemTitle } from '../components/ProblemMeta'
import { MISTAKE_TAG_LABELS, OUTCOME_LABELS, RECALL_LABELS } from '../lib/labels'

function fmtClock(totalSec: number): string {
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const HINT_BUTTON_LABEL: Record<number, string> = {
  1: '需要一点方向(L1)',
  2: '需要更深一层提示(L2)',
  3: '给我算法骨架(L3)',
  4: '看完整讲解(投降 · L4)',
}

export default function ProblemPage({ profile }: { profile: Profile | null }) {
  const { id } = useParams()
  const problemId = Number(id)

  const [problem, setProblem] = useState<Problem | null>(null)
  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [error, setError] = useState('')

  // ── timer ────────────────────────────────────────────────────────────────
  const [seconds, setSeconds] = useState(0)
  const [running, setRunning] = useState(true)
  useEffect(() => {
    if (!running) return
    const t = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [running])

  // ── coach chat ───────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [hintLevel, setHintLevel] = useState(0)
  const [streaming, setStreaming] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatError, setChatError] = useState('')
  const chatBottom = useRef<HTMLDivElement>(null)

  // ── record form ──────────────────────────────────────────────────────────
  const [formOpen, setFormOpen] = useState(false)
  const [outcome, setOutcome] = useState<Outcome>('ac')
  const [recall, setRecall] = useState<number | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [code, setCode] = useState('')
  const [explanation, setExplanation] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<FinishResult | null>(null)

  useEffect(() => {
    if (!Number.isFinite(problemId)) return
    api.getProblem(problemId).then(setProblem).catch((e: unknown) => setError(String(e)))
    api
      .startAttempt(problemId)
      .then((a) => {
        setAttempt(a)
        setHintLevel(a.hint_level_max)
      })
      .catch((e: unknown) => setError(String(e)))
  }, [problemId])

  useEffect(() => {
    chatBottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendToCoach = useCallback(
    async (level: number, userText: string | null) => {
      if (!attempt || streaming) return
      setChatError('')
      const history = [...messages]
      if (userText) history.push({ role: 'user', content: userText })
      setMessages([...history, { role: 'assistant', content: '' }])
      setStreaming(true)
      try {
        await streamHint({ attempt_id: attempt.id, level, messages: history }, (delta) => {
          setMessages((cur) => {
            const next = [...cur]
            next[next.length - 1] = {
              role: 'assistant',
              content: next[next.length - 1].content + delta,
            }
            return next
          })
        })
        setHintLevel((lv) => Math.max(lv, level))
      } catch (e) {
        setMessages((cur) => cur.slice(0, userText ? -2 : -1))
        setChatError(e instanceof Error ? e.message : String(e))
      } finally {
        setStreaming(false)
      }
    },
    [attempt, messages, streaming],
  )

  const toggleTag = (tag: string) =>
    setTags((cur) => (cur.includes(tag) ? cur.filter((t) => t !== tag) : [...cur, tag]))

  const submitRecord = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!attempt || recall === null) return
    setSubmitting(true)
    setError('')
    try {
      const res = await api.finishAttempt(attempt.id, {
        outcome,
        duration_sec: seconds,
        recall_self_report: recall,
        mistake_tags: tags,
        code_snapshot: code || undefined,
        self_explanation: explanation || undefined,
      })
      setResult(res)
      setRunning(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (error && !problem) return <p className="text-vermilion-deep">{error}</p>
  if (!problem || !attempt) return <p className="text-ink-faint">准备中…</p>

  const url = profile ? problemUrl(problem.slug, profile.platform) : '#'
  const platformName = profile?.platform === 'leetcode_com' ? 'leetcode.com' : 'leetcode.cn'
  const finished = result !== null

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_minmax(320px,420px)]">
      {/* ── left: problem meta + timer + record ── */}
      <div>
        <div className="rise flex flex-wrap items-center gap-2">
          <DifficultyBadge difficulty={problem.difficulty} />
          <PatternChips patterns={problem.patterns} />
        </div>
        <h1 className="rise rise-1 mt-2 font-display text-2xl font-semibold">
          <ProblemTitle problem={problem} />
        </h1>

        <div className="rise rise-2 mt-4 flex items-center gap-3">
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-paper transition-opacity hover:opacity-85"
          >
            在 {platformName} 打开 ↗
          </a>
          <span className="text-xs text-ink-faint">题面与判题都在官网完成</span>
        </div>

        {/* timer */}
        <div className="rise rise-3 mt-6 flex items-center gap-4 rounded-md border border-line bg-card px-5 py-4 shadow-sm">
          <span
            className={`font-mono text-4xl font-semibold tabular-nums ${
              running && !finished ? '' : 'text-ink-faint'
            }`}
          >
            {fmtClock(seconds)}
          </span>
          {!finished && (
            <button
              onClick={() => setRunning((r) => !r)}
              className="rounded-md border border-line px-3 py-1.5 text-sm text-ink-soft hover:border-ink-faint"
            >
              {running ? '暂停' : '继续'}
            </button>
          )}
          {running && !finished && <span className="tick-pulse h-2 w-2 rounded-full bg-vermilion" />}
        </div>

        {/* record form / result */}
        {finished ? (
          <ResultPanel result={result} />
        ) : formOpen ? (
          <form
            onSubmit={submitRecord}
            className="rise mt-6 space-y-5 rounded-md border border-line bg-card p-5 shadow-sm"
          >
            <fieldset>
              <legend className="mb-2 text-sm font-medium">结果</legend>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(OUTCOME_LABELS) as Outcome[]).map((o) => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => setOutcome(o)}
                    className={`rounded-md border px-3 py-1.5 text-sm ${
                      outcome === o
                        ? 'border-vermilion bg-vermilion-wash font-medium'
                        : 'border-line hover:border-ink-faint'
                    }`}
                  >
                    {OUTCOME_LABELS[o]}
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="mb-2 text-sm font-medium">
                回忆自评 <span className="text-xs font-normal text-ink-faint">(必填,决定复习间隔)</span>
              </legend>
              <div className="flex flex-wrap gap-2">
                {RECALL_LABELS.map((label, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setRecall(i)}
                    className={`rounded-md border px-2.5 py-1.5 text-xs ${
                      recall === i
                        ? 'border-vermilion bg-vermilion-wash font-medium'
                        : 'border-line hover:border-ink-faint'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="mb-2 text-sm font-medium">
                错误标签 <span className="text-xs font-normal text-ink-faint">(多选,喂给弱点档案)</span>
              </legend>
              <div className="flex flex-wrap gap-2">
                {Object.entries(MISTAKE_TAG_LABELS).map(([tag, label]) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => toggleTag(tag)}
                    className={`rounded-md border px-2.5 py-1.5 text-xs ${
                      tags.includes(tag)
                        ? 'border-vermilion bg-vermilion-wash font-medium'
                        : 'border-line hover:border-ink-faint'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>

            <label className="block">
              <span className="mb-1 block text-sm font-medium">AC 代码(粘贴归档)</span>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="h-36 w-full resize-y rounded-md border border-line bg-paper px-3 py-2 font-mono text-xs outline-none focus:border-vermilion"
                placeholder="def solution(): ..."
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium">
                用自己的话讲一遍 <span className="text-xs font-normal text-ink-faint">(可选)</span>
              </span>
              <textarea
                value={explanation}
                onChange={(e) => setExplanation(e.target.value)}
                className="h-20 w-full resize-y rounded-md border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-vermilion"
                placeholder="为什么这样做?复杂度?哪个 edge case 容易漏?"
              />
            </label>

            {error && <p className="text-sm text-vermilion-deep">{error}</p>}

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={submitting || recall === null}
                className="rounded-md bg-vermilion px-5 py-2 text-sm font-medium text-white hover:bg-vermilion-deep disabled:opacity-40"
              >
                {submitting ? '提交中…' : '提交记录'}
              </button>
              {recall === null && (
                <span className="text-xs text-ink-faint">先完成回忆自评</span>
              )}
            </div>
          </form>
        ) : (
          <button
            onClick={() => {
              setFormOpen(true)
              setRunning(false)
            }}
            className="rise rise-4 mt-6 rounded-md bg-vermilion px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-vermilion-deep"
          >
            完成,记录结果
          </button>
        )}
      </div>

      {/* ── right: coach chat ── */}
      <aside className="flex h-[calc(100vh-9rem)] flex-col rounded-md border border-line bg-card shadow-sm lg:sticky lg:top-6">
        <div className="border-b border-line px-4 py-3">
          <h2 className="font-display font-semibold">教练</h2>
          <p className="text-xs text-ink-faint">卡住了再来问——挣扎的时间才是学习发生的地方。</p>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
          {messages.length === 0 && (
            <p className="mt-8 text-center text-sm text-ink-faint">
              还没有提示。
              <br />
              先自己想一想,需要时逐级请求。
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[92%] whitespace-pre-wrap rounded-md px-3 py-2 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'ml-auto bg-paper-deep'
                  : 'border border-line bg-paper'
              } ${
                m.role === 'assistant' && streaming && i === messages.length - 1
                  ? 'stream-cursor'
                  : ''
              }`}
            >
              {m.content}
            </div>
          ))}
          <div ref={chatBottom} />
        </div>

        {chatError && <p className="px-4 pb-1 text-xs text-vermilion-deep">{chatError}</p>}

        <div className="border-t border-line p-3">
          {finished ? (
            <p className="text-center text-xs text-ink-faint">本次做题已记录,提示窗已关闭。</p>
          ) : (
            <>
              {hintLevel >= 1 && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    if (!chatInput.trim()) return
                    sendToCoach(hintLevel, chatInput.trim())
                    setChatInput('')
                  }}
                  className="mb-2 flex gap-2"
                >
                  <input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    disabled={streaming}
                    placeholder={`在 L${hintLevel} 内继续追问…`}
                    className="min-w-0 flex-1 rounded-md border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-vermilion"
                  />
                  <button
                    type="submit"
                    disabled={streaming || !chatInput.trim()}
                    className="rounded-md border border-line px-3 py-2 text-sm text-ink-soft hover:border-ink-faint disabled:opacity-40"
                  >
                    发送
                  </button>
                </form>
              )}
              {hintLevel < 4 && (
                <button
                  onClick={() => sendToCoach(hintLevel + 1, null)}
                  disabled={streaming}
                  className={`w-full rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                    hintLevel + 1 === 4
                      ? 'border border-vermilion text-vermilion hover:bg-vermilion-wash'
                      : 'bg-ink text-paper hover:opacity-85'
                  }`}
                >
                  {HINT_BUTTON_LABEL[hintLevel + 1]}
                </button>
              )}
              <p className="mt-2 text-center text-[11px] text-ink-faint">
                已用提示:L{hintLevel} · 提示深度会影响复习安排
              </p>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}

function ResultPanel({ result }: { result: FinishResult }) {
  const review = result.review
  return (
    <div className="rise mt-6 rounded-md border border-line bg-card p-5 shadow-sm">
      <h2 className="font-display text-lg font-semibold text-seal-green">已记录 ✓</h2>
      {review ? (
        <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="text-xs text-ink-faint">证据合成质量分</dt>
            <dd className="font-mono text-xl font-semibold">
              {result.quality?.toFixed(1)}
              <span className="text-xs text-ink-faint"> / 5</span>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">下次复习</dt>
            <dd className="font-mono text-xl font-semibold">{review.due_date}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">掌握度</dt>
            <dd className="text-xl">
              {review.mastery === 'learning' ? '学习中' : review.mastery === 'reviewing' ? '复习中' : '已掌握'}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="mt-2 text-sm text-ink-soft">热身题不进入复习循环——AC 即通过。</p>
      )}
      <div className="mt-4 flex gap-3">
        <Link
          to="/"
          className="rounded-md bg-vermilion px-4 py-2 text-sm font-medium text-white hover:bg-vermilion-deep"
        >
          回到今日计划
        </Link>
        <Link to="/stats" className="rounded-md border border-line px-4 py-2 text-sm text-ink-soft">
          看看进度
        </Link>
      </div>
    </div>
  )
}

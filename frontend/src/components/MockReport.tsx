import { useState } from 'react'
import type { ChatMessage, MockDrill, MockRubric } from '../lib/api'
import { patternLabel } from '../lib/labels'

export const VERDICT_META: Record<string, { label: string; cls: string }> = {
  strong_hire: { label: 'Strong Hire', cls: 'bg-seal-green text-white' },
  hire: { label: 'Hire', cls: 'bg-seal-green-wash text-seal-green' },
  lean_hire: { label: 'Lean Hire', cls: 'bg-amber-wash text-amber-warn' },
  no_hire: { label: 'No Hire', cls: 'bg-vermilion-wash text-vermilion-deep' },
}

const RUBRIC_LABELS: [keyof MockRubric, string][] = [
  ['communication', '沟通表达'],
  ['problem_solving', '解题推进'],
  ['code_correctness', '代码正确性'],
  ['complexity_analysis', '复杂度分析'],
  ['edge_cases', '边界意识'],
  ['time_management', '时间管理'],
]

export function VerdictBadge({ verdict }: { verdict: string | null }) {
  const meta = verdict ? VERDICT_META[verdict] : null
  if (!meta) return null
  return (
    <span className={`rounded-md px-3 py-1 text-sm font-semibold ${meta.cls}`}>{meta.label}</span>
  )
}

export function RubricBars({ rubric }: { rubric: MockRubric }) {
  return (
    <div className="space-y-2">
      {RUBRIC_LABELS.map(([key, label]) => {
        const score = rubric[key]
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-sm text-ink-soft">{label}</span>
            <div className="flex flex-1 gap-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className={`h-3 flex-1 rounded-sm ${
                    i <= score
                      ? score <= 2
                        ? 'bg-vermilion'
                        : score === 3
                          ? 'bg-amber-warn'
                          : 'bg-seal-green'
                      : 'bg-paper-deep'
                  }`}
                />
              ))}
            </div>
            <span className="w-8 text-right font-mono text-sm font-semibold">{score}</span>
          </div>
        )
      })}
    </div>
  )
}

export function DrillList({ drills }: { drills: MockDrill[] }) {
  if (drills.length === 0) return null
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-ink-soft">补练处方</h3>
      <ul className="space-y-2">
        {drills.map((d, i) => (
          <li key={i} className="rounded-md bg-paper p-3 text-sm">
            <span className="mr-2 rounded-sm border border-line bg-card px-1.5 py-0.5 text-xs text-ink-soft">
              {patternLabel(d.pattern)} × {d.count}
            </span>
            {d.instruction}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function TranscriptView({ transcript }: { transcript: ChatMessage[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-sm text-vermilion underline-offset-2 hover:underline"
      >
        {open ? '收起对话记录 ▲' : `回看完整对话(${transcript.length} 轮)▼`}
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          {transcript.map((m, i) => (
            <div
              key={i}
              className={`whitespace-pre-wrap rounded-md px-3 py-2 text-sm leading-relaxed ${
                m.role === 'user' ? 'ml-8 bg-paper-deep' : 'mr-8 border border-line bg-paper'
              }`}
            >
              <span className="mb-1 block text-[11px] text-ink-faint">
                第 {i + 1} 轮 · {m.role === 'user' ? '候选人' : '面试官'}
              </span>
              {m.content}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

import type { Problem } from '../lib/api'
import { DIFFICULTY_LABELS, patternLabel } from '../lib/labels'

const DIFF_STYLE: Record<string, string> = {
  easy: 'bg-seal-green-wash text-seal-green',
  medium: 'bg-amber-wash text-amber-warn',
  hard: 'bg-vermilion-wash text-vermilion-deep',
}

export function DifficultyBadge({ difficulty }: { difficulty: string }) {
  return (
    <span
      className={`inline-block rounded-sm px-1.5 py-0.5 text-xs font-medium ${DIFF_STYLE[difficulty] ?? ''}`}
    >
      {DIFFICULTY_LABELS[difficulty] ?? difficulty}
    </span>
  )
}

export function PatternChips({ patterns }: { patterns: string[] }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      {patterns.map((p) => (
        <span
          key={p}
          className="rounded-sm border border-line bg-card px-1.5 py-0.5 text-xs text-ink-soft"
        >
          {patternLabel(p)}
        </span>
      ))}
    </span>
  )
}

/** importance 1-4 rendered as filled dots — 4 = must-know */
export function ImportanceDots({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" title={`重要度 ${value}/4`}>
      {[1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={`h-1.5 w-1.5 rounded-full ${i <= value ? 'bg-vermilion' : 'bg-line'}`}
        />
      ))}
    </span>
  )
}

export function ProblemTitle({ problem }: { problem: Problem }) {
  return (
    <span className="font-medium">
      {problem.lc_id != null && (
        <span className="font-mono text-ink-faint">{problem.lc_id}. </span>
      )}
      {problem.title}
    </span>
  )
}

// Typed API client for the FastAPI backend (proxied at /api in dev).

export type Track = 'mle' | 'ai4s' | 'swe_newgrad' | 'career_switch'
export type Level = 'junior' | 'mid' | 'senior'
export type Platform = 'leetcode_cn' | 'leetcode_com'
export type Outcome = 'ac_first_try' | 'ac' | 'failed' | 'abandoned'

export interface Profile {
  id: number
  avatar_url?: string | null
  name: string
  background: string
  target_track: Track
  target_level: Level
  timeline_weeks: number | null
  weekly_hours: number
  preferred_lang: string
  platform: Platform
  include_primers: boolean
}

export interface Problem {
  id: number
  track: string
  lc_id: number | null
  slug: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  patterns: string[]
  importance: number
  // ML-track problems carry their original statement + browser-judged test spec
  statement?: string | null
  test_spec?: Record<string, unknown> | null
}

export interface PlanItem {
  problem: Problem
  url: string
  kind: 'review' | 'new' | 'bonus'
  done: boolean
  stale: boolean
  due_date: string | null
  overdue_days: number | null
  review_count: number | null
  mastery: string | null
}

export interface TodayPlan {
  items: PlanItem[]
  done_count: number
  total_count: number
  bonus_done: number
  budget_minutes: number
  streak: number
}

export interface Attempt {
  id: number
  problem_id: number
  started_at: string
  outcome: Outcome | null
  hint_level_max: number
  judge_failures: number
  duration_sec: number | null
  mistake_tags: string[]
}

export interface ReviewState {
  problem_id: number
  ease_factor: number
  interval_days: number
  due_date: string
  review_count: number
  last_quality: number | null
  mastery: string
}

export interface FinishResult {
  attempt: Attempt
  review: ReviewState | null
  quality: number | null
}

export interface Stats {
  pattern_progress: { pattern: string; solved: number; total: number }[]
  difficulty_progress: { difficulty: string; solved: number; total: number }[]
  streak: number
  heatmap: Record<string, number>
  total_solved: number
  total_attempts: number
  ac_first_try_rate: number | null
  avg_hint_level_30d: number | null
}

export interface CodeReview {
  correctness_risks: string[]
  complexity: { claimed: string | null; actual: string }
  style_issues: string[]
  optimal_comparison: string
  mistake_tags_suggested: string[]
}

export interface TeachbackResult {
  passed: boolean
  gaps: string[]
  follow_up_question: string | null
  mastery: string | null
}

export interface Weaknesses {
  tags: { tag: string; count: number; weighted: number; rate: number }[]
  patterns: { pattern: string; attempts: number; error_rate: number }[]
  weak_patterns: string[]
}

export interface Report {
  id: number
  period_start: string
  period_end: string
  content_md: string
  metrics: Record<string, unknown>
  created_at: string
}

export type ReportSummary = Pick<Report, 'id' | 'period_start' | 'period_end' | 'created_at'>

export interface MockProblem {
  id: number
  lc_id: number | null
  title: string
}

export interface MockRubric {
  communication: number
  problem_solving: number
  code_correctness: number
  complexity_analysis: number
  edge_cases: number
  time_management: number
}

export interface MockDrill {
  pattern: string
  count: number
  instruction: string
}

export interface MockSession {
  id: number
  problem: MockProblem
  transcript: ChatMessage[]
  duration_sec: number | null
  rubric: MockRubric | null
  verdict: string | null
  postmortem: string | null
  drills: MockDrill[] | null
  created_at: string
}

export interface MockSummary {
  id: number
  problem: MockProblem
  verdict: string | null
  rubric_avg: number | null
  created_at: string
}

export interface MockStart {
  session_id: number
  problem: MockProblem
  opening: string
  duration_sec: number
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = await resp.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail)
  }
  return resp.json() as Promise<T>
}

const inflightStarts = new Map<number, Promise<Attempt>>()

export const api = {
  getProfile: () => request<Profile>('/api/profile'),
  saveProfile: (p: Omit<Profile, 'id'>) =>
    request<Profile>('/api/profile', { method: 'POST', body: JSON.stringify(p) }),
  getTodayPlan: () => request<TodayPlan>('/api/plan/today'),
  addBonusProblem: () => request<PlanItem>('/api/plan/bonus', { method: 'POST' }),
  getProblem: (id: number) => request<Problem>(`/api/problems/${id}`),
  startAttempt: (problem_id: number) => {
    // dedupe concurrent starts (React StrictMode double-mounts effects in dev)
    const pending = inflightStarts.get(problem_id)
    if (pending) return pending
    const p = request<Attempt>('/api/attempts', {
      method: 'POST',
      body: JSON.stringify({ problem_id }),
    }).finally(() => inflightStarts.delete(problem_id))
    inflightStarts.set(problem_id, p)
    return p
  },
  finishAttempt: (
    id: number,
    body: {
      outcome: Outcome
      duration_sec: number
      recall_self_report: number
      mistake_tags: string[]
      code_snapshot?: string
      self_explanation?: string
      judge_failures?: number
    },
  ) => request<FinishResult>(`/api/attempts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  getStats: () => request<Stats>('/api/stats'),
  reviewCode: (attempt_id: number) =>
    request<CodeReview>('/api/review-code', {
      method: 'POST',
      body: JSON.stringify({ attempt_id }),
    }),
  confirmTags: (attemptId: number, tags: string[]) =>
    request<{ mistake_tags: string[] }>(`/api/attempts/${attemptId}/confirm-tags`, {
      method: 'POST',
      body: JSON.stringify({ tags }),
    }),
  teachback: (attempt_id: number, transcript: ChatMessage[]) =>
    request<TeachbackResult>('/api/teachback', {
      method: 'POST',
      body: JSON.stringify({ attempt_id, transcript }),
    }),
  getWeaknesses: () => request<Weaknesses>('/api/weaknesses'),
  generateWeeklyReport: () => request<Report>('/api/reports/weekly', { method: 'POST' }),
  listReports: () => request<ReportSummary[]>('/api/reports'),
  getReport: (id: number) => request<Report>(`/api/reports/${id}`),
  listProblems: (track = 'algo') => request<Problem[]>(`/api/problems?track=${track}`),
  startMock: (problem_id: number | null) =>
    request<MockStart>('/api/mock/start', {
      method: 'POST',
      body: JSON.stringify({ problem_id }),
    }),
  finishMock: (session_id: number, duration_sec: number, code: string | null) =>
    request<MockSession>('/api/mock/finish', {
      method: 'POST',
      body: JSON.stringify({ session_id, duration_sec, code }),
    }),
  listMock: () => request<MockSummary[]>('/api/mock'),
  getMock: (id: number) => request<MockSession>(`/api/mock/${id}`),
}

export function problemUrl(slug: string, platform: Platform): string {
  const host = platform === 'leetcode_cn' ? 'leetcode.cn' : 'leetcode.com'
  return `https://${host}/problems/${slug}/`
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** Stream a hint over SSE; onDelta fires per text chunk. Resolves when done. */
export function streamHint(
  body: { attempt_id: number; level: number; messages: ChatMessage[] },
  onDelta: (text: string) => void,
): Promise<void> {
  return streamSSE('/api/hints', body, onDelta)
}

/** Stream one interviewer reply in a mock session. */
export function streamMockMessage(
  body: { session_id: number; message: string },
  onDelta: (text: string) => void,
): Promise<void> {
  return streamSSE('/api/mock/message', body, onDelta)
}

async function streamSSE(
  path: string,
  body: unknown,
  onDelta: (text: string) => void,
): Promise<void> {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok || !resp.body) {
    let detail = resp.statusText
    try {
      const parsed = await resp.json()
      if (typeof parsed.detail === 'string') detail = parsed.detail
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const evt of events) {
      const line = evt.trim()
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6)
      if (payload === '[DONE]') return
      const parsed = JSON.parse(payload) as { text?: string; error?: string }
      if (parsed.error) throw new ApiError(503, parsed.error)
      if (parsed.text) onDelta(parsed.text)
    }
  }
}

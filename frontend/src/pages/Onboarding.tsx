import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Level, type Platform, type Profile, type Track } from '../lib/api'

const TRACKS: { value: Track; label: string; note: string }[] = [
  { value: 'mle', label: 'MLE', note: '机器学习工程师(算法 70 : ML 30)' },
  { value: 'ai4s', label: 'AI4S', note: 'AI for Science(算法 60 : ML 40)' },
  { value: 'swe_newgrad', label: 'SWE 应届', note: '纯算法,完整覆盖' },
  { value: 'career_switch', label: '转行者', note: '缓坡 + 入门热身' },
]

const LEVELS: { value: Level; label: string }[] = [
  { value: 'junior', label: '初级' },
  { value: 'mid', label: '中级' },
  { value: 'senior', label: '高级' },
]

export default function Onboarding({
  profile,
  onSaved,
}: {
  profile: Profile | null
  onSaved: (p: Profile) => void
}) {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: profile?.name ?? '',
    background: profile?.background ?? '',
    target_track: profile?.target_track ?? ('mle' as Track),
    target_level: profile?.target_level ?? ('junior' as Level),
    timeline_weeks: profile?.timeline_weeks ?? null,
    weekly_hours: profile?.weekly_hours ?? 8,
    preferred_lang: profile?.preferred_lang ?? 'python',
    platform: profile?.platform ?? ('leetcode_cn' as Platform),
    include_primers: profile?.include_primers ?? false,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const saved = await api.saveProfile(form)
      onSaved(saved)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  const fieldClass =
    'w-full rounded-md border border-line bg-card px-3 py-2 text-sm outline-none focus:border-vermilion'

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="rise font-display text-2xl font-semibold">
        <span className="pen-underline">{profile ? '我的画像' : '开始之前'}</span>
      </h1>
      <p className="rise rise-1 mt-3 text-sm text-ink-soft">
        课程、提示颗粒度、面试 bar 都会按这份画像校准。改了随时保存。
      </p>

      <form onSubmit={submit} className="rise rise-2 mt-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="mb-1 block text-sm text-ink-soft">称呼</span>
            <input
              className={fieldClass}
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="怎么称呼你"
              required
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-ink-soft">做题语言</span>
            <input
              className={fieldClass}
              value={form.preferred_lang}
              onChange={(e) => set('preferred_lang', e.target.value)}
            />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-sm text-ink-soft">
            背景(教练会据此调整讲解方式)
          </span>
          <textarea
            className={`${fieldClass} h-20 resize-none`}
            value={form.background}
            onChange={(e) => set('background', e.target.value)}
            placeholder="例:计算化学 PhD,写过 Python 科研脚本,零前端经验"
          />
        </label>

        <fieldset>
          <legend className="mb-2 text-sm text-ink-soft">目标赛道</legend>
          <div className="grid grid-cols-2 gap-2">
            {TRACKS.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => {
                  set('target_track', t.value)
                  if (t.value === 'career_switch') set('include_primers', true)
                }}
                className={`rounded-md border px-3 py-2 text-left transition-colors ${
                  form.target_track === t.value
                    ? 'border-vermilion bg-vermilion-wash'
                    : 'border-line bg-card hover:border-ink-faint'
                }`}
              >
                <span className="block text-sm font-medium">{t.label}</span>
                <span className="block text-xs text-ink-soft">{t.note}</span>
              </button>
            ))}
          </div>
          <p className="mt-1 text-xs text-ink-faint">M1 阶段课程模板以 MLE 为准,其余赛道 M4 生效。</p>
        </fieldset>

        <div className="grid grid-cols-3 gap-4">
          <label className="block">
            <span className="mb-1 block text-sm text-ink-soft">目标级别</span>
            <select
              className={fieldClass}
              value={form.target_level}
              onChange={(e) => set('target_level', e.target.value as Level)}
            >
              {LEVELS.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-ink-soft">每周投入(小时)</span>
            <input
              type="number"
              min={1}
              max={80}
              className={fieldClass}
              value={form.weekly_hours}
              onChange={(e) => set('weekly_hours', Number(e.target.value))}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-ink-soft">面试倒计时(周,可空)</span>
            <input
              type="number"
              min={1}
              className={fieldClass}
              value={form.timeline_weeks ?? ''}
              onChange={(e) =>
                set('timeline_weeks', e.target.value === '' ? null : Number(e.target.value))
              }
              placeholder="无死线"
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <fieldset>
            <legend className="mb-2 text-sm text-ink-soft">做题平台(题目跳转到)</legend>
            <div className="flex gap-2">
              {(['leetcode_cn', 'leetcode_com'] as Platform[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => set('platform', p)}
                  className={`rounded-md border px-3 py-1.5 text-sm ${
                    form.platform === p
                      ? 'border-vermilion bg-vermilion-wash font-medium'
                      : 'border-line bg-card'
                  }`}
                >
                  {p === 'leetcode_cn' ? 'leetcode.cn' : 'leetcode.com'}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="flex items-end gap-2 pb-1.5">
            <input
              type="checkbox"
              checked={form.include_primers}
              onChange={(e) => set('include_primers', e.target.checked)}
              className="h-4 w-4 accent-vermilion"
            />
            <span className="text-sm">
              加入零基础热身(官方入门 20 题)
            </span>
          </label>
        </div>

        {error && <p className="text-sm text-vermilion-deep">{error}</p>}

        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-vermilion px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-vermilion-deep disabled:opacity-50"
        >
          {saving ? '保存中…' : profile ? '保存修改' : '生成我的课程'}
        </button>
      </form>
    </div>
  )
}

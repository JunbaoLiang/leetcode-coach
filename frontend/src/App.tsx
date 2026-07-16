import { useEffect, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api, ApiError, type Profile } from './lib/api'
import Onboarding from './pages/Onboarding'
import Today from './pages/Today'
import ProblemPage from './pages/Problem'
import Stats from './pages/Stats'
import WeaknessesPage from './pages/Weaknesses'
import ReportsPage from './pages/Reports'
import MockPage from './pages/Mock'
import MockDetailPage from './pages/MockDetail'

function Shell({ profile, children }: { profile: Profile | null; children: React.ReactNode }) {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `px-2 py-1 text-sm transition-colors ${
      isActive ? 'text-vermilion font-medium' : 'text-ink-soft hover:text-ink'
    }`
  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    window.location.href = '/'
  }
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-card/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-display text-xl font-semibold">
            刷题<span className="text-vermilion">教练</span>
          </Link>
          {profile?.avatar_url && (
            <span className="order-last flex items-center gap-2">
              <img
                src={profile.avatar_url}
                alt={profile.name}
                className="h-7 w-7 rounded-full border border-line"
              />
              <button onClick={logout} className="text-xs text-ink-faint hover:text-ink">
                登出
              </button>
            </span>
          )}
          {profile && (
            <nav className="flex items-center gap-2">
              <NavLink to="/" end className={navClass}>
                今日计划
              </NavLink>
              <NavLink to="/stats" className={navClass}>
                进度看板
              </NavLink>
              <NavLink to="/weaknesses" className={navClass}>
                弱点档案
              </NavLink>
              <NavLink to="/mock" className={navClass}>
                模拟面试
              </NavLink>
              <NavLink to="/reports" className={navClass}>
                周报
              </NavLink>
              <NavLink to="/onboarding" className={navClass}>
                我的画像
              </NavLink>
            </nav>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  )
}

function Gate({
  profile,
  loading,
  onSaved,
}: {
  profile: Profile | null
  loading: boolean
  onSaved: (p: Profile) => void
}) {
  const navigate = useNavigate()
  useEffect(() => {
    if (!loading && profile === null) navigate('/onboarding', { replace: true })
  }, [loading, profile, navigate])

  if (loading) return <p className="text-ink-faint">加载中…</p>
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding profile={profile} onSaved={onSaved} />} />
      <Route path="/" element={<Today />} />
      <Route path="/problem/:id" element={<ProblemPage profile={profile} />} />
      <Route path="/stats" element={<Stats />} />
      <Route path="/weaknesses" element={<WeaknessesPage />} />
      <Route path="/mock" element={<MockPage />} />
      <Route path="/mock/:id" element={<MockDetailPage />} />
      <Route path="/reports" element={<ReportsPage />} />
    </Routes>
  )
}

function Login() {
  return (
    <div className="mx-auto mt-24 max-w-sm text-center">
      <h1 className="rise font-display text-3xl font-semibold">
        刷题<span className="text-vermilion">教练</span>
      </h1>
      <p className="rise rise-1 mt-3 text-sm text-ink-soft">
        AI 教练帮你记住更多做过的题、修复真实的弱点。
      </p>
      <a
        href="/api/auth/github"
        className="rise rise-2 mt-8 inline-block rounded-md bg-ink px-6 py-3 text-sm font-medium text-paper hover:opacity-85"
      >
        使用 GitHub 登录
      </a>
    </div>
  )
}

export default function App() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [authRequired, setAuthRequired] = useState(false)
  const [fatal, setFatal] = useState(false)

  useEffect(() => {
    const load = async (retried: boolean) => {
      try {
        setProfile(await api.getProfile())
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) setAuthRequired(true)
        else if (e instanceof ApiError && e.status === 404) {
          /* genuinely no profile -> Gate routes to onboarding */
        } else if (!retried) {
          // transient backend/DB hiccup (e.g. Neon waking from autosuspend) — retry once
          await new Promise((r) => setTimeout(r, 2500))
          return load(true)
        } else {
          console.error(e)
          setFatal(true) // never mistake an outage for "no profile"
          return
        }
      }
      setLoading(false)
    }
    load(false)
  }, [])

  if (authRequired) return <Login />
  if (fatal)
    return (
      <div className="mx-auto mt-24 max-w-sm text-center">
        <h1 className="font-display text-2xl font-semibold">连接不上后端</h1>
        <p className="mt-3 text-sm text-ink-soft">
          可能是服务正在唤醒,你的数据都还在。稍等几秒再试。
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 rounded-md bg-vermilion px-5 py-2 text-sm font-medium text-white hover:bg-vermilion-deep"
        >
          重试
        </button>
      </div>
    )

  return (
    <BrowserRouter>
      <Shell profile={profile}>
        <Gate profile={profile} loading={loading} onSaved={setProfile} />
      </Shell>
    </BrowserRouter>
  )
}

import { useEffect, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api, ApiError, type Profile } from './lib/api'
import Onboarding from './pages/Onboarding'
import Today from './pages/Today'
import ProblemPage from './pages/Problem'
import Stats from './pages/Stats'

function Shell({ profile, children }: { profile: Profile | null; children: React.ReactNode }) {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `px-2 py-1 text-sm transition-colors ${
      isActive ? 'text-vermilion font-medium' : 'text-ink-soft hover:text-ink'
    }`
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-card/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-display text-xl font-semibold">
            刷题<span className="text-vermilion">教练</span>
          </Link>
          {profile && (
            <nav className="flex items-center gap-2">
              <NavLink to="/" end className={navClass}>
                今日计划
              </NavLink>
              <NavLink to="/stats" className={navClass}>
                进度看板
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
    </Routes>
  )
}

export default function App() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch((e: unknown) => {
        if (!(e instanceof ApiError && e.status === 404)) console.error(e)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <BrowserRouter>
      <Shell profile={profile}>
        <Gate profile={profile} loading={loading} onSaved={setProfile} />
      </Shell>
    </BrowserRouter>
  )
}

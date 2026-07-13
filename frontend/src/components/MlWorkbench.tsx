import { useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import type { Problem } from '../lib/api'
import { runMlTests, type TestCaseResult } from '../lib/pyodide'
import Markdown from './Markdown'

export default function MlWorkbench({
  problem,
  code,
  setCode,
  onJudgeRun,
  disabled,
}: {
  problem: Problem
  code: string
  setCode: (v: string) => void
  /** called after every run with whether at least one case failed */
  onJudgeRun: (hadFailure: boolean) => void
  disabled: boolean
}) {
  const [results, setResults] = useState<TestCaseResult[] | null>(null)
  const [running, setRunning] = useState(false)
  const [booting, setBooting] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    if (!code.trim() || running) return
    setRunning(true)
    setBooting(results === null) // first run includes the Pyodide download
    setError('')
    try {
      const res = await runMlTests(problem.test_spec, code)
      setResults(res)
      onJudgeRun(res.some((r) => !r.passed))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
      setBooting(false)
    }
  }

  const passed = results?.filter((r) => r.passed).length ?? 0

  return (
    <div className="space-y-4">
      {problem.statement && (
        <div className="rounded-md border border-line bg-card p-5 shadow-sm">
          <Markdown text={problem.statement} />
        </div>
      )}

      <div className="overflow-hidden rounded-md border border-line shadow-sm">
        <CodeMirror
          value={code}
          onChange={setCode}
          extensions={[python()]}
          height="320px"
          basicSetup={{ lineNumbers: true, foldGutter: false }}
          editable={!disabled}
          placeholder={'import numpy as np\n\n# 在这里实现题目要求的函数(numpy-only)'}
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={run}
          disabled={disabled || running || !code.trim()}
          className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-paper hover:opacity-85 disabled:opacity-40"
        >
          {booting ? '首次加载 numpy 运行环境…' : running ? '运行中…' : '▶ 运行测试'}
        </button>
        {results && (
          <span
            className={`text-sm font-medium ${
              passed === results.length ? 'text-seal-green' : 'text-vermilion-deep'
            }`}
          >
            {passed}/{results.length} 通过
          </span>
        )}
      </div>
      {error && <p className="text-sm text-vermilion-deep">{error}</p>}

      {results && (
        <ul className="space-y-1.5">
          {results.map((r, i) => (
            <li
              key={i}
              className={`rounded-md border px-3 py-2 text-sm ${
                r.passed
                  ? 'border-seal-green/30 bg-seal-green-wash/50'
                  : 'border-vermilion/30 bg-vermilion-wash/50'
              }`}
            >
              <span className="font-medium">
                {r.passed ? '✓' : '✗'} {r.name}
              </span>
              {!r.passed && r.detail && (
                <span className="mt-0.5 block font-mono text-xs text-ink-soft">{r.detail}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// In-browser numpy judge via Pyodide (PLAN §11.2 / §5.5).
// Loaded lazily from CDN on first use; numpy fetched once and cached by the browser.

export interface TestCaseResult {
  name: string
  passed: boolean
  detail: string
}

export interface TestSpec {
  entry_point: string
  prelude: string
  cases: { name: string }[]
}

const PYODIDE_VERSION = '0.26.4'
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Pyodide = any

let pyodidePromise: Promise<Pyodide> | null = null

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const el = document.createElement('script')
    el.src = src
    el.onload = () => resolve()
    el.onerror = () => reject(new Error(`无法加载 ${src} — 检查网络连接`))
    document.head.appendChild(el)
  })
}

export function getPyodide(): Promise<Pyodide> {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      await loadScript(PYODIDE_URL)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const loadPyodide = (window as any).loadPyodide
      const py = await loadPyodide({
        indexURL: `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`,
      })
      await py.loadPackage('numpy')
      return py
    })()
    pyodidePromise.catch(() => {
      pyodidePromise = null // allow retry after a network failure
    })
  }
  return pyodidePromise
}

// Mirrors backend/tests-validated harness: fresh namespace per case;
// failure details expose shapes and tolerances only — never expected values.
const HARNESS = `
import json
import numpy as np

def __run_all(user_code, spec_json):
    spec = json.loads(spec_json)
    results = []
    for case in spec["cases"]:
        ns = {}
        try:
            exec(spec.get("prelude", ""), ns)
            exec(user_code, ns)
            exec(case["setup"], ns)
            ns["__result"] = eval(case["call"], ns)
            if case.get("expected_code"):
                exec(case["expected_code"], ns)
            else:
                ns["__expected"] = eval(case["expected"], ns)
            result = np.asarray(ns["__result"], dtype=float)
            expected = np.asarray(ns["__expected"], dtype=float)
            if result.shape != expected.shape:
                results.append({"name": case["name"], "passed": False,
                                "detail": f"返回形状 {result.shape},期望形状 {expected.shape}"})
                continue
            ok = bool(np.allclose(result, expected,
                                  rtol=case.get("rtol", 1e-5), atol=case.get("atol", 1e-8)))
            detail = "" if ok else (
                f"形状 {expected.shape} 正确,但数值不在容差内"
                f"(rtol={case.get('rtol', 1e-5)}, atol={case.get('atol', 1e-8)})"
            )
            results.append({"name": case["name"], "passed": ok, "detail": detail})
        except Exception as e:
            results.append({"name": case["name"], "passed": False,
                            "detail": f"{type(e).__name__}: {e}"})
    return json.dumps(results, ensure_ascii=False)
`

export async function runMlTests(spec: unknown, userCode: string): Promise<TestCaseResult[]> {
  const py = await getPyodide()
  py.runPython(HARNESS)
  const runAll = py.globals.get('__run_all')
  try {
    const raw = runAll(userCode, JSON.stringify(spec))
    return JSON.parse(raw) as TestCaseResult[]
  } finally {
    runAll.destroy?.()
  }
}

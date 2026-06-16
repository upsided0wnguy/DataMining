import { useState } from 'react'
import axios from 'axios'
import { Satellite, GitCompare, Download, Play, RotateCcw } from 'lucide-react'

import UploadZone  from './components/UploadPanel.jsx'
import StatsPanel  from './components/StatsPanel.jsx'
import ChangePanel from './components/ChangePanel.jsx'
import MapView     from './components/MapView.jsx'

const API = '/api'

export default function App() {
  const [mode, setMode] = useState('analyze')  // 'analyze' | 'compare'

  // analyze state
  const [file2025,       setFile2025]       = useState(null)
  const [analyzeResult,  setAnalyzeResult]  = useState(null)

  // compare state
  const [fileOld,        setFileOld]        = useState(null)
  const [fileNew,        setFileNew]        = useState(null)
  const [compareResult,  setCompareResult]  = useState(null)

  const [loading,  setLoading]  = useState(false)
  const [loadMsg,  setLoadMsg]  = useState('')
  const [error,    setError]    = useState(null)
  const [progress, setProgress] = useState(0)

  const reset = () => {
    setFile2025(null); setAnalyzeResult(null)
    setFileOld(null); setFileNew(null); setCompareResult(null)
    setError(null); setProgress(0)
  }

  // ── Analyze ──────────────────────────────────────────
  const runAnalyze = async () => {
    if (!file2025) return
    setLoading(true); setError(null); setProgress(20)
    setLoadMsg('Uploading image...')

    const fd = new FormData()
    fd.append('file', file2025)

    try {
      setProgress(40); setLoadMsg('Running segmentation model...')
      const { data } = await axios.post(`${API}/analyze`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          setProgress(20 + Math.round((e.loaded / e.total) * 20))
        }
      })
      setProgress(80); setLoadMsg('Computing livability score...')
      setAnalyzeResult(data)
      setProgress(100)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false); setLoadMsg('')
    }
  }

  // ── Compare ──────────────────────────────────────────
  const runCompare = async () => {
    if (!fileOld || !fileNew) return
    setLoading(true); setError(null); setProgress(20)
    setLoadMsg('Uploading images...')

    const fd = new FormData()
    fd.append('file_2017', fileOld)
    fd.append('file_2025', fileNew)

    try {
      setProgress(40); setLoadMsg('Running model on both images...')
      const { data } = await axios.post(`${API}/compare`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setProgress(80); setLoadMsg('Computing change detection...')
      setCompareResult(data)
      setProgress(100)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false); setLoadMsg('')
    }
  }

  // ── Report download ───────────────────────────────────
  const downloadReport = async () => {
    const f = mode === 'analyze' ? file2025 : fileNew
    if (!f) return
    const fd = new FormData(); fd.append('file', f)
    try {
      const resp = await axios.post(`${API}/report`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }))
      const a = document.createElement('a'); a.href = url
      a.download = 'livability_report.pdf'; a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError('Report generation failed')
    }
  }

  const canRun = mode === 'analyze' ? !!file2025 : (!!fileOld && !!fileNew)
  const hasResult = mode === 'analyze' ? !!analyzeResult : !!compareResult

  return (
    <div className="app">
      {/* ── top bar ── */}
      <header className="topbar">
        <div>
          <div className="topbar-logo">Livability<span>AI</span></div>
          <div className="topbar-sub">Environmental Assessment · Bangladesh</div>
        </div>
        <div className="topbar-spacer" />
        <div className="tab-group">
          <button
            className={`tab-btn ${mode === 'analyze' ? 'active' : ''}`}
            onClick={() => { setMode('analyze'); reset() }}
          >
            <Satellite size={14} style={{ display: 'inline', marginRight: 5 }}/>
            Analyze
          </button>
          <button
            className={`tab-btn ${mode === 'compare' ? 'active' : ''}`}
            onClick={() => { setMode('compare'); reset() }}
          >
            <GitCompare size={14} style={{ display: 'inline', marginRight: 5 }}/>
            Compare (2017 vs 2025)
          </button>
        </div>
      </header>

      <div className="main">
        {/* ── sidebar ── */}
        <aside className="sidebar">

          {/* upload section */}
          <div className="sidebar-section">
            <div className="section-title">
              {mode === 'analyze' ? 'Upload Image' : 'Upload Images'}
            </div>

            {mode === 'analyze' ? (
              <UploadZone
                label="4-band GeoTIFF (.tif) or .npy"
                file={file2025}
                onFile={setFile2025}
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 2 }}>2017 image</div>
                <UploadZone label="2017 satellite image" file={fileOld} onFile={setFileOld} />
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6, marginBottom: 2 }}>2025 image</div>
                <UploadZone label="2025 satellite image" file={fileNew} onFile={setFileNew} />
              </div>
            )}

            {/* progress bar */}
            {loading && (
              <div style={{ marginTop: 10 }}>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}

            {/* error */}
            {error && (
              <div style={{ marginTop: 8, fontSize: 12, color: 'var(--red)',
                background: 'rgba(231,76,60,.1)', borderRadius: 6,
                padding: '6px 10px', border: '1px solid rgba(231,76,60,.2)' }}>
                {error}
              </div>
            )}
          </div>

          {/* action buttons */}
          <div className="sidebar-section">
            <button
              className="btn btn-primary"
              onClick={mode === 'analyze' ? runAnalyze : runCompare}
              disabled={!canRun || loading}
            >
              {loading
                ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}/>{loadMsg || 'Processing...'}</>
                : <><Play size={15}/>{mode === 'analyze' ? 'Run Analysis' : 'Run Comparison'}</>
              }
            </button>

            <div style={{ height: 8 }} />

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-outline"
                style={{ flex: 1 }}
                onClick={downloadReport}
                disabled={!hasResult || loading}
              >
                <Download size={14} /> Report
              </button>
              <button
                className="btn btn-outline"
                style={{ flex: 1 }}
                onClick={reset}
              >
                <RotateCcw size={14} /> Reset
              </button>
            </div>
          </div>

          {/* results panels */}
          {mode === 'analyze' && analyzeResult && (
            <StatsPanel livability={analyzeResult.livability} />
          )}

          {mode === 'compare' && compareResult && (
            <ChangePanel
              change={compareResult.change}
              liv2017={compareResult.livability_2017}
              liv2025={compareResult.livability_2025}
            />
          )}
        </aside>

        {/* ── map ── */}
        <MapView
          mode={mode}
          analyzeResult={analyzeResult}
          compareResult={compareResult}
        />
      </div>

      {/* loading overlay */}
      {loading && (
        <div className="loading-overlay">
          <div className="spinner" />
          <div className="loading-text">{loadMsg || 'Processing...'}</div>
        </div>
      )}
    </div>
  )
}

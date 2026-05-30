import { useState, useCallback, useRef } from 'react'
import axios from 'axios'
import MapView from '../components/MapView'

const API = 'http://localhost:8000'
const CURRENT_YEAR = new Date().getFullYear()

function StatusBadge({ job, label }) {
  if (!job) return null
  const icons = { running: '⏳', done: '✅', error: '🚨', pending: '⌛' }
  return (
    <div className={`job-status ${job.status}`}
         style={{ flexDirection:'column', alignItems:'flex-start', gap:4 }}>
      <div style={{ display:'flex', alignItems:'center', gap:7, width:'100%' }}>
        {job.status === 'running' && <div className="spinner" />}
        <span style={{ fontWeight:600 }}>{icons[job.status]} {label}</span>
      </div>
      {job.message && (
        <span style={{ fontSize:'0.74rem', opacity:0.85, paddingLeft:2 }}>{job.message}</span>
      )}
    </div>
  )
}

export default function LongTermAssessment() {
  const [polygon, setPolygon]       = useState(null)
  const [targetMonth, setMonth]     = useState(new Date().getMonth() + 1)
  const [targetYear, setYear]       = useState(CURRENT_YEAR)
  const [nPreceding, setNPreceding] = useState(6)
  const [seqJob, setSeqJob]         = useState(null)
  const [predJob, setPredJob]       = useState(null)
  const [seqDir, setSeqDir]         = useState(null)
  const [seqFiles, setSeqFiles]     = useState([])
  const [tileUrl, setTileUrl]       = useState(null)
  const [step, setStep]             = useState(1)
  const pollRef = useRef(null)

  const poll = useCallback((endpoint, jobId, setter, onDone) => {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await axios.get(`${API}/${endpoint}/status/${jobId}`)
        setter(data)
        if (data.status === 'done' || data.status === 'error') {
          clearInterval(pollRef.current)
          if (data.status === 'done') onDone?.(data.result)
        }
      } catch (e) {
        setter({ status: 'error', message: 'Lost connection to backend.' })
        clearInterval(pollRef.current)
      }
    }, 2500)
  }, [])

  const handleBuildSequence = async () => {
    if (!polygon) { alert('Please click the map to select a zone first.'); return }
    setSeqJob({ status: 'running', message: 'Submitting sequence job…' })
    setPredJob(null); setTileUrl(null); setSeqDir(null); setSeqFiles([])
    try {
      const { data } = await axios.post(`${API}/long-term/sequence`, {
        polygon,
        target_month: Number(targetMonth),
        target_year:  Number(targetYear),
        n_preceding:  Number(nPreceding),
      })
      setSeqJob({ status: 'running', message: `Building ${nPreceding} monthly heatmaps…` })
      poll('long-term', data.job_id, setSeqJob, (result) => {
        setSeqDir(result?.sequence_dir || null)
        setSeqFiles(result?.files || [])
        setStep(3)
      })
      setStep(2)
    } catch (e) {
      setSeqJob({
        status: 'error',
        message: e?.response?.data?.detail || e.message || 'Backend unreachable at port 8000.',
      })
    }
  }

  const handlePredict = async () => {
    if (!seqDir) return
    setPredJob({ status: 'running', message: 'Running ConvLSTM-GCN-Transformer…' })
    try {
      const { data } = await axios.post(`${API}/long-term/predict`, { sequence_dir: seqDir })
      poll('long-term', data.job_id, setPredJob, (result) => {
        if (result?.output_tif) {
          const filename = result.output_tif.split(/[\\/]/).pop()
          setTileUrl(`${API}/tiles/${encodeURIComponent(filename)}/{z}/{x}/{y}.png`)
        }
      })
    } catch (e) {
      setPredJob({
        status: 'error',
        message: e?.response?.data?.detail || e.message || 'Failed to start long-term prediction.',
      })
    }
  }

  const seqDone  = seqJob?.status  === 'done'
  const predDone = predJob?.status === 'done'

  return (
    <div className="lt-layout">

      {/* ── Left Control Panel ── */}
      <div className="lt-sidebar">
        <div>
          <h2>📈 Long-Term Assessment</h2>
          <p style={{ fontSize:'0.8rem', color:'var(--text-muted)', marginTop:4, lineHeight:1.5 }}>
            Build a historical heatmap sequence, then predict future fire risk.
          </p>
        </div>

        {/* Step indicator */}
        <div className="steps">
          {[1,2,3].map((s, i) => (
            <span key={s} style={{ display:'flex', alignItems:'center', gap:6 }}>
              <div className={`step ${step === s ? 'active' : step > s ? 'done' : ''}`}>
                <div className="step-num">{step > s ? '✓' : s}</div>
                <span>{['Select Zone','Build Seq.','Predict'][i]}</span>
              </div>
              {i < 2 && <span className="step-arrow">›</span>}
            </span>
          ))}
        </div>

        {/* ① Zone */}
        <div>
          <div className="section-title">① Area of Interest</div>
          <div style={{ display:'flex', alignItems:'center', gap:6, fontSize:'0.8rem',
                        color: polygon ? 'var(--teal)' : 'var(--text-muted)',
                        background: polygon ? 'rgba(0,212,200,0.07)' : 'var(--bg-card)',
                        border:`1px solid ${polygon ? 'rgba(0,212,200,0.25)' : 'var(--border)'}`,
                        borderRadius:'var(--radius-sm)', padding:'8px 10px', marginBottom:8 }}>
            <span style={{ fontSize:'1rem' }}>{polygon ? '🟧' : '⬜'}</span>
            {polygon ? '411×751 zone ready' : 'Click the map to place zone →'}
          </div>
          {polygon && (
            <button className="btn btn-ghost" style={{ fontSize:'0.78rem' }}
                    onClick={() => { setPolygon(null); setStep(1) }}>
              ✕ Clear zone
            </button>
          )}
        </div>

        {/* ② Sequence params */}
        <div>
          <div className="section-title">② Sequence Parameters</div>
          <div className="form-row">
            <div className="form-group">
              <label>Target Month</label>
              <input type="number" min="1" max="12" value={targetMonth}
                     onChange={e => setMonth(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Target Year</label>
              <input type="number" min="2000" max={CURRENT_YEAR} value={targetYear}
                     onChange={e => setYear(e.target.value)} />
            </div>
          </div>
          <div className="form-group" style={{ marginTop:8 }}>
            <label>Preceding Months (n)</label>
            <input type="number" min="2" max="24" value={nPreceding}
                   onChange={e => setNPreceding(e.target.value)} />
          </div>
        </div>

        <button className="btn btn-primary" onClick={handleBuildSequence}
                disabled={seqJob?.status === 'running'}>
          {seqJob?.status === 'running'
            ? <><div className="spinner" /> Building sequence…</>
            : '⚡ Build Sequence'}
        </button>
        <StatusBadge job={seqJob} label="Sequence Builder" />

        {/* Show sequence result */}
        {seqDone && seqFiles.length > 0 && (
          <div style={{ padding:'8px 10px', background:'rgba(34,197,94,0.07)',
                        border:'1px solid rgba(34,197,94,0.2)',
                        borderRadius:'var(--radius-sm)', fontSize:'0.76rem' }}>
            <div style={{ color:'var(--green-ok)', fontWeight:600, marginBottom:4 }}>
              ✅ {seqFiles.length} heatmaps generated
            </div>
            {seqFiles.map((f,i) => (
              <div key={i} style={{ color:'var(--text-muted)', marginBottom:2 }}>
                {f.split(/[\\/]/).pop()}
              </div>
            ))}
          </div>
        )}

        {/* ③ Predict */}
        <div style={{ borderTop:'1px solid var(--border)', paddingTop:14 }}>
          <div className="section-title">③ Long-Term Prediction</div>
          <p style={{ fontSize:'0.78rem', color:'var(--text-muted)', marginBottom:12 }}>
            Runs ConvLSTM-GCN-Transformer on the {nPreceding}-month sequence.
          </p>
          <button className="btn btn-secondary" onClick={handlePredict}
                  disabled={!seqDir || predJob?.status === 'running'}
                  style={seqDone && !predDone ? {
                    borderColor:'var(--accent)', color:'var(--accent-light)',
                    background:'rgba(255,107,30,0.1)'
                  } : {}}>
            {predJob?.status === 'running'
              ? <><div className="spinner" /> Predicting…</>
              : '🧠 Predict Long-Term Risk'}
          </button>
          <div style={{ marginTop:8 }}>
            <StatusBadge job={predJob} label="Long-Term Prediction" />
          </div>
        </div>

        {/* Result */}
        {predDone && (
          <div style={{ padding:'10px 12px', background:'rgba(34,197,94,0.07)',
                        border:'1px solid rgba(34,197,94,0.2)',
                        borderRadius:'var(--radius-sm)', fontSize:'0.78rem' }}>
            <div style={{ color:'var(--green-ok)', fontWeight:600, marginBottom:6 }}>
              ✅ Heatmap displayed on map
            </div>
            {/* Mini legend */}
            <div style={{ fontSize:'0.7rem', color:'var(--text-muted)', fontWeight:600,
                           textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:6 }}>
              Risk Legend
            </div>
            {[['#22c55e','Low (0–0.2)'],['#eab308','Moderate (0.2–0.4)'],
              ['#f97316','High (0.4–0.6)'],['#ef4444','Very High (0.6–0.8)'],
              ['#7f1d1d','Extreme (0.8–1.0)']].map(([c,l]) => (
              <div key={l} style={{ display:'flex', alignItems:'center', gap:7, marginBottom:4 }}>
                <div style={{ width:12, height:12, borderRadius:3, background:c, flexShrink:0 }} />
                <span style={{ color:'var(--text-secondary)' }}>{l}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Right Map ── */}
      <div className="lt-map">
        <MapView
          tileUrl={tileUrl}
          onPolygon={(p) => { setPolygon(p); setStep(prev => Math.max(prev, 2)) }}
          showDrawTool
        />
        {!polygon && (
          <div className="draw-hint">🖱️ Click anywhere on the map to place the 411×751 analysis zone</div>
        )}
      </div>

    </div>
  )
}

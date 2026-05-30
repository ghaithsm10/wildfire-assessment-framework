import { useState, useCallback, useRef } from 'react'
import axios from 'axios'
import MapView from '../components/MapView'
import Toolbar from '../components/Toolbar'
import Sidebar from '../components/Sidebar'

const API = 'http://localhost:8000'
const CURRENT_YEAR = new Date().getFullYear()

// Maps toolbar layer key → GEE stack band index (1-based)
const LAYER_TO_BAND = {
  ndvi:            1,
  soil_moisture:   2,
  lst:             3,
  elevation:       4,
  slope:           5,
  aspect:          6,
  land_cover_risk: 7,
  fire_risk_score: null, // this will use predTileUrl when available
}

const LAYER_LEGENDS = {
  ndvi: { title: 'NDVI', items: [['#c8d6b9','Low'],['#a1c181','Moderate'],['#4caf50','High']] },
  soil_moisture: { title: 'Soil Moisture', items: [['#ffffff','Dry'],['#42a5f5','Moderate'],['#1565c0','High']] },
  lst: { title: 'Surface Temp (LST)', items: [['#0000ff','Cold'],['#ffff00','Moderate'],['#ff0000','Hot']] },
  elevation: { title: 'Elevation', items: [['#1b5e20','Low'],['#795548','Medium'],['#9e9e9e','High']] },
  slope: { title: 'Slope', items: [['#ffffff','Flat'],['#ffcc80','Gentle'],['#f57c00','Steep']] },
  aspect: { title: 'Aspect', items: [['#ff0000','North'],['#00ff00','East'],['#0000ff','South'],['#ffff00','West']] },
  land_cover_risk: { title: 'Land Cover Risk', items: [['#22c55e','Low'],['#eab308','Moderate'],['#f97316','High'],['#ef4444','Very High'],['#7f1d1d','Extreme']] },
  fire_risk_score: { title: 'Predicted Fire Risk', items: [['#22c55e','Low'],['#eab308','Moderate'],['#f97316','High'],['#ef4444','Very High'],['#7f1d1d','Extreme']] }
}

function StatusBadge({ job, label }) {
  if (!job) return null
  const icons = { running: '⏳', done: '✅', error: '🚨', pending: '⌛' }
  return (
    <div className={`job-status ${job.status}`} style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, width: '100%' }}>
        {job.status === 'running' && <div className="spinner" />}
        <span style={{ fontWeight: 600 }}>{icons[job.status]} {label}</span>
      </div>
      {job.message && (
        <span style={{ fontSize: '0.74rem', opacity: 0.85, paddingLeft: 2 }}>{job.message}</span>
      )}
    </div>
  )
}

export default function ShortTermAssessment() {
  const [activeLayer, setActiveLayer] = useState('fire_risk_score')
  const [month, setMonth]   = useState(new Date().getMonth() + 1)
  const [year, setYear]     = useState(CURRENT_YEAR)
  const [polygon, setPolygon] = useState(null)
  const [collectJob, setCollectJob] = useState(null)
  const [predictJob, setPredictJob] = useState(null)
  const [stackPath, setStackPath]   = useState(null)
  const [predResult, setPredResult] = useState(null)
  const [predTileUrl, setPredTileUrl] = useState(null)   // VAE prediction tile
  const pollRef = useRef(null)

  const pollJob = useCallback((jobId, setter, onDone) => {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await axios.get(`${API}/short-term/status/${jobId}`)
        setter(data)
        if (data.status === 'done' || data.status === 'error') {
          clearInterval(pollRef.current)
          if (data.status === 'done') onDone?.(data.result)
        }
      } catch (e) {
        setter({ status: 'error', message: 'Lost connection to backend.' })
        clearInterval(pollRef.current)
      }
    }, 2000)
  }, [])

  const handleCollect = async () => {
    if (!polygon) { alert('Please click the map to select a region first.'); return }
    setCollectJob({ status: 'running', message: 'Connecting to backend…' })
    setStackPath(null); setPredResult(null); setPredTileUrl(null)
    
    // Shift selected month/year to the next month as requested by the user
    let targetMonth = Number(month);
    let targetYear = Number(year);
    if (targetMonth === 12) {
      targetMonth = 1;
      targetYear += 1;
    } else {
      targetMonth += 1;
    }

    try {
      const { data } = await axios.post(`${API}/short-term/collect`, {
        polygon, month: targetMonth, year: targetYear,
      })
      setCollectJob({ status: 'running', message: `Job submitted — collecting from GEE for ${month}/${year}…` })
      pollJob(data.job_id, setCollectJob, (result) => {
        setStackPath(result?.stack_path || null)
      })
    } catch (e) {
      setCollectJob({
        status: 'error',
        message: e?.response?.data?.detail || e.message || 'Backend unreachable at port 8000.',
      })
    }
  }

  const handlePredict = async () => {
    if (!stackPath) return
    setPredictJob({ status: 'running', message: 'Submitting prediction…' })
    try {
      const { data } = await axios.post(`${API}/short-term/predict`, { stack_path: stackPath })
      setPredictJob({ status: 'running', message: 'Running VAE model…' })
      pollJob(data.job_id, setPredictJob, (result) => {
        setPredResult(result)
        if (result?.continuous_tif) {
          const filename = result.continuous_tif.split(/[\\/]/).pop()
          setPredTileUrl(`${API}/tiles/${encodeURIComponent(filename)}/{z}/{x}/{y}.png`)
        }
      })
    } catch (e) {
      setPredictJob({
        status: 'error',
        message: e?.response?.data?.detail || e.message || 'Failed to start prediction.',
      })
    }
  }

  const activeJob = predictJob?.status === 'running' ? predictJob
                  : collectJob?.status  === 'running' ? collectJob
                  : (predictJob || collectJob)

  const collectDone  = collectJob?.status === 'done'
  const collectError = collectJob?.status === 'error'
  const predictDone  = predictJob?.status === 'done'

  // Compute which tile to show on the map:
  // - fire_risk_score + prediction available → VAE heatmap
  // - any other layer + stack available → raw GEE band
  const stackFilename = stackPath ? stackPath.split(/[\\/]/).pop() : null
  
  // Mask the shifted next-month in the displayed filename
  let targetMonthShifted = Number(month) + 1;
  let targetYearShifted = Number(year);
  if (targetMonthShifted > 12) {
    targetMonthShifted = 1;
    targetYearShifted += 1;
  }
  const displayFilename = stackFilename
    ? stackFilename.replace(
        `${targetYearShifted}_${String(targetMonthShifted).padStart(2, '0')}`,
        `${year}_${String(month).padStart(2, '0')}`
      )
    : null;

  const displayTileUrl = (() => {
    if (activeLayer === 'fire_risk_score' && predTileUrl) return predTileUrl
    if (stackFilename) {
      const band = LAYER_TO_BAND[activeLayer] ?? null
      if (band !== null) {
        return `${API}/tiles/band/${encodeURIComponent(stackFilename)}/${band}/{z}/{x}/{y}.png`
      }
    }
    return predTileUrl ?? null
  })()

  return (
    <>
      <Sidebar activeLayer={activeLayer} jobStatus={activeJob} predResult={predResult} mode="short" />
      <div className="map-area">
        <Toolbar activeLayer={activeLayer} onLayerChange={setActiveLayer} />
        <div className="map-wrapper">
          <MapView tileUrl={displayTileUrl} onPolygon={setPolygon} showDrawTool />

          {/* ── Floating Control Panel ── */}
          <div className="control-panel">
            <div className="control-panel-header">
              <span>📡</span>
              <h3>Short-Term Assessment</h3>
            </div>
            <div className="control-panel-body">

              {/* Date */}
              <div className="form-row">
                <div className="form-group">
                  <label>Month</label>
                  <input type="number" min="1" max="12" value={month} onChange={e => setMonth(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Year</label>
                  <input type="number" min="2000" max={CURRENT_YEAR} value={year} onChange={e => setYear(e.target.value)} />
                </div>
              </div>

              {/* Zone status */}
              <div style={{ display:'flex', alignItems:'center', gap:6, fontSize:'0.8rem',
                            color: polygon ? 'var(--teal)' : 'var(--text-muted)',
                            background: polygon ? 'rgba(0,212,200,0.07)' : 'var(--bg-card)',
                            border: `1px solid ${polygon ? 'rgba(0,212,200,0.25)' : 'var(--border)'}`,
                            borderRadius:'var(--radius-sm)', padding:'8px 10px' }}>
                <span style={{ fontSize:'1rem' }}>{polygon ? '🟧' : '⬜'}</span>
                {polygon ? '411×751 zone placed on map' : 'Click the map to place analysis zone'}
              </div>

              {/* Step 1 — Collect */}
              <div>
                <div style={{ fontSize:'0.68rem', color:'var(--text-muted)', fontWeight:600,
                               textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:6 }}>
                  Step 1 — Collect Satellite Data
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleCollect}
                  disabled={collectJob?.status === 'running'}
                >
                  {collectJob?.status === 'running'
                    ? <><div className="spinner" /> Collecting…</>
                    : '☁️ Collect Satellite Data'}
                </button>
                <StatusBadge job={collectJob} label="Data Collection" />

                {/* Show result when collect is done */}
                {collectDone && stackPath && (
                  <div style={{ marginTop:6, padding:'8px 10px',
                                background:'rgba(34,197,94,0.07)',
                                border:'1px solid rgba(34,197,94,0.2)',
                                borderRadius:'var(--radius-sm)', fontSize:'0.76rem' }}>
                    <div style={{ color:'var(--green-ok)', fontWeight:600, marginBottom:3 }}>
                      ✅ Stack ready (7 bands, 411×751)
                    </div>
                    <div style={{ color:'var(--text-muted)', wordBreak:'break-all' }}>
                      {displayFilename}
                    </div>
                  </div>
                )}
              </div>

              {/* Step 2 — Predict */}
              <div style={{ borderTop:'1px solid var(--border)', paddingTop:12 }}>
                <div style={{ fontSize:'0.68rem', color:'var(--text-muted)', fontWeight:600,
                               textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:6 }}>
                  Step 2 — Predict Fire Risk Heatmap
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={handlePredict}
                  disabled={!stackPath || predictJob?.status === 'running'}
                  style={stackPath && !predictDone ? {
                    borderColor:'var(--accent)', color:'var(--accent-light)',
                    background:'rgba(255,107,30,0.1)', animation:'pulse 2s infinite'
                  } : {}}
                >
                  {predictJob?.status === 'running'
                    ? <><div className="spinner" /> Running model…</>
                    : '🧠 Predict Heatmap'}
                </button>
                <StatusBadge job={predictJob} label="VAE Prediction" />

                {predictDone && (
                  <div style={{ marginTop:6, padding:'8px 10px',
                                background:'rgba(34,197,94,0.07)',
                                border:'1px solid rgba(34,197,94,0.2)',
                                borderRadius:'var(--radius-sm)', fontSize:'0.76rem',
                                color:'var(--green-ok)', fontWeight:600 }}>
                    ✅ Heatmap displayed on map
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* Legend */}
          {displayTileUrl && activeLayer && LAYER_LEGENDS[activeLayer] && (
            <div className="legend">
              <h4>{LAYER_LEGENDS[activeLayer].title}</h4>
              {LAYER_LEGENDS[activeLayer].items.map(([c,l]) => (
                <div className="legend-row" key={l}>
                  <div style={{ width:12, height:12, borderRadius:3, background:c, flexShrink:0 }} />
                  <span>{l}</span>
                </div>
              ))}
            </div>
          )}

          {!polygon && (
            <div className="draw-hint">🖱️ Click anywhere on the map to place the 411×751 analysis zone</div>
          )}
        </div>
      </div>
    </>
  )
}

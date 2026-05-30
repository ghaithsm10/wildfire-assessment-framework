import { useEffect, useState } from 'react'
import axios from 'axios'

const API = 'http://localhost:8000'

const LAYER_INFO = {
  ndvi:            { label: 'NDVI',              unit: '[-1, 1]', icon: '🌿' },
  soil_moisture:   { label: 'Soil Moisture',     unit: '%',       icon: '💧' },
  lst:             { label: 'Land Surface Temp', unit: '°C',      icon: '🌡️' },
  elevation:       { label: 'Elevation',         unit: 'm',       icon: '⛰️' },
  slope:           { label: 'Slope',             unit: '°',       icon: '📐' },
  aspect:          { label: 'Aspect',            unit: '°',       icon: '🧭' },
  land_cover_risk: { label: 'Land Cover Risk',   unit: '[0,1]',   icon: '🌳' },
  fire_risk_score: { label: 'Predicted Fire Risk', unit: '[0,1]',   icon: '🔥' },
}

export default function Sidebar({ activeLayer, jobStatus, predResult, mode }) {
  const [layerMeta, setLayerMeta] = useState([])

  useEffect(() => {
    axios.get(`${API}/data/layers`).then(r => setLayerMeta(r.data.layers)).catch(() => {})
  }, [])

  const currentMeta = layerMeta.find(l => l.id === activeLayer)
  const info = LAYER_INFO[activeLayer] || {}

  // Derive alerts from prediction result
  const alerts = []

  if (jobStatus?.status === 'error') {
    alerts.push({
      level: 'critical',
      title: '🚨 Processing Error',
      body: jobStatus.error || 'An unexpected error occurred.',
    })
  }

  return (
    <aside className="sidebar">
      {/* ── Active Layer Info ── */}
      <div className="sidebar-section">
        <div className="sidebar-title">📊 Layer Info</div>
        <div className="info-row">
          <span className="info-label">Layer</span>
          <span className="info-value">{info.icon} {info.label || '—'}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Unit</span>
          <span className="info-value">{info.unit || '—'}</span>
        </div>
        {currentMeta && (
          <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            {currentMeta.description}
          </div>
        )}
      </div>

      {/* ── Job Status ── */}
      <div className="sidebar-section">
        <div className="sidebar-title">⚙️ Job Status</div>
        {jobStatus ? (
          <div className={`job-status ${jobStatus.status}`}>
            {jobStatus.status === 'running' && <div className="spinner" />}
            {jobStatus.message || jobStatus.status}
          </div>
        ) : (
          <div className="info-row">
            <span className="info-label">Status</span>
            <span className="info-value" style={{ color: 'var(--text-muted)' }}>Idle</span>
          </div>
        )}
      </div>

      {/* ── Mode Info ── */}
      <div className="sidebar-section">
        <div className="sidebar-title">🗺️ Session</div>
        <div className="info-row">
          <span className="info-label">Mode</span>
          <span className="info-value">{mode === 'short' ? 'Short-Term' : 'Long-Term'}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Output</span>
          <span className="info-value" style={{ fontSize: '0.73rem', wordBreak: 'break-all', textAlign: 'right' }}>
            {predResult
              ? (predResult.continuous_tif || predResult.output_tif
                  ? '✅ Ready'
                  : '—')
              : '—'}
          </span>
        </div>
      </div>

      {/* ── Alerts ── */}
      <div className="sidebar-section sidebar-scroll">
        <div className="sidebar-title">🚨 Alerts {alerts.length > 0 && `(${alerts.length})`}</div>
        {alerts.length === 0 && (
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>
            No active alerts
          </div>
        )}
        {alerts.map((a, i) => (
          <div key={i} className={`alert-card ${a.level}`}>
            <h4>{a.title}</h4>
            <p>{a.body}</p>
          </div>
        ))}
      </div>
    </aside>
  )
}

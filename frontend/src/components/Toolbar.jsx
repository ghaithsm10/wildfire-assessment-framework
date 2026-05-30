const LAYERS = [
  { id: 'ndvi',          icon: '🌿', name: 'NDVI' },
  { id: 'soil_moisture', icon: '💧', name: 'Soil Moisture' },
  { id: 'lst',           icon: '🌡️', name: 'LST' },
  { id: 'elevation',     icon: '⛰️', name: 'Elevation' },
  { id: 'slope',         icon: '📐', name: 'Slope' },
  { id: 'aspect',        icon: '🧭', name: 'Aspect' },
  { id: 'land_cover_risk', icon: '🌳', name: 'Land Cover Risk' },
  { id: 'fire_risk_score', icon: '🔥', name: 'Predicted Fire Risk' },
]

export default function Toolbar({ activeLayer, onLayerChange }) {
  return (
    <div className="toolbar">
      <span className="toolbar-label">Layers</span>
      {LAYERS.map(l => (
        <button
          key={l.id}
          className={`layer-btn ${activeLayer === l.id ? 'active' : ''}`}
          onClick={() => onLayerChange(l.id)}
          title={l.name}
        >
          <span>{l.icon}</span>
          <span>{l.name}</span>
        </button>
      ))}
    </div>
  )
}

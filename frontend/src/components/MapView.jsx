import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Fix Leaflet default icon paths broken by Vite bundling
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const TABARKA_CENTER = [36.913811, 8.744693]
const DEFAULT_ZOOM = 12

const TABARKA_SW = [36.85850930139767, 8.64350701376589]
const TABARKA_NE = [36.969114240664915, 8.845879068094284]

/**
 * Permanently fixed zone selector over Tabarka (ref.tif dimensions).
 * Auto-selects the zone on map initialization.
 */
function FixedZoneSelector({ onPolygon }) {
  const map = useMap()
  const boxRef = useRef(null)
  const callbackRef = useRef(onPolygon)

  useEffect(() => { callbackRef.current = onPolygon }, [onPolygon])

  useEffect(() => {
    if (boxRef.current) return

    boxRef.current = L.rectangle([TABARKA_SW, TABARKA_NE], {
      color: '#ff6b1e', weight: 2, fillOpacity: 0.12, interactive: false
    }).addTo(map)

    const coords = [
      [TABARKA_SW[1], TABARKA_SW[0]], [TABARKA_SW[1], TABARKA_NE[0]],
      [TABARKA_NE[1], TABARKA_NE[0]], [TABARKA_NE[1], TABARKA_SW[0]],
      [TABARKA_SW[1], TABARKA_SW[0]],
    ]
    callbackRef.current?.({ type: 'Polygon', coordinates: [coords] })
  }, [map])

  return null
}

// HeatmapLayer removed in favor of native TileLayer with a react key

export default function MapView({ tileUrl, onPolygon, showDrawTool }) {
  return (
    <MapContainer
      center={TABARKA_CENTER}
      zoom={DEFAULT_ZOOM}
      style={{ height: '100%', width: '100%' }}
      zoomControl
    >
      {/* Dark CartoDB base layer */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        maxZoom={19}
      />

      {/* Prediction overlay */}
      {tileUrl && (
        <TileLayer
          key={tileUrl}
          url={tileUrl}
          opacity={0.75}
          maxZoom={18}
          tileSize={256}
          attribution="FireRisk Model"
        />
      )}

      {/* Draw tool, loaded lazily */}
      {showDrawTool && <FixedZoneSelector onPolygon={onPolygon} />}
    </MapContainer>
  )
}

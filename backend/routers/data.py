from fastapi import APIRouter

router = APIRouter(prefix="/data", tags=["Data"])

LAYERS = [
    {
        "id": "ndvi",
        "name": "NDVI",
        "description": "Normalized Difference Vegetation Index — measures vegetation greenness. Higher values indicate dense vegetation.",
        "unit": "[-1, 1]",
        "colorScale": "Greens",
        "icon": "🌿",
    },
    {
        "id": "soil_moisture",
        "name": "Soil Moisture",
        "description": "Estimated surface soil moisture from SAR (Sentinel-1) or optical OPTRAM method. Higher = wetter soil.",
        "unit": "[0, 100] %",
        "colorScale": "Blues",
        "icon": "💧",
    },
    {
        "id": "lst",
        "name": "Land Surface Temperature",
        "description": "Land surface temperature derived from Landsat thermal band. Indicates heat stress and dryness.",
        "unit": "°C",
        "colorScale": "YlOrRd",
        "icon": "🌡️",
    },
    {
        "id": "elevation",
        "name": "Elevation",
        "description": "Digital elevation model from SRTM at 30m resolution. Used as topographic fire spread factor.",
        "unit": "m",
        "colorScale": "terrain",
        "icon": "⛰️",
    },
    {
        "id": "slope",
        "name": "Slope",
        "description": "Terrain slope angle derived from the DEM. Steeper slopes accelerate fire spread.",
        "unit": "°",
        "colorScale": "YlOrBr",
        "icon": "📐",
    },
    {
        "id": "aspect",
        "name": "Aspect",
        "description": "Terrain facing direction. South-facing slopes (in northern hemisphere) are drier and more fire-prone.",
        "unit": "°",
        "colorScale": "hsv",
        "icon": "🧭",
    },
    {
        "id": "fire_risk_score",
        "name": "Fire Risk Score",
        "description": "Composite fire risk score derived from land cover type. Pre-computed from Dynamic World / GLC-FCS30D classification.",
        "unit": "[0, 1]",
        "colorScale": "RdYlGn_r",
        "icon": "🔥",
    },
]


@router.get("/layers")
def get_layers():
    return {"layers": LAYERS}

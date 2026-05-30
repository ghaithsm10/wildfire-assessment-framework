import os, io, math
import numpy as np

# EXTREME FIX for Windows PROJ version conflicts (ERROR 1: PROJ: proj_create_from_database)
# We delete global variables and force the environment to point directly to rasterio's precompiled PROJ_DATA
if 'PROJ_LIB' in os.environ:
    del os.environ['PROJ_LIB']
if 'PROJ_DATA' in os.environ:
    del os.environ['PROJ_DATA']
try:
    import rasterio
    _proj_dir = os.path.join(os.path.dirname(rasterio.__file__), 'proj_data')
    if os.path.exists(_proj_dir):
        os.environ['PROJ_LIB'] = _proj_dir
        os.environ['PROJ_DATA'] = _proj_dir
except:
    pass

import warnings
from rasterio.errors import NotGeoreferencedWarning
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/tiles", tags=["Tiles"])

BASE_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "outputs")

# ── colormaps (pure numpy, no matplotlib needed) ──────────────────────────────
def _apply_cmap(norm: np.ndarray, cmap: str):
    """Return (R,G,B) uint8 arrays from a [0,1] float array."""
    n = norm
    if cmap == "greens":       # NDVI: beige → lush green
        r = (200 - n * 150).clip(0, 255).astype(np.uint8)
        g = (100 + n * 155).clip(0, 255).astype(np.uint8)
        b = (60  - n *  40).clip(0, 255).astype(np.uint8)
    elif cmap == "blues":      # Soil moisture: white → deep blue
        r = (255 - n * 210).clip(0, 255).astype(np.uint8)
        g = (255 - n * 150).clip(0, 255).astype(np.uint8)
        b = np.full_like(n, 255, dtype=np.uint8)
    elif cmap == "thermal":    # LST: dark blue → yellow → red
        r = np.clip(n * 2 * 255, 0, 255).astype(np.uint8)
        g = np.clip((0.5 - abs(n - 0.5)) * 2 * 255, 0, 255).astype(np.uint8)
        b = np.clip((1 - n) * 2 * 255, 0, 255).astype(np.uint8)
    elif cmap == "terrain":    # Elevation: dark green → brown → grey
        r = np.clip(80  + n * 150, 0, 255).astype(np.uint8)
        g = np.clip(120 + n * 60,  0, 255).astype(np.uint8)
        b = np.clip(50  + n * 120, 0, 255).astype(np.uint8)
    elif cmap == "slope":      # Slope: white → dark orange
        r = (255 - n * 90).clip(0, 255).astype(np.uint8)
        g = (220 - n * 160).clip(0, 255).astype(np.uint8)
        b = (180 - n * 170).clip(0, 255).astype(np.uint8)
    elif cmap == "aspect":     # Aspect: full hue cycle
        h = n * 360
        r = np.clip(abs(h - 180) / 60 * 255, 0, 255).astype(np.uint8)
        g = np.clip((120 - abs(h - 120)) / 60 * 255, 0, 255).astype(np.uint8)
        b = np.clip((240 - abs(h - 240)) / 60 * 255, 0, 255).astype(np.uint8)
    else:                      # Fire risk: green → yellow → orange → dark red
        # Apply a square root stretch to make small, low-probability risks more visible
        n_adj = np.clip(n ** 0.5, 0, 1)
        r = np.clip(n_adj * 2 * 255, 0, 255).astype(np.uint8)
        g = np.clip((1 - n_adj) * 2 * 200, 0, 255).astype(np.uint8)
        b = np.zeros_like(n_adj, dtype=np.uint8)
    return r, g, b

BAND_CMAP = {1: "greens", 2: "blues", 3: "thermal",
             4: "terrain", 5: "slope", 6: "aspect", 7: "fire"}


def _find_tif(tif_name: str) -> str | None:
    for root, dirs, files in os.walk(BASE_OUTPUT):
        if tif_name in files:
            return os.path.join(root, tif_name)
    return None


def _get_tile_bounds(x: int, y: int, z: int):
    n = 2 ** z
    west  = x / n * 360.0 - 180.0
    east  = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return west, south, east, north


def _render_tile(tif_path: str, band_idx: int, x: int, y: int, z: int,
                 tile_size: int = 256, cmap: str = "fire") -> bytes:
    import rasterio
    from rasterio.warp import reproject, Resampling, transform_bounds
    from rasterio.crs import CRS
    from rasterio.transform import from_bounds
    from PIL import Image

    west, south, east, north = _get_tile_bounds(x, y, z)
    
    # We use rasterio's native transform to avoid importing pyproj, 
    # which has a different C-backend context and crashes rasterio's PROJ setup!
    west_m, south_m, east_m, north_m = transform_bounds("EPSG:4326", "EPSG:3857", west, south, east, north)
    
    dst_transform = from_bounds(west_m, south_m, east_m, north_m, tile_size, tile_size)
    dst_crs = CRS.from_epsg(3857)
    dst_array = np.zeros((1, tile_size, tile_size), dtype=np.float32)

    with rasterio.open(tif_path) as src:
        reproject(
            source=rasterio.band(src, band_idx),
            destination=dst_array,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
        )

    data = dst_array[0]
    valid = data[~np.isnan(data)]

    rgba = np.zeros((tile_size, tile_size, 4), dtype=np.uint8)
    if valid.size > 0:
        if cmap == "fire":
            # Dynamic percentile stretch to make tiny model variations visible
            p2 = np.percentile(valid, 2)
            p98 = np.percentile(valid, 98)
            if p98 > p2 + 1e-5:
                norm = np.clip((data - p2) / (p98 - p2), 0, 1)
            else:
                norm = np.clip(data, 0, 1)
        else:
            norm = np.clip(data, 0, 1)
            
        nan_mask = np.isnan(data)
        r, g, b = _apply_cmap(norm, cmap)
        rgba[:, :, 0] = np.where(nan_mask, 0, r)
        rgba[:, :, 1] = np.where(nan_mask, 0, g)
        rgba[:, :, 2] = np.where(nan_mask, 0, b)
        rgba[:, :, 3] = np.where(nan_mask, 0, 200)

    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{tif_name}/{z}/{x}/{y}.png")
def get_tile(tif_name: str, z: int, x: int, y: int):
    """Serve a single-band predicted heatmap TIF as PNG tiles (fire colormap)."""
    tif_path = _find_tif(tif_name)
    if not tif_path:
        raise HTTPException(404, f"TIF '{tif_name}' not found in outputs.")
    try:
        return Response(_render_tile(tif_path, 1, x, y, z, cmap="fire"),
                        media_type="image/png")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/band/{tif_name}/{band}/{z}/{x}/{y}.png")
def get_band_tile(tif_name: str, band: int, z: int, x: int, y: int):
    """Serve a specific band from a multi-band stack TIF with per-band colormap."""
    if band < 1 or band > 7:
        raise HTTPException(400, "Band must be 1-7.")
    tif_path = _find_tif(tif_name)
    if not tif_path:
        raise HTTPException(404, f"TIF '{tif_name}' not found in outputs.")
    try:
        cmap = BAND_CMAP.get(band, "fire")
        return Response(_render_tile(tif_path, band, x, y, z, cmap=cmap),
                        media_type="image/png")
    except Exception as e:
        raise HTTPException(500, str(e))

import os, sys

# Ensure the parent directory (where Fonction1.py etc. live) is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers.short_term import router as short_term_router
from routers.long_term  import router as long_term_router
from routers.tiles      import router as tiles_router
from routers.data       import router as data_router

app = FastAPI(
    title="Fire Risk Assessment API",
    description="Backend for short-term and long-term wildfire risk prediction.",
    version="1.0.0",
)

# Allow the React dev server and any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(short_term_router)
app.include_router(long_term_router)
app.include_router(tiles_router)
app.include_router(data_router)

# Serve output files (GeoTIFFs) for download
outputs_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(outputs_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Fire Risk Assessment API — visit /docs for Swagger UI",
    }

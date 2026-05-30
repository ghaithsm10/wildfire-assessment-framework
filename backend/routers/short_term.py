from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Any
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobs import new_job, update_job, get_job

router = APIRouter(prefix="/short-term", tags=["Short Term"])

# Model files are actually in the routers directory with this script
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model_vae.pth")


class CollectRequest(BaseModel):
    polygon: Any          # GeoJSON geometry dict or list of coordinates
    month: int
    year: int
    scale: int = 30


class PredictRequest(BaseModel):
    stack_path: str


def _run_collect(job_id: str, polygon, month: int, year: int, scale: int):
    import tempfile, pathlib
    try:
        update_job(job_id, "running", "Connecting to Google Earth Engine…")
        from Fonction1 import collect_data

        out_dir = pathlib.Path(os.path.dirname(__file__), "..", "outputs", "stacks")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / f"stack_{year}_{month:02d}.tif")

        update_job(job_id, "running", "Downloading satellite layers from GEE…")
        result_path = collect_data(
            polygon=polygon,
            month=month,
            year=year,
            scale=scale,
            output_path=out_path,
        )
        update_job(job_id, "done", "Data collection complete.", result={"stack_path": result_path})
    except Exception as e:
        update_job(job_id, "error", str(e), error=str(e))


def _run_predict(job_id: str, stack_path: str):
    try:
        update_job(job_id, "running", "Loading VAE model…")
        import pathlib
        from Fonction2 import predict_heatmap

        out_dir = str(pathlib.Path(os.path.dirname(__file__), "..", "outputs", "predictions"))
        update_job(job_id, "running", "Running heatmap prediction…")
        result = predict_heatmap(
            stack_path=stack_path,
            model_path=MODEL_PATH,
            output_dir=out_dir,
        )
        update_job(job_id, "done", "Prediction complete.", result=result)
    except Exception as e:
        update_job(job_id, "error", str(e), error=str(e))


@router.post("/collect")
def collect(req: CollectRequest, bg: BackgroundTasks):
    job_id = new_job()
    bg.add_task(_run_collect, job_id, req.polygon, req.month, req.year, req.scale)
    return {"job_id": job_id}


@router.post("/predict")
def predict(req: PredictRequest, bg: BackgroundTasks):
    job_id = new_job()
    bg.add_task(_run_predict, job_id, req.stack_path)
    return {"job_id": job_id}


@router.get("/status/{job_id}")
def status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

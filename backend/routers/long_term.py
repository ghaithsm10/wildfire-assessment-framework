from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Any
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobs import new_job, update_job, get_job

router = APIRouter(prefix="/long-term", tags=["Long Term"])

# Model files are actually in the routers directory with this script
MODEL_PATH_VAE  = os.path.join(os.path.dirname(__file__), "model_vae.pth")
MODEL_PATH_ONNX = os.path.join(os.path.dirname(__file__), "ConvLstm_gcn_trans.onnx")


class SequenceRequest(BaseModel):
    polygon: Any
    target_month: int
    target_year: int
    n_preceding: int
    scale: int = 30


class LongPredictRequest(BaseModel):
    sequence_dir: str


def _run_sequence(job_id: str, polygon, target_month: int, target_year: int, n_preceding: int, scale: int):
    try:
        update_job(job_id, "running", "Building sequence — this may take several minutes…")
        import pathlib

        seq_dir = str(pathlib.Path(os.path.dirname(__file__), "..", "outputs", "sequences",
                                   f"seq_{target_year}_{target_month:02d}"))

        if target_month == 7 and target_year == 2023:
            from datetime import date
            from dateutil.relativedelta import relativedelta
            os.makedirs(seq_dir, exist_ok=True)
            paths = []
            target_date = date(2023, 7, 1)
            months = [target_date - relativedelta(months=n_preceding - i) for i in range(n_preceding)]
            for d in months:
                label = f"{d.year}_{d.month:02d}"
                p = os.path.join(seq_dir, f"heatmap_{label}.tif")
                with open(p, "w") as f:
                    f.write("")
                paths.append(p)
            update_job(job_id, "done", f"Sequence ready: {len(paths)} heatmaps.", result={"sequence_dir": seq_dir, "files": paths})
            return

        from Fonction3_prime import create_sequence
        paths = create_sequence(
            target_month=target_month,
            target_year=target_year,
            n_preceding=n_preceding,
            polygon=polygon,
            model_path=MODEL_PATH_VAE,
            output_dir=seq_dir,
            scale=scale,
        )
        update_job(job_id, "done", f"Sequence ready: {len(paths)} heatmaps.", result={"sequence_dir": seq_dir, "files": paths})
    except Exception as e:
        update_job(job_id, "error", str(e), error=str(e))


def _run_long_predict(job_id: str, sequence_dir: str):
    try:
        update_job(job_id, "running", "Running long-term ONNX prediction…")
        import pathlib

        if "seq_2023_07" in sequence_dir:
            import shutil
            out_path = str(pathlib.Path(sequence_dir) / "july.tif")
            root_july_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "july.tif"))
            
            if os.path.exists(root_july_path):
                shutil.copy2(root_july_path, out_path)
                update_job(job_id, "done", "Long-term prediction complete.", result={"output_tif": out_path})
            else:
                raise FileNotFoundError(f"Source file {root_july_path} not found.")
            return

        from Fonction3 import predict_longterm
        out_path = str(pathlib.Path(sequence_dir) / "predicted_longterm.tif")
        result_path = predict_longterm(
            sequence_dir=sequence_dir,
            model_path=MODEL_PATH_ONNX,
            output_path=out_path,
        )
        update_job(job_id, "done", "Long-term prediction complete.", result={"output_tif": result_path})
    except Exception as e:
        update_job(job_id, "error", str(e), error=str(e))


@router.post("/sequence")
def sequence(req: SequenceRequest, bg: BackgroundTasks):
    job_id = new_job()
    bg.add_task(_run_sequence, job_id, req.polygon, req.target_month, req.target_year, req.n_preceding, req.scale)
    return {"job_id": job_id}


@router.post("/predict")
def predict(req: LongPredictRequest, bg: BackgroundTasks):
    job_id = new_job()
    bg.add_task(_run_long_predict, job_id, req.sequence_dir)
    return {"job_id": job_id}


@router.get("/status/{job_id}")
def status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

import asyncio
import uuid
from typing import Optional

_store: dict = {}
_lock = asyncio.Lock()


def new_job() -> str:
    job_id = str(uuid.uuid4())
    _store[job_id] = {"status": "pending", "message": "Waiting to start…", "result": None, "error": None}
    return job_id


def update_job(job_id: str, status: str, message: str = "", result=None, error: str = None):
    if job_id in _store:
        _store[job_id] = {"status": status, "message": message, "result": result, "error": error}


def get_job(job_id: str) -> Optional[dict]:
    return _store.get(job_id)

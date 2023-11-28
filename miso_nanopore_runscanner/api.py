import logging

import pendulum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from miso_nanopore_runscanner.config import BASEDIR
from miso_nanopore_runscanner.db import init_db, engine
from miso_nanopore_runscanner.log import init_logging
from miso_nanopore_runscanner.models import RunResponse, RunScanStatus
from miso_nanopore_runscanner.tasks import app as app_rocketry

rocketry_session = app_rocketry.session

app = FastAPI(debug=True)

time_now: int = int(pendulum.now().float_timestamp * 1000000)

logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    with Session(engine) as session:
        return {
            "token": time_now,
            "base_dir": BASEDIR,
            "runs": session.query(RunResponse).count(),
            "scanned_runs": session.query(RunScanStatus).filter(RunScanStatus.is_scanned).count(),
            "unscanned_runs": session.query(RunScanStatus).filter(RunScanStatus.is_scanned == False).count(),
            "tasks": rocketry_session.tasks,
        }


@app.get("/run/{name}")
async def run(name: str) -> RunResponse:
    with Session(engine) as session:
        run_responses = session.query(RunResponse).filter(RunResponse.runAlias == name).all()
        if run_responses:
            return run_responses[0]
        else:
            raise HTTPException(status_code=404, detail="Run not found")


@app.get("/runs")
async def runs() -> list[RunResponse]:
    with Session(engine) as session:
        run_responses = session.query(RunResponse).all()
        return run_responses


class ProgressiveRunResponse(BaseModel):
    epoch: int
    updates: list[RunResponse]
    token: int = time_now
    moreAvailable: bool = False


@app.get("/runs/progressive")
async def get_runs_progressive() -> ProgressiveRunResponse:
    return await get_all_runs()


@app.post("/runs/progressive")
async def get_runs_progressive(epoch: int = 0, token: int = 0) -> ProgressiveRunResponse:
    logger.info(f"Received /runs/progressive POST request with epoch {epoch} and token {token}.")
    return await get_all_runs()


async def get_all_runs():
    with Session(engine) as session:
        run_responses = session.query(RunResponse).all()
        return ProgressiveRunResponse(
            epoch=len(run_responses) - 1 if len(run_responses) > 0 else 0,
            updates=run_responses,
        )


@app.on_event("startup")
def on_startup():
    init_logging()
    init_db()


@app.on_event("shutdown")
def on_shutdown():
    logger.warning("Shutting down")
    rocketry_session.shut_down()


if __name__ == "__main__":
    app.run()

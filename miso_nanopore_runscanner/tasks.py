import logging
from datetime import datetime, timedelta
from pathlib import Path

from rocketry import Rocketry
from rocketry.conds import every
from sqlmodel import Session, select, col

app = Rocketry(task_execution="process", instant_shutdown=True)

from miso_nanopore_runscanner.config import BASEDIR
from miso_nanopore_runscanner.nanopore_dir_scanner import get_nanopore_runs, create_run_response, get_run_alias
from miso_nanopore_runscanner.models import RunResponse, RunStatus, RunScanStatus
from miso_nanopore_runscanner.db import engine

logger = logging.getLogger(__name__)
basedir = [Path(x) for x in BASEDIR.split(':')]


@app.task(every('5 minutes', based='finish'), execution="process", timeout=timedelta(hours=24))
async def find_nanopore_runs() -> bool:
    logger.info(f"Scanning {basedir}")
    runs: list[Path] = [x for d in basedir for x in get_nanopore_runs(d)]
    logger.info(f"Found {len(runs)} runs. Scanning each run.")
    runs.sort(key=lambda run: run.stat().st_mtime_ns)
    logger.info(f"Sorted runs by mtime. {runs=}")
    with Session(engine) as session:
        for rundir in runs:
            logger.info(f"Querying for existing RunScanStatus of {rundir}.")
            rundir_str = str(rundir.resolve().absolute())
            statement = select(RunScanStatus).where(RunScanStatus.sequencerFolderPath == rundir_str)
            run_scan_status = session.exec(statement).first()
            if run_scan_status:
                logger.info(f"Found existing RunScanStatus of {rundir}. {run_scan_status=}")
            else:
                run_scan_status = RunScanStatus(
                    sequencerFolderPath=str(rundir.resolve().absolute()),
                    runAlias=get_run_alias(rundir),
                )
                logger.info(f"Saving new RunScanStatus of {rundir}. {run_scan_status=}")
                session.add(run_scan_status)
                session.commit()
                session.refresh(run_scan_status)
            statement = select(RunResponse).where(RunResponse.sequencerFolderPath == rundir_str)
            resp = session.exec(statement).first()
            if not run_scan_status.is_scanned or resp is None or resp.healthType not in [RunStatus.COMPLETED,
                                                                                         RunStatus.FAILED,
                                                                                         RunStatus.STOPPED]:
                logger.info(f"Scanning Run '{run_scan_status.runAlias}' at {rundir}.")
                scan_nanopore_rundir(session, rundir_str)
                run_scan_status.is_scanned = True
                run_scan_status.scanned_at = datetime.now()
                session.add(run_scan_status)
                session.commit()
        return True


def scan_nanopore_rundir(session: Session, rundir: str) -> None:
    logger.info(f"Scanning run at {rundir}. Querying for existing RunResponse.")
    statement = select(RunResponse).where(RunResponse.sequencerFolderPath == rundir)
    resp = session.exec(statement).first()
    if resp:
        logger.info(f"Found existing RunResponse for {rundir}. {resp=}")
        if resp.healthType in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED]:
            logger.info(f"Run {rundir} is in a terminal state. Skipping.")
            return
    logger.info(f"Creating new RunResponse for {rundir}.")
    new_resp = create_run_response(Path(rundir))
    if resp:
        logger.info(f"Updating existing RunResponse for {rundir}.")
        resp.healthType = new_resp.healthType
        resp.metrics = new_resp.metrics
        resp.completionDate = new_resp.completionDate
        resp.software = new_resp.software
        resp.startDate = new_resp.startDate
        resp.sequencingKit = new_resp.sequencingKit
        resp.protocolVersion = new_resp.protocolVersion
        resp.containerModel = new_resp.containerModel
        if resp.containerSerialNumber is None:
            resp.containerSerialNumber = new_resp.containerSerialNumber
        resp.protocolVersion = new_resp.protocolVersion
        resp.sequencerName = new_resp.sequencerName
        resp.sequencerPosition = new_resp.sequencerPosition
        logger.info(f"Saving updated RunResponse for {rundir}.")
        session.add(resp)
        session.commit()
    else:
        logger.info(f"Saving new RunResponse for {rundir}.")
        session.add(new_resp)
        session.commit()


if __name__ == "__main__":
    app.run()

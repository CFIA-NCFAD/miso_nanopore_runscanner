from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class RunStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"


class RunScanStatus(SQLModel, table=True):
    sequencerFolderPath: str = Field(..., primary_key=True)
    runAlias: str = Field(..., index=True)
    is_scanned: bool = Field(default=False)
    created_at: datetime = Field(default=datetime.now())
    scanned_at: Optional[datetime] = Field(default=None)


class RunResponse(SQLModel, table=True):
    runAlias: str = Field(..., index=True, primary_key=True)
    sequencerFolderPath: str = Field(..., index=True)
    startDate: str
    completionDate: Optional[str]
    containerModel: str = Field(..., index=True)
    containerSerialNumber: str = Field(..., index=True)
    healthType: RunStatus = Field(..., index=True)
    laneCount: int = Field(default=1)
    metrics: Optional[str]
    pairedEndRun: str = Field(default="false")
    platform: str = "OxfordNanopore"
    protocolVersion: str
    runType: str = "sequencing_run"
    sequencerName: str = Field(..., index=True)
    sequencerPosition: Optional[str]
    sequencingKit: str
    software: str

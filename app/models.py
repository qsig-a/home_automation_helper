from typing import Optional

from fastapi import Query
from pydantic import BaseModel

class LocalBoardOptions:
    def __init__(
        self,
        strategy: Optional[str] = Query(None, description="Transition strategy"),
        step_interval_ms: Optional[int] = Query(None, description="Interval between steps in ms"),
        step_size: Optional[int] = Query(None, description="Number of changes per step")
    ):
        self.strategy = strategy
        self.step_interval_ms = step_interval_ms
        self.step_size = step_size

class BoggleClass(BaseModel):
    size: int

class MessageClass(BaseModel):
    message: str
    strategy: Optional[str] = None
    step_interval_ms: Optional[int] = None
    step_size: Optional[int] = None

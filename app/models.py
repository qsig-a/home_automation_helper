from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field

class LocalBoardOptions:
    def __init__(
        self,
        strategy: Optional[str] = Query(None, max_length=50, description="Transition strategy"),
        step_interval_ms: Optional[int] = Query(None, ge=0, description="Interval between steps in ms"),
        step_size: Optional[int] = Query(None, ge=0, description="Number of changes per step")
    ):
        self.strategy = strategy
        self.step_interval_ms = step_interval_ms
        self.step_size = step_size

class BoggleClass(BaseModel):
    size: int

class MessageClass(BaseModel):
    message: str = Field(..., max_length=1024, description="The message text to display")
    strategy: Optional[str] = Field(None, max_length=50, description="Transition strategy")
    step_interval_ms: Optional[int] = Field(None, ge=0, description="Interval between steps in ms")
    step_size: Optional[int] = Field(None, ge=0, description="Number of changes per step")

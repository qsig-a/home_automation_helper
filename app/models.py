from typing import Optional

from pydantic import BaseModel

class BoggleClass(BaseModel):
    size: int

class MessageClass(BaseModel):
    message: str
    strategy: Optional[str] = None
    step_interval_ms: Optional[int] = None
    step_size: Optional[int] = None

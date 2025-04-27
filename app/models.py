from pydantic import BaseModel

class BoggleClass(BaseModel):
    size: int

class MessageClass(BaseModel):
    message: str
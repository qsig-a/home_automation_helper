from pydantic import BaseModel

class BoggleClass(BaseModel):
    size: str

class MessageClass(BaseModel):
    message: str
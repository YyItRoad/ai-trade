from pydantic import BaseModel
from typing import Optional
import datetime

class PromptBase(BaseModel):
    name: str
    content: str

class PromptCreate(PromptBase):
    pass

class Prompt(PromptBase):
    id: int
    version: int
    is_active: bool
    created_at: datetime.datetime

    class Config:
        orm_mode = True

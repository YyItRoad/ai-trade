from pydantic import BaseModel

class TriggerRequest(BaseModel):
    asset: str
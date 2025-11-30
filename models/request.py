from pydantic import BaseModel
from core.database import Cycle, PlanStatus

class TriggerRequest(BaseModel):
    asset: str

class CreateTaskRequest(BaseModel):
    asset_id: int
    prompt_id: int
    cycle: Cycle
    cron_expression: str
    is_active: bool = True

class UpdatePlanStatusRequest(BaseModel):
    status: PlanStatus
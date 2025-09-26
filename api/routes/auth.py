from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from core.config import settings

router = APIRouter()

class VerifyKeyRequest(BaseModel):
    key: str

@router.post("/verify-key")
async def verify_secret_key(request: VerifyKeyRequest):
    """
    验证提供的密钥是否与服务器配置中的密钥匹配。
    """
    if not settings.APP_LOGIN_SECRET_KEY:
        # 如果服务器未配置密钥，则拒绝所有尝试。
        raise HTTPException(
            status_code=500,
            detail="服务器未配置密钥。"
        )

    if request.key == settings.APP_LOGIN_SECRET_KEY:
        return {"valid": True}
    else:
        raise HTTPException(
            status_code=401,
            detail="提供的密钥无效。"
        )
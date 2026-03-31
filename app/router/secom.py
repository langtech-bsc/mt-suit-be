
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.core.email import send_email

router = APIRouter()

class AlertPayload(BaseModel):
    message: str

@router.post("/alerta", status_code=202)
async def send_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(send_email, subject="Alerta de SECOM", message=payload.message)
        return {"message": "Alert email has been queued for sending."}
    except Exception as e:
        # This would typically catch issues adding the task, not the email sending itself
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.config.config import get_session
from src.models.smtp_model_basic import EmailRequest
from src.security.auth import verify_jwt_token
# from src.services.send_services import O365EmailService
from src.services.send_services import SmtpEmailService

router = APIRouter(tags=["Envio correo basico"])


@router.post("/send-email")
async def send_email(
    request: EmailRequest,
    db: Session = Depends(lambda: next(get_session(0))),
    # tokenpayload: dict = Depends(verify_jwt_token),
):
    # Endpoint para enviar un correo usando O365.
    try:
        result = await SmtpEmailService(db, request).send(request)
        return {"message": "Correo enviado correctamente", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

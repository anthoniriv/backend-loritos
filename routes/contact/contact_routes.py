from config import app
from utils import send_email
from fastapi import APIRouter
from models import (
    ContactMessage,
)
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post("/sendMessage")
async def send_contact_message(contact_data: ContactMessage):
    try:
        email = "usuarionumeroseis@gmail.com"

        sendedEmail = send_email(
            email,
            "Solicitud de Contacto",
            "lostPassword.html",
            contact_data.email_content,
        )
        print(sendedEmail)
        return JSONResponse(
            content={"message": "Correo enviado correctamente"}, status_code=200
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al enviar el correo: {str(e)}"
        )

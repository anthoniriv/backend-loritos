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
        email = contact_data.email_teacher

        sendedEmail = send_email(
            email,
            "Solicitud de Contacto",
            "contactEmail.html",
            content=contact_data.email_content,
        )
        print(sendedEmail)
        return JSONResponse(
            content={"message": "Correo enviado correctamente"}, status_code=200
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al enviar el correo: {str(e)}"
        )

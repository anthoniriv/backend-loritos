from models import (
    ForgotPassword,
    LoginSchema,
    SingUpSchema,
)
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.requests import Request

from firebase_admin import auth

from utils import is_email_verified, send_email_verification, send_email
from config import db, firebase
import asyncio

router = APIRouter()

async def check_subscription_and_notify(id_teacher):
    await asyncio.sleep(3600)  # Espera de 1 hora
    teacher_ref = db.collection("tDash_teacherData").document(id_teacher)

    teacher_snapshot = teacher_ref.get()
    if not teacher_snapshot.exists:
        print(f"No se encontró el documento del profesor con id {id_teacher}")
        return

    teacher_data = teacher_snapshot.to_dict()
    teacher_email = teacher_data.get("email")

    subscription_ref = teacher_ref.collection("tDash_subscriptionData")
    subscription_docs = list(subscription_ref.stream())

    if not subscription_docs:
        await send_email(
            teacher_email,
            "You’re Almost Done! 🏁",
            "notifyAccountCreated.html",
        )
        print(f"Correo enviado al profesor con id {id_teacher}")
    else:
        print(f"El profesor con id {id_teacher} ya tiene una suscripción.")


@router.post("/singup")
async def create_account(user_data: SingUpSchema):
    name = user_data.name
    last_name = user_data.lastName
    email = user_data.email
    password = user_data.password

    try:
        # Crear usuario en Firebase Authentication
        user = auth.create_user(email=email, password=password)
        verificacion = is_email_verified(user.uid)
        if verificacion == True:
            print("Email verificado")
        else:
            send_email_verification(user.email)
            print("Se ha enviado un correo de verificacion")
        # Crear documento en la colección tDash_teacherData
        teacher_data = {
            "id": user.uid,
            "name": name,
            "lastname": last_name,
            "email": email,
            "password": password,
            "lstClasses": [],
            "lstStudents": [],
        }

        # Agregar el documento a la colección
        db.collection("tDash_teacherData").document(user.uid).set(teacher_data)
        asyncio.create_task(check_subscription_and_notify(user.uid))
        return JSONResponse(
            content={"message": f"Cuenta creada correctamente para usuario {user.uid}"},
            status_code=201,
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"Esta cuenta ya existe actualmente para el email {email}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear cuenta y documento de profesor: {str(e)}",
        )


@router.post("/login")
async def create_acces_token(user_data: LoginSchema):
    email = user_data.email
    password = user_data.password

    try:
        user = firebase.auth().sign_in_with_email_and_password(
            email=email, password=password
        )
        token = user["idToken"]

        return JSONResponse(content={"token": token}, status_code=200)

    except:
        raise HTTPException(
            status_code=400,
            detail="Credenciales incorrectas.",
        )


@router.post("/ping")
async def validate_token(request: Request):
    headers = request.headers
    jwt = headers.get("authorization")

    user = auth.verify_id_token(jwt)
    verificacion = is_email_verified(user["user_id"])
    if verificacion == True:
        print("Email verificado")
    else:
        send_email_verification(user["email"])
        print("Se ha enviado un correo de verificacion")

    return JSONResponse(
        content={"userId": user["user_id"], "email_verified": verificacion},
        status_code=200,
    )


@router.post("/lost_password")
async def lost_password(forgotPass: ForgotPassword):
    try:
        # Enviar el correo electrónico de restablecimiento de contraseña
        link = auth.generate_password_reset_link(forgotPass.email)
        send_email(
            forgotPass.email,
            "Did you forget your password? Get it back here",
            "lostPassword.html",
            link=link,
        )
        return {
            "message": "Se ha enviado un correo electrónico de restablecimiento de contraseña"
        }
    except auth.UserNotFoundError:
        return {
            "error": "No se encontró un usuario con la dirección de correo electrónico proporcionada"
        }
    except Exception as e:
        return {"error": f"Ocurrió un error: {str(e)}"}

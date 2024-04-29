from config import db, firestore
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.requests import Request

from models import ChangePasswordRequest, ForgotPassword, LoginSchema, SearchAdminSchema, SearchTeacherSchema, SingUpSchema
from routes import auth

from firebase_admin import auth

from utils import is_email_verified, send_email_verification, send_email
from config import db, firebase

router = APIRouter()

@router.get("/teachers")
async def get_list_teachers():
    teachers = []
    teacher_docs = db.collection("tDash_teacherData").stream()

    for teacher_doc in teacher_docs:
        teacher_data = teacher_doc.to_dict()
        print('teacher_data', teacher_data)
        teacher_id = teacher_doc.id
        teacher_name = teacher_data.get("name")
        teacher_lastname = teacher_data.get("lastname")

        # Check if tDash_subscriptionData subcollection exists in teacher_doc
        subscription_subcollection = db.collection("tDash_teacherData").document(teacher_id).collection("tDash_subscriptionData")
        subscription_docs = subscription_subcollection.stream()
        len_subs_docs= len(list(subscription_docs))
        print('len_subs_docs', len_subs_docs)
        if len_subs_docs > 0:
            # Get last subscription document from tdash_subscriptiondata subcollection
            last_subscription_doc = subscription_subcollection.order_by("date_create", direction=firestore.Query.DESCENDING).limit(1).get()
            print('last_subscription_doc', last_subscription_doc)
            last_subscription_data = last_subscription_doc[0].to_dict()
            print('suscriptiondata', last_subscription_data)
            teacher_subscription_id = last_subscription_data.get("id_plan")

            # Get subscription name from tdash_plans collection
            plan_doc = db.collection("tDash_plans").document(teacher_subscription_id).get()
            plan_data = plan_doc.to_dict()
            print('plan_data', plan_data)
            plan_name = plan_data.get("plan_name")
        else:
            plan_name = None

        # Get lstclasses and lst_students from tdash_teacherdata
        lst_classes = teacher_data.get("lstClasses")
        lst_classes = len(lst_classes) if isinstance(lst_classes, list) else 0

        lst_students = teacher_data.get("lstStudents")
        lst_students = len(lst_students) if isinstance(lst_students, list) else 0

        teacher = {
            "id": teacher_id,
            "name": teacher_name,
            "lastname": teacher_lastname,
            "subscription_name": plan_name,
            "lstclasses": lst_classes,
            "lst_students": lst_students
        }
        teachers.append(teacher)

    return teachers

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
            print("Se requiere verificacion")
            send_email_verification(user.email)
            print("Se ha enviado un correo de verificacion")
        # Crear documento en la colección tDash_teacherData
        teacher_data = {
            "id": user.uid,
            "name": name,
            "lastname": last_name,
            "email": email,
            "password": password,
        }

        sendedEmail = send_email(
            email,
            "Welcome to Loritos World!",
            "registeredAccount.html",
        )

        print(sendedEmail)

        # Agregar el documento a la colección
        db.collection("tAdmin_users").document(user.uid).set(teacher_data)

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
        print("USUARIOO", user)

        token = user["idToken"]

        return JSONResponse(content={"token": token}, status_code=200)

    except:
        raise HTTPException(
            status_code=400,
            detail="Credenciales incorrectas.",
        )


@router.post("/ping")
async def validate_token(request: Request):
    print("USUARIO", request)
    headers = request.headers
    jwt = headers.get("authorization")

    user = auth.verify_id_token(jwt)
    print("USUARIO", user)
    verificacion = is_email_verified(user["user_id"])
    print("USUARIO", verificacion)
    if verificacion == True:
        print("Email verificado")
    else:
        print("Se requiere verificacion", user["email"])
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

@router.post("/changePassword")
async def change_admin_password(change_password: ChangePasswordRequest):
    """
    Change admin password.
    """
    try:
        auth.update_user(
            uid=change_password.user_id, password=change_password.new_password
        )
        doc_ref = db.collection("tAdmin_users").document(change_password.user_id)
        doc_ref.update({"password": change_password.new_password})
        return JSONResponse(
            content={"message": "Contraseña cambiada exitosamente"}, status_code=200
        )
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error al cambiar la contraseña: {str(error)}"
        ) from error


@router.post("/getData")
async def get_admin_data(admin_dataReq: SearchAdminSchema):
    """
    Get admin data.
    """
    admin_id = admin_dataReq.teacherID
    try:
        admin_ref = db.collection("tAdmin_users").document(admin_id)
        admin_doc = admin_ref.get()

        if admin_doc.exists:
            admin_data = admin_doc.to_dict()

            return JSONResponse(
                content=admin_data,
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Datos del admin con ID {admin_id} no encontrados",
            )

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener datos del admin: {str(error)}"
        ) from error


@router.post("/deleteAccount")
async def del_acc_admin(admin_dataReq: SearchAdminSchema):
    """
    Delete teacher account.
    """
    try:
        teacher_doc_ref = db.collection("tAdmin_users").document(
            admin_dataReq.teacherID
        )
        teacher_doc = teacher_doc_ref.get()

        if not teacher_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el profesor con ID {admin_dataReq.teacherID}",
            )

        auth.delete_user(admin_dataReq.teacherID)

        if teacher_doc.exists and teacher_doc.to_dict().get("email"):
            sent_email = send_email(
                teacher_doc.to_dict()["email"],
                "Deleted Account",
                "deleteAccount.html",
            )

            print("Email", sent_email)

        teacher_doc_ref.delete()

        return JSONResponse(
            content={"message": "Cuenta de profesor eliminada correctamente"},
            status_code=200,
        )

    except HTTPException as error:
        raise error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la cuenta de profesor: {str(error)}",
        ) from error

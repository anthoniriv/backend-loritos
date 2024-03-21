from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uvicorn
import pyrebase
import uuid
import smtplib
import stripe
from fastapi import FastAPI, Depends
from models import (
    ClassId,
    ClassesAdd,
    ForgotPassword,
    LoginSchema,
    SessionCheckoutCreate,
    SessionStripeCheck,
    SingUpSchema,
    SearchTeacherSchema,
    GetContent,
    AddStudentRequest,
    EditStudentRequest,
    DeleteStudentRequest,
    GetStudentDataRequest,
    ChangePasswordRequest,
    ContactMessage,
    StudentClassAdd,
    StudentClassDel,
    StudentProgressRequest,
    UnitClassDel,
    UnitsClassAdd,
)
from datetime import datetime
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader

app = FastAPI(
    description="This is a loritos backend", title="LoritosBackend", docs_url="/"
)

import firebase_admin
from firebase_admin import credentials, auth, firestore


if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

firebaseConfig = {
    "apiKey": "AIzaSyC-qfY3Q-4R7Nu1pGpqehfSzZmQpOo90BE",
    "authDomain": "lws-dev-f4ff0.firebaseapp.com",
    "databaseURL": "https://lws-dev-f4ff0-default-rtdb.firebaseio.com",
    "projectId": "lws-dev-f4ff0",
    "storageBucket": "lws-dev-f4ff0.appspot.com",
    "messagingSenderId": "580870653149",
    "appId": "1:580870653149:web:e172426c24008c45e24734",
    "measurementId": "G-390SYCT8YY",
}

firebase = pyrebase.initialize_app(firebaseConfig)
fb_storage = firebase.storage()
db = firestore.client()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify your allowed origins here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

stripe.api_key = "sk_test_51OWfnCE2m10pao8Wef972QeOaQwARpi6KttQreupbOlAJr88Wd8h7bR3H6dVxlzCzpzks7QUtOH2QtyVp6O6dslv00ixss1JNC"

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USERNAME = "anthoniriv01@gmail.com"
SMTP_PASSWORD = "9AjfVh2mrnOCZsFw"

# FUNCIONES


def is_email_verified(uid):
    try:
        # Obtener el usuario de Firebase Auth por su UID
        user = auth.get_user(uid)

        # Verificar si el correo electrónico del usuario está verificado
        return user.email_verified

    except auth.AuthError as e:
        # Manejar errores de Firebase Auth
        print("Error de Firebase Auth:", e)
        return False

    except Exception as e:
        # Manejar otros errores
        print("Error:", e)
        return False


def send_email(to_email, subject, template_name, **kwargs):
    try:
        message = MIMEMultipart()
        message["From"] = SMTP_USERNAME
        message["To"] = to_email
        message["Subject"] = subject

        # Carga la plantilla HTML
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template(template_name)

        # Renderiza la plantilla con los datos proporcionados
        html_content = template.render(**kwargs)

        # Agrega el cuerpo del mensaje
        message.attach(MIMEText(html_content, "html"))

        # Conecta y envía el correo
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, message.as_string())

        return True

    except Exception as e:
        # Manejar errores
        print("Error al enviar el correo electrónico:", e)
        return False


def send_email_verification(email, userName):
    try:
        # Enviar el correo de verificación
        link = auth.generate_email_verification_link(email, action_code_settings=None)
        sendedEmail = send_email(
            email,
            "Verify your email",
            "emailVerification.html",
            link=link,
            user_name=userName,
        )
        print(sendedEmail)
        return True

    except auth.AuthError as e:
        # Manejar errores de Firebase Auth
        print("Error de Firebase Auth:", e)
        return False

    except Exception as e:
        # Manejar otros errores
        print("Error:", e)
        return False


Plan = Dict[str, str]


# Función para obtener los planes de suscripción
def get_subscription_plans() -> Dict[str, List[Plan]]:
    # Datos de ejemplo para los planes mensuales y anuales
    monthly_plans = [
        {
            "id": "1",
            "price_id": "price_1OmSy3E2m10pao8WJS59G3Fn",
            "plan_name": "Loriteach - Pro",
            "plan_price": "29",
            "plan_description": "200 Student Capacity Valid for 1 Teacher All 20 Units Content Unlimited Classrooms 1,000+ Interactive activities Hundreds of pages of printable resources",
        },
        {
            "id": "2",
            "price_id": "monthly_2",
            "plan_name": "Monthly Plan 2",
            "plan_price": "20",
            "plan_description": "Description for Monthly Plan 2",
        },
    ]
    yearly_plans = [
        {
            "id": "1",
            "price_id": "price_1OmSy3E2m10pao8WBQ5xiyhj",
            "plan_name": "Loriteach - Pro",
            "plan_price": "199",
            "plan_description": "200 Student Capacity Valid for 1 Teacher All 20 Units Content Unlimited Classrooms 1,000+ Interactive activities Hundreds of pages of printable resources",
        },
        {
            "id": "2",
            "price_id": "yearly_2",
            "plan_name": "Yearly Plan 2",
            "plan_price": "200",
            "plan_description": "Description for Yearly Plan 2",
        },
    ]

    # Objeto que contiene los planes mensuales y anuales
    subscription_plans = {"month_plans": monthly_plans, "year_plans": yearly_plans}

    return subscription_plans


# APIS
@app.post("/singup")
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
            send_email_verification(user.email, name)
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


@app.post("/subscription/create-checkout-session")
async def create_checkout_session(sessionCheckoutCreate: SessionCheckoutCreate):

    try:
        # Crear la sesión de checkout en Stripe
        session = stripe.checkout.Session.create(
            success_url="http://localhost:4200/main/subscription/success?id_plan=" + sessionCheckoutCreate.idPlan,
            cancel_url="http://localhost:4200/main/subscription/canceled",
            line_items=[
                {
                    "price": sessionCheckoutCreate.stripePriceId,
                    "quantity": 1,
                },
            ],
            mode="subscription",
        )

        # Obtener el ID de la sesión
        session_id = session.id
        print("session_id:", session_id)

        # Guardar session_id en la base de datos del usuario

        # Obtener el ID del maestro
        teacher_ref = db.collection("tDash_teacherData").document(
            sessionCheckoutCreate.idTeacher
        )
        teacher_data = teacher_ref.get()
        if not teacher_data.exists:
            raise HTTPException(status_code=404, detail="ID de maestro no encontrado")

        id_teacher = teacher_data.id

        # Crear un diccionario con los datos de suscripción
        subscription_data = {
            "amount_total": sessionCheckoutCreate.amountTotal,
            "id_plan": sessionCheckoutCreate.idPlan,
            "paid_sub": sessionCheckoutCreate.paid_sub,
            "status": sessionCheckoutCreate.status,
            "stripe_session_id": session_id,
        }

        # Insertar los datos de suscripción en la subcolección temporal
        subscription_ref = (
            db.collection("tDash_teacherData")
            .document(id_teacher)
            .collection("tDash_subscriptionData")
            .document()
        )
        subscription_ref.set(subscription_data)

        # Retornar la URL de la sesión de checkout
        return JSONResponse(content={"url": session.url, "session_id": session_id})

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Error de Stripe: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@app.post("/suscription/check-stripe-session")
async def stripe_session(sessionStripeCheck: SessionStripeCheck):
    try:
        # Simular recuperación del usuario de la base de datos
        user = {
            "stripe_session_id": sessionStripeCheck.stripe_session_id,
            "paid_sub": sessionStripeCheck.paid_sub,
        }

        # Verificar si el usuario tiene una sesión de Stripe y si no ha pagado ya
        if not user["stripe_session_id"] or user["paid_sub"]:
            return PlainTextResponse(content="fail")

        # Verificar el estado de la sesión de Stripe
        session = stripe.checkout.Session.retrieve(user["stripe_session_id"])
        print("🔥🔥🔥 SESSION", session)
        # Actualizar el usuario si la sesión está completa
        if session and session.status == "complete":
            # Actualizar el usuario en la base de datos
            # db.update_user_stripe(userId, True)
            # Retornar "success" si se actualizó correctamente
            return PlainTextResponse(content="success")
        else:
            # Retornar "fail" si la sesión no está completa
            return PlainTextResponse(content="fail")

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Error de Stripe: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@app.post("/login")
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


@app.post("/ping")
async def validate_token(request: Request):
    headers = request.headers
    jwt = headers.get("authorization")

    user = auth.verify_id_token(jwt)
    print("USUARIO", user)
    verificacion = is_email_verified(user["user_id"])
    if verificacion == True:
        print("Email verificado")
    else:
        print("Se requiere verificacion")
        send_email_verification(user["email"], user["name"])
        print("Se ha enviado un correo de verificacion")

    return JSONResponse(
        content={"userId": user["user_id"], "email_verified": verificacion},
        status_code=200,
    )


@app.post("/lost_password")
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


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        user = auth.verify_id_token(token)
        return user
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación expirado")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación inválido")


@app.post("/dashboard/teacher/changePassword")
async def change_teacher_password(changePassword: ChangePasswordRequest):
    try:
        auth.update_user(
            uid=changePassword.user_id, password=changePassword.new_password
        )
        doc_ref = db.collection("tDash_teacherData").document(changePassword.user_id)
        doc_ref.update({"password": changePassword.new_password})
        return JSONResponse(
            content={"message": "Contraseña cambiada exitosamente"}, status_code=200
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al cambiar la contraseña: {str(e)}"
        )


@app.post("/dashboard/teacher/getData")
async def get_teacher_data(teacherData: SearchTeacherSchema):
    teacherID = teacherData.teacherID
    try:
        doc_ref = db.collection("tDash_teacherData").document(teacherID)
        doc = doc_ref.get()

        if doc.exists:
            teacher_data = doc.to_dict()
            return JSONResponse(content={"data": teacher_data}, status_code=200)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Datos del profesor con ID {teacherID} no encontrados",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener datos del profesor: {str(e)}"
        )


@app.get("/dashboard/getFrequentlyQuestions")
async def get_frequently_questions():
    try:
        collection_ref = db.collection("tDash_frequentQuestions")
        docs = collection_ref.stream()

        frequent_questions = []

        for doc in docs:
            frequent_questions.append(doc.to_dict())

        return JSONResponse(content={"data": frequent_questions}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener preguntas frecuentes: {str(e)}"
        )


@app.post("/dashboard/sendMessage")
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


@app.post("/dashboard/getContent")
async def get_type_content(contentID: GetContent):
    try:
        content_type_id = contentID.contentTypeId

        collection_ref = db.collection("tDash_content")
        docs = collection_ref.where("typeContent", "==", content_type_id).stream()

        content = []

        for doc in docs:
            doc_data = doc.to_dict()
            content_item = {
                "name": doc_data["name"],
                "description": doc_data["description"],
                "typeContent": doc_data["typeContent"],
                "content": {"listDocuments": [], "listContent": []},
            }

            content_units_ref = doc.reference.collection("tDash_ContentUnits")
            content_units_docs = content_units_ref.stream()

            for unit_doc in content_units_docs:
                unit_doc_data = unit_doc.to_dict()
                if unit_doc_data.get("fileType") == 2:
                    content_item["content"]["listDocuments"].append(unit_doc_data)
                else:
                    content_item["content"]["listContent"].append(unit_doc_data)

            content.append(content_item)

        return JSONResponse(content={"data": content}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener el contenido: {str(e)}"
        )


@app.get("/dashboard/students")
async def get_all_students():
    try:
        collection_ref = db.collection("tDash_students")
        docs = collection_ref.stream()

        list_students = []

        for doc in docs:
            student_data = doc.to_dict()

            # Convertir campos de fecha y hora a cadenas de texto
            for key, value in student_data.items():
                if isinstance(value, datetime):
                    student_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")

            list_students.append(student_data)

        return JSONResponse(content={"data": list_students}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener estudiantes: {str(e)}"
        )


@app.post("/dashboard/students/add")
async def add_new_student(student_data: AddStudentRequest):
    try:
        if not student_data.names:
            raise HTTPException(
                status_code=400,
                detail="Se requiere al menos un nombre en los datos del estudiante",
            )

        for name in student_data.names:
            current_time = datetime.utcnow()

            new_student_data = {
                "id": "0",
                "name": name,
                "avatarCode": 1,
                "className": None,
                "dateAdded": current_time,
                "lastConnection": current_time,
                "lastModifiedDate": current_time,
                "idTeacher": student_data.teacherId,
            }

            new_student_ref = db.collection("tDash_students").add(new_student_data)
            new_student_id = new_student_ref[1].id

            new_student_data["id"] = new_student_id
            db.collection("tDash_students").document(new_student_id).set(
                new_student_data
            )

        return JSONResponse(
            content={"message": "Estudiantes agregados exitosamente"}, status_code=201
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al agregar estudiantes: {str(e)}"
        )


@app.post("/dashboard/students/getStudentData")
async def get_student_data(request_data: GetStudentDataRequest):
    try:
        student_id = request_data.student_id

        students_collection = db.collection("tDash_students")

        query = students_collection.where("id", "==", student_id).limit(1)
        query_result = query.stream()

        student_docs = list(query_result)
        if student_docs:
            student_data = student_docs[0].to_dict()

            for field in ["lastConnection", "dateAdded"]:
                if field in student_data:
                    student_data[field] = student_data[field].isoformat()

            return JSONResponse(content={"data": student_data}, status_code=200)
        else:
            raise HTTPException(
                status_code=404, detail=f"Estudiante con ID {student_id} no encontrado"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener datos del estudiante: {str(e)}"
        )


@app.post("/dashboard/students/edit")
async def edit_student(student_data: EditStudentRequest):
    try:
        student_id = student_data.id

        students_collection = db.collection("tDash_students")

        query = students_collection.where("id", "==", student_id).limit(1)
        query_result = query.stream()

        student_docs = list(query_result)
        if student_docs:
            update_data = {}
            if student_data.name is not None:
                update_data["name"] = student_data.name
            if student_data.avatarCode is not None:
                update_data["avatarCode"] = student_data.avatarCode
            if student_data.currentCoins is not None:
                update_data["currentCoins"] = student_data.currentCoins
            if student_data.totalCoinsWin is not None:
                update_data["totalCoinsWin"] = student_data.totalCoinsWin
            if student_data.lastConnection is not None:
                update_data["lastConnection"] = student_data.lastConnection
            if student_data.lstProgress is not None:
                update_data["lstProgress"] = student_data.lstProgress

            students_collection.document(student_docs[0].id).update(update_data)

            return JSONResponse(
                content={"message": "Estudiante actualizado exitosamente"},
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"Estudiante con ID {student_id} no encontrado"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar estudiante: {str(e)}"
        )


@app.post("/dashboard/students/getProgress")
async def get_progress_student():
    pass


@app.post("/dashboard/students/delete")
async def delete_student(delete_data: DeleteStudentRequest):
    try:
        student_id = delete_data.id

        students_collection = db.collection("tDash_students")

        query = students_collection.where("id", "==", student_id).limit(1)
        query_result = query.stream()

        student_docs = list(query_result)
        if student_docs:
            students_collection.document(student_docs[0].id).delete()

            return JSONResponse(
                content={"message": "Estudiante eliminado exitosamente"},
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"Estudiante con ID {student_id} no encontrado"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar estudiante: {str(e)}"
        )


@app.post("/dashboard/classes/create")
async def create_classes(classes_add: ClassesAdd):
    try:
        current_time = datetime.now()

        class_data = {
            "idTeacher": classes_add.idTeacher,
            "className": classes_add.name_class,
            "user": "teacherTest",
            "password": "testPassword",
            "worldId": classes_add.type_class,
            "lstUnits": None,
            "lstStudents": None,
            "createdDate": current_time,
            "lastModifiedDate": current_time,
        }

        # Agregar un nuevo documento a la colección tDash_Classes
        new_class_ref = db.collection("tDash_class").add(class_data)

        print(new_class_ref)

        return JSONResponse(
            content={"message": "Clase creada correctamente"}, status_code=201
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al crear la clase: {str(e)}"
        )


@app.get("/dashboard/classes")
async def get_classes():
    try:
        collection_ref = db.collection("tDash_class")
        docs = collection_ref.stream()
        classes_data = []

        for doc in docs:
            class_data = doc.to_dict()
            if "createdDate" in class_data:
                class_data["createdDate"] = class_data["createdDate"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if "lastModifiedDate" in class_data:
                class_data["lastModifiedDate"] = class_data[
                    "lastModifiedDate"
                ].strftime("%Y-%m-%d %H:%M:%S")
            class_data["id"] = doc.id
            classes_data.append(class_data)

        return JSONResponse(content={"data": classes_data}, status_code=200)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener las clases: {str(e)}"
        )


@app.post("/dashboard/classes/getClass")
async def get_class(class_get: ClassId):
    try:
        doc_ref = db.collection("tDash_class").document(class_get.id_class)
        doc = doc_ref.get()

        if doc.exists:
            class_data = doc.to_dict()
            if "createdDate" in class_data:
                class_data["createdDate"] = class_data["createdDate"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if "lastModifiedDate" in class_data:
                class_data["lastModifiedDate"] = class_data[
                    "lastModifiedDate"
                ].strftime("%Y-%m-%d %H:%M:%S")
            class_data["id"] = doc.id
            print("CLASS_dATA", class_data)
            # Obtener datos de tDash_content
            listaUnits = []
            for unit_id in class_data.get("lstUnits", []):
                unit_ref = db.collection("tDash_content").document(unit_id)
                unit_doc = unit_ref.get()
                if unit_doc.exists:
                    listaUnits.append(unit_doc.to_dict())
            print("listaUnits", listaUnits)
            # Obtener datos de tDash_students
            listaStudents = []
            for student_id in class_data.get("lstStudents", []):
                student_ref = db.collection("tDash_students").document(student_id)
                student_doc = student_ref.get()
                if student_doc.exists:
                    student_data = student_doc.to_dict()
                    # Convertir objetos datetime a cadenas de texto
                    if "dateAdded" in student_data:
                        student_data["dateAdded"] = student_data["dateAdded"].strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    if "lastModifiedDate" in student_data:
                        student_data["lastModifiedDate"] = student_data[
                            "lastModifiedDate"
                        ].strftime("%Y-%m-%d %H:%M:%S")
                    if "lastConnection" in student_data:
                        student_data["lastConnection"] = student_data[
                            "lastConnection"
                        ].strftime("%Y-%m-%d %H:%M:%S")
                    listaStudents.append(student_data)
            print("listaStudents", listaStudents)
            # Agregar listas de unidades y estudiantes a class_data
            class_data["listaUnits"] = listaUnits
            class_data["listaStudents"] = listaStudents

            # Convertir a JSON y devolver la respuesta
            return JSONResponse(content={"data": class_data}, status_code=200)
        else:
            # Si el documento no existe, devolver un error
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {class_get.id_class}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener la clase: {str(e)}"
        )


@app.post("/dashboard/classes/deleteClass")
async def delete_class(class_delete: ClassId):
    try:
        doc_ref = db.collection("tDash_class").document(class_delete.id_class)

        if doc_ref.get().exists:
            doc_ref.delete()
            return JSONResponse(
                content={
                    "message": f"Clase con ID {class_delete.id_class} eliminada correctamente"
                },
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {class_delete.id_class}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar la clase: {str(e)}"
        )


@app.post("/dashboard/classes/addStudents")
async def add_students(student_add: StudentClassAdd):
    try:
        current_time = datetime.now()

        class_ref = db.collection("tDash_class").document(student_add.class_id)

        if class_ref.get().exists:
            class_ref.update(
                {"lstStudents": firestore.ArrayUnion(student_add.student_ids)}
            )

            # Obtener el nombre de la clase
            class_data = class_ref.get().to_dict()
            class_name = class_data.get("className")

            # Actualizar className para cada estudiante
            for student_id in student_add.student_ids:
                student_ref = db.collection("tDash_students").document(student_id)
                student_ref.update({"className": class_name})

                # Crear un documento en tDash_classStudentData
                student_class_data = {
                    "idClass": student_add.class_id,
                    "idStudent": student_id,
                    "currentUnit": None,
                    "currentContent": None,
                    "currentCoins": 0,
                    "totalCoinsWin": 0,
                    "lastConnection": current_time,
                    "lstProgress": None,
                }
                db.collection("tDash_classStudentData").add(student_class_data)

            return JSONResponse(
                content={"message": "Estudiantes añadidos correctamente"},
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {student_add.class_id}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al añadir estudiantes a la clase: {str(e)}"
        )


@app.post("/dashboard/classes/addUnits")
async def add_unitsClasses(units_add: UnitsClassAdd):
    try:
        # Obtener la referencia al documento de la clase
        class_ref = db.collection("tDash_class").document(units_add.class_id)

        # Verificar si el documento de la clase existe
        if class_ref.get().exists:
            # Actualizar la lista de estudiantes con los nuevos IDs
            class_ref.update({"lstUnits": firestore.ArrayUnion(units_add.unit_ids)})

            return JSONResponse(
                content={"message": "Estudiantes añadidos correctamente"},
                status_code=200,
            )
        else:
            return {
                "message": f"Unidades {units_add.unit_ids} agregadas a la clase {units_add.class_id} correctamente"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al agregar unidades a la clase: {str(e)}"
        )


@app.post("/dashboard/classes/delUnit")
async def del_unit_classes(unit_del: UnitClassDel):
    try:
        # Obtener el ID de la clase y el ID de la unidad a eliminar
        class_id = unit_del.class_id
        unit_id = unit_del.unit_id

        # Verificar si la clase existe
        class_doc = db.collection("tDash_class").document(class_id).get()
        if not class_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"Clase con ID {class_id} no encontrada"
            )

        # Eliminar la unidad de la lista lstUnits de la clase en la base de datos
        class_ref = db.collection("tDash_class").document(class_id)
        class_ref.update({"lstUnits": firestore.ArrayRemove([unit_id])})

        return {
            "message": f"Unidad {unit_id} eliminada de la clase {class_id} correctamente"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar la unidad de la clase: {str(e)}"
        )


@app.post("/dashboard/classes/delStudents")
async def del_student_classes(student_del: StudentClassDel):
    try:
        # Obtener el ID de la clase y los IDs de los estudiantes a eliminar
        class_id = student_del.class_id
        students_id = student_del.student_id

        # Verificar si la clase existe
        class_doc = db.collection("tDash_class").document(class_id).get()
        if not class_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"Clase con ID {class_id} no encontrada"
            )

        # Eliminar los estudiantes de la lista lstStudents de la clase en la base de datos
        class_ref = db.collection("tDash_class").document(class_id)
        class_ref.update({"lstStudents": firestore.ArrayRemove(students_id)})

        return {
            "message": f"Estudiantes {students_id} eliminados de la clase {class_id} correctamente"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar los estudiantes de la clase: {str(e)}",
        )


@app.post("/dashboard/classes/student/progress")
async def get_student_progress(studentProgressData: StudentProgressRequest):
    try:
        query = (
            db.collection("tDash_classStudentData")
            .where("idStudent", "==", studentProgressData.idStudent)
            .where("idClass", "==", studentProgressData.idClass)
        )
        query_result = query.get()

        for doc in query_result:
            doc_dict = doc.to_dict()
            doc_dict["lastConnection"] = doc_dict["lastConnection"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            return JSONResponse(content={"data": doc_dict}, status_code=200)

        raise HTTPException(
            status_code=404,
            detail="No se encontró ningún documento que coincida con los IDs proporcionados.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener el progreso del estudiante: {str(e)}",
        )


@app.get("/dashboard/suscription/plans")
async def get_subscription_plans_route(plan_id: str = None):
    try:
        # Consultar la colección de planes
        plans_ref = db.collection("tDash_plans")

        if plan_id:
            # Obtener el documento del plan con el ID especificado
            plan_doc = plans_ref.document(plan_id).get()
            if plan_doc.exists:
                # Devolver el plan con el ID especificado
                return JSONResponse(
                    content={"plan": plan_doc.to_dict()}, status_code=200
                )
            else:
                # Si no se encuentra el plan con el ID especificado, devolver un error
                raise HTTPException(
                    status_code=404, detail=f"No se encontró el plan con ID {plan_id}"
                )
        else:
            # Inicializar diccionarios para planes mensuales y anuales
            plans_mensuales = {}
            plans_anuales = {}

            # Iterar sobre los documentos de la colección
            for doc in plans_ref.stream():
                plan_data = doc.to_dict()
                plan_id = doc.id
                type_plan = plan_data.get("type_plan")

                # Agregar el plan al diccionario correspondiente según su tipo
                if type_plan == 1:
                    plans_mensuales[plan_id] = plan_data
                else:
                    plans_anuales[plan_id] = plan_data

            # Devolver los planes organizados
            return JSONResponse(
                content={
                    "plans_mensuales": plans_mensuales,
                    "plans_anuales": plans_anuales,
                },
                status_code=200,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los planes de suscripción: {str(e)}",
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

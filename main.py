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
    UnitClassDel,
    UnitsClassAdd,
)
from datetime import datetime
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

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


def send_email(to_email, body):
    try:
        subject = "Mensaje desde el dashboard"

        # Configura el mensaje
        message = MIMEMultipart()
        message["From"] = SMTP_USERNAME
        message["To"] = to_email
        message["Subject"] = subject

        # Agrega el cuerpo del mensaje
        message.attach(MIMEText(body, "plain"))

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


def send_email_verification(email):
    try:
        # Enviar el correo de verificación
        link = auth.generate_email_verification_link(email, action_code_settings=None)
        message = link
        print("MENSAJE", message)
        sendedEmail = send_email(email, message)
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


@app.post("/suscription/create-checkout-session")
async def create_checkout_session(sessionCheckoutCreate: SessionCheckoutCreate):
    CLIENT_URL = "http://localhost:4200/main"
    try:
        # Crear la sesión de checkout en Stripe
        session = stripe.checkout.Session.create(
            success_url=CLIENT_URL,
            cancel_url=CLIENT_URL,
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

        # Retornar la URL de la sesión de checkout
        return JSONResponse(content={"url": session.url})

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Error de Stripe: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@app.get("/suscription/check-stripe-session")
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
        send_email_verification(user["email"])
        print("Se ha enviado un correo de verificacion")

    return JSONResponse(
        content={"userId": user["user_id"], "email_verified": verificacion},
        status_code=200,
    )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        user = auth.verify_id_token(token)
        return user
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación expirado")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación inválido")


@app.post("/dashboard/teacher/changePassword")
async def change_teacher_password(
    password_data: ChangePasswordRequest, current_user: dict = Depends(get_current_user)
):
    try:
        # Verificar la contraseña actual del usuario
        email = current_user.get("email")
        auth.verify_password(email=email, password=password_data.current_password)

        # Cambiar la contraseña del usuario
        auth.update_user(
            uid=current_user.get("user_id"), password=password_data.new_password
        )

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

        sendedEmail = send_email(email, contact_data.email_content)
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
        docs = collection_ref.where("contentType", "==", content_type_id).stream()

        content = {
            "listImages": [],
            "listPdf": [],
            "listGames": [],
            "listVideos": [],
        }

        for doc in docs:
            content_data = doc.to_dict()

            file_type = content_data.get("fileType")
            if file_type == 1:
                content["listImages"].append(content_data)
            elif file_type == 2:
                content["listPdf"].append(content_data)
            elif file_type == 3:
                content["listGames"].append(content_data)
            elif file_type == 4:
                content["listVideos"].append(content_data)

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
            # Generar un uuidv4 random para el campo 'id'
            student_id = str(uuid.uuid4())

            # Obtener la fecha y hora del momento actual para el campo 'lastConnection'
            current_time = datetime.utcnow()

            # Estructurar los datos del estudiante
            new_student_data = {
                "id": student_id,
                "name": name,
                "avatarCode": 1,  # Puedes ajustar este valor según tus necesidades
                "currentCoins": 0,
                "className": "",
                "totalCoinsWin": 0,
                "dateAdded": current_time,
                "lastConnection": current_time,
                "idTeacher": student_data.teacherId,
                "lstProgress": [],  # Puedes ajustar este valor según tus necesidades
            }

            # Insertar el estudiante en la colección
            db.collection("tDash_students").add(new_student_data)

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
        # Obtener la referencia al documento de la clase
        class_ref = db.collection("tDash_class").document(student_add.class_id)

        # Verificar si el documento de la clase existe
        if class_ref.get().exists:
            # Actualizar la lista de estudiantes con los nuevos IDs
            class_ref.update(
                {"lstStudents": firestore.ArrayUnion(student_add.student_ids)}
            )

            return JSONResponse(
                content={"message": "Estudiantes añadidos correctamente"},
                status_code=200,
            )
        else:
            # Si el documento de la clase no existe, devolver un error
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

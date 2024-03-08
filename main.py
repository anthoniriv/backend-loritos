from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uvicorn
import pyrebase
import uuid
import smtplib
from fastapi import FastAPI, Depends
from models import (
    LoginSchema,
    SingUpSchema,
    SearchTeacherSchema,
    GetContent,
    AddStudentRequest,
    EditStudentRequest,
    DeleteStudentRequest,
    GetStudentDataRequest,
    ChangePasswordRequest,
    ContactMessage,
)
from datetime import datetime
from fastapi.responses import JSONResponse
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


@app.post("/login")
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


@app.post("/ping")
async def validate_token(request: Request):
    headers = request.headers
    jwt = headers.get("authorization")

    user = auth.verify_id_token(jwt)

    return JSONResponse(content={"userId": user["user_id"]}, status_code=200)


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
        # Configura los detalles del servidor de correo
        smtp_server = "smtp-relay.brevo.com"  # Reemplaza con tu servidor SMTP
        smtp_port = 587
        smtp_username = "anthoniriv01@gmail.com"  # Reemplaza con tu correo
        smtp_password = "9AjfVh2mrnOCZsFw"  # Reemplaza con tu contraseña

        # Configura el contenido del correo
        subject = "Mensaje desde el dashboard"
        body = f"Nombre: {contact_data.name}\nApellidos: {contact_data.last_name}\nEnvio: {contact_data.email_content}"

        # Configura el mensaje
        message = MIMEMultipart()
        message["From"] = smtp_username
        message["To"] = "holasoyanthoni@gmail.com"
        message["Subject"] = subject

        # Agrega el cuerpo del mensaje
        message.attach(MIMEText(body, "plain"))

        # Conecta y envía el correo
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(
                smtp_username, "holasoyanthoni@gmail.com", message.as_string()
            )

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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

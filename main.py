import uvicorn
import pyrebase
from fastapi import FastAPI
from models import LoginSchema, SingUpSchema, SearchTeacherSchema, GetContent
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.requests import Request

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


@app.post("/singup")
async def create_account(user_data: SingUpSchema):
    email = user_data.email
    password = user_data.password

    try:
        user = auth.create_user(email=email, password=password)

        return JSONResponse(
            content={"message": f"Cuenta creada correctamente para usuario {user.uid}"},
            status_code=201,
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"Esta cuenta ya existe actualmente para el email {email}",
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

    return user["user_id"]


@app.post("/dashboard/teacher/changePassword")
async def change_teacher_password():
    pass


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
async def send_contact_message():
    pass


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
async def add_new_student():
    pass


@app.post("/dashboard/students/edit")
async def edit_student():
    pass


@app.post("/dashboard/students/getProgress")
async def get_progress_student():
    pass


@app.post("/dashboard/students/delete")
async def delete_student():
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

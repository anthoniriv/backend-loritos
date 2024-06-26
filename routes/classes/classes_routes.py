import base64
import random
import string
from datetime import datetime
import pdfkit
from jinja2 import Template
from config import db, firestore
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
import boto3
from io import BytesIO
from utils import get_student_progress_data
from models import (
    AddStudentClassRequest,
    ClassId,
    ClassesAdd,
    EditClassRequest,
    IdClass,
    StudentClassAdd,
    StudentClassDel,
    StudentProgressRequest,
    UnitClassDel,
    UnitsClassAdd,
)

from routes.classes.models import ProgressClassRequest

router = APIRouter()



def validate_class_name(class_name: str):
    class_docs = db.collection("tDash_class").where("className", "==", class_name).get()
    if len(class_docs) > 0:
        raise HTTPException(status_code=400, detail="The class name already exist.")

@router.post("/create")
async def create_classes(classes_add: ClassesAdd):
    try:
        current_time = datetime.now()

        validate_class_name(classes_add.name_class)

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

        new_class_ref = db.collection("tDash_class").add(class_data)
        new_class_id = new_class_ref[1].id

        class_data["id"] = new_class_id

        db.collection("tDash_class").document(new_class_id).set(class_data)

        teacher_data_ref = db.collection("tDash_teacherData").document(
            classes_add.idTeacher
        )
        teacher_doc = teacher_data_ref.get()

        if teacher_doc.exists:
            lst_classes = teacher_doc.to_dict().get("lstClasses", [])

            lst_classes.append(new_class_id)

            teacher_data_ref.update({"lstClasses": lst_classes})

        return JSONResponse(
            content={"message": "Clase creada correctamente", "class_id": new_class_id},
            status_code=201,
        )
    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al crear la clase: {str(e)}"
        )

@router.get("/")
async def get_classes(teacherID: str):
    try:
        teacher_ref = db.collection("tDash_teacherData").document(teacherID)
        teacher_doc = teacher_ref.get()

        if not teacher_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"No se encontró el profesor con ID {teacherID}"
            )

        teacher_data = teacher_doc.to_dict()
        lst_classes_ids = teacher_data.get("lstClasses", [])
        classes_ref = db.collection("tDash_class").where("id", "in", lst_classes_ids)
        classes_docs = classes_ref.stream()

        classes_data = []
        for doc in classes_docs:
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


@router.post("/getClass")
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
            listaUnits = []
            if class_data.get("lstUnits") is not None:  # Validar que no sea nulo
                for unit_id in class_data["lstUnits"]:
                    unit_ref = db.collection("tDash_content").document(unit_id)
                    unit_doc = unit_ref.get()
                    if unit_doc.exists:
                        listaUnits.append(unit_doc.to_dict())
            listaStudents = []
            if class_data.get("lstStudents") is not None:  # Validar que no sea nulo
                for student_id in class_data["lstStudents"]:
                    student_ref = db.collection("tDash_students").document(student_id)
                    student_doc = student_ref.get()
                    if student_doc.exists:
                        student_data = student_doc.to_dict()
                        if "dateAdded" in student_data:
                            student_data["dateAdded"] = student_data[
                                "dateAdded"
                            ].strftime("%Y-%m-%d %H:%M:%S")
                        if "lastModifiedDate" in student_data:
                            student_data["lastModifiedDate"] = student_data[
                                "lastModifiedDate"
                            ].strftime("%Y-%m-%d %H:%M:%S")
                        if "lastConnection" in student_data:
                            student_data["lastConnection"] = student_data[
                                "lastConnection"
                            ].strftime("%Y-%m-%d %H:%M:%S")
                        listaStudents.append(student_data)
            class_data["listaUnits"] = listaUnits
            class_data["listaStudents"] = listaStudents

            return JSONResponse(content={"data": class_data}, status_code=200)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {class_get.id_class}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener la clase: {str(e)}"
        )


@router.post("/deleteClass")
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


def add_students_to_class(class_id: str, student_ids: list):
    current_time = datetime.now()
    class_ref = db.collection("tDash_class").document(class_id)

    if class_ref.get().exists:
        class_ref.update({"lstStudents": firestore.ArrayUnion(student_ids)})

        # Obtener el nombre de la clase
        class_data = class_ref.get().to_dict()
        class_name = class_data.get("className")

        # Actualizar className para cada estudiante
        for student_id in student_ids:
            student_ref = db.collection("tDash_students").document(student_id)
            student_ref.update({"className": class_name, "classId": class_id})

            # Crear un documento en tDash_classStudentData
            student_class_data = {
                "idClass": class_id,
                "idStudent": student_id,
                "currentUnit": None,
                "currentContent": None,
                "currentCoins": 0,
                "totalCoinsWin": 0,
                "lastConnection": current_time,
                "lstProgress": None,
            }
            db.collection("tDash_classStudentData").add(student_class_data)

        return True, "Estudiantes añadidos correctamente"
    else:
        return False, f"No se encontró la clase con ID {class_id}"


@router.post("/addStudents")
async def add_students_route(student_add: StudentClassAdd):
    try:
        success, message = add_students_to_class(
            student_add.class_id, student_add.student_ids
        )
        if success:
            return JSONResponse(
                content={"message": message},
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=message,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al añadir estudiantes a la clase: {str(e)}"
        )

@router.post("/addNewStudentClass")
async def add_new_student(student_data: AddStudentClassRequest):
    try:
        if not student_data.names:
            raise HTTPException(
                status_code=400,
                detail="Se requiere al menos un nombre en los datos del estudiante",
            )

        idStudents = []

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

            idStudents.append(new_student_id)

            new_student_data["id"] = new_student_id
            db.collection("tDash_students").document(new_student_id).set(
                new_student_data
            )

            teacher_data_ref = db.collection("tDash_teacherData").document(
                student_data.teacherId
            )
            teacher_data_ref.update(
                {"lstStudents": firestore.ArrayUnion([new_student_id])}
            )

        # Agregar los nuevos estudiantes a la clase
        success, message = add_students_to_class(student_data.classId, idStudents)
        if success:
            return JSONResponse(
                content={"message": message}, status_code=201
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=message,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al agregar estudiantes: {str(e)}"
        )

@router.post("/addUnits")
async def add_unitsClasses(units_add: UnitsClassAdd):
    try:
        class_ref = db.collection("tDash_class").document(units_add.class_id)

        if class_ref.get().exists:
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


@router.post("/delUnit")
async def del_unit_classes(unit_del: UnitClassDel):
    try:
        class_id = unit_del.class_id
        unit_id = unit_del.unit_id

        class_doc = db.collection("tDash_class").document(class_id).get()
        if not class_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"Clase con ID {class_id} no encontrada"
            )

        class_ref = db.collection("tDash_class").document(class_id)
        class_ref.update({"lstUnits": firestore.ArrayRemove([unit_id])})

        return {
            "message": f"Unidad {unit_id} eliminada de la clase {class_id} correctamente"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar la unidad de la clase: {str(e)}"
        )


@router.post("/delStudents")
async def del_student_classes(student_del: StudentClassDel):
    try:
        class_id = student_del.class_id
        students_id = student_del.student_id

        class_doc = db.collection("tDash_class").document(class_id).get()
        if not class_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"Clase con ID {class_id} no encontrada"
            )

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


@router.post("/getLstStudents")
async def get_lst_student_classes(idClass: IdClass):
    try:
        class_doc = db.collection("tDash_class").document(idClass.idClass).get()

        if class_doc.exists:
            lst_students = class_doc.to_dict().get("lstStudents", [])

            students_data = []
            students_docs = (
                db.collection("tDash_students")
                .where("__name__", "in", lst_students)
                .stream()
            )

            for student_doc in students_docs:
                student_data = student_doc.to_dict()

                # Convertir fechas si es necesario
                for key, value in student_data.items():
                    if isinstance(value, datetime):
                        student_data[key] = value.isoformat()

                students_data.append(student_data)

            return JSONResponse(content={"students": students_data}, status_code=200)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {idClass.idClass}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los datos de los estudiantes: {str(e)}",
        )


@router.post("/getLstUnits")
async def get_lst_unit_classes(idClass: IdClass):
    try:
        class_doc = db.collection("tDash_class").document(idClass.idClass).get()

        if class_doc.exists:
            lst_units = class_doc.to_dict().get("lstUnits", [])

            units_data = []
            units_docs = (
                db.collection("tDash_content")
                .where("__name__", "in", lst_units)
                .stream()
            )

            for unit_doc in units_docs:
                unit_data = unit_doc.to_dict()
                unit_id = unit_doc.id

                unit_data["id"] = unit_id

                units_data.append(unit_data)

            return JSONResponse(content={"units": units_data}, status_code=200)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {idClass.idClass}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los datos de las unidades: {str(e)}",
        )

def generate_username():
    return f"teacher{random.randint(1000, 9999)}"

# Generar una contraseña aleatoria de longitud 8
def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

@router.post("/getCredentials")
async def get_credentials(idClass: IdClass):
    try:
        # Obtener los datos de la clase
        class_doc = db.collection("tDash_class").document(idClass.idClass).get()
        if class_doc.exists:
            class_data = class_doc.to_dict()

            # Verificar si el archivo PDF ya existe
            s3 = boto3.client("s3")
            bucket_name = "cred-loriworld-test"
            pdf_file_name = f"class_credentials_{idClass.idClass}.pdf"
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=pdf_file_name)
            random_username = generate_username()
            random_password = generate_password()
            if "Contents" in response:
                # El archivo PDF ya existe, obtener la URL pública del PDF en S3
                s3_url = f"https://{bucket_name}.s3.amazonaws.com/{pdf_file_name}"
                return {"pdf_url": s3_url}
            else:
                # El archivo PDF no existe, generar y guardar el PDF en S3 de Amazon
                # Renderizar la plantilla HTML con los datos de la clase
                template_str = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                    <title>Credentials</title>
                    <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                    }
                    .container {
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                    }
                    .top {
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        width: 100%;
                        margin-bottom: 40px;
                    }
                    img {
                        outline: none;
                        text-decoration: none;
                        -ms-interpolation-mode: bicubic;
                        display: block;
                        max-width: 266px;
                        width: 100%;
                        height: auto;
                        margin-left: 150px;
                    }
                    .stu,
                    h1 {
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        width: 100%;
                    }
                    .down {
                        margin-top: 40px;
                    }
                    </style>
                </head>
                <body>
                    <div class="container">
                    <div class="top">
                        <img
                        align="center"
                        border="0"
                        src="https://www.loritosworld.com/wp-content/themes/loritos-world/assets/img/image-9.png"
                        alt=""
                        title=""
                        style="
                            outline: none;
                            text-decoration: none;
                            -ms-interpolation-mode: bicubic;
                            clear: both;
                            display: inline-block !important;
                            border: none;
                            height: auto;
                            float: none;
                            max-width: 366px;
                        "
                        width="366"
                        />
                    </div>
                    <div class="mid">
                        <p>
                        Only students you want in this class should have access to this
                        information:
                        </p>
                        <h1>Class Name {{ class_name }}</h1>
                        <h2>USERNAME: {{ user }}</h2>
                        <h2>PASSWORD: {{ password }}</h2>
                    </div>
                    <div class="down">
                        <p class="stu">
                        Students can only log in through a smartphone or tablet
                        </p>
                        <h4>
                        1. Make sure you have the Loritos World app installed and open it up
                        </h4>
                        <h4>2. Press I Already Have An Account</h4>
                        <h4>3. Type in your username and password and tap Sign In</h4>
                    </div>
                    </div>
                </body>
                </html>
                """
                template = Template(template_str)
                html_content = template.render(
                    class_name=class_data["className"],
                    user=random_username,
                    password=random_password,
                )

                # Generar el PDF
                pdf = pdfkit.from_string(html_content, False)

                # Guardar el PDF en S3 de Amazon
                s3.upload_fileobj(BytesIO(pdf), bucket_name, pdf_file_name)

                # Obtener la URL pública del PDF en S3
                s3_url = f"https://{bucket_name}.s3.amazonaws.com/{pdf_file_name}"

                # Retornar la URL pública del PDF
                return {"pdf_url": s3_url}

        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {idClass.idClass}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener las credenciales de la clase: {str(e)}",
        )


@router.post("/student/progress")
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


@router.post("/editClass")
async def edit_class(editClassRequest: EditClassRequest):
    try:
        id_class = editClassRequest.idClass

        new_class_name = editClassRequest.className

        class_ref = db.collection("tDash_class").document(id_class)
        class_doc = class_ref.get()

        if class_doc.exists:
            class_ref.update({"className": new_class_name})

            return JSONResponse(
                content={"message": "Nombre de clase actualizado correctamente"},
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la clase con ID {id_class}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al editar el nombre de la clase: {str(e)}",
        )

class_collection = db.collection("tDash_class")

@router.post("/progressClass")
async def progress_class(progressClassRequest: ProgressClassRequest):
    try:
        class_id = progressClassRequest.classID

        # Obtener la lista de estudiantes (lstStudents) para el classID dado
        class_doc_ref = class_collection.document(class_id)
        class_doc = class_doc_ref.get().to_dict()

        if class_doc:
            lst_students = class_doc.get("lstStudents", [])
            print("lst_students", lst_students)

            # Lista para almacenar el progreso de cada estudiante
            progress_list = []

            # Iterar sobre cada estudiante en lst_students y obtener su progreso
            for student_id in lst_students:
                student_progress = get_student_progress_data(student_id, class_id)
                progress_list.append(student_progress)

            return progress_list
        else:
            raise HTTPException(status_code=404, detail=f"No se encontró la clase con ID: {class_id}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el progreso de la clase: {str(e)}")

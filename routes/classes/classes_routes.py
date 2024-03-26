import base64
from datetime import datetime

from jinja2 import Template
from config import db, firestore
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException

from models import (
    ClassId,
    ClassesAdd,
    IdClass,
    StudentClassAdd,
    StudentClassDel,
    StudentProgressRequest,
    UnitClassDel,
    UnitsClassAdd,
)

router = APIRouter()


@router.post("/create")
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

        new_class_ref = db.collection("tDash_class").add(class_data)

        teacher_data_ref = db.collection("tDash_teacherData").document(
            classes_add.idTeacher
        )
        teacher_doc = teacher_data_ref.get()

        if teacher_doc.exists:
            lst_classes = teacher_doc.to_dict().get("lstClasses", [])

            lst_classes.append(new_class_ref[1].id)

            teacher_data_ref.update({"lstClasses": lst_classes})

        return JSONResponse(
            content={"message": "Clase creada correctamente"}, status_code=201
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al crear la clase: {str(e)}"
        )


@router.get("/")
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
            print("CLASS_dATA", class_data)
            listaUnits = []
            if class_data.get("lstUnits") is not None:  # Validar que no sea nulo
                for unit_id in class_data["lstUnits"]:
                    unit_ref = db.collection("tDash_content").document(unit_id)
                    unit_doc = unit_ref.get()
                    if unit_doc.exists:
                        listaUnits.append(unit_doc.to_dict())
            print("listaUnits", listaUnits)
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
            print("listaStudents", listaStudents)
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


@router.post("/addStudents")
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

            for student_id in lst_students:
                student_doc = db.collection("tDash_students").document(student_id).get()
                if student_doc.exists:
                    student_data = student_doc.to_dict()

                    for key, value in student_data.items():
                        if isinstance(value, datetime):
                            student_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")

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
            class_id = class_doc.id

            lst_units = class_doc.to_dict().get("lstUnits", [])

            units_data = []

            for unit_id in lst_units:
                unit_doc = db.collection("tDash_content").document(unit_id).get()
                if unit_doc.exists:
                    unit_id = unit_doc.id

                    unit_data = unit_doc.to_dict()
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


from utils import render_html_template


@router.post("/getCredentials")
async def add_unitsClasses(idClass: IdClass):
    try:
        # Obtener los datos de la clase
        class_doc = db.collection("tDash_class").document(idClass.idClass).get()
        if class_doc.exists:
            class_data = class_doc.to_dict()

            # Renderizar la plantilla HTML con los datos de la clase
            html_content = render_html_template(
                "classCredentialsTemplate.html",
                {
                    "class_name": class_data["className"],
                    "user": class_data["user"],
                    "password": class_data["password"],
                },
            )

            # Devolver el contenido HTML con el tipo de contenido MIME adecuado
            return HTMLResponse(content=html_content, status_code=200)

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

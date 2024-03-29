from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from config import db, firestore
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from models import (
    AddStudentRequest,
    EditStudentRequest,
    DeleteStudentRequest,
    GetStudentDataRequest,
)


router = APIRouter()


from concurrent.futures import ThreadPoolExecutor


@router.get("/")
async def get_all_students(teacherID: str, hasClass: bool = True):
    try:
        teacher_ref = db.collection("tDash_teacherData").document(teacherID)
        teacher_doc = teacher_ref.get()

        if not teacher_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"No se encontró el profesor con ID {teacherID}"
            )

        teacher_data = teacher_doc.to_dict()
        lst_students_ids = teacher_data.get("lstStudents", [])
        print("lst_students_ids", lst_students_ids)
        students_ref = db.collection("tDash_students").where(
            "id", "in", lst_students_ids
        )
        students_docs = students_ref.stream()
        print("students_docs", students_docs)

        # Función para procesar un documento de estudiante
        def process_student_doc(student_doc):
            student_data = student_doc.to_dict()

            has_class = bool(student_data.get("className", ""))
            if hasClass:
                return student_data if has_class else None
            else:
                return student_data if not has_class else None

        with ThreadPoolExecutor() as executor:
            processed_students = list(executor.map(process_student_doc, students_docs))

        list_students = [
            student for student in processed_students if student is not None
        ]

        for student in list_students:
            for key, value in student.items():
                if isinstance(value, datetime):
                    student[key] = value.strftime("%Y-%m-%d %H:%M:%S")

        return JSONResponse(content={"data": list_students}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener estudiantes: {str(e)}"
        )


@router.post("/add")
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

            teacher_data_ref = db.collection("tDash_teacherData").document(
                student_data.teacherId
            )
            teacher_data_ref.update(
                {"lstStudents": firestore.ArrayUnion([new_student_id])}
            )

        return JSONResponse(
            content={"message": "Estudiantes agregados exitosamente"}, status_code=201
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al agregar estudiantes: {str(e)}"
        )


@router.post("/getStudentData")
async def get_student_data(request_data: GetStudentDataRequest):
    try:
        student_id = request_data.student_id

        students_collection = db.collection("tDash_students")

        student_doc_ref = students_collection.document(student_id)
        student_doc = student_doc_ref.get()

        if student_doc.exists:
            student_data = student_doc.to_dict()

            for key, value in student_data.items():
                if isinstance(value, datetime):
                    student_data[key] = value.isoformat()

            return JSONResponse(content={"data": student_data}, status_code=200)
        else:
            raise HTTPException(
                status_code=404, detail=f"Estudiante con ID {student_id} no encontrado"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener datos del estudiante: {str(e)}"
        )


@router.post("/edit")
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


@router.post("/getProgress")
async def get_progress_student():
    pass


@router.post("/delete")
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

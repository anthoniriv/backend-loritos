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

@router.get("/dashboard/students")
async def get_all_students(teacherID: str):
    try:
        collection_ref = db.collection("tDash_students")

        query = collection_ref.where("idTeacher", "==", teacherID)
        docs = query.stream()

        list_students = []

        for doc in docs:
            student_data = doc.to_dict()

            for key, value in student_data.items():
                if isinstance(value, datetime):
                    student_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")

            list_students.append(student_data)

        return JSONResponse(content={"data": list_students}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener estudiantes: {str(e)}"
        )


@router.post("/dashboard/students/add")
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


@router.post("/dashboard/students/getStudentData")
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


@router.post("/dashboard/students/edit")
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


@router.post("/dashboard/students/getProgress")
async def get_progress_student():
    pass

@router.post("/dashboard/students/delete")
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

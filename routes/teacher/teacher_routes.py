from datetime import datetime
from config import db, auth
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from models import (
    SearchTeacherSchema,
    ChangePasswordRequest,
)

router = APIRouter()


@router.post("/changePassword")
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


@router.post("/getData")
async def get_teacher_data(teacherData: SearchTeacherSchema):
    teacherID = teacherData.teacherID
    try:
        teacher_ref = db.collection("tDash_teacherData").document(teacherID)
        teacher_doc = teacher_ref.get()

        if teacher_doc.exists:
            teacher_data = teacher_doc.to_dict()

            for key, value in teacher_data.items():
                if isinstance(value, datetime):
                    teacher_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")

            subscription_data_query = teacher_ref.collection(
                "tDash_subscriptionData"
            ).limit(1)
            subscription_data_docs = subscription_data_query.get()

            subscription_data = None
            if subscription_data_docs:
                subscription_data = subscription_data_docs[0].to_dict()

                renew_date = subscription_data.get("renewDate")
                if isinstance(renew_date, datetime):
                    subscription_data["renewDate"] = renew_date.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                plan_id = subscription_data.get("id_plan")
                plan_doc = db.collection("tDash_plans").document(plan_id).get()
                if plan_doc.exists:
                    plan_data = plan_doc.to_dict()
                    max_students = plan_data.get("maxStudents")
                    lst_students = teacher_data.get("lstStudents", [])
                    if max_students == len(lst_students):
                        teacher_data["limitStudents"] = True
                    else:
                        teacher_data["limitStudents"] = False

            return JSONResponse(
                content={
                    "teacher_data": teacher_data,
                    "subscription_data": subscription_data,
                },
                status_code=200,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Datos del profesor con ID {teacherID} no encontrados",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener datos del profesor: {str(e)}"
        )


@router.post("/deleteAccount")
async def del_acc_teacher(teacherData: SearchTeacherSchema):
    try:
        # Obtener el documento a eliminar de tDash_teacherData
        teacher_doc_ref = db.collection("tDash_teacherData").document(
            teacherData.teacherID
        )
        teacher_doc = teacher_doc_ref.get()

        if not teacher_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el profesor con ID {teacherData.teacherID}",
            )

        # Obtener las listas de clases y estudiantes del profesor
        lst_classes = teacher_doc.to_dict().get("lstClasses", [])
        lst_students = teacher_doc.to_dict().get("lstStudents", [])

        # Eliminar todas las clases del profesor de la colección tDash_class
        for class_id in lst_classes:
            class_ref = db.collection("tDash_class").document(class_id)
            class_ref.delete()

        # Eliminar a los estudiantes del profesor de la colección tDash_students
        for student_id in lst_students:
            student_ref = db.collection("tDash_students").document(student_id)
            student_ref.delete()

        # Eliminar las referencias a los estudiantes del profesor en tDash_classStudentData
        class_student_data_ref = db.collection("tDash_classStudentData")
        class_student_data_query = class_student_data_ref.where(
            "idStudent", "in", lst_students
        )
        class_student_data_docs = class_student_data_query.stream()

        for doc in class_student_data_docs:
            doc_ref = class_student_data_ref.document(doc.id)
            doc_ref.delete()

        # Eliminar el usuario del módulo de autenticación de Firebase
        auth.delete_user(teacherData.teacherID)

        # Eliminar el documento del profesor de tDash_teacherData
        teacher_doc_ref.delete()

        return JSONResponse(
            content={"message": "Cuenta de profesor eliminada correctamente"},
            status_code=200,
        )

    except auth.AuthError as e:
        # Maneja los errores relacionados con la autenticación de Firebase
        raise HTTPException(
            status_code=500, detail=f"Error de autenticación de Firebase: {e}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar la cuenta de profesor: {str(e)}"
        )

from datetime import datetime
from config import db, auth
from utils import send_email
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from models import (
    SearchTeacherSchema,
    ChangePasswordRequest,
    StudentsAmountSchema,
)

router = APIRouter()


@router.post("/changePassword")
async def change_teacher_password(change_password: ChangePasswordRequest):
    """
    Change teacher password.
    """
    try:
        auth.update_user(
            uid=change_password.user_id, password=change_password.new_password
        )
        doc_ref = db.collection("tDash_teacherData").document(change_password.user_id)
        doc_ref.update({"password": change_password.new_password})
        return JSONResponse(
            content={"message": "Contraseña cambiada exitosamente"}, status_code=200
        )
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error al cambiar la contraseña: {str(error)}"
        ) from error


@router.post("/getData")
async def get_teacher_data(teacher_data: SearchTeacherSchema):
    """
    Get teacher data.
    """
    teacher_id = teacher_data.teacherID
    try:
        teacher_ref = db.collection("tDash_teacherData").document(teacher_id)
        teacher_doc = teacher_ref.get()

        if teacher_doc.exists:
            teacher_data = teacher_doc.to_dict()

            for key, value in teacher_data.items():
                if isinstance(value, datetime):
                    teacher_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")

            subscription_data = {}
            if teacher_data.get("hasSuscription", True):
                subscription_data_query = (
                    teacher_ref.collection("tDash_subscriptionData")
                    .order_by("date_create", direction="DESCENDING")
                    .limit(1)
                )
                subscription_data_docs = subscription_data_query.get()

                if subscription_data_docs:
                    subscription_data = subscription_data_docs[0].to_dict()

                    renew_date = subscription_data.get("renewDate")
                    if isinstance(renew_date, datetime):
                        subscription_data["renewDate"] = renew_date.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    due_date = subscription_data.get("fechaVencimiento")
                    if isinstance(due_date, datetime):
                        subscription_data["fechaVencimiento"] = due_date.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                    create_date = subscription_data.get("date_create")
                    if isinstance(create_date, datetime):
                        subscription_data["date_create"] = create_date.strftime(
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
                detail=f"Datos del profesor con ID {teacher_id} no encontrados",
            )

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener datos del profesor: {str(error)}"
        ) from error


@router.post("/deleteAccount")
async def del_acc_teacher(teacher_data: SearchTeacherSchema):
    """
    Delete teacher account.
    """
    try:
        teacher_doc_ref = db.collection("tDash_teacherData").document(
            teacher_data.teacherID
        )
        teacher_doc = teacher_doc_ref.get()

        if not teacher_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el profesor con ID {teacher_data.teacherID}",
            )

        lst_classes = teacher_doc.to_dict().get("lstClasses")
        lst_students = teacher_doc.to_dict().get("lstStudents")

        if lst_classes:
            for class_id in lst_classes:
                class_ref = db.collection("tDash_class").document(class_id)
                class_ref.delete()

        if lst_students:
            for student_id in lst_students:
                if student_id:
                    student_ref = db.collection("tDash_students").document(student_id)
                    student_ref.delete()

            class_student_data_ref = db.collection("tDash_classStudentData")
            class_student_data_query = class_student_data_ref.where(
                "idStudent", "in", lst_students
            )
            class_student_data_docs = class_student_data_query.stream()

            if class_student_data_docs:
                for doc in class_student_data_docs:
                    student_id = doc.to_dict().get("idStudent")
                    if student_id:
                        doc_ref = class_student_data_ref.document(doc.id)
                        doc_ref.delete()

        auth.delete_user(teacher_data.teacherID)

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


@router.post("/studentsAmount")
async def get_students_amount(student_amount_req: StudentsAmountSchema):
    """
    Get the amount of students for a teacher.
    """
    try:
        teacher_ref = db.collection("tDash_teacherData").document(
            student_amount_req.teacherID
        )
        teacher_doc = teacher_ref.get()

        if teacher_doc.exists:
            teacher_data = teacher_doc.to_dict()
            lst_students = teacher_data.get("lstStudents", [])
            students_amount = len(lst_students)

            plan_id = student_amount_req.planID
            plan_doc = db.collection("tDash_plans").document(plan_id).get()

            if plan_doc.exists:
                plan_data = plan_doc.to_dict()
                max_students = plan_data.get("maxStudents")
                limit_students = students_amount == max_students

                return JSONResponse(
                    content={
                        "students_amount": students_amount,
                        "max_students": max_students,
                        "limit_students": limit_students,
                    },
                    status_code=200,
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Plan with ID {plan_id} not found",
                )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Teacher with ID {student_amount_req.teacherId} not found",
            )

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error getting students amount: {str(error)}"
        ) from error


@router.post("/validateSub")
async def validate_subscription(teacher_data: SearchTeacherSchema):
    """
    Validate teacher subscription.
    """
    try:
        teacher_ref = db.collection("tDash_teacherData").document(
            teacher_data.teacherID
        )
        teacher_doc = teacher_ref.get()

        if teacher_doc.exists:
            teacher_data = teacher_doc.to_dict()

            if teacher_data.get("hasSuscription", True):
                subscription_data_query = (
                    teacher_ref.collection("tDash_subscriptionData")
                    .order_by("date_create", direction="DESCENDING")
                    .limit(1)
                )
                subscription_data_docs = subscription_data_query.get()

                if subscription_data_docs:
                    subscription_data = subscription_data_docs[0].to_dict()
                    due_date = subscription_data.get("fechaVencimiento")
                    if isinstance(due_date, datetime):
                        due_date = due_date.strftime("%Y-%m-%d %H:%M:%S")
                    return JSONResponse(
                        content={"has_sub": True},
                        status_code=200,
                    )
                else:
                    return JSONResponse(
                        content={"has_sub": False},
                        status_code=200,
                    )
            else:
                return JSONResponse(
                    content={"has_sub": True},
                    status_code=200,
                )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Teacher with ID {teacher_data.teacherID} not found",
            )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating teacher subscription: {str(error)}",
        ) from error

import base64
from datetime import datetime
import pdfkit
from jinja2 import Template
from config import db, firestore
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get("/teachers")
async def get_list_teachers():
    teachers = []
    teacher_docs = db.collection("tDash_teacherData").stream()

    for teacher_doc in teacher_docs:
        teacher_data = teacher_doc.to_dict()
        print('teacher_data', teacher_data)
        teacher_id = teacher_doc.id
        teacher_name = teacher_data.get("name")
        teacher_lastname = teacher_data.get("lastname")

        # Check if tDash_subscriptionData subcollection exists in teacher_doc
        subscription_subcollection = db.collection("tDash_teacherData").document(teacher_id).collection("tDash_subscriptionData")
        subscription_docs = subscription_subcollection.stream()
        len_subs_docs= len(list(subscription_docs))
        print('len_subs_docs', len_subs_docs)
        if len_subs_docs > 0:
            # Get last subscription document from tdash_subscriptiondata subcollection
            last_subscription_doc = subscription_subcollection.order_by("date_create", direction=firestore.Query.DESCENDING).limit(1).get()
            print('last_subscription_doc', last_subscription_doc)
            last_subscription_data = last_subscription_doc[0].to_dict()
            print('suscriptiondata', last_subscription_data)
            teacher_subscription_id = last_subscription_data.get("id_plan")

            # Get subscription name from tdash_plans collection
            plan_doc = db.collection("tDash_plans").document(teacher_subscription_id).get()
            plan_data = plan_doc.to_dict()
            print('plan_data', plan_data)
            plan_name = plan_data.get("plan_name")
        else:
            plan_name = None

        # Get lstclasses and lst_students from tdash_teacherdata
        lst_classes = teacher_data.get("lstClasses")
        lst_classes = len(lst_classes) if isinstance(lst_classes, list) else 0

        lst_students = teacher_data.get("lstStudents")
        lst_students = len(lst_students) if isinstance(lst_students, list) else 0

        teacher = {
            "id": teacher_id,
            "name": teacher_name,
            "lastname": teacher_lastname,
            "subscription_name": plan_name,
            "lstclasses": lst_classes,
            "lst_students": lst_students
        }
        teachers.append(teacher)

    return teachers
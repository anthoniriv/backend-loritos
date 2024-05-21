# pylint: disable=import-error
from http.client import HTTPException
import os
import smtplib
from config import db, firestore
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from firebase_admin import auth
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

def is_email_verified(uid):
    try:
        user = auth.get_user(uid)

        return user.email_verified

    except Exception as e:
        print("Error:", e)
        return False


def send_email(to_email, subject, template_name, **kwargs):
    try:
        message = MIMEMultipart()
        message["From"] = SMTP_USERNAME
        message["To"] = to_email
        message["Subject"] = subject

        # Carga la plantilla HTML
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template(template_name)

        html_content = template.render(**kwargs)

        message.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP('smtp.gmail.com:587') as server:
            server.ehlo('Gmail')
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, message.as_string())

        return True

    except Exception as e:
        print("Error al enviar el correo electrónico:", e)
        return False


def send_email_verification(email):
    try:
        link = auth.generate_email_verification_link(email, action_code_settings=None)
        sendedEmail = send_email(
            email,
            "Verify your email",
            "emailVerification.html",
            link=link,
        )
        return True

    except Exception as e:
        print("Error:", e)
        return False

def render_html_template(template_name, data):
    try:
        # Obtener la ruta al directorio de las plantillas
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Crear el entorno de Jinja2
        env = Environment(loader=FileSystemLoader(templates_dir))

        # Obtener la plantilla
        template = env.get_template(template_name)

        # Renderizar la plantilla con los datos proporcionados
        html_content = template.render(**data)

        return html_content

    except Exception as e:
        raise RuntimeError(f"Error al renderizar la plantilla HTML: {str(e)}")

content_collection = db.collection("tDash_content")
student_progress_collection = db.collection("tDash_studentProgress")
class_student_data_collection = db.collection("tDash_classStudentData")
student_collection = db.collection("tDash_students")


def get_class_student_data(student_id: str, class_id: str):
    try:
        # Consultar el documento en la colección tDash_classStudentData
        query = class_student_data_collection.where("idStudent", "==", student_id).where("idClass", "==", class_id).limit(1).stream()

        for doc in query:
            return doc  # Retorna el primer documento que coincida

        raise HTTPException(status_code=404, detail="No se encontró el documento para el estudiante y la clase.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los datos del estudiante y la clase: {str(e)}")

def get_class_student_data(student_id: str, class_id: str):
    try:
        # Consultar el documento en la colección tDash_classStudentData
        query = class_student_data_collection.where("idStudent", "==", student_id).where("idClass", "==", class_id).limit(1).stream()

        for doc in query:
            return doc  # Retorna el primer documento que coincida

        raise HTTPException(status_code=404, detail="No se encontró el documento para el estudiante y la clase.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los datos del estudiante y la clase: {str(e)}")

def split_unit_and_game(current_unit: str):
    actualUnit, actualGame = current_unit.split("-")
    return int(actualUnit[2:]), int(actualGame)

def convert_seconds_to_days_and_months(seconds: int):
    # Calcular el número de días y meses
    days = seconds // 86400  # 24 * 60 * 60 (segundos en un día)
    months = days // 30  # Promedio de 30 días por mes

    return days, months

def get_student_name(student_id: str):
    try:
        # Obtener el nombre del estudiante de la colección tDash_students
        student_doc = student_collection.document(student_id).get().to_dict()
        student_name = student_doc.get("name", "")
        return student_name
    except Exception as e:
        # Manejar cualquier error que pueda ocurrir durante la obtención del nombre
        raise HTTPException(status_code=500, detail=f"Error al obtener el nombre del estudiante: {str(e)}")

def get_student_progress_data(student_id: str, class_id: str):
    try:
        # Obtener el nombre del estudiante
        student_name = get_student_name(student_id)

        student_progress_doc = student_progress_collection.document(student_id).get()
        class_student_data_doc = get_class_student_data(student_id, class_id)

        current_coins = class_student_data_doc.get("currentCoins")
        total_coins_win = class_student_data_doc.get("totalCoinsWin")

        if student_progress_doc.exists:
            class_subcollection = student_progress_doc.reference.collection(class_id)
            class_doc_query = class_subcollection.limit(1).stream()

            for class_doc in class_doc_query:
                current_unit = class_doc.get("idContent")
                timeSpend = class_doc.get("time")
                actualUnit, actualGame = split_unit_and_game(current_unit)

                content_docs = content_collection.where("typeContent", "==", 1).stream()

                total_documents = 0
                total_unidades = 0

                for content_doc in content_docs:
                    units_query = content_doc.reference.collection("tDash_ContentUnits").stream()
                    units_list = list(units_query)
                    total_units = len(units_list)
                    total_documents += total_units
                    total_unidades += 1

                # Convertir tiempo en segundos a meses y años
                days, months = convert_seconds_to_days_and_months(timeSpend)

                return {
                    "studentID": student_id,
                    "studentName": student_name,
                    "actualGame": actualGame,
                    "gamesTotal": total_documents,
                    "currentCoins": current_coins,
                    "totalCoinsWin": total_coins_win,
                    "timeSpend": timeSpend,
                    "timeSpendInDays": days,
                    "timeSpendInMonths": months,
                    "unitCompleted": actualUnit - 1,
                    "unitQuantity": total_unidades
                }

        else:
            raise HTTPException(status_code=404, detail="No se encontró el progreso del estudiante o la subcolección.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el progreso del estudiante: {str(e)}")

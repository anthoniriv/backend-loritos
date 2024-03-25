# pylint: disable=import-error
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from firebase_admin import auth
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

def is_email_verified(uid):
    try:
        user = auth.get_user(uid)

        return user.email_verified

    except auth.AuthError as e:
        print("Error de Firebase Auth:", e)
        return False

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

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, message.as_string())

        return True

    except Exception as e:
        print("Error al enviar el correo electrónico:", e)
        return False


def send_email_verification(email, userName):
    try:
        link = auth.generate_email_verification_link(email, action_code_settings=None)
        sendedEmail = send_email(
            email,
            "Verify your email",
            "emailVerification.html",
            link=link,
            user_name=userName,
        )
        print(sendedEmail)
        return True

    except auth.AuthError as e:
        print("Error de Firebase Auth:", e)
        return False

    except Exception as e:
        print("Error:", e)
        return False

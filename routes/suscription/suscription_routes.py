from fastapi import APIRouter
from typing import Optional
from config import db, stripe

import stripe
from datetime import datetime, timedelta
from models import (
    CancelSuscription,
    SessionCheckoutCreate,
    SessionStripeCheck,
    SubscribeTeacher,
)
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import HTTPException

from utils import send_email

router = APIRouter()


@router.post("/create-checkout-session")
async def create_checkout_session(sessionCheckoutCreate: SessionCheckoutCreate):

    try:
        session = stripe.checkout.Session.create(
            success_url="http://localhost:4200/subscription/success?id_plan="
            + sessionCheckoutCreate.idPlan,
            cancel_url="http://localhost:4200/subscription/canceled",
            line_items=[
                {
                    "price": sessionCheckoutCreate.stripePriceId,
                    "quantity": 1,
                },
            ],
            mode="subscription",
        )

        session_id = session.id
        print("session_id:", session_id)

        teacher_ref = db.collection("tDash_teacherData").document(
            sessionCheckoutCreate.idTeacher
        )
        teacher_data = teacher_ref.get()
        if not teacher_data.exists:
            raise HTTPException(status_code=404, detail="ID de maestro no encontrado")

        id_teacher = teacher_data.id

        subscription_data = {
            "amount_total": sessionCheckoutCreate.amountTotal,
            "id_plan": sessionCheckoutCreate.idPlan,
            "paid_sub": sessionCheckoutCreate.paid_sub,
            "status": sessionCheckoutCreate.status,
            "stripe_session_id": session_id,
            "date_create": datetime.now(),
        }

        subscription_ref = (
            db.collection("tDash_teacherData")
            .document(id_teacher)
            .collection("tDash_subscriptionData")
            .document()
        )
        subscription_ref.set(subscription_data)

        return JSONResponse(content={"url": session.url, "session_id": session_id})

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Error de Stripe: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@router.post("/check-stripe-session")
async def stripe_session(sessionStripeCheck: SessionStripeCheck):
    try:
        user = {
            "stripe_session_id": sessionStripeCheck.stripe_session_id,
            "paid_sub": sessionStripeCheck.paid_sub,
        }

        if not user["stripe_session_id"] or user["paid_sub"]:
            return PlainTextResponse(content="fail")

        session = stripe.checkout.Session.retrieve(user["stripe_session_id"])
        suscription = stripe.Subscription.retrieve(session["subscription"])
        invoice = stripe.Invoice.retrieve(session["invoice"])
        activeSus = suscription["plan"]["active"]
        urlInvoice = invoice["invoice_pdf"]
        renewDate = invoice["lines"]["data"][0]["period"]["end"]

        if session and session.status == "complete":
            teacher_data_ref = db.collection("tDash_teacherData").document(
                sessionStripeCheck.userId
            )
            teacher_data = teacher_data_ref.get().to_dict()

            subscription_data_query = (
                teacher_data_ref.collection("tDash_subscriptionData")
                .where("stripe_session_id", "==", user["stripe_session_id"])
                .limit(1)
            )

            subscription_data_docs = subscription_data_query.stream()

            for doc in subscription_data_docs:
                print("DOCCCID", doc.id)
                docID = doc.id
                subscription_data = doc.to_dict()
                break
            else:
                subscription_data = {}

            # Actualizar los datos del usuario en Firebase
            teacher_data_ref.update({"hasSuscription": True})

            # Crear un nuevo objeto JSON con todas las variables asignadas
            response_data = {
                "success": "true",
                "suscriptionId": session["subscription"],
                "urlInvoice": urlInvoice,
                "renewDate": renewDate,
                "activeSus": activeSus,
                "status": session.status,
                "subscriptionData": subscription_data,
            }

            subscription_data_ref = teacher_data_ref.collection(
                "tDash_subscriptionData"
            ).document(docID)
            subscription_data_ref.set(
                {
                    "stripe_session_id": user["stripe_session_id"],
                    "subscriptionId": session["subscription"],
                    "invoiceId": session["invoice"],
                    "paid_sub": activeSus,
                    "status": session.status,
                    "renewDate": datetime.fromtimestamp(renewDate),
                },
                merge=True,
            )

            sendedEmail = send_email(
                teacher_data["email"],
                "Suscription Owned",
                "newSuscription.html",
                subscriptionId=session["subscription"],
                renewDate=renewDate,
                activeSus=activeSus,
                urlInvoice=urlInvoice,
            )

            print(sendedEmail)

            return JSONResponse(content=response_data, status_code=200)
        else:
            teacher_data_ref = db.collection("tDash_teacherData").document(
                sessionStripeCheck.userId
            )
            subscription_data_ref = teacher_data_ref.collection(
                "tDash_subscriptionData"
            )
            subscription_data_docs = subscription_data_ref.stream()

            for doc in subscription_data_docs:
                doc.reference.delete()

            return JSONResponse(
                content={"message": "Cancelación exitosa"}, status_code=200
            )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Error de Stripe: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@router.post("/cancel-stripe-suscription")
async def cancel_suscription(cancelSuscription: CancelSuscription):
    try:
        teacher_data_ref = db.collection("tDash_teacherData").document(
            cancelSuscription.userId
        )

        teacher_data = teacher_data_ref.get().to_dict()

        teacher_data_doc = teacher_data_ref.get()
        if not teacher_data_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el documento para el ID {cancelSuscription.userId}",
            )

        subscription_data_query = teacher_data_ref.collection(
            "tDash_subscriptionData"
        ).limit(1)

        subscription_data_docs = subscription_data_query.get()

        if not subscription_data_docs:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron datos de suscripción para el usuario",
            )

        for doc in subscription_data_docs:
            idDoc = doc.id
            subscription_data = doc.to_dict()
            break
        else:
            subscription_data = {}

        print("asdasdas", subscription_data)

        if (
            "id_plan" in subscription_data
        ):  # Verifica si hay datos en subscription_data
            if subscription_data.get("free_plan"):
                teacher_data_ref.update({"hasSuscription": False})
            else:
                print("asdasdas2", subscription_data["subscriptionId"])
                stripe.Subscription.cancel(subscription_data["subscriptionId"])
                # Delete the subscription data document
                # teacher_data_ref.collection("tDash_subscriptionData").document(idDoc).delete()

                sendedEmail = send_email(
                    teacher_data["email"],
                    "Suscription Cancelled",
                    "canceledSuscription.html",
                )

                print(sendedEmail)

                # Actualizar el valor de 'hasSuscription' a False después de cancelar la suscripción
                teacher_data_ref.update({"hasSuscription": False})
        else:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron datos de suscripción para el usuario",
            )

        return JSONResponse(
            content={"message": "Suscripción cancelada correctamente"}, status_code=200
        )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Error de Stripe: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@router.post("/webhook")
async def payment_webhook(webhook: Optional[dict] = None):
    try:
        if webhook["type"] == "invoice.payment_failed":
            if webhook["type"] == "invoice.payment_failed":
                subscription_id = webhook["data"]["object"]["id"]
                if webhook["data"]["object"]["attempt_count"] == 1:
                    print("attempt_count", 1)
                    return JSONResponse(content={"message": "Webhook procesado correctamente"}, status_code=200)
                elif webhook["data"]["object"]["attempt_count"] == 4:
                    print("attempt_count", 4)
                    return JSONResponse(content={"message": "Suscripción cancelada correctamente"}, status_code=200)
                else:
                    return JSONResponse(content={"message": "Evento recibido pero no se requiere acción"}, status_code=200)
            else:
                return JSONResponse(content={"message": "Evento no relacionado con pago fallido, no se requiere acción"}, status_code=200)
        elif webhook["type"] == "customer.subscription.deleted":
            print("Suscripción cancelada correctamente", webhook)
            if webhook["data"]["object"]["cancellation_details"]["reason"] == "payment_failed":
                user = stripe.Customer.retrieve(webhook["data"]["object"]["customer"])
                print("Email subscripcion", user["email"])
                print("Cancelado por error de metodo de pago")
                teacher_docs = db.collection("tDash_teacherData").where("email", "==", user["email"]).limit(1).stream()
                print("Usuario obtenido de bd", teacher_docs)
                for doc in teacher_docs:
                    print("documento", teacher_docs)
                    doc.reference.update({"hasSuscription": False})
                if teacher_docs:
                    teacher_ref = doc.reference
                    subscription_ref = teacher_ref.collection("tDash_subscriptionData")
                    batch = db.batch()
                    subscription_docs = subscription_ref.stream()
                    for sub_doc in subscription_docs:
                        batch.delete(sub_doc.reference)
                    batch.commit()
        else:
            print("No se proporcionaron datos en el webhook.")
        return JSONResponse(content={"message": "Webhook recibido correctamente"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@router.get("/plans")
async def get_subscription_plans_route(plan_id: Optional[str] = None):
    try:
        # Consultar la colección de planes
        plans_ref = db.collection("tDash_plans")

        if plan_id:
            # Obtener el documento del plan con el ID especificado
            plan_doc = plans_ref.document(plan_id).get()
            if plan_doc.exists:
                # Devolver el plan con el ID especificado como un objeto
                return JSONResponse(
                    content={"plan": plan_doc.to_dict()}, status_code=200
                )
            else:
                # Si no se encuentra el plan con el ID especificado, devolver un error
                raise HTTPException(
                    status_code=404, detail=f"No se encontró el plan con ID {plan_id}"
                )
        else:
            # Inicializar listas para planes mensuales, anuales y gratuitos
            plans_mensuales = []
            plans_anuales = []
            plans_gratuitos = []

            # Iterar sobre los documentos de la colección
            for doc in plans_ref.stream():
                plan_data = doc.to_dict()
                type_plan = plan_data.get("type_plan")
                order = plan_data.get("order")

                # Determinar la lista en la que agregar el plan según su tipo
                if type_plan == 0:
                    plans_gratuitos.append(plan_data)
                elif type_plan == 1:
                    plans_mensuales.append(plan_data)
                elif type_plan == 2:
                    plans_anuales.append(plan_data)

            # Ordenar las listas según el valor de "order"
            plans_mensuales.sort(key=lambda x: x.get("order", float("inf")))
            plans_anuales.sort(key=lambda x: x.get("order", float("inf")))
            plans_gratuitos.sort(key=lambda x: x.get("order", float("inf")))

            # Devolver los planes organizados como listas
            return JSONResponse(
                content={
                    "plans_mensuales": plans_mensuales,
                    "plans_anuales": plans_anuales,
                    "plans_gratuitos": plans_gratuitos,
                },
                status_code=200,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los planes de suscripción: {str(e)}",
        )


@router.post("/freeSubscribeTeacher")
async def free_subscribe_teacher(subscribe_teacher: SubscribeTeacher):
    """
    Subscribe a teacher to a free plan.

    Args:
        subscribe_teacher (SubscribeTeacher): The subscription details.

    Returns:
        JSONResponse: The response message.
    """
    try:
        # Check if there is an existing subscription with free_plan = True
        existing_subscription = db.collection("tDash_teacherData").document(subscribe_teacher.teacherID).collection("tDash_subscriptionData").where("free_plan", "==", True).get()
        if existing_subscription:
            raise HTTPException(status_code=400, detail="Ya existe una suscripción gratuita para este profesor")

        # Get the plan details from tDash_plans collection
        plan_doc = db.collection("tDash_plans").document(subscribe_teacher.planID).get()
        if not plan_doc.exists:
            raise HTTPException(
                status_code=404, detail=f"No se encontró el plan con ID {subscribe_teacher.planID}"
            )

        plan_data = plan_doc.to_dict()

        # Calculate the expiration date (30 days from the current date)
        expiration_date = datetime.now() + timedelta(days=30)

        # Create the subscription data
        subscription_data = {
            "amount_total": plan_data["plan_price"],
            "id_plan": subscribe_teacher.planID,
            "status": "complete",
            "fechaVencimiento": expiration_date,
            "free_plan": True,
            "date_create": datetime.now(),
        }

        # Create a new document in tDash_subscriptionData subcollection
        subscription_ref = (
            db.collection("tDash_teacherData")
            .document(subscribe_teacher.teacherID)
            .collection("tDash_subscriptionData")
            .document()
        )
        subscription_ref.set(subscription_data)

        # Update the hasSuscription value to True in tDash_teacherData collection
        teacher_ref = db.collection("tDash_teacherData").document(subscribe_teacher.teacherID)
        teacher_ref.update({"hasSuscription": True})

        return JSONResponse(
            content={"message": "Subscripción exitosa"}, status_code=200
        )

    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error interno: {error}") from error

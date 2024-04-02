import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase
import stripe
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import credentials, auth, firestore

# Configurar Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

firebaseConfig = {
    "apiKey": "AIzaSyC-qfY3Q-4R7Nu1pGpqehfSzZmQpOo90BE",
    "authDomain": "lws-dev-f4ff0.firebaseapp.com",
    "databaseURL": "https://lws-dev-f4ff0-default-rtdb.firebaseio.com",
    "projectId": "lws-dev-f4ff0",
    "storageBucket": "lws-dev-f4ff0.appspot.com",
    "messagingSenderId": "580870653149",
    "appId": "1:580870653149:web:e172426c24008c45e24734",
    "measurementId": "G-390SYCT8YY",
}

firebase = pyrebase.initialize_app(firebaseConfig)
fb_storage = firebase.storage()
db = firestore.client()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Configurar Stripe
stripe.api_key = "sk_test_51OWfnCE2m10pao8Wef972QeOaQwARpi6KttQreupbOlAJr88Wd8h7bR3H6dVxlzCzpzks7QUtOH2QtyVp6O6dslv00ixss1JNC"


SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USERNAME = "devteampe@gmail.com"
SMTP_PASSWORD = "leaj tdaz vnfg teeb"

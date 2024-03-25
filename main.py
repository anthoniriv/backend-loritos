import uvicorn
from firebase_admin import auth
from fastapi import FastAPI, Depends
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from routes.auth.auth_routes import router as auth_router
from routes.suscription.suscription_routes import router as suscription_router
from routes.common.common_routes import router as common_router
from routes.teacher.teacher_routes import router as teacher_router
from routes.classes.classes_routes import router as classes_router
from routes.student.student_routes import router as student_router
from routes.content.content_routes import router as content_router
from routes.contact.contact_routes import router as contact_router

app = FastAPI(
    description="This is a loritos backend", title="LoritosBackend", docs_url="/"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify your allowed origins here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# APIS
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        user = auth.verify_id_token(token)
        return user
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación expirado")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticación inválido")


app.include_router(auth_router, prefix="/dashboard/auth", tags=["Auth"])
app.include_router(suscription_router, prefix="/dashboard/suscription", tags=["Suscription"])
app.include_router(common_router, prefix="/dashboard/common", tags=["Common"])
app.include_router(teacher_router, prefix="/dashboard/teacher", tags=["Teacher"])
app.include_router(classes_router, prefix="/dashboard/classes", tags=["Classes"])
app.include_router(student_router, prefix="/dashboard/students", tags=["Students"])
app.include_router(content_router, prefix="/dashboard/content", tags=["Content"])
app.include_router(contact_router, prefix="/dashboard/contact", tags=["Contact"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
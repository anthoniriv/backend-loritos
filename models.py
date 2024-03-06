from pydantic import BaseModel


class SingUpSchema(BaseModel):
    email:str
    password:str

    class Config:
        schema_extra = {
            "example": {
                "email": "example@example.com",
                "password": "password123"
            }
        }

class LoginSchema(BaseModel):
    email:str
    password:str

    class Config:
        schema_extra = {
            "example": {
                "email": "example@example.com",
                "password": "password123"
            }
        }

class SearchTeacherSchema(BaseModel):
    teacherID: str

class GetContent(BaseModel):
    contentTypeId: int
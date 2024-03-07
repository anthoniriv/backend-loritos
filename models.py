from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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

class AddStudentRequest(BaseModel):
    names: List[str]

class EditStudentRequest(BaseModel):
    id: str
    name: Optional[str] = None
    avatarCode: Optional[int] = None
    currentCoins: Optional[int] = None
    totalCoinsWin: Optional[int] = None
    lastConnection: Optional[datetime] = None
    lstProgress: Optional[List[str]] = None

    class Config:
        orm_mode = True
        pre = True

class DeleteStudentRequest(BaseModel):
    id: str
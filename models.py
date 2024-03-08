from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SingUpSchema(BaseModel):
    name:str
    lastName:str
    email:str
    password:str

class LoginSchema(BaseModel):
    email:str
    password:str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

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

class GetStudentDataRequest(BaseModel):
    student_id: str

class ContactMessage(BaseModel):
    email_content: str
    name: str
    last_name: str
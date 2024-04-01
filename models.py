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
    user_id: str
    new_password: str

class ForgotPassword(BaseModel):
    email: str
class SearchTeacherSchema(BaseModel):
    teacherID: str

class GetContent(BaseModel):
    contentTypeId: str

class AddStudentRequest(BaseModel):
    names: List[str]
    teacherId: str

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
    ids: str
    teacherId: str

class GetStudentDataRequest(BaseModel):
    student_id: str

class ContactMessage(BaseModel):
    email_content: str

class SessionCheckoutCreate(BaseModel):
    idTeacher: str
    stripePriceId:str
    amountTotal: int
    idPlan: str
    paid_sub: bool
    status: str

class SessionStripeCheck(BaseModel):
    userId: str
    stripe_session_id:str
    paid_sub: bool

class CancelSuscription(BaseModel):
    userId: str

class ClassesAdd(BaseModel):
    name_class: str
    type_class: str
    idTeacher: str

class ClassId(BaseModel):
    id_class: str

class StudentClassAdd(BaseModel):
    class_id: str
    student_ids: List[str]

class StudentClassDel(BaseModel):
    class_id: str
    student_id: List[str]

class UnitsClassAdd(BaseModel):
    class_id: str
    unit_ids: List[str]

class UnitClassDel(BaseModel):
    class_id: str
    unit_id: str

class StudentProgressRequest(BaseModel):
    idStudent: str
    idClass: str

class IdClass(BaseModel):
    idClass: str

class EditClassRequest(BaseModel):
    idClass: str
    className: str
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class GetProgressRequest(BaseModel):
    studentID:str
    classID:str
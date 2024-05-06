from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProgressClassRequest(BaseModel):
    classID:str
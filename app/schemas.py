from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class SchoolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(pattern=r'^[a-z0-9-]{3,80}$')
    admin_email: EmailStr
    admin_password: str = Field(min_length=12, max_length=128)

class LoginRequest(BaseModel):
    school_slug: str
    email: EmailStr
    password: str

class StudentCreate(BaseModel):
    enrollment: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    classroom: str = Field(min_length=1, max_length=60)
    shift: str = Field(min_length=1, max_length=30)

class StudentOut(StudentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    active: bool

class MealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    student_id: str
    meal_date: date
    entered_at: datetime
    exited_at: datetime | None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'

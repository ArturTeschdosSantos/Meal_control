import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def new_id():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class School(Base):
    __tablename__ = 'schools'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default='operator', nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint('school_id', 'email', name='uq_user_school_email'),)

class Student(Base):
    __tablename__ = 'students'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True, nullable=False)
    enrollment: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    classroom: Mapped[str] = mapped_column(String(60), nullable=False)
    shift: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint('school_id', 'enrollment', name='uq_student_school_enrollment'),)

class Meal(Base):
    __tablename__ = 'meals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True, nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True, nullable=False)
    meal_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entered_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    exited_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    __table_args__ = (UniqueConstraint('student_id', 'meal_date', name='uq_meal_student_date'),)

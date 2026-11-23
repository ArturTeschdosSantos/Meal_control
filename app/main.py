from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import get_db
from .models import Meal, School, Student, User
from .schemas import LoginRequest, MealOut, SchoolCreate, StudentCreate, StudentOut, TokenOut
from .security import admin_only, create_token, current_user, hash_password, verify_password
from .settings import settings

app = FastAPI(title='Meal Control API', version='0.1.0', description='Gestão de refeições escolares multi-instituição')

def local_date() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/v1/schools', status_code=201)
def create_school(data: SchoolCreate, db: Session = Depends(get_db)):
    # MVP: bootstrap público para avaliação local. Proteger antes de expor na internet.
    if db.scalar(select(School).where(School.slug == data.slug)):
        raise HTTPException(409, 'Identificador da escola já utilizado')
    school = School(name=data.name, slug=data.slug)
    db.add(school)
    db.flush()
    user = User(school_id=school.id, email=str(data.admin_email).lower(),
                password_hash=hash_password(data.admin_password), role='admin')
    db.add(user)
    db.commit()
    return {'id': school.id, 'slug': school.slug, 'message': 'Escola e administrador criados'}

@app.post('/v1/auth/login', response_model=TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    school = db.scalar(select(School).where(School.slug == data.school_slug, School.active.is_(True)))
    user = db.scalar(select(User).where(User.school_id == school.id, User.email == str(data.email).lower())) if school else None
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, 'Credenciais inválidas')
    return TokenOut(access_token=create_token(user))

@app.post('/v1/students', response_model=StudentOut, status_code=201)
def create_student(data: StudentCreate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    student = Student(school_id=user.school_id, **data.model_dump())
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Matrícula já cadastrada nesta escola')
    db.refresh(student)
    return student

@app.get('/v1/students', response_model=list[StudentOut])
def list_students(user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return db.scalars(select(Student).where(Student.school_id == user.school_id).order_by(Student.name).offset(offset).limit(limit)).all()

@app.post('/v1/meals/{student_id}/entry', response_model=MealOut, status_code=201)
def entry(student_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    student = db.scalar(select(Student).where(Student.id == student_id, Student.school_id == user.school_id, Student.active.is_(True)))
    if not student:
        raise HTTPException(404, 'Aluno ativo não encontrado nesta escola')
    meal = Meal(school_id=user.school_id, student_id=student_id, meal_date=local_date(), entered_by=user.id)
    db.add(meal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Almoço já registrado para este aluno hoje')
    db.refresh(meal)
    return meal

@app.post('/v1/meals/{student_id}/exit', response_model=MealOut)
def exit_meal(student_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meal = db.scalar(select(Meal).where(Meal.school_id == user.school_id, Meal.student_id == student_id,
                                       Meal.meal_date == local_date()).with_for_update())
    if not meal:
        raise HTTPException(404, 'Não existe entrada registrada hoje para este aluno')
    if meal.exited_at is not None:
        raise HTTPException(409, 'Saída já registrada')
    meal.exited_at = datetime.now(timezone.utc)
    meal.exited_by = user.id
    db.commit()
    db.refresh(meal)
    return meal

@app.get('/v1/reports/daily')
def daily_report(day: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    day = day or local_date()
    total = db.scalar(select(func.count(Meal.id)).where(Meal.school_id == user.school_id, Meal.meal_date == day)) or 0
    exited = db.scalar(select(func.count(Meal.id)).where(Meal.school_id == user.school_id, Meal.meal_date == day, Meal.exited_at.is_not(None))) or 0
    return {'date': day, 'lunches_served': total, 'exits': exited, 'inside': total - exited}

@app.get('/v1/reports/period')
def period_report(start: date, end: date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if end < start or (end - start).days > 366:
        raise HTTPException(422, 'Período inválido (máximo 366 dias)')
    rows = db.execute(select(Meal.meal_date, func.count(Meal.id)).where(Meal.school_id == user.school_id,
                      Meal.meal_date >= start, Meal.meal_date <= end).group_by(Meal.meal_date).order_by(Meal.meal_date)).all()
    return {'start': start, 'end': end, 'total_lunches': sum(n for _, n in rows),
            'days': [{'date': d, 'lunches': n} for d, n in rows]}

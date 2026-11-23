from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db import Base, get_db
from app.main import app

engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
Session = sessionmaker(engine, expire_on_commit=False)

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def override_db():
    with Session() as db:
        yield db

app.dependency_overrides[get_db] = override_db
client = TestClient(app)

def school(slug):
    response = client.post('/v1/schools', json={'name': 'Escola '+slug, 'slug': slug, 'admin_email': 'admin@example.com', 'admin_password': 'secret-123456789'})
    assert response.status_code == 201, response.text
    response = client.post('/v1/auth/login', json={'school_slug': slug, 'email': 'admin@example.com', 'password': 'secret-123456789'})
    assert response.status_code == 200, response.text
    return {'Authorization': 'Bearer '+response.json()['access_token']}

def student(headers, enrollment='001'):
    response = client.post('/v1/students', headers=headers, json={'enrollment': enrollment, 'name':'Ana Silva', 'classroom':'3A','shift':'tarde'})
    assert response.status_code == 201, response.text
    return response.json()['id']

def test_meal_lifecycle_prevents_duplicates_and_reports():
    headers = school('escola-um')
    sid = student(headers)
    assert client.post(f'/v1/meals/{sid}/exit', headers=headers).status_code == 404
    entered = client.post(f'/v1/meals/{sid}/entry', headers=headers)
    assert entered.status_code == 201, entered.text
    assert client.post(f'/v1/meals/{sid}/entry', headers=headers).status_code == 409
    assert client.get('/v1/reports/daily', headers=headers).json()['lunches_served'] == 1
    assert client.post(f'/v1/meals/{sid}/exit', headers=headers).status_code == 200
    assert client.post(f'/v1/meals/{sid}/exit', headers=headers).status_code == 409
    report = client.get('/v1/reports/daily', headers=headers).json()
    assert report['exits'] == 1 and report['inside'] == 0

def test_tenant_isolation():
    a = school('escola-a')
    b = school('escola-b')
    sid = student(a)
    assert client.get('/v1/students', headers=b).json() == []
    assert client.post(f'/v1/meals/{sid}/entry', headers=b).status_code == 404
    assert client.post(f'/v1/meals/{sid}/entry', headers=a).status_code == 201
    assert client.get('/v1/reports/daily', headers=b).json()['lunches_served'] == 0

def test_auth_required_and_enrollment_unique_per_school():
    a = school('escola-c')
    student(a, '123')
    response = client.post('/v1/students', headers=a, json={'enrollment':'123','name':'Outra Pessoa', 'classroom':'2B','shift':'manha'})
    assert response.status_code == 409
    assert client.get('/v1/students').status_code in (401, 403)

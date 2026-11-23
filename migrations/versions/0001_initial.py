"""Initial schema for schools, users, students and meals.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('schools', sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(160), nullable=False), sa.Column('slug', sa.String(80), nullable=False), sa.Column('active', sa.Boolean(), nullable=False))
    op.create_index('ix_schools_slug', 'schools', ['slug'], unique=True)
    op.create_table('users', sa.Column('id', sa.String(36), primary_key=True), sa.Column('school_id', sa.String(36), sa.ForeignKey('schools.id'), nullable=False), sa.Column('email', sa.String(254), nullable=False), sa.Column('password_hash', sa.String(255), nullable=False), sa.Column('role', sa.String(20), nullable=False), sa.Column('active', sa.Boolean(), nullable=False), sa.UniqueConstraint('school_id','email', name='uq_user_school_email'))
    op.create_index('ix_users_school_id','users',['school_id'])
    op.create_table('students', sa.Column('id', sa.String(36), primary_key=True), sa.Column('school_id', sa.String(36), sa.ForeignKey('schools.id'), nullable=False), sa.Column('enrollment', sa.String(40), nullable=False), sa.Column('name', sa.String(160), nullable=False), sa.Column('classroom', sa.String(60), nullable=False), sa.Column('shift', sa.String(30), nullable=False), sa.Column('active', sa.Boolean(), nullable=False), sa.UniqueConstraint('school_id','enrollment', name='uq_student_school_enrollment'))
    op.create_index('ix_students_school_id','students',['school_id'])
    op.create_table('meals', sa.Column('id', sa.String(36), primary_key=True), sa.Column('school_id', sa.String(36), sa.ForeignKey('schools.id'), nullable=False), sa.Column('student_id', sa.String(36), sa.ForeignKey('students.id'), nullable=False), sa.Column('meal_date', sa.Date(), nullable=False), sa.Column('entered_at', sa.DateTime(timezone=True), nullable=False), sa.Column('exited_at', sa.DateTime(timezone=True)), sa.Column('entered_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('exited_by', sa.String(36), sa.ForeignKey('users.id')), sa.UniqueConstraint('student_id','meal_date', name='uq_meal_student_date'))
    op.create_index('ix_meals_school_id','meals',['school_id'])
    op.create_index('ix_meals_student_id','meals',['student_id'])
    op.create_index('ix_meals_meal_date','meals',['meal_date'])

def downgrade():
    op.drop_table('meals')
    op.drop_table('students')
    op.drop_table('users')
    op.drop_table('schools')

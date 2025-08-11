from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Building(db.Model):
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    building_code = db.Column(db.String(10), unique=True, nullable=False)  # مثل K7
    building_name = db.Column(db.String(100), nullable=True)
    total_rooms = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    rooms = db.relationship('Room', backref='building', lazy=True, cascade='all, delete-orphan')

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    room_type = db.Column(db.String(20), nullable=False)  # ثنائي، ثلاثي، رباعي
    total_beds = db.Column(db.Integer, nullable=False)
    price_per_bed = db.Column(db.Float, nullable=False)
    monthly_revenue = db.Column(db.Float, nullable=False)
    room_code = db.Column(db.String(20), unique=True, nullable=True)  # مثل K71
    status = db.Column(db.String(20), default='available')  # available, partially_occupied, fully_occupied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    bed_assignments = db.relationship('BedAssignment', backref='room', lazy=True, cascade='all, delete-orphan')
    
    @property
    def occupied_beds(self):
        return BedAssignment.query.filter_by(room_id=self.id, status='active').count()
    
    @property
    def available_beds(self):
        return self.total_beds - self.occupied_beds

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    guardian_id = db.Column(db.String(50), nullable=True)
    university = db.Column(db.String(100), nullable=True)
    contract_start = db.Column(db.Date, nullable=True)
    contract_end = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    bed_assignments = db.relationship('BedAssignment', backref='student', lazy=True)
    financial_records = db.relationship('FinancialRecord', backref='student', lazy=True)

class BedAssignment(db.Model):
    __tablename__ = 'bed_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    bed_number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, ended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FinancialRecord(db.Model):
    __tablename__ = 'financial_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month_for = db.Column(db.String(20), nullable=False)  # مثل "2025-08"
    payment_method = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # maintenance, utilities, other
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    receipt_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OverduePayment(db.Model):
    __tablename__ = 'overdue_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    month_due = db.Column(db.String(20), nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    days_overdue = db.Column(db.Integer, nullable=False, default=0)
    last_reminder = db.Column(db.Date, nullable=True)
    follow_up_status = db.Column(db.String(20), default='new')  # new, reminded, collected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقة
    student_ref = db.relationship('Student', backref='overdue_payments')


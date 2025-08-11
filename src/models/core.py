from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from models.user import db

class Building(db.Model):
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    building_code = db.Column(db.String(10), unique=True, nullable=False)  # K6, K7
    building_name = db.Column(db.String(100), nullable=True)
    total_rooms = db.Column(db.Integer, nullable=False, default=13)
    total_beds = db.Column(db.Integer, nullable=False, default=26)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    rooms = db.relationship('Room', backref='building', lazy=True, cascade='all, delete-orphan')
    beds = db.relationship('Bed', backref='building', lazy=True, cascade='all, delete-orphan')

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, ..., 13
    room_type = db.Column(db.String(20), nullable=False, default='double')  # single, double, triple, quad
    total_beds = db.Column(db.Integer, nullable=False, default=2)  # مرونة في عدد الأسرة
    price_per_bed = db.Column(db.Float, nullable=False, default=55.0)
    monthly_revenue = db.Column(db.Float, nullable=False)
    room_code = db.Column(db.String(20), unique=True, nullable=False)  # K601, K602, K701, K702
    status = db.Column(db.String(20), default='available')  # available, partially_occupied, fully_occupied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    beds = db.relationship('Bed', backref='room', lazy=True, cascade='all, delete-orphan')
    bed_assignments = db.relationship('BedAssignment', backref='room', lazy=True, cascade='all, delete-orphan')
    
    @property
    def occupied_beds(self):
        return Bed.query.filter_by(room_id=self.id, status='occupied').count()
    
    @property
    def available_beds(self):
        return Bed.query.filter_by(room_id=self.id, status='available').count()
    
    def update_monthly_revenue(self):
        """تحديث الإيرادات الشهرية بناءً على عدد الأسرة والسعر"""
        self.monthly_revenue = self.total_beds * self.price_per_bed

class Bed(db.Model):
    __tablename__ = 'beds'
    
    id = db.Column(db.Integer, primary_key=True)
    bed_code = db.Column(db.String(10), unique=True, nullable=False)  # K6111, K6112, K7111, K7112
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    bed_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4 (حسب عدد الأسرة في الغرفة)
    price = db.Column(db.Float, nullable=False, default=55.0)
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    bed_assignments = db.relationship('BedAssignment', backref='bed', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_bed_code(building_code, room_number, bed_number):
        """توليد رمز السرير بنظام KxYYZ"""
        return f"{building_code}{room_number:02d}{bed_number}"

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    national_id = db.Column(db.String(20), nullable=True)  # رقم الهوية
    guardian_phone = db.Column(db.String(20), nullable=True)  # رقم هاتف الأقارب
    university = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(20), nullable=False, default='student')  # student, employee
    contract_start = db.Column(db.Date, nullable=True)
    contract_end = db.Column(db.Date, nullable=True)
    rent_amount = db.Column(db.Float, nullable=False, default=55.0)  # قيمة الإيجار
    security_deposit = db.Column(db.Float, nullable=False, default=100.0)  # مبلغ التأمين
    deposit_status = db.Column(db.String(20), default='paid')  # paid, returned
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    bed_assignments = db.relationship('BedAssignment', backref='student', lazy=True)
    payments = db.relationship('Payment', backref='student', lazy=True)
    overdue_payments = db.relationship('OverduePayment', backref='student', lazy=True)
    
    @property
    def current_bed(self):
        """الحصول على السرير الحالي للطالبة"""
        assignment = BedAssignment.query.filter_by(
            student_id=self.id, 
            status='active'
        ).first()
        return assignment.bed if assignment else None
    
    @property
    def total_balance(self):
        """حساب الرصيد الإجمالي (المدفوع - المستحق)"""
        total_paid = sum([p.amount for p in self.payments if p.status == 'confirmed'])
        # حساب المستحق بناءً على فترة الإقامة
        # يمكن تطوير هذا لاحقاً
        return total_paid

class BedAssignment(db.Model):
    __tablename__ = 'bed_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    bed_id = db.Column(db.Integer, db.ForeignKey('beds.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, ended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(50), nullable=False, default='rent')  # rent, deposit, penalty
    payment_date = db.Column(db.Date, nullable=False)
    month_year = db.Column(db.String(10), nullable=True)  # "2025-08" للإيجارات الشهرية
    payment_method = db.Column(db.String(50), nullable=True, default='cash')  # cash, transfer, card
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, pending, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # maintenance, utilities, supplies, other
    expense_date = db.Column(db.Date, nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    receipt_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OverduePayment(db.Model):
    __tablename__ = 'overdue_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    month_due = db.Column(db.String(10), nullable=False)  # "2025-08"
    amount_due = db.Column(db.Float, nullable=False)
    days_overdue = db.Column(db.Integer, nullable=False, default=0)
    last_reminder = db.Column(db.Date, nullable=True)
    follow_up_status = db.Column(db.String(20), default='new')  # new, reminded, collected, written_off
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Archive(db.Model):
    __tablename__ = 'archive'
    
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    national_id = db.Column(db.String(20), nullable=True)
    bed_code = db.Column(db.String(10), nullable=False)  # آخر سرير كانت تشغله
    departure_date = db.Column(db.Date, nullable=False)
    total_paid = db.Column(db.Float, default=0.0)
    total_due = db.Column(db.Float, default=0.0)
    final_balance = db.Column(db.Float, default=0.0)  # موجب = لها، سالب = عليها
    security_deposit = db.Column(db.Float, default=0.0)
    deposit_returned = db.Column(db.Boolean, default=False)
    reason_for_leaving = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)

# دوال مساعدة لإدارة النظام

def setup_initial_data():
    """إعداد البيانات الأولية للمباني والغرف والأسرة"""
    
    # إضافة المباني
    buildings_data = [
        {'building_code': 'K6', 'building_name': 'مبنى K6', 'total_rooms': 13, 'total_beds': 26},
        {'building_code': 'K7', 'building_name': 'مبنى K7', 'total_rooms': 13, 'total_beds': 26}
    ]
    
    for building_data in buildings_data:
        existing = Building.query.filter_by(building_code=building_data['building_code']).first()
        if not existing:
            building = Building(**building_data)
            db.session.add(building)
    
    db.session.commit()
    
    # إضافة الغرف والأسرة
    for building in Building.query.all():
        for room_num in range(1, 14):  # غرف 1-13
            room_code = f"{building.building_code}{room_num:02d}"
            
            existing_room = Room.query.filter_by(room_code=room_code).first()
            if not existing_room:
                room = Room(
                    building_id=building.id,
                    room_number=room_num,
                    room_type='double',
                    total_beds=2,  # افتراضياً سريرين لكل غرفة
                    price_per_bed=55.0,
                    monthly_revenue=110.0,
                    room_code=room_code
                )
                db.session.add(room)
                db.session.commit()
                
                # إضافة الأسرة
                for bed_num in range(1, room.total_beds + 1):
                    bed_code = Bed.generate_bed_code(building.building_code, room_num, bed_num)
                    
                    existing_bed = Bed.query.filter_by(bed_code=bed_code).first()
                    if not existing_bed:
                        bed = Bed(
                            bed_code=bed_code,
                            building_id=building.id,
                            room_id=room.id,
                            bed_number=bed_num,
                            price=55.0,
                            status='available'
                        )
                        db.session.add(bed)
    
    db.session.commit()
    print("تم إعداد البيانات الأولية بنجاح!")

def add_bed_to_room(room_id, price=55.0):
    """إضافة سرير جديد لغرفة موجودة"""
    room = Room.query.get(room_id)
    if not room:
        return False, "الغرفة غير موجودة"
    
    # تحديد رقم السرير الجديد
    new_bed_number = room.total_beds + 1
    
    # توليد رمز السرير
    building = Building.query.get(room.building_id)
    bed_code = Bed.generate_bed_code(building.building_code, room.room_number, new_bed_number)
    
    # التأكد من عدم وجود السرير
    existing = Bed.query.filter_by(bed_code=bed_code).first()
    if existing:
        return False, "رمز السرير موجود مسبقاً"
    
    # إضافة السرير
    bed = Bed(
        bed_code=bed_code,
        building_id=room.building_id,
        room_id=room.id,
        bed_number=new_bed_number,
        price=price,
        status='available'
    )
    db.session.add(bed)
    
    # تحديث عدد الأسرة في الغرفة
    room.total_beds += 1
    room.update_monthly_revenue()
    
    # تحديث إجمالي الأسرة في المبنى
    building.total_beds += 1
    
    db.session.commit()
    return True, f"تم إضافة السرير {bed_code} بنجاح"

def remove_bed_from_room(bed_id):
    """حذف سرير من غرفة (إذا كان متاحاً)"""
    bed = Bed.query.get(bed_id)
    if not bed:
        return False, "السرير غير موجود"
    
    if bed.status == 'occupied':
        return False, "لا يمكن حذف سرير مشغول"
    
    room = Room.query.get(bed.room_id)
    building = Building.query.get(bed.building_id)
    
    # حذف السرير
    db.session.delete(bed)
    
    # تحديث عدد الأسرة
    room.total_beds -= 1
    room.update_monthly_revenue()
    building.total_beds -= 1
    
    db.session.commit()
    return True, f"تم حذف السرير {bed.bed_code} بنجاح"

def get_system_statistics():
    """الحصول على إحصائيات النظام"""
    total_beds = Bed.query.count()
    occupied_beds = Bed.query.filter_by(status='occupied').count()
    available_beds = total_beds - occupied_beds
    
    total_students = Student.query.filter_by(status='active').count()
    total_revenue = total_beds * 55.0  # الإيرادات المتوقعة
    
    # الإيرادات الفعلية
    from sqlalchemy import func, extract
    current_month = datetime.now().strftime('%Y-%m')
    actual_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.month_year == current_month,
        Payment.status == 'confirmed'
    ).scalar() or 0
    
    # المصروفات
    total_expenses = db.session.query(func.sum(Expense.amount)).filter(
        extract('month', Expense.expense_date) == datetime.now().month,
        extract('year', Expense.expense_date) == datetime.now().year
    ).scalar() or 0
    
    return {
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'available_beds': available_beds,
        'total_students': total_students,
        'expected_revenue': total_revenue,
        'actual_revenue': actual_revenue,
        'total_expenses': total_expenses,
        'net_profit': actual_revenue - total_expenses,
        'occupancy_rate': (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    }


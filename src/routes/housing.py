from flask import Blueprint, request, jsonify
from src.models.housing import db, Building, Room, Student, BedAssignment, FinancialRecord, Expense, OverduePayment
from datetime import datetime, date
import json

housing_bp = Blueprint('housing', __name__)

# مسارات الغرف والمباني
@housing_bp.route('/buildings', methods=['GET'])
def get_buildings():
    buildings = Building.query.all()
    return jsonify([{
        'id': b.id,
        'building_code': b.building_code,
        'building_name': b.building_name,
        'total_rooms': b.total_rooms,
        'rooms_count': len(b.rooms)
    } for b in buildings])

@housing_bp.route('/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.all()
    return jsonify([{
        'id': r.id,
        'building_code': r.building.building_code,
        'room_number': r.room_number,
        'room_type': r.room_type,
        'total_beds': r.total_beds,
        'occupied_beds': r.occupied_beds,
        'available_beds': r.available_beds,
        'price_per_bed': r.price_per_bed,
        'monthly_revenue': r.monthly_revenue,
        'status': r.status
    } for r in rooms])

@housing_bp.route('/rooms/available', methods=['GET'])
def get_available_rooms():
    rooms = Room.query.filter(Room.total_beds > Room.occupied_beds).all()
    return jsonify([{
        'id': r.id,
        'building_code': r.building.building_code,
        'room_number': r.room_number,
        'available_beds': r.available_beds,
        'price_per_bed': r.price_per_bed
    } for r in rooms if r.available_beds > 0])

# مسارات الطالبات
@housing_bp.route('/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'phone': s.phone,
        'university': s.university,
        'status': s.status,
        'contract_start': s.contract_start.isoformat() if s.contract_start else None,
        'contract_end': s.contract_end.isoformat() if s.contract_end else None,
        'current_room': get_student_current_room(s.id)
    } for s in students])

@housing_bp.route('/students', methods=['POST'])
def create_student():
    data = request.get_json()
    
    student = Student(
        name=data['name'],
        phone=data.get('phone'),
        guardian_id=data.get('guardian_id'),
        university=data.get('university'),
        contract_start=datetime.strptime(data['contract_start'], '%Y-%m-%d').date() if data.get('contract_start') else None,
        contract_end=datetime.strptime(data['contract_end'], '%Y-%m-%d').date() if data.get('contract_end') else None,
        notes=data.get('notes')
    )
    
    db.session.add(student)
    db.session.commit()
    
    return jsonify({'message': 'تم إنشاء الطالبة بنجاح', 'student_id': student.id}), 201

@housing_bp.route('/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    student = Student.query.get_or_404(student_id)
    current_assignment = BedAssignment.query.filter_by(student_id=student_id, status='active').first()
    
    return jsonify({
        'id': student.id,
        'name': student.name,
        'phone': student.phone,
        'guardian_id': student.guardian_id,
        'university': student.university,
        'status': student.status,
        'contract_start': student.contract_start.isoformat() if student.contract_start else None,
        'contract_end': student.contract_end.isoformat() if student.contract_end else None,
        'notes': student.notes,
        'current_room': get_student_current_room(student_id),
        'financial_summary': get_student_financial_summary(student_id)
    })

# مسارات تخصيص الأسرة
@housing_bp.route('/assign-bed', methods=['POST'])
def assign_bed():
    data = request.get_json()
    
    # التحقق من توفر السرير
    room = Room.query.get_or_404(data['room_id'])
    if room.available_beds <= 0:
        return jsonify({'error': 'لا توجد أسرة متاحة في هذه الغرفة'}), 400
    
    # إنهاء أي تخصيص سابق للطالبة
    old_assignment = BedAssignment.query.filter_by(student_id=data['student_id'], status='active').first()
    if old_assignment:
        old_assignment.status = 'ended'
        old_assignment.end_date = date.today()
    
    # إنشاء تخصيص جديد
    assignment = BedAssignment(
        student_id=data['student_id'],
        room_id=data['room_id'],
        bed_number=data['bed_number'],
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    )
    
    db.session.add(assignment)
    db.session.commit()
    
    return jsonify({'message': 'تم تخصيص السرير بنجاح'}), 201

# مسارات السجل المالي
@housing_bp.route('/financial-records', methods=['POST'])
def add_payment():
    data = request.get_json()
    
    record = FinancialRecord(
        student_id=data['student_id'],
        payment_date=datetime.strptime(data['payment_date'], '%Y-%m-%d').date(),
        amount=data['amount'],
        month_for=data['month_for'],
        payment_method=data.get('payment_method'),
        notes=data.get('notes')
    )
    
    db.session.add(record)
    
    # إزالة من قائمة المتأخرات إن وجدت
    overdue = OverduePayment.query.filter_by(
        student_id=data['student_id'],
        month_due=data['month_for']
    ).first()
    if overdue:
        overdue.follow_up_status = 'collected'
    
    db.session.commit()
    
    return jsonify({'message': 'تم تسجيل الدفعة بنجاح'}), 201

@housing_bp.route('/students/<int:student_id>/payments', methods=['GET'])
def get_student_payments(student_id):
    payments = FinancialRecord.query.filter_by(student_id=student_id).order_by(FinancialRecord.payment_date.desc()).all()
    return jsonify([{
        'id': p.id,
        'payment_date': p.payment_date.isoformat(),
        'amount': p.amount,
        'month_for': p.month_for,
        'payment_method': p.payment_method,
        'notes': p.notes,
        'status': p.status
    } for p in payments])

# مسارات المتأخرات
@housing_bp.route('/overdue-payments', methods=['GET'])
def get_overdue_payments():
    overdue = OverduePayment.query.filter_by(follow_up_status='new').all()
    return jsonify([{
        'id': o.id,
        'student_name': o.student_ref.name,
        'student_phone': o.student_ref.phone,
        'month_due': o.month_due,
        'amount_due': o.amount_due,
        'days_overdue': o.days_overdue,
        'last_reminder': o.last_reminder.isoformat() if o.last_reminder else None
    } for o in overdue])

# مسارات المصروفات
@housing_bp.route('/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    
    expense = Expense(
        expense_date=datetime.strptime(data['expense_date'], '%Y-%m-%d').date(),
        description=data['description'],
        amount=data['amount'],
        category=data['category'],
        building_id=data.get('building_id'),
        room_id=data.get('room_id'),
        receipt_url=data.get('receipt_url')
    )
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify({'message': 'تم تسجيل المصروف بنجاح'}), 201

@housing_bp.route('/expenses', methods=['GET'])
def get_expenses():
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    return jsonify([{
        'id': e.id,
        'expense_date': e.expense_date.isoformat(),
        'description': e.description,
        'amount': e.amount,
        'category': e.category,
        'building_code': e.building.building_code if e.building_id else None,
        'room_number': e.room.room_number if e.room_id else None
    } for e in expenses])

# دوال مساعدة
def get_student_current_room(student_id):
    assignment = BedAssignment.query.filter_by(student_id=student_id, status='active').first()
    if assignment:
        return {
            'building_code': assignment.room.building.building_code,
            'room_number': assignment.room.room_number,
            'bed_number': assignment.bed_number
        }
    return None

def get_student_financial_summary(student_id):
    payments = FinancialRecord.query.filter_by(student_id=student_id).all()
    total_paid = sum(p.amount for p in payments)
    overdue_count = OverduePayment.query.filter_by(student_id=student_id, follow_up_status='new').count()
    
    return {
        'total_paid': total_paid,
        'payments_count': len(payments),
        'overdue_count': overdue_count
    }


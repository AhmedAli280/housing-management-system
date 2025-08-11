from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from models.user import db
from models.core import (
    Building, Room, Bed, Student, BedAssignment, Payment, Expense, Archive,
    get_system_statistics
)
from datetime import datetime, date
import pandas as pd
import os
import io
from functools import wraps

dashboard_advanced_bp = Blueprint('dashboard_advanced', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً'}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@dashboard_advanced_bp.route('/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """الحصول على إحصائيات لوحة التحكم"""
    try:
        stats = get_system_statistics()
        
        # إحصائيات إضافية
        buildings = Building.query.all()
        building_stats = []
        
        for building in buildings:
            building_beds = Bed.query.filter_by(building_id=building.id).count()
            occupied_beds = Bed.query.filter_by(building_id=building.id, status='occupied').count()
            available_beds = building_beds - occupied_beds
            
            building_stats.append({
                'building_code': building.building_code,
                'building_name': building.building_name,
                'total_beds': building_beds,
                'occupied_beds': occupied_beds,
                'available_beds': available_beds,
                'occupancy_rate': (occupied_beds / building_beds * 100) if building_beds > 0 else 0,
                'expected_revenue': building_beds * 55
            })
        
        # إحصائيات المدفوعات الشهرية
        current_month = datetime.now().strftime('%Y-%m')
        monthly_payments = Payment.query.filter_by(month_year=current_month, status='confirmed').all()
        payment_summary = {
            'total_payments': len(monthly_payments),
            'total_amount': sum([p.amount for p in monthly_payments]),
            'rent_payments': len([p for p in monthly_payments if p.payment_type == 'rent']),
            'deposit_payments': len([p for p in monthly_payments if p.payment_type == 'deposit'])
        }
        
        # إحصائيات المصروفات
        current_month_expenses = Expense.query.filter(
            db.extract('month', Expense.expense_date) == datetime.now().month,
            db.extract('year', Expense.expense_date) == datetime.now().year
        ).all()
        
        expense_summary = {
            'total_expenses': len(current_month_expenses),
            'total_amount': sum([e.amount for e in current_month_expenses]),
            'maintenance_expenses': sum([e.amount for e in current_month_expenses if e.category == 'maintenance']),
            'utilities_expenses': sum([e.amount for e in current_month_expenses if e.category == 'utilities']),
            'other_expenses': sum([e.amount for e in current_month_expenses if e.category == 'other'])
        }
        
        return jsonify({
            'success': True,
            'data': {
                'general_stats': stats,
                'building_stats': building_stats,
                'payment_summary': payment_summary,
                'expense_summary': expense_summary
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في جلب الإحصائيات: {str(e)}'
        })

@dashboard_advanced_bp.route('/dashboard/upload_excel', methods=['POST'])
@login_required
def upload_excel_file():
    """رفع ملف Excel ومعالجة البيانات"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'لم يتم اختيار ملف'})
        
        file = request.files['file']
        file_type = request.form.get('file_type', 'payments')  # payments, students, expenses
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'لم يتم اختيار ملف'})
        
        if file and allowed_file(file.filename):
            # قراءة الملف مباشرة من الذاكرة
            try:
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                # معالجة البيانات حسب النوع
                if file_type == 'payments':
                    result = process_payments_excel(df)
                elif file_type == 'students':
                    result = process_students_excel(df)
                elif file_type == 'expenses':
                    result = process_expenses_excel(df)
                else:
                    return jsonify({'success': False, 'message': 'نوع ملف غير مدعوم'})
                
                return jsonify(result)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'خطأ في قراءة الملف: {str(e)}'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'نوع الملف غير مدعوم. يرجى استخدام Excel أو CSV'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في رفع الملف: {str(e)}'
        })

def process_payments_excel(df):
    """معالجة ملف Excel للمدفوعات"""
    try:
        processed = 0
        errors = []
        
        # التحقق من وجود الأعمدة المطلوبة
        required_columns = ['student_name', 'amount', 'payment_date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'message': f'أعمدة مفقودة في الملف: {", ".join(missing_columns)}'
            }
        
        for index, row in df.iterrows():
            try:
                # البحث عن الطالبة
                student = Student.query.filter(
                    Student.name.contains(str(row['student_name']).strip())
                ).first()
                
                if not student:
                    errors.append(f'الصف {index + 1}: لم يتم العثور على الطالبة {row["student_name"]}')
                    continue
                
                # تحويل التاريخ
                payment_date = pd.to_datetime(row['payment_date']).date()
                
                # إنشاء الدفعة
                payment = Payment(
                    student_id=student.id,
                    amount=float(row['amount']),
                    payment_type=row.get('payment_type', 'rent'),
                    payment_date=payment_date,
                    month_year=payment_date.strftime('%Y-%m'),
                    payment_method=row.get('payment_method', 'cash'),
                    notes=row.get('notes', ''),
                    status='confirmed'
                )
                
                db.session.add(payment)
                processed += 1
                
            except Exception as e:
                errors.append(f'الصف {index + 1}: {str(e)}')
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'تم معالجة {processed} دفعة بنجاح',
            'processed': processed,
            'errors': errors
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'خطأ في معالجة ملف المدفوعات: {str(e)}'
        }

def process_students_excel(df):
    """معالجة ملف Excel للطالبات"""
    try:
        processed = 0
        errors = []
        
        required_columns = ['name', 'phone']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'message': f'أعمدة مفقودة في الملف: {", ".join(missing_columns)}'
            }
        
        for index, row in df.iterrows():
            try:
                # التحقق من عدم وجود الطالبة مسبقاً
                existing = Student.query.filter_by(name=str(row['name']).strip()).first()
                if existing:
                    errors.append(f'الصف {index + 1}: الطالبة {row["name"]} موجودة مسبقاً')
                    continue
                
                # إنشاء الطالبة
                student = Student(
                    name=str(row['name']).strip(),
                    phone=str(row.get('phone', '')).strip(),
                    national_id=str(row.get('national_id', '')).strip(),
                    guardian_phone=str(row.get('guardian_phone', '')).strip(),
                    university=str(row.get('university', '')).strip(),
                    category=row.get('category', 'student'),
                    rent_amount=float(row.get('rent_amount', 55.0)),
                    security_deposit=float(row.get('security_deposit', 100.0)),
                    contract_start=pd.to_datetime(row.get('contract_start', date.today())).date() if pd.notna(row.get('contract_start')) else date.today(),
                    status='active'
                )
                
                db.session.add(student)
                processed += 1
                
            except Exception as e:
                errors.append(f'الصف {index + 1}: {str(e)}')
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'تم إضافة {processed} طالبة بنجاح',
            'processed': processed,
            'errors': errors
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'خطأ في معالجة ملف الطالبات: {str(e)}'
        }

def process_expenses_excel(df):
    """معالجة ملف Excel للمصروفات"""
    try:
        processed = 0
        errors = []
        
        required_columns = ['description', 'amount', 'expense_date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'message': f'أعمدة مفقودة في الملف: {", ".join(missing_columns)}'
            }
        
        for index, row in df.iterrows():
            try:
                expense = Expense(
                    description=str(row['description']).strip(),
                    amount=float(row['amount']),
                    category=row.get('category', 'other'),
                    expense_date=pd.to_datetime(row['expense_date']).date(),
                    receipt_number=str(row.get('receipt_number', '')).strip(),
                    notes=str(row.get('notes', '')).strip()
                )
                
                db.session.add(expense)
                processed += 1
                
            except Exception as e:
                errors.append(f'الصف {index + 1}: {str(e)}')
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'تم إضافة {processed} مصروف بنجاح',
            'processed': processed,
            'errors': errors
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'خطأ في معالجة ملف المصروفات: {str(e)}'
        }

@dashboard_advanced_bp.route('/dashboard/export/<data_type>', methods=['GET'])
@login_required
def export_data(data_type):
    """تصدير البيانات إلى Excel"""
    try:
        if data_type == 'students':
            return export_students_data()
        elif data_type == 'payments':
            return export_payments_data()
        elif data_type == 'expenses':
            return export_expenses_data()
        elif data_type == 'beds':
            return export_beds_data()
        else:
            return jsonify({'success': False, 'message': 'نوع بيانات غير مدعوم'})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تصدير البيانات: {str(e)}'
        })

def export_students_data():
    """تصدير بيانات الطالبات"""
    students = Student.query.filter_by(status='active').all()
    
    data = []
    for student in students:
        # الحصول على السرير الحالي
        assignment = BedAssignment.query.filter_by(
            student_id=student.id, 
            status='active'
        ).first()
        
        bed_code = ''
        building_name = ''
        room_number = ''
        
        if assignment:
            bed = Bed.query.get(assignment.bed_id)
            room = Room.query.get(assignment.room_id)
            building = Building.query.get(bed.building_id)
            bed_code = bed.bed_code
            building_name = building.building_name
            room_number = room.room_number
        
        # حساب إجمالي المدفوعات
        total_payments = sum([p.amount for p in student.payments if p.status == 'confirmed'])
        
        data.append({
            'الاسم': student.name,
            'الجوال': student.phone or '',
            'رقم الهوية': student.national_id or '',
            'جوال الأقارب': student.guardian_phone or '',
            'الجامعة': student.university or '',
            'الفئة': 'طالبة' if student.category == 'student' else 'موظفة',
            'رقم السرير': bed_code,
            'المبنى': building_name,
            'رقم الغرفة': room_number,
            'الإيجار الشهري': student.rent_amount,
            'مبلغ التأمين': student.security_deposit,
            'إجمالي المدفوعات': total_payments,
            'تاريخ بداية العقد': student.contract_start.strftime('%Y-%m-%d') if student.contract_start else '',
            'تاريخ نهاية العقد': student.contract_end.strftime('%Y-%m-%d') if student.contract_end else '',
            'ملاحظات': student.notes or ''
        })
    
    df = pd.DataFrame(data)
    
    # إنشاء ملف Excel في الذاكرة
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='الطالبات النشطات', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'students_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

def export_payments_data():
    """تصدير بيانات المدفوعات"""
    payments = Payment.query.order_by(Payment.payment_date.desc()).all()
    
    data = []
    for payment in payments:
        student = Student.query.get(payment.student_id)
        
        data.append({
            'اسم الطالبة': student.name,
            'المبلغ': payment.amount,
            'نوع الدفعة': 'إيجار' if payment.payment_type == 'rent' else 'تأمين' if payment.payment_type == 'deposit' else 'أخرى',
            'تاريخ الدفع': payment.payment_date.strftime('%Y-%m-%d'),
            'الشهر': payment.month_year or '',
            'طريقة الدفع': payment.payment_method or '',
            'الحالة': 'مؤكد' if payment.status == 'confirmed' else 'معلق',
            'ملاحظات': payment.notes or ''
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='المدفوعات', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'payments_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

def export_expenses_data():
    """تصدير بيانات المصروفات"""
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    
    data = []
    for expense in expenses:
        data.append({
            'الوصف': expense.description,
            'المبلغ': expense.amount,
            'الفئة': expense.category,
            'تاريخ المصروف': expense.expense_date.strftime('%Y-%m-%d'),
            'رقم الإيصال': expense.receipt_number or '',
            'ملاحظات': expense.notes or ''
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='المصروفات', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'expenses_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

def export_beds_data():
    """تصدير بيانات الأسرة"""
    beds = Bed.query.all()
    
    data = []
    for bed in beds:
        room = Room.query.get(bed.room_id)
        building = Building.query.get(bed.building_id)
        
        # الحصول على الطالبة الحالية
        assignment = BedAssignment.query.filter_by(
            bed_id=bed.id, 
            status='active'
        ).first()
        
        student_name = ''
        if assignment:
            student = Student.query.get(assignment.student_id)
            student_name = student.name
        
        data.append({
            'رقم السرير': bed.bed_code,
            'المبنى': building.building_name,
            'رقم الغرفة': room.room_number,
            'رقم السرير في الغرفة': bed.bed_number,
            'السعر': bed.price,
            'الحالة': 'مشغول' if bed.status == 'occupied' else 'متاح' if bed.status == 'available' else 'صيانة',
            'اسم الطالبة': student_name
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='الأسرة', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'beds_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@dashboard_advanced_bp.route('/dashboard/bed_management', methods=['POST'])
@login_required
def manage_beds():
    """إدارة الأسرة (إضافة/حذف/تعديل)"""
    try:
        data = request.get_json()
        action = data.get('action')  # add, remove, update
        
        if action == 'add':
            return add_bed_to_room_api(data)
        elif action == 'remove':
            return remove_bed_api(data)
        elif action == 'update':
            return update_bed_api(data)
        else:
            return jsonify({'success': False, 'message': 'عملية غير مدعومة'})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إدارة الأسرة: {str(e)}'
        })

def add_bed_to_room_api(data):
    """إضافة سرير جديد عبر API"""
    from models.core import add_bed_to_room
    
    room_id = data.get('room_id')
    price = data.get('price', 55.0)
    
    if not room_id:
        return jsonify({'success': False, 'message': 'رقم الغرفة مطلوب'})
    
    success, message = add_bed_to_room(room_id, price)
    
    return jsonify({
        'success': success,
        'message': message
    })

def remove_bed_api(data):
    """حذف سرير عبر API"""
    from models.core import remove_bed_from_room
    
    bed_id = data.get('bed_id')
    
    if not bed_id:
        return jsonify({'success': False, 'message': 'رقم السرير مطلوب'})
    
    success, message = remove_bed_from_room(bed_id)
    
    return jsonify({
        'success': success,
        'message': message
    })

def update_bed_api(data):
    """تحديث بيانات سرير عبر API"""
    bed_id = data.get('bed_id')
    new_price = data.get('price')
    new_status = data.get('status')
    
    if not bed_id:
        return jsonify({'success': False, 'message': 'رقم السرير مطلوب'})
    
    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'success': False, 'message': 'السرير غير موجود'})
    
    if new_price is not None:
        bed.price = float(new_price)
    
    if new_status is not None:
        bed.status = new_status
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'تم تحديث بيانات السرير بنجاح'
    })


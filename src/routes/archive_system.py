from flask import Blueprint, request, jsonify, session
from models.user import db
from models.core import (
    Student, BedAssignment, Payment, Expense, Archive,
    get_system_statistics
)
from datetime import datetime, date, timedelta
from functools import wraps

archive_system_bp = Blueprint('archive_system', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً'}), 401
        return f(*args, **kwargs)
    return decorated_function

@archive_system_bp.route('/archive/student', methods=['POST'])
@login_required
def archive_student():
    """أرشفة طالبة مع حساب الرصيد النهائي"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        departure_date = data.get('departure_date', date.today().isoformat())
        departure_reason = data.get('departure_reason', '')
        notes = data.get('notes', '')
        
        if not student_id:
            return jsonify({'success': False, 'message': 'رقم الطالبة مطلوب'})
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': 'الطالبة غير موجودة'})
        
        if student.status == 'archived':
            return jsonify({'success': False, 'message': 'الطالبة مؤرشفة مسبقاً'})
        
        # حساب الرصيد النهائي
        financial_summary = calculate_student_final_balance(student_id)
        
        # إنشاء سجل الأرشيف
        archive_record = Archive(
            student_id=student_id,
            student_name=student.name,
            departure_date=datetime.strptime(departure_date, '%Y-%m-%d').date(),
            departure_reason=departure_reason,
            total_payments=financial_summary['total_payments'],
            total_rent_due=financial_summary['total_rent_due'],
            security_deposit=financial_summary['security_deposit'],
            final_balance=financial_summary['final_balance'],
            refund_amount=financial_summary['refund_amount'],
            notes=notes,
            archived_by='admin',  # يمكن تحسينه لاحقاً
            archived_at=datetime.now()
        )
        
        # تحديث حالة الطالبة
        student.status = 'archived'
        student.departure_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
        
        # تحرير السرير
        active_assignment = BedAssignment.query.filter_by(
            student_id=student_id, 
            status='active'
        ).first()
        
        if active_assignment:
            active_assignment.status = 'completed'
            active_assignment.end_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
            
            # تحديث حالة السرير
            from models.core import Bed
            bed = Bed.query.get(active_assignment.bed_id)
            if bed:
                bed.status = 'available'
        
        db.session.add(archive_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم أرشفة الطالبة {student.name} بنجاح',
            'financial_summary': financial_summary,
            'archive_id': archive_record.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'خطأ في أرشفة الطالبة: {str(e)}'
        })

def calculate_student_final_balance(student_id):
    """حساب الرصيد النهائي للطالبة"""
    try:
        student = Student.query.get(student_id)
        
        # إجمالي المدفوعات
        total_payments = sum([
            p.amount for p in student.payments 
            if p.status == 'confirmed'
        ])
        
        # مدفوعات الإيجار
        rent_payments = sum([
            p.amount for p in student.payments 
            if p.status == 'confirmed' and p.payment_type == 'rent'
        ])
        
        # مدفوعات التأمين
        deposit_payments = sum([
            p.amount for p in student.payments 
            if p.status == 'confirmed' and p.payment_type == 'deposit'
        ])
        
        # حساب الإيجار المستحق
        if student.contract_start and student.departure_date:
            months_stayed = calculate_months_between_dates(
                student.contract_start, 
                student.departure_date
            )
            total_rent_due = months_stayed * student.rent_amount
        else:
            # تقدير بناءً على تاريخ أول دفعة إيجار
            first_rent_payment = Payment.query.filter_by(
                student_id=student_id,
                payment_type='rent',
                status='confirmed'
            ).order_by(Payment.payment_date).first()
            
            if first_rent_payment:
                months_stayed = calculate_months_between_dates(
                    first_rent_payment.payment_date,
                    student.departure_date or date.today()
                )
                total_rent_due = months_stayed * student.rent_amount
            else:
                total_rent_due = 0
        
        # حساب الرصيد النهائي
        rent_balance = rent_payments - total_rent_due
        deposit_balance = deposit_payments
        
        # إذا كان رصيد الإيجار سالب، يخصم من التأمين
        if rent_balance < 0:
            remaining_deposit = deposit_balance + rent_balance  # rent_balance سالب
            refund_amount = max(0, remaining_deposit)
            final_balance = rent_balance if remaining_deposit < 0 else 0
        else:
            # إذا كان رصيد الإيجار موجب أو صفر، يُرد التأمين كاملاً
            refund_amount = deposit_balance
            final_balance = rent_balance
        
        return {
            'total_payments': total_payments,
            'rent_payments': rent_payments,
            'deposit_payments': deposit_payments,
            'total_rent_due': total_rent_due,
            'security_deposit': student.security_deposit,
            'rent_balance': rent_balance,
            'deposit_balance': deposit_balance,
            'final_balance': final_balance,
            'refund_amount': refund_amount,
            'months_stayed': months_stayed if 'months_stayed' in locals() else 0
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'total_payments': 0,
            'total_rent_due': 0,
            'security_deposit': 0,
            'final_balance': 0,
            'refund_amount': 0
        }

def calculate_months_between_dates(start_date, end_date):
    """حساب عدد الأشهر بين تاريخين"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    
    # إضافة جزء من الشهر إذا كان اليوم أكبر
    if end_date.day >= start_date.day:
        months += 1
    
    return max(1, months)  # على الأقل شهر واحد

@archive_system_bp.route('/archive/list', methods=['GET'])
@login_required
def get_archived_students():
    """الحصول على قائمة الطالبات المؤرشفات"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = Archive.query
        
        if search:
            query = query.filter(
                Archive.student_name.contains(search)
            )
        
        archives = query.order_by(Archive.archived_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        archive_list = []
        for archive in archives.items:
            archive_list.append({
                'id': archive.id,
                'student_name': archive.student_name,
                'departure_date': archive.departure_date.strftime('%Y-%m-%d'),
                'departure_reason': archive.departure_reason,
                'total_payments': archive.total_payments,
                'total_rent_due': archive.total_rent_due,
                'security_deposit': archive.security_deposit,
                'final_balance': archive.final_balance,
                'refund_amount': archive.refund_amount,
                'notes': archive.notes,
                'archived_at': archive.archived_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({
            'success': True,
            'data': archive_list,
            'pagination': {
                'page': page,
                'pages': archives.pages,
                'per_page': per_page,
                'total': archives.total,
                'has_next': archives.has_next,
                'has_prev': archives.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب الأرشيف: {str(e)}'
        })

@archive_system_bp.route('/archive/student/<int:student_id>/preview', methods=['GET'])
@login_required
def preview_student_archive(student_id):
    """معاينة أرشفة الطالبة قبل التأكيد"""
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': 'الطالبة غير موجودة'})
        
        if student.status == 'archived':
            return jsonify({'success': False, 'message': 'الطالبة مؤرشفة مسبقاً'})
        
        # حساب الرصيد النهائي
        financial_summary = calculate_student_final_balance(student_id)
        
        # معلومات السرير الحالي
        active_assignment = BedAssignment.query.filter_by(
            student_id=student_id, 
            status='active'
        ).first()
        
        bed_info = {}
        if active_assignment:
            from models.core import Bed, Room, Building
            bed = Bed.query.get(active_assignment.bed_id)
            room = Room.query.get(active_assignment.room_id)
            building = Building.query.get(bed.building_id)
            
            bed_info = {
                'bed_code': bed.bed_code,
                'room_number': room.room_number,
                'building_name': building.building_name,
                'assignment_date': active_assignment.start_date.strftime('%Y-%m-%d')
            }
        
        return jsonify({
            'success': True,
            'data': {
                'student_info': {
                    'id': student.id,
                    'name': student.name,
                    'phone': student.phone,
                    'university': student.university,
                    'contract_start': student.contract_start.strftime('%Y-%m-%d') if student.contract_start else '',
                    'rent_amount': student.rent_amount,
                    'security_deposit': student.security_deposit
                },
                'bed_info': bed_info,
                'financial_summary': financial_summary
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في معاينة الأرشفة: {str(e)}'
        })

@archive_system_bp.route('/archive/restore/<int:archive_id>', methods=['POST'])
@login_required
def restore_student(archive_id):
    """استعادة طالبة من الأرشيف"""
    try:
        archive_record = Archive.query.get(archive_id)
        if not archive_record:
            return jsonify({'success': False, 'message': 'سجل الأرشيف غير موجود'})
        
        student = Student.query.get(archive_record.student_id)
        if not student:
            return jsonify({'success': False, 'message': 'الطالبة غير موجودة'})
        
        # استعادة حالة الطالبة
        student.status = 'active'
        student.departure_date = None
        
        # حذف سجل الأرشيف
        db.session.delete(archive_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم استعادة الطالبة {student.name} من الأرشيف بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'خطأ في استعادة الطالبة: {str(e)}'
        })

@archive_system_bp.route('/reports/financial_summary', methods=['GET'])
@login_required
def get_financial_summary():
    """تقرير مالي شامل"""
    try:
        # فترة التقرير
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = date.today().replace(day=1).isoformat()  # بداية الشهر الحالي
        if not end_date:
            end_date = date.today().isoformat()  # اليوم
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # إحصائيات عامة
        stats = get_system_statistics()
        
        # المدفوعات في الفترة
        payments_in_period = Payment.query.filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
            Payment.status == 'confirmed'
        ).all()
        
        # المصروفات في الفترة
        expenses_in_period = Expense.query.filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).all()
        
        # تحليل المدفوعات
        rent_payments = [p for p in payments_in_period if p.payment_type == 'rent']
        deposit_payments = [p for p in payments_in_period if p.payment_type == 'deposit']
        other_payments = [p for p in payments_in_period if p.payment_type not in ['rent', 'deposit']]
        
        # تحليل المصروفات
        maintenance_expenses = [e for e in expenses_in_period if e.category == 'maintenance']
        utilities_expenses = [e for e in expenses_in_period if e.category == 'utilities']
        other_expenses = [e for e in expenses_in_period if e.category not in ['maintenance', 'utilities']]
        
        # حساب الأرباح
        total_revenue = sum([p.amount for p in payments_in_period])
        total_expenses = sum([e.amount for e in expenses_in_period])
        net_profit = total_revenue - total_expenses
        
        # معدل التحصيل
        expected_monthly_revenue = stats['expected_revenue']
        collection_rate = (total_revenue / expected_monthly_revenue * 100) if expected_monthly_revenue > 0 else 0
        
        # الطالبات المتأخرات في الدفع
        current_month = date.today().strftime('%Y-%m')
        active_students = Student.query.filter_by(status='active').all()
        
        overdue_students = []
        for student in active_students:
            monthly_payment = Payment.query.filter_by(
                student_id=student.id,
                month_year=current_month,
                payment_type='rent',
                status='confirmed'
            ).first()
            
            if not monthly_payment:
                overdue_students.append({
                    'id': student.id,
                    'name': student.name,
                    'phone': student.phone,
                    'rent_amount': student.rent_amount
                })
        
        return jsonify({
            'success': True,
            'data': {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                },
                'summary': {
                    'total_revenue': total_revenue,
                    'total_expenses': total_expenses,
                    'net_profit': net_profit,
                    'collection_rate': round(collection_rate, 2),
                    'expected_revenue': expected_monthly_revenue
                },
                'payments_breakdown': {
                    'rent_payments': {
                        'count': len(rent_payments),
                        'amount': sum([p.amount for p in rent_payments])
                    },
                    'deposit_payments': {
                        'count': len(deposit_payments),
                        'amount': sum([p.amount for p in deposit_payments])
                    },
                    'other_payments': {
                        'count': len(other_payments),
                        'amount': sum([p.amount for p in other_payments])
                    }
                },
                'expenses_breakdown': {
                    'maintenance': {
                        'count': len(maintenance_expenses),
                        'amount': sum([e.amount for e in maintenance_expenses])
                    },
                    'utilities': {
                        'count': len(utilities_expenses),
                        'amount': sum([e.amount for e in utilities_expenses])
                    },
                    'other': {
                        'count': len(other_expenses),
                        'amount': sum([e.amount for e in other_expenses])
                    }
                },
                'overdue_students': overdue_students,
                'system_stats': stats
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إنشاء التقرير المالي: {str(e)}'
        })

@archive_system_bp.route('/reports/occupancy_history', methods=['GET'])
@login_required
def get_occupancy_history():
    """تقرير تاريخ الإشغال"""
    try:
        months = request.args.get('months', 6, type=int)  # آخر 6 أشهر افتراضياً
        
        history = []
        current_date = date.today()
        
        for i in range(months):
            # حساب تاريخ بداية ونهاية الشهر
            if i == 0:
                month_start = current_date.replace(day=1)
                month_end = current_date
            else:
                month_date = current_date.replace(day=1) - timedelta(days=i*30)
                month_start = month_date.replace(day=1)
                # آخر يوم في الشهر
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year+1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = month_start.replace(month=month_start.month+1, day=1) - timedelta(days=1)
            
            # حساب الإشغال في ذلك الشهر
            assignments_in_month = BedAssignment.query.filter(
                BedAssignment.start_date <= month_end,
                db.or_(
                    BedAssignment.end_date >= month_start,
                    BedAssignment.end_date.is_(None)
                )
            ).all()
            
            occupied_beds = len(assignments_in_month)
            total_beds = stats['total_beds'] if 'stats' in locals() else 52
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
            
            # الإيرادات في ذلك الشهر
            month_payments = Payment.query.filter(
                Payment.payment_date >= month_start,
                Payment.payment_date <= month_end,
                Payment.status == 'confirmed',
                Payment.payment_type == 'rent'
            ).all()
            
            month_revenue = sum([p.amount for p in month_payments])
            
            history.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'occupied_beds': occupied_beds,
                'total_beds': total_beds,
                'occupancy_rate': round(occupancy_rate, 2),
                'revenue': month_revenue
            })
        
        return jsonify({
            'success': True,
            'data': {
                'history': list(reversed(history)),  # ترتيب تصاعدي
                'summary': {
                    'avg_occupancy': round(sum([h['occupancy_rate'] for h in history]) / len(history), 2),
                    'total_revenue': sum([h['revenue'] for h in history]),
                    'best_month': max(history, key=lambda x: x['occupancy_rate']),
                    'worst_month': min(history, key=lambda x: x['occupancy_rate'])
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إنشاء تقرير الإشغال: {str(e)}'
        })


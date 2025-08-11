from flask import Blueprint, request, jsonify, session
from src.routes.auth import login_required
from src.models.housing import db, Building, Room, Student, BedAssignment, FinancialRecord, Expense, OverduePayment
from datetime import datetime, date
import re
import json

ai_agent_bp = Blueprint('ai_agent', __name__)

@ai_agent_bp.route('/chat', methods=['POST'])
@login_required
def process_chat_message():
    """معالجة رسائل المحادثة وتنفيذ الأوامر"""
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'الرسالة فارغة'}), 400
    
    try:
        response = process_user_command(message)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

def process_user_command(message):
    """معالجة أوامر المستخدم وإرجاع الرد المناسب"""
    message_lower = message.lower()
    
    # أوامر عرض الغرف المتاحة
    if any(keyword in message_lower for keyword in ['غرف', 'متاح', 'فارغ', 'شاغر']):
        return get_available_rooms()
    
    # أوامر المتأخرات في الدفع
    elif any(keyword in message_lower for keyword in ['متأخر', 'دفع', 'مستحق']):
        return get_overdue_payments()
    
    # أوامر قائمة الطالبات
    elif any(keyword in message_lower for keyword in ['طالبات', 'قائمة', 'أسماء']):
        return get_students_list()
    
    # أوامر تسجيل الدفعات
    elif any(keyword in message_lower for keyword in ['سجل', 'دفع']) and any(keyword in message_lower for keyword in ['ريال', 'مبلغ']):
        return process_payment_registration(message)
    
    # أوامر تسجيل المصروفات
    elif any(keyword in message_lower for keyword in ['مصروف', 'فاتورة', 'تكلفة']):
        return process_expense_registration(message)
    
    # رد افتراضي
    else:
        return get_default_response()

def get_available_rooms():
    """عرض الغرف المتاحة"""
    try:
        rooms = Room.query.all()
        available_rooms = []
        total_available_beds = 0
        total_potential_revenue = 0
        
        for room in rooms:
            occupied_beds = BedAssignment.query.filter_by(
                room_id=room.id, 
                status='active'
            ).count()
            
            available_beds = room.total_beds - occupied_beds
            if available_beds > 0:
                available_rooms.append({
                    'room_number': room.room_number,
                    'available_beds': available_beds,
                    'room_type': room.room_type,
                    'price_per_bed': room.price_per_bed
                })
                total_available_beds += available_beds
                total_potential_revenue += available_beds * room.price_per_bed
        
        if not available_rooms:
            return "🏠 <strong>جميع الغرف مشغولة حالياً</strong><br><br>لا توجد أسرة متاحة في الوقت الحالي."
        
        response = "<strong>الغرف المتاحة حالياً:</strong><br><br>"
        response += f"🏠 <strong>مبنى K7:</strong><br>"
        
        for room in available_rooms:
            response += f"• غرفة {room['room_number']}: {room['available_beds']} سرير متاح ({room['room_type']} - {room['price_per_bed']} ريال)<br>"
        
        response += f"<br>💰 <strong>إجمالي الأسرة المتاحة:</strong> {total_available_beds} سرير<br>"
        response += f"💰 <strong>إجمالي الإيرادات المحتملة:</strong> {total_potential_revenue} ريال شهرياً"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في عرض الغرف المتاحة: {str(e)}"

def get_overdue_payments():
    """عرض المتأخرات في الدفع"""
    try:
        current_month = datetime.now().strftime('%Y-%m')
        
        # البحث عن الطالبات المتأخرات
        overdue_students = db.session.query(Student, BedAssignment, Room).join(
            BedAssignment, Student.id == BedAssignment.student_id
        ).join(
            Room, BedAssignment.room_id == Room.id
        ).filter(
            BedAssignment.status == 'active'
        ).all()
        
        overdue_list = []
        
        for student, assignment, room in overdue_students:
            # التحقق من وجود دفعة لهذا الشهر
            payment_exists = FinancialRecord.query.filter_by(
                student_id=student.id,
                payment_month=current_month
            ).first()
            
            if not payment_exists:
                overdue_list.append({
                    'name': student.full_name,
                    'room': room.room_number,
                    'amount': room.price_per_bed,
                    'phone': student.phone_number,
                    'month': current_month
                })
        
        if not overdue_list:
            return "✅ <strong>ممتاز!</strong><br><br>جميع الطالبات منتظمات في الدفع لهذا الشهر."
        
        response = "<strong>الطالبات المتأخرات في الدفع:</strong><br><br>"
        
        for student in overdue_list:
            response += f"⚠️ <strong>{student['name']}</strong> - غرفة {student['room']}<br>"
            response += f"المبلغ: {student['amount']} ريال (شهر {student['month']})<br>"
            response += f"الجوال: {student['phone']}<br><br>"
        
        response += "هل تريد إرسال تذكير لهن؟"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في عرض المتأخرات: {str(e)}"

def get_students_list():
    """عرض قائمة الطالبات"""
    try:
        total_students = Student.query.count()
        active_assignments = BedAssignment.query.filter_by(status='active').count()
        total_rooms = Room.query.count()
        occupied_rooms = db.session.query(Room.id).join(BedAssignment).filter(
            BedAssignment.status == 'active'
        ).distinct().count()
        
        # حساب المنتظمات والمتأخرات
        current_month = datetime.now().strftime('%Y-%m')
        paid_students = db.session.query(FinancialRecord.student_id).filter_by(
            payment_month=current_month
        ).distinct().count()
        
        overdue_students = total_students - paid_students
        
        response = "<strong>قائمة الطالبات الحاليات:</strong><br><br>"
        response += f"👥 <strong>إجمالي الطالبات:</strong> {total_students} طالبة<br>"
        response += f"🏠 <strong>الغرف المشغولة:</strong> {occupied_rooms} من {total_rooms} غرف<br>"
        response += f"💚 <strong>منتظمات في الدفع:</strong> {paid_students} طالبة<br>"
        response += f"⚠️ <strong>متأخرات:</strong> {overdue_students} طالبة<br><br>"
        response += "هل تريد عرض تفاصيل طالبة معينة؟"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في عرض قائمة الطالبات: {str(e)}"

def process_payment_registration(message):
    """معالجة تسجيل الدفعات"""
    try:
        # استخراج اسم الطالبة والمبلغ من الرسالة
        name_match = re.search(r'الطالبة\s+([^دفعت]+)', message)
        amount_match = re.search(r'(\d+)\s*ريال', message)
        month_match = re.search(r'لشهر\s+(\w+)', message)
        
        if not name_match or not amount_match:
            return "يرجى تحديد اسم الطالبة والمبلغ بوضوح.<br>مثال: سجل أن الطالبة فاطمة أحمد دفعت 55 ريال لشهر أغسطس"
        
        student_name = name_match.group(1).strip()
        amount = float(amount_match.group(1))
        month = month_match.group(1) if month_match else datetime.now().strftime('%Y-%m')
        
        # البحث عن الطالبة
        student = Student.query.filter(
            Student.full_name.contains(student_name.split()[0])
        ).first()
        
        if not student:
            return f"لم يتم العثور على طالبة باسم '{student_name}'.<br>يرجى التحقق من الاسم والمحاولة مرة أخرى."
        
        # تسجيل الدفعة
        payment = FinancialRecord(
            student_id=student.id,
            amount=amount,
            payment_date=datetime.now().date(),
            payment_month=month,
            payment_method='نقدي',
            notes=f'تم التسجيل عبر الوكيل الذكي'
        )
        
        db.session.add(payment)
        db.session.commit()
        
        response = f"✅ <strong>تم تسجيل الدفعة بنجاح!</strong><br><br>"
        response += f"الطالبة: {student.full_name}<br>"
        response += f"المبلغ: {amount} ريال<br>"
        response += f"الشهر: {month}<br>"
        response += f"التاريخ: {datetime.now().strftime('%Y-%m-%d')}<br><br>"
        response += "تم تحديث السجل المالي وإزالة الطالبة من قائمة المتأخرات."
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في تسجيل الدفعة: {str(e)}"

def process_expense_registration(message):
    """معالجة تسجيل المصروفات"""
    try:
        # استخراج تفاصيل المصروف من الرسالة
        amount_match = re.search(r'(\d+)\s*ريال', message)
        
        if not amount_match:
            return """<strong>تسجيل مصروف جديد:</strong><br><br>
            📝 يرجى تزويدي بالمعلومات التالية:<br>
            • وصف المصروف<br>
            • المبلغ<br>
            • التاريخ<br>
            • الفئة (صيانة/فواتير/أخرى)<br><br>
            مثال: "سجل مصروف فاتورة كهرباء 150 ريال اليوم" """
        
        amount = float(amount_match.group(1))
        
        # تحديد نوع المصروف
        if 'كهرباء' in message or 'فاتورة' in message:
            category = 'فواتير'
            description = 'فاتورة كهرباء'
        elif 'صيانة' in message:
            category = 'صيانة'
            description = 'أعمال صيانة'
        else:
            category = 'أخرى'
            description = 'مصروف عام'
        
        # تسجيل المصروف
        expense = Expense(
            description=description,
            amount=amount,
            expense_date=datetime.now().date(),
            category=category,
            notes='تم التسجيل عبر الوكيل الذكي'
        )
        
        db.session.add(expense)
        db.session.commit()
        
        response = f"✅ <strong>تم تسجيل المصروف بنجاح!</strong><br><br>"
        response += f"الوصف: {description}<br>"
        response += f"المبلغ: {amount} ريال<br>"
        response += f"الفئة: {category}<br>"
        response += f"التاريخ: {datetime.now().strftime('%Y-%m-%d')}<br><br>"
        response += "تم تحديث سجل المصروفات."
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في تسجيل المصروف: {str(e)}"

def get_default_response():
    """الرد الافتراضي"""
    return """أفهم طلبك، ولكن أحتاج لمزيد من التفاصيل.<br><br>
    يمكنني مساعدتك في:<br>
    • إدارة الطالبات والغرف<br>
    • تسجيل الدفعات والمتابعات<br>
    • عرض التقارير المالية<br>
    • تسجيل المصروفات<br><br>
    جرب أحد الأوامر السريعة أعلاه."""


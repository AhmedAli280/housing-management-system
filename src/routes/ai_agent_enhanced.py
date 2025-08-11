from flask import Blueprint, request, jsonify, session
from models.user import db
from models.core import (
    Building, Room, Bed, Student, BedAssignment, Payment, Expense, 
    get_system_statistics, add_bed_to_room, remove_bed_from_room
)
from datetime import datetime, date
import re
from functools import wraps

ai_agent_enhanced_bp = Blueprint('ai_agent_enhanced', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً'}), 401
        return f(*args, **kwargs)
    return decorated_function

@ai_agent_enhanced_bp.route('/ai_agent_enhanced', methods=['POST'])
@login_required
def ai_agent():
    """الوكيل الذكي المحسن مع دعم النظام الجديد"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'الرجاء كتابة رسالة'
            })
        
        # معالجة الرسالة وتحديد النية
        response = process_user_message(user_message)
        
        return jsonify({
            'success': True,
            'message': response
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })

def process_user_message(message):
    """معالجة رسالة المستخدم وتحديد النية"""
    message = message.lower().strip()
    
    # أنماط الأوامر المختلفة
    patterns = {
        'show_rooms': [
            'اعرض الغرف', 'عرض الغرف', 'الغرف المتاحة', 'غرف متاحة', 
            'شواغر', 'الشواغر', 'أسرة متاحة', 'اسرة متاحة'
        ],
        'show_students': [
            'اعرض الطالبات', 'عرض الطالبات', 'قائمة الطالبات', 
            'الطالبات النشطات', 'طالبات نشطات'
        ],
        'add_student': [
            'أضف طالبة', 'اضف طالبة', 'تسجيل طالبة', 'طالبة جديدة'
        ],
        'record_payment': [
            'دفعت', 'دفع', 'سدد', 'سددت', 'مدفوع'
        ],
        'record_expense': [
            'مصروف', 'تصليح', 'صيانة', 'فاتورة'
        ],
        'statistics': [
            'إحصائيات', 'احصائيات', 'تقرير', 'ملخص', 'نظرة عامة'
        ],
        'add_bed': [
            'أضف سرير', 'اضف سرير', 'سرير جديد', 'زيادة سرير'
        ],
        'building_info': [
            'مبنى', 'مباني', 'k6', 'k7'
        ]
    }
    
    # تحديد النية
    intent = determine_intent(message, patterns)
    
    # تنفيذ الأمر حسب النية
    if intent == 'show_rooms':
        return show_available_rooms()
    elif intent == 'show_students':
        return show_active_students()
    elif intent == 'add_student':
        return handle_add_student(message)
    elif intent == 'record_payment':
        return handle_payment_record(message)
    elif intent == 'record_expense':
        return handle_expense_record(message)
    elif intent == 'statistics':
        return show_system_statistics()
    elif intent == 'add_bed':
        return handle_add_bed(message)
    elif intent == 'building_info':
        return show_building_info(message)
    else:
        return handle_general_query(message)

def determine_intent(message, patterns):
    """تحديد نية المستخدم من الرسالة"""
    for intent, keywords in patterns.items():
        for keyword in keywords:
            if keyword in message:
                return intent
    return 'general'

def show_available_rooms():
    """عرض الغرف والأسرة المتاحة"""
    try:
        available_beds = Bed.query.filter_by(status='available').all()
        
        if not available_beds:
            return "جميع الأسرة مشغولة حالياً."
        
        # تجميع حسب المبنى
        buildings_data = {}
        
        for bed in available_beds:
            building = Building.query.get(bed.building_id)
            room = Room.query.get(bed.room_id)
            
            if building.building_code not in buildings_data:
                buildings_data[building.building_code] = {
                    'name': building.building_name,
                    'beds': []
                }
            
            buildings_data[building.building_code]['beds'].append({
                'bed_code': bed.bed_code,
                'room_number': room.room_number,
                'price': bed.price
            })
        
        response = "🏢 **الغرف والأسرة المتاحة:**\n\n"
        
        total_available = 0
        total_revenue = 0
        
        for building_code, data in buildings_data.items():
            response += f"**{data['name']} ({building_code}):**\n"
            
            # ترتيب الأسرة حسب رقم الغرفة
            sorted_beds = sorted(data['beds'], key=lambda x: x['room_number'])
            
            for bed in sorted_beds:
                response += f"• غرفة {bed['room_number']} - سرير متاح ({bed['bed_code']}) - {bed['price']} ريال\n"
                total_available += 1
                total_revenue += bed['price']
            
            response += "\n"
        
        response += f"📊 **الملخص:**\n"
        response += f"• إجمالي الأسرة المتاحة: {total_available} سرير\n"
        response += f"• الإيرادات المتوقعة من الشواغر: {total_revenue} ريال شهرياً\n"
        
        # إضافة إحصائيات عامة
        stats = get_system_statistics()
        response += f"• إجمالي الأسرة في النظام: {stats['total_beds']} سرير\n"
        response += f"• معدل الإشغال: {stats['occupancy_rate']:.1f}%"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في عرض الغرف: {str(e)}"

def show_active_students():
    """عرض الطالبات النشطات"""
    try:
        students = Student.query.filter_by(status='active').all()
        
        if not students:
            return "لا توجد طالبات نشطات حالياً."
        
        response = f"👥 **الطالبات النشطات ({len(students)}):**\n\n"
        
        for student in students:
            # الحصول على السرير الحالي
            assignment = BedAssignment.query.filter_by(
                student_id=student.id, 
                status='active'
            ).first()
            
            bed_info = "غير محدد"
            if assignment:
                bed = Bed.query.get(assignment.bed_id)
                room = Room.query.get(assignment.room_id)
                building = Building.query.get(bed.building_id)
                bed_info = f"{bed.bed_code} ({building.building_name} غرفة {room.room_number})"
            
            response += f"**{student.name}**\n"
            response += f"• الجوال: {student.phone or 'غير محدد'}\n"
            response += f"• السرير: {bed_info}\n"
            response += f"• الإيجار: {student.rent_amount} ريال\n"
            response += f"• الفئة: {'طالبة' if student.category == 'student' else 'موظفة'}\n\n"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في عرض الطالبات: {str(e)}"

def handle_add_student(message):
    """معالجة إضافة طالبة جديدة"""
    try:
        # استخراج المعلومات من الرسالة
        # نمط: "أضف طالبة جديدة: فاطمة أحمد، جوال 0501234567، غرفة K611، إيجار 55"
        
        # البحث عن الاسم
        name_match = re.search(r'(?:طالبة جديدة:|أضف طالبة:)\s*([^،,]+)', message)
        if not name_match:
            return "الرجاء تحديد اسم الطالبة. مثال: أضف طالبة جديدة: فاطمة أحمد، جوال 0501234567"
        
        name = name_match.group(1).strip()
        
        # البحث عن رقم الجوال
        phone_match = re.search(r'(?:جوال|هاتف|موبايل)\s*:?\s*(\d+)', message)
        phone = phone_match.group(1) if phone_match else None
        
        # البحث عن رقم السرير
        bed_match = re.search(r'(?:غرفة|سرير)\s*:?\s*(K\d+)', message, re.IGNORECASE)
        bed_code = bed_match.group(1).upper() if bed_match else None
        
        # البحث عن الإيجار
        rent_match = re.search(r'(?:إيجار|ايجار)\s*:?\s*(\d+)', message)
        rent = float(rent_match.group(1)) if rent_match else 55.0
        
        if not bed_code:
            return "الرجاء تحديد رقم السرير. مثال: غرفة K6011"
        
        # التحقق من وجود السرير وأنه متاح
        bed = Bed.query.filter_by(bed_code=bed_code).first()
        if not bed:
            return f"السرير {bed_code} غير موجود في النظام."
        
        if bed.status != 'available':
            return f"السرير {bed_code} غير متاح حالياً."
        
        # إنشاء الطالبة
        student = Student(
            name=name,
            phone=phone,
            rent_amount=rent,
            contract_start=date.today(),
            status='active'
        )
        db.session.add(student)
        db.session.flush()  # للحصول على ID
        
        # تخصيص السرير
        assignment = BedAssignment(
            student_id=student.id,
            bed_id=bed.id,
            room_id=bed.room_id,
            start_date=date.today(),
            status='active'
        )
        db.session.add(assignment)
        
        # تحديث حالة السرير
        bed.status = 'occupied'
        
        db.session.commit()
        
        # معلومات إضافية
        room = Room.query.get(bed.room_id)
        building = Building.query.get(bed.building_id)
        
        response = f"✅ **تم تسجيل الطالبة بنجاح!**\n\n"
        response += f"**الاسم:** {name}\n"
        response += f"**الجوال:** {phone or 'غير محدد'}\n"
        response += f"**السرير:** {bed_code}\n"
        response += f"**الموقع:** {building.building_name} غرفة {room.room_number}\n"
        response += f"**الإيجار:** {rent} ريال شهرياً\n"
        response += f"**تاريخ البداية:** {date.today().strftime('%Y-%m-%d')}"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في تسجيل الطالبة: {str(e)}"

def handle_payment_record(message):
    """معالجة تسجيل دفعة"""
    try:
        # نمط: "فاطمة دفعت 55 ريال" أو "سميرة سددت 40"
        
        # البحث عن الاسم والمبلغ
        payment_match = re.search(r'(\w+)\s+(?:دفعت|دفع|سددت|سدد)\s+(\d+)', message)
        if not payment_match:
            return "الرجاء تحديد الاسم والمبلغ. مثال: فاطمة دفعت 55 ريال"
        
        name = payment_match.group(1)
        amount = float(payment_match.group(2))
        
        # البحث عن الطالبة
        student = Student.query.filter(Student.name.contains(name)).first()
        if not student:
            return f"لم يتم العثور على طالبة باسم {name}"
        
        # تسجيل الدفعة
        payment = Payment(
            student_id=student.id,
            amount=amount,
            payment_type='rent',
            payment_date=date.today(),
            month_year=datetime.now().strftime('%Y-%m'),
            status='confirmed'
        )
        db.session.add(payment)
        db.session.commit()
        
        # حساب إجمالي المدفوعات
        total_payments = sum([p.amount for p in student.payments if p.status == 'confirmed'])
        
        response = f"✅ **تم تسجيل الدفعة بنجاح!**\n\n"
        response += f"**الطالبة:** {student.name}\n"
        response += f"**المبلغ المدفوع:** {amount} ريال\n"
        response += f"**التاريخ:** {date.today().strftime('%Y-%m-%d')}\n"
        response += f"**إجمالي المدفوعات:** {total_payments} ريال"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في تسجيل الدفعة: {str(e)}"

def handle_expense_record(message):
    """معالجة تسجيل مصروف"""
    try:
        # نمط: "تصليح مكيف 50 ريال" أو "صيانة 30"
        
        expense_match = re.search(r'(تصليح|صيانة|فاتورة|مصروف)\s+(.+?)\s+(\d+)', message)
        if not expense_match:
            return "الرجاء تحديد نوع المصروف والمبلغ. مثال: تصليح مكيف 50 ريال"
        
        category = expense_match.group(1)
        description = expense_match.group(2).strip()
        amount = float(expense_match.group(3))
        
        # تحديد فئة المصروف
        category_map = {
            'تصليح': 'maintenance',
            'صيانة': 'maintenance',
            'فاتورة': 'utilities',
            'مصروف': 'other'
        }
        
        expense = Expense(
            description=f"{category} {description}",
            amount=amount,
            category=category_map.get(category, 'other'),
            expense_date=date.today()
        )
        db.session.add(expense)
        db.session.commit()
        
        response = f"✅ **تم تسجيل المصروف بنجاح!**\n\n"
        response += f"**الوصف:** {category} {description}\n"
        response += f"**المبلغ:** {amount} ريال\n"
        response += f"**التاريخ:** {date.today().strftime('%Y-%m-%d')}\n"
        response += f"**الفئة:** {category}"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في تسجيل المصروف: {str(e)}"

def show_system_statistics():
    """عرض إحصائيات النظام"""
    try:
        stats = get_system_statistics()
        
        response = f"📊 **إحصائيات النظام:**\n\n"
        response += f"🏢 **المباني والأسرة:**\n"
        response += f"• إجمالي الأسرة: {stats['total_beds']} سرير\n"
        response += f"• أسرة مشغولة: {stats['occupied_beds']} سرير\n"
        response += f"• أسرة متاحة: {stats['available_beds']} سرير\n"
        response += f"• معدل الإشغال: {stats['occupancy_rate']:.1f}%\n\n"
        
        response += f"👥 **الطالبات:**\n"
        response += f"• عدد الطالبات النشطات: {stats['total_students']}\n\n"
        
        response += f"💰 **الوضع المالي:**\n"
        response += f"• الإيرادات المتوقعة: {stats['expected_revenue']} ريال\n"
        response += f"• الإيرادات الفعلية: {stats['actual_revenue']} ريال\n"
        response += f"• إجمالي المصروفات: {stats['total_expenses']} ريال\n"
        response += f"• صافي الربح: {stats['net_profit']} ريال\n"
        
        # إضافة تفاصيل المباني
        buildings = Building.query.all()
        response += f"\n🏢 **تفاصيل المباني:**\n"
        for building in buildings:
            building_beds = Bed.query.filter_by(building_id=building.id).count()
            occupied = Bed.query.filter_by(building_id=building.id, status='occupied').count()
            response += f"• {building.building_name}: {occupied}/{building_beds} مشغول\n"
        
        return response
        
    except Exception as e:
        return f"حدث خطأ في عرض الإحصائيات: {str(e)}"

def handle_add_bed(message):
    """معالجة إضافة سرير جديد"""
    try:
        # نمط: "أضف سرير في غرفة K601" أو "سرير جديد K701"
        
        room_match = re.search(r'(?:غرفة|في)\s*(K\d+)', message, re.IGNORECASE)
        if not room_match:
            return "الرجاء تحديد رقم الغرفة. مثال: أضف سرير في غرفة K601"
        
        room_code = room_match.group(1).upper()
        
        # البحث عن الغرفة
        room = Room.query.filter_by(room_code=room_code).first()
        if not room:
            return f"الغرفة {room_code} غير موجودة في النظام."
        
        # البحث عن السعر (اختياري)
        price_match = re.search(r'(?:سعر|بسعر)\s*(\d+)', message)
        price = float(price_match.group(1)) if price_match else 55.0
        
        # إضافة السرير
        success, message_result = add_bed_to_room(room.id, price)
        
        if success:
            # إعادة تحميل الغرفة للحصول على البيانات المحدثة
            room = Room.query.get(room.id)
            building = Building.query.get(room.building_id)
            
            response = f"✅ **{message_result}**\n\n"
            response += f"**الغرفة:** {room_code}\n"
            response += f"**الموقع:** {building.building_name}\n"
            response += f"**عدد الأسرة الآن:** {room.total_beds} أسرة\n"
            response += f"**الإيرادات الشهرية:** {room.monthly_revenue} ريال"
            
            return response
        else:
            return f"❌ {message_result}"
        
    except Exception as e:
        return f"حدث خطأ في إضافة السرير: {str(e)}"

def show_building_info(message):
    """عرض معلومات مبنى محدد"""
    try:
        # البحث عن رمز المبنى
        building_match = re.search(r'(K\d+)', message, re.IGNORECASE)
        if building_match:
            building_code = building_match.group(1).upper()
            building = Building.query.filter_by(building_code=building_code).first()
            
            if not building:
                return f"المبنى {building_code} غير موجود في النظام."
            
            # إحصائيات المبنى
            total_beds = Bed.query.filter_by(building_id=building.id).count()
            occupied_beds = Bed.query.filter_by(building_id=building.id, status='occupied').count()
            available_beds = total_beds - occupied_beds
            
            response = f"🏢 **معلومات {building.building_name}:**\n\n"
            response += f"**رمز المبنى:** {building.building_code}\n"
            response += f"**عدد الغرف:** {building.total_rooms}\n"
            response += f"**إجمالي الأسرة:** {total_beds}\n"
            response += f"**أسرة مشغولة:** {occupied_beds}\n"
            response += f"**أسرة متاحة:** {available_beds}\n"
            response += f"**معدل الإشغال:** {(occupied_beds/total_beds*100):.1f}%\n"
            response += f"**الإيرادات المتوقعة:** {total_beds * 55} ريال شهرياً"
            
            return response
        else:
            # عرض جميع المباني
            buildings = Building.query.all()
            response = f"🏢 **جميع المباني ({len(buildings)}):**\n\n"
            
            for building in buildings:
                total_beds = Bed.query.filter_by(building_id=building.id).count()
                occupied_beds = Bed.query.filter_by(building_id=building.id, status='occupied').count()
                
                response += f"**{building.building_name} ({building.building_code}):**\n"
                response += f"• الغرف: {building.total_rooms}\n"
                response += f"• الأسرة: {occupied_beds}/{total_beds} مشغول\n"
                response += f"• الإيرادات: {total_beds * 55} ريال\n\n"
            
            return response
        
    except Exception as e:
        return f"حدث خطأ في عرض معلومات المبنى: {str(e)}"

def handle_general_query(message):
    """معالجة الاستفسارات العامة"""
    help_text = """
🤖 **مرحباً! أنا مساعدك الذكي لإدارة السكنات**

**الأوامر المتاحة:**

📋 **عرض المعلومات:**
• "اعرض الغرف المتاحة" - لعرض الأسرة الشاغرة
• "اعرض الطالبات" - لعرض الطالبات النشطات
• "إحصائيات" - لعرض ملخص النظام
• "مبنى K6" - لعرض معلومات مبنى محدد

👥 **إدارة الطالبات:**
• "أضف طالبة جديدة: فاطمة أحمد، جوال 0501234567، غرفة K6011"

💰 **المعاملات المالية:**
• "فاطمة دفعت 55 ريال" - لتسجيل دفعة
• "تصليح مكيف 50 ريال" - لتسجيل مصروف

🛏️ **إدارة الأسرة:**
• "أضف سرير في غرفة K601" - لإضافة سرير جديد

**جرب أي أمر من الأوامر أعلاه!**
    """
    
    return help_text


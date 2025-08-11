from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import re

# إنشاء التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = 'housing_management_secret_key_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'housing_system.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعداد CORS
CORS(app)

# إعداد قاعدة البيانات
db = SQLAlchemy(app)

# النماذج
class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True, nullable=False)
    floors = db.Column(db.Integer, default=3)
    rooms_per_floor = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    rooms = db.relationship('Room', backref='building', lazy=True, cascade='all, delete-orphan')

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(20), default='student')  # student, supervisor
    max_beds = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    beds = db.relationship('Bed', backref='room', lazy=True, cascade='all, delete-orphan')

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bed_id = db.Column(db.String(10), unique=True, nullable=False)  # KxYYZ format
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    price = db.Column(db.Float, default=55.0)
    is_occupied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='bed', uselist=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    national_id = db.Column(db.String(20), unique=True)
    university = db.Column(db.String(100))
    bed_id = db.Column(db.Integer, db.ForeignKey('bed.id'), nullable=False)
    check_in_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(20), default='rent')  # rent, deposit
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    student = db.relationship('Student', backref='payments')

# دوال مساعدة
def create_buildings_and_rooms():
    """إنشاء المباني والغرف والأسرة"""
    buildings_data = [
        {'name': 'K6', 'floors': 3, 'rooms_per_floor': 4},
        {'name': 'K7', 'floors': 3, 'rooms_per_floor': 4}
    ]
    
    for building_data in buildings_data:
        building = Building.query.filter_by(name=building_data['name']).first()
        if not building:
            building = Building(**building_data)
            db.session.add(building)
            db.session.commit()
            
            # إنشاء الغرف والأسرة
            for floor in range(1, building.floors + 1):
                # غرف الطالبات
                for room_num in range(1, building.rooms_per_floor + 1):
                    room_number = f"{building.name}{floor:02d}{room_num}"
                    room = Room(
                        number=room_number,
                        building_id=building.id,
                        floor=floor,
                        room_type='student',
                        max_beds=2
                    )
                    db.session.add(room)
                    db.session.commit()
                    
                    # إنشاء الأسرة
                    for bed_num in range(1, 3):  # سريرين في كل غرفة
                        bed_id = f"{building.name}{floor:01d}{room_num:02d}{bed_num}"
                        bed = Bed(
                            bed_id=bed_id,
                            room_id=room.id,
                            price=55.0
                        )
                        db.session.add(bed)
                
                # غرفة المشرفة
                supervisor_room_number = f"{building.name}{floor:02d}5"
                supervisor_room = Room(
                    number=supervisor_room_number,
                    building_id=building.id,
                    floor=floor,
                    room_type='supervisor',
                    max_beds=1
                )
                db.session.add(supervisor_room)
                db.session.commit()
                
                # سرير المشرفة
                supervisor_bed_id = f"{building.name}{floor:01d}051"
                supervisor_bed = Bed(
                    bed_id=supervisor_bed_id,
                    room_id=supervisor_room.id,
                    price=55.0
                )
                db.session.add(supervisor_bed)
            
            db.session.commit()

def process_ai_request(message):
    """معالجة طلبات الوكيل الذكي"""
    message = message.strip().lower()
    
    # إحصائيات النظام
    if any(word in message for word in ['إحصائيات', 'احصائيات', 'إحصائية', 'احصائية', 'نظرة عامة']):
        total_beds = Bed.query.count()
        occupied_beds = Bed.query.filter_by(is_occupied=True).count()
        available_beds = total_beds - occupied_beds
        total_students = Student.query.filter_by(is_active=True).count()
        total_buildings = Building.query.count()
        total_rooms = Room.query.count()
        
        monthly_revenue = total_beds * 55
        current_revenue = occupied_beds * 55
        
        return {
            'type': 'statistics',
            'data': {
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'available_beds': available_beds,
                'total_students': total_students,
                'total_buildings': total_buildings,
                'total_rooms': total_rooms,
                'monthly_revenue': monthly_revenue,
                'current_revenue': current_revenue,
                'occupancy_rate': round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0
            },
            'message': f"""📊 **إحصائيات النظام الشاملة:**

🏢 **المباني والغرف:**
• عدد المباني: {total_buildings} مباني (K6 + K7)
• إجمالي الغرف: {total_rooms} غرفة
• إجمالي الأسرة: {total_beds} سرير

🛏️ **حالة الأسرة:**
• الأسرة المشغولة: {occupied_beds} سرير
• الأسرة المتاحة: {available_beds} سرير
• معدل الإشغال: {round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0}%

👥 **الطالبات:**
• عدد الطالبات النشطات: {total_students} طالبة

💰 **الإيرادات:**
• الإيرادات المتوقعة: {monthly_revenue:,} ريال شهرياً
• الإيرادات الحالية: {current_revenue:,} ريال شهرياً

🎯 **نظام الترقيم:** KxYYZ (مثال: K6011, K7012)"""
        }
    
    # عدد الأسرة
    elif any(word in message for word in ['عدد الأسرة', 'كم سرير', 'عدد الاسرة', 'كم الاسرة']):
        total_beds = Bed.query.count()
        available_beds = Bed.query.filter_by(is_occupied=False).count()
        occupied_beds = total_beds - available_beds
        
        return {
            'type': 'beds_count',
            'data': {
                'total_beds': total_beds,
                'available_beds': available_beds,
                'occupied_beds': occupied_beds
            },
            'message': f"""🛏️ **إحصائيات الأسرة:**

• **إجمالي الأسرة:** {total_beds} سرير
• **الأسرة المتاحة:** {available_beds} سرير  
• **الأسرة المشغولة:** {occupied_beds} سرير

📍 **التوزيع:**
• مبنى K6: 26 سرير
• مبنى K7: 26 سرير

💡 **نظام الترقيم الجديد KxYYZ:**
مثال: K6011 (مبنى K6، غرفة 01، سرير 1)"""
        }
    
    # الغرف المتاحة
    elif any(word in message for word in ['غرف متاحة', 'اسرة متاحة', 'أسرة متاحة', 'غرف فارغة']):
        available_beds = Bed.query.filter_by(is_occupied=False).all()
        
        if available_beds:
            beds_list = []
            for bed in available_beds[:10]:  # أول 10 أسرة
                beds_list.append(f"• {bed.bed_id} - {bed.price} ريال")
            
            beds_text = "\\n".join(beds_list)
            more_text = f"\\n... و {len(available_beds) - 10} سرير آخر" if len(available_beds) > 10 else ""
            
            return {
                'type': 'available_beds',
                'data': {'beds': [bed.bed_id for bed in available_beds]},
                'message': f"""🟢 **الأسرة المتاحة ({len(available_beds)} سرير):**

{beds_text}{more_text}

💰 **السعر:** 55 ريال شهرياً لكل سرير
📞 **للحجز:** تواصل مع الإدارة"""
            }
        else:
            return {
                'type': 'no_available_beds',
                'data': {},
                'message': "❌ **لا توجد أسرة متاحة حالياً**\\n\\n📞 يرجى التواصل مع الإدارة للاستفسار عن قائمة الانتظار"
            }
    
    # رسالة افتراضية
    else:
        return {
            'type': 'help',
            'data': {},
            'message': """🤖 **مرحباً! أنا مساعد إدارة السكن الذكي**

يمكنني مساعدتك في:
• عرض إحصائيات النظام
• البحث عن الأسرة المتاحة  
• عرض معلومات الطالبات
• حساب الإيرادات والمدفوعات

💡 **جرب أن تسأل:**
• "إحصائيات النظام"
• "اعرض الغرف المتاحة"  
• "كم عدد الأسرة؟"

🎯 **النظام الجديد يدعم 52 سرير في مبنيين!**"""
        }

# المسارات
@app.route('/')
def index():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    password = data.get('password', '')
    
    if password == 'admin123':
        session['authenticated'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'كلمة مرور خاطئة'})

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'authenticated' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'الرسالة مطلوبة'}), 400
    
    response = process_ai_request(message)
    return jsonify(response)

@app.route('/api/students')
def get_students():
    if 'authenticated' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    students = Student.query.filter_by(is_active=True).all()
    students_data = []
    
    for student in students:
        students_data.append({
            'id': student.id,
            'name': student.name,
            'phone': student.phone,
            'national_id': student.national_id,
            'university': student.university,
            'bed_id': student.bed.bed_id if student.bed else None,
            'check_in_date': student.check_in_date.strftime('%Y-%m-%d') if student.check_in_date else None
        })
    
    return jsonify(students_data)

@app.route('/api/beds')
def get_beds():
    if 'authenticated' not in session:
        return jsonify({'error': 'غير مصرح'}), 401
    
    beds = Bed.query.all()
    beds_data = []
    
    for bed in beds:
        beds_data.append({
            'id': bed.id,
            'bed_id': bed.bed_id,
            'room_number': bed.room.number,
            'building_name': bed.room.building.name,
            'price': bed.price,
            'is_occupied': bed.is_occupied,
            'student_name': bed.student.name if bed.student else None
        })
    
    return jsonify(beds_data)

# إعداد قاعدة البيانات
def setup_database():
    """إعداد قاعدة البيانات الأولي"""
    with app.app_context():
        # إنشاء الجداول
        db.create_all()
        
        # التحقق من وجود البيانات
        if Building.query.count() == 0:
            print("🆕 تم إنشاء قاعدة البيانات الجديدة")
            create_buildings_and_rooms()
            
            buildings_count = Building.query.count()
            rooms_count = Room.query.count()
            beds_count = Bed.query.count()
            
            print(f"✅ تم إنشاء {buildings_count} مباني")
            print(f"✅ تم إنشاء {rooms_count} غرفة")
            print(f"✅ تم إنشاء {beds_count} سرير")
            print("🚀 النظام الجديد جاهز!")
        else:
            print("📊 قاعدة البيانات موجودة مسبقاً")

if __name__ == '__main__':
    setup_database()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)

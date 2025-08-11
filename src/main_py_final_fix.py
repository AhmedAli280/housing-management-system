"""
الحل الأول: إعادة بناء النظام بالكامل
ملف main.py جديد يستخدم النماذج الجديدة فقط
"""

import os
import sys

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# إنشاء التطبيق
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'housing_management_secret_key_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'housing_system_new.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعداد CORS وقاعدة البيانات
CORS(app)
db = SQLAlchemy(app)

# ===== النماذج الجديدة مباشرة في main.py =====

class Building(db.Model):
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True, nullable=False)  # K6, K7
    total_rooms = db.Column(db.Integer, nullable=False)
    
    rooms = db.relationship('Room', backref='building', lazy=True, cascade='all, delete-orphan')

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_number = db.Column(db.String(5), nullable=False)  # 01, 02, 03...
    max_beds = db.Column(db.Integer, default=2)
    
    beds = db.relationship('Bed', backref='room', lazy=True, cascade='all, delete-orphan')
    
    @property
    def full_room_code(self):
        return f"{self.building.name}{self.room_number}"

class Bed(db.Model):
    __tablename__ = 'beds'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    bed_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3...
    monthly_rent = db.Column(db.Float, default=55.0)
    is_occupied = db.Column(db.Boolean, default=False)
    
    assignments = db.relationship('BedAssignment', backref='bed', lazy=True)
    
    @property
    def bed_code(self):
        # نظام KxYYZ: K6011, K6012, K7011, K7012
        return f"{self.room.building.name}{self.room.room_number}{self.bed_number}"

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    national_id = db.Column(db.String(20))
    university = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(20))
    join_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    
    assignments = db.relationship('BedAssignment', backref='student', lazy=True)
    payments = db.relationship('Payment', backref='student', lazy=True)

class BedAssignment(db.Model):
    __tablename__ = 'bed_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    bed_id = db.Column(db.Integer, db.ForeignKey('beds.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_type = db.Column(db.String(20), default='rent')  # rent, deposit, other
    description = db.Column(db.Text)

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

# ===== إعداد البيانات الأولية =====

def setup_initial_data():
    """إعداد البيانات الأولية للنظام الجديد"""
    from datetime import date
    
    # إنشاء المباني
    k6 = Building(name='K6', total_rooms=13)
    k7 = Building(name='K7', total_rooms=13)
    db.session.add_all([k6, k7])
    db.session.commit()
    
    # إنشاء الغرف والأسرة
    for building in [k6, k7]:
        for room_num in range(1, 14):  # 13 غرفة
            room_number = f"{room_num:02d}"  # 01, 02, 03...
            room = Room(building_id=building.id, room_number=room_number, max_beds=2)
            db.session.add(room)
            db.session.commit()
            
            # إنشاء سريرين في كل غرفة
            for bed_num in [1, 2]:
                bed = Bed(room_id=room.id, bed_number=bed_num, monthly_rent=55.0)
                db.session.add(bed)
    
    db.session.commit()
    print(f"✅ تم إنشاء {Building.query.count()} مباني")
    print(f"✅ تم إنشاء {Room.query.count()} غرفة")
    print(f"✅ تم إنشاء {Bed.query.count()} سرير")

# ===== المسارات =====

@app.route('/')
def index():
    if not session.get('logged_in'):
        return send_from_directory(app.static_folder, 'login.html')
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
    password = request.json.get('password')
    if password == 'admin123':
        session['logged_in'] = True
        return {'success': True}
    return {'success': False}, 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return {'success': True}

@app.route('/api/ai_agent', methods=['POST'])
def ai_agent():
    if not session.get('logged_in'):
        return {'error': 'غير مصرح'}, 401
    
    message = request.json.get('message', '').strip()
    
    if 'إحصائيات' in message or 'احصائيات' in message:
        total_beds = Bed.query.count()
        occupied_beds = Bed.query.filter_by(is_occupied=True).count()
        available_beds = total_beds - occupied_beds
        total_students = Student.query.filter_by(is_active=True).count()
        total_buildings = Building.query.count()
        
        # حساب الإيرادات المتوقعة
        expected_revenue = total_beds * 55  # 55 ريال لكل سرير
        
        response = f"""📊 **إحصائيات النظام الجديد:**

🏢 **المباني:** {total_buildings} مباني (K6, K7)
🛏️ **إجمالي الأسرة:** {total_beds} سرير
✅ **الأسرة المتاحة:** {available_beds} سرير
👥 **الطالبات النشطات:** {total_students} طالبة
💰 **الإيرادات المتوقعة:** {expected_revenue} ريال شهرياً

🎯 **نظام الترقيم الجديد KxYYZ:**
- K6011, K6012 (مبنى K6، غرفة 01، سرير 1 و 2)
- K7011, K7012 (مبنى K7، غرفة 01، سرير 1 و 2)
- وهكذا حتى K6132, K7132

✨ **النظام الجديد يعمل بكامل طاقته!**"""
        
        return {
            'response': response,
            'actions': [
                {'text': 'تفاصيل أكثر', 'action': 'show_details'},
                {'text': 'عرض الغرف', 'action': 'show_rooms'}
            ]
        }
    
    elif 'غرف' in message or 'متاح' in message:
        available_beds = db.session.query(Bed).join(Room).join(Building).filter(
            Bed.is_occupied == False
        ).all()
        
        response = f"🛏️ **الأسرة المتاحة ({len(available_beds)} سرير):**\n\n"
        
        for bed in available_beds[:10]:  # أول 10 أسرة
            response += f"• **{bed.bed_code}** - {bed.monthly_rent} ريال شهرياً\n"
        
        if len(available_beds) > 10:
            response += f"\n... و {len(available_beds) - 10} سرير آخر متاح"
        
        return {
            'response': response,
            'actions': [
                {'text': 'عرض الكل', 'action': 'show_all_beds'},
                {'text': 'إضافة طالبة', 'action': 'add_student'}
            ]
        }
    
    else:
        return {
            'response': 'مرحباً! أنا مساعدك الذكي لإدارة السكن. يمكنني مساعدتك في:\n\n• عرض إحصائيات النظام\n• عرض الغرف المتاحة\n• إدارة الطالبات\n• تسجيل المدفوعات',
            'actions': [
                {'text': 'إحصائيات النظام', 'action': 'stats'},
                {'text': 'الغرف المتاحة', 'action': 'available_rooms'}
            ]
        }

# ===== تشغيل التطبيق =====

if __name__ == '__main__':
    with app.app_context():
        # حذف قاعدة البيانات القديمة إذا كانت موجودة
        db_path = os.path.join(os.path.dirname(__file__), 'housing_system_new.db')
        if os.path.exists(db_path):
            os.remove(db_path)
            print("🗑️ تم حذف قاعدة البيانات القديمة")
        
        # إنشاء قاعدة البيانات الجديدة
        db.create_all()
        print("🆕 تم إنشاء قاعدة البيانات الجديدة")
        
        # إعداد البيانات الأولية
        setup_initial_data()
        
        print("🚀 النظام الجديد جاهز!")
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5003)), debug=False)

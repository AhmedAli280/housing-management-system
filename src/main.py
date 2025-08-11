from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime

# إنشاء التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = 'housing_management_secret_key_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'housing_system.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعداد CORS
CORS(app)

# إعداد قاعدة البيانات
db = SQLAlchemy(app)

# النماذج المُبسطة
class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True, nullable=False)
    total_rooms = db.Column(db.Integer, default=13)
    total_beds = db.Column(db.Integer, default=26)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False)
    building_name = db.Column(db.String(10), nullable=False)
    beds_count = db.Column(db.Integer, default=2)
    is_occupied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    room_number = db.Column(db.String(10))
    check_in_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# دوال مساعدة
def create_initial_data():
    """إنشاء البيانات الأولية"""
    try:
        # إنشاء المباني
        if Building.query.count() == 0:
            k6 = Building(name='K6', total_rooms=13, total_beds=26)
            k7 = Building(name='K7', total_rooms=13, total_beds=26)
            db.session.add(k6)
            db.session.add(k7)
            
            # إنشاء الغرف
            for building in ['K6', 'K7']:
                for i in range(1, 14):  # 13 غرفة
                    room_number = f"{building}{i:02d}"
                    room = Room(
                        number=room_number,
                        building_name=building,
                        beds_count=2,
                        is_occupied=False
                    )
                    db.session.add(room)
            
            db.session.commit()
            print(f"✅ تم إنشاء 2 مباني و 26 غرفة و 52 سرير")
            return True
    except Exception as e:
        print(f"❌ خطأ في إنشاء البيانات: {e}")
        return False

def process_ai_request(message):
    """معالجة طلبات الوكيل الذكي"""
    try:
        message = message.strip().lower()
        
        # إحصائيات النظام
        if any(word in message for word in ['إحصائيات', 'احصائيات', 'نظرة عامة']):
            total_buildings = Building.query.count()
            total_rooms = Room.query.count()
            total_beds = total_buildings * 26  # 26 سرير لكل مبنى
            occupied_rooms = Room.query.filter_by(is_occupied=True).count()
            available_rooms = total_rooms - occupied_rooms
            
            return {
                'type': 'statistics',
                'message': f"""📊 **إحصائيات النظام:**

🏢 **المباني:** {total_buildings} مباني (K6 + K7)
🏠 **الغرف:** {total_rooms} غرفة
🛏️ **الأسرة:** {total_beds} سرير
🟢 **متاح:** {available_rooms} غرفة
🔴 **مشغول:** {occupied_rooms} غرفة

💰 **الإيرادات المتوقعة:** {total_beds * 55:,} ريال شهرياً

🎯 **النظام جاهز لاستقبال بيانات Excel الحقيقية!**"""
            }
        
        # عدد الأسرة
        elif any(word in message for word in ['عدد الأسرة', 'كم سرير', 'عدد الاسرة']):
            total_beds = Building.query.count() * 26
            return {
                'type': 'beds_count',
                'message': f"""🛏️ **عدد الأسرة:**

• **إجمالي الأسرة:** {total_beds} سرير
• **مبنى K6:** 26 سرير
• **مبنى K7:** 26 سرير

📋 **جاهز لاستقبال بيانات Excel مع:**
• أسماء الساكنين
• أرقام الغرف الفعلية
• عدد الأسرة في كل غرفة"""
            }
        
        # الغرف المتاحة
        elif any(word in message for word in ['غرف متاحة', 'غرف فارغة']):
            available_rooms = Room.query.filter_by(is_occupied=False).all()
            if available_rooms:
                rooms_list = [f"• {room.number}" for room in available_rooms[:10]]
                rooms_text = "\n".join(rooms_list)
                more_text = f"\n... و {len(available_rooms) - 10} غرفة أخرى" if len(available_rooms) > 10 else ""
                
                return {
                    'type': 'available_rooms',
                    'message': f"""🟢 **الغرف المتاحة ({len(available_rooms)} غرفة):**

{rooms_text}{more_text}

📤 **جاهز لرفع ملف Excel** مع بيانات الساكنين الحقيقية"""
                }
            else:
                return {
                    'type': 'no_available_rooms',
                    'message': "📊 **جميع الغرف محجوزة حسب البيانات الحالية**\n\n📤 **ارفع ملف Excel** لتحديث البيانات الفعلية"
                }
        
        # رسالة افتراضية
        else:
            return {
                'type': 'help',
                'message': """🤖 **مرحباً! نظام إدارة السكن جاهز**

📊 **النظام الحالي:**
• 2 مباني (K6 + K7)
• 52 سرير إجمالي
• جاهز لاستقبال بيانات Excel

💡 **جرب:**
• "إحصائيات النظام"
• "كم عدد الأسرة؟"
• "اعرض الغرف المتاحة"

📤 **التالي:** رفع ملف Excel مع بيانات الساكنين الحقيقية"""
            }
    except Exception as e:
        return {
            'type': 'error',
            'message': f"❌ خطأ في معالجة الطلب: {str(e)}"
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
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if password == 'admin123':
            session['authenticated'] = True
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'كلمة مرور خاطئة'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}'})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        if 'authenticated' not in session:
            return jsonify({'error': 'غير مصرح'}), 401
        
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'الرسالة مطلوبة'}), 400
        
        response = process_ai_request(message)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': f'خطأ في الخادم: {str(e)}'}), 500

@app.route('/api/stats')
def get_stats():
    try:
        if 'authenticated' not in session:
            return jsonify({'error': 'غير مصرح'}), 401
        
        total_buildings = Building.query.count()
        total_rooms = Room.query.count()
        total_beds = total_buildings * 26
        
        return jsonify({
            'buildings': total_buildings,
            'rooms': total_rooms,
            'beds': total_beds,
            'status': 'ready_for_excel'
        })
    except Exception as e:
        return jsonify({'error': f'خطأ: {str(e)}'}), 500

# إعداد قاعدة البيانات
def setup_database():
    """إعداد قاعدة البيانات"""
    try:
        with app.app_context():
            db.create_all()
            
            if Building.query.count() == 0:
                print("🆕 إنشاء قاعدة البيانات الجديدة...")
                success = create_initial_data()
                if success:
                    print("🚀 النظام جاهز لاستقبال بيانات Excel!")
                else:
                    print("⚠️ تم إنشاء قاعدة البيانات الأساسية")
            else:
                print("📊 قاعدة البيانات موجودة")
                
    except Exception as e:
        print(f"❌ خطأ في إعداد قاعدة البيانات: {e}")

if __name__ == '__main__':
    setup_database()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)


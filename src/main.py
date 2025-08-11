from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os

# إنشاء التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = 'housing_secret_2025'

# بيانات مؤقتة في الذاكرة
system_data = {
    'buildings': ['K6', 'K7'],
    'total_rooms': 26,
    'total_beds': 52,
    'students': [],
    'ready_for_excel': True
}

def process_chat(message):
    """معالج الوكيل الذكي البسيط"""
    message = message.lower().strip()
    
    if 'إحصائيات' in message or 'احصائيات' in message:
        return f"""📊 **إحصائيات النظام:**

🏢 المباني: {len(system_data['buildings'])} مباني (K6 + K7)
🏠 الغرف: {system_data['total_rooms']} غرفة  
🛏️ الأسرة: {system_data['total_beds']} سرير

💰 الإيرادات المتوقعة: {system_data['total_beds'] * 55:,} ريال شهرياً

✅ النظام جاهز لاستقبال ملف Excel مع بيانات الساكنين الحقيقية!"""

    elif 'عدد' in message and ('أسرة' in message or 'اسرة' in message):
        return f"""🛏️ **عدد الأسرة:**

• إجمالي الأسرة: {system_data['total_beds']} سرير
• مبنى K6: 26 سرير
• مبنى K7: 26 سرير

📤 جاهز لرفع ملف Excel مع:
• أسماء الساكنين
• أرقام الغرف الفعلية  
• عدد الأسرة في كل غرفة"""

    elif 'غرف' in message and 'متاح' in message:
        return f"""🟢 **الغرف المتاحة:**

النظام جاهز لاستقبال البيانات الحقيقية من ملف Excel

📋 سيتم تحديث حالة الغرف بناءً على:
• أسماء الساكنين الفعليين
• أرقام الغرف المشغولة
• عدد الأسرة في كل غرفة"""

    else:
        return """🤖 **مرحباً! نظام إدارة السكن**

📊 النظام الحالي:
• 2 مباني (K6 + K7)
• 52 سرير إجمالي
• جاهز لاستقبال بيانات Excel

💡 جرب:
• "إحصائيات النظام"
• "كم عدد الأسرة؟"
• "اعرض الغرف المتاحة"

📤 التالي: رفع ملف Excel مع البيانات الحقيقية"""

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
    
    response_text = process_chat(message)
    return jsonify({
        'type': 'response',
        'message': response_text
    })

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'working',
        'buildings': system_data['buildings'],
        'total_beds': system_data['total_beds'],
        'ready_for_excel': system_data['ready_for_excel']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 تشغيل النظام البسيط...")
    print(f"📊 {system_data['total_beds']} سرير في {len(system_data['buildings'])} مباني")
    print("✅ جاهز لاستقبال بيانات Excel!")
    app.run(host='0.0.0.0', port=port, debug=False)


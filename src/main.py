from flask import Flask, jsonify, request
import os

# إنشاء التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = 'housing_secret_2025'

# بيانات النظام
system_data = {
    'buildings': ['K6', 'K7'],
    'total_rooms': 26,
    'total_beds': 52,
    'students': [],
    'ready_for_excel': True,
    'status': 'working'
}

def process_chat(message):
    """معالج الوكيل الذكي البسيط"""
    message = message.lower().strip()
    
    if 'إحصائيات' in message or 'احصائيات' in message:
        return f"""📊 إحصائيات النظام:

🏢 المباني: {len(system_data['buildings'])} مباني (K6 + K7)
🏠 الغرف: {system_data['total_rooms']} غرفة  
🛏️ الأسرة: {system_data['total_beds']} سرير

💰 الإيرادات المتوقعة: {system_data['total_beds'] * 55:,} ريال شهرياً

✅ النظام جاهز لاستقبال ملف Excel مع بيانات الساكنين الحقيقية!"""

    elif 'عدد' in message and ('أسرة' in message or 'اسرة' in message):
        return f"""🛏️ عدد الأسرة:

• إجمالي الأسرة: {system_data['total_beds']} سرير
• مبنى K6: 26 سرير
• مبنى K7: 26 سرير

📤 جاهز لرفع ملف Excel مع:
• أسماء الساكنين
• أرقام الغرف الفعلية  
• عدد الأسرة في كل غرفة"""

    elif 'غرف' in message and 'متاح' in message:
        return f"""🟢 الغرف المتاحة:

النظام جاهز لاستقبال البيانات الحقيقية من ملف Excel

📋 سيتم تحديث حالة الغرف بناءً على:
• أسماء الساكنين الفعليين
• أرقام الغرف المشغولة
• عدد الأسرة في كل غرفة"""

    else:
        return """🤖 مرحباً! نظام إدارة السكن

📊 النظام الحالي:
• 2 مباني (K6 + K7)
• 52 سرير إجمالي
• جاهز لاستقبال بيانات Excel

💡 جرب:
• "إحصائيات النظام"
• "كم عدد الأسرة؟"
• "اعرض الغرف المتاحة"

📤 التالي: رفع ملف Excel مع البيانات الحقيقية"""

# الصفحة الرئيسية
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>نظام إدارة السكن</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
            .chat-container { border: 1px solid #ddd; border-radius: 10px; height: 400px; overflow-y: auto; padding: 15px; margin-bottom: 20px; background: #fafafa; }
            .input-container { display: flex; gap: 10px; }
            input[type="text"] { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            button { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #2980b9; }
            .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .user-message { background: #e3f2fd; text-align: right; }
            .bot-message { background: #f1f8e9; text-align: right; white-space: pre-line; }
            .status { background: #4caf50; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏠 نظام إدارة سكنات الطالبات</h1>
                <div class="status">✅ النظام يعمل - 52 سرير في مبنيين جاهز لاستقبال بيانات Excel</div>
            </div>
            
            <div id="chat-container" class="chat-container">
                <div class="message bot-message">🤖 مرحباً! أنا الوكيل الذكي لنظام إدارة السكن. جرب: "إحصائيات النظام"</div>
            </div>
            
            <div class="input-container">
                <input type="text" id="messageInput" placeholder="اكتب رسالتك هنا..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">إرسال</button>
            </div>
        </div>

        <script>
            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                if (!message) return;

                // عرض رسالة المستخدم
                addMessage(message, 'user-message');
                input.value = '';

                // إرسال الرسالة للخادم
                fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                })
                .then(response => response.json())
                .then(data => {
                    addMessage(data.message, 'bot-message');
                })
                .catch(error => {
                    addMessage('عذراً، حدث خطأ في الاتصال.', 'bot-message');
                });
            }

            function addMessage(text, className) {
                const container = document.getElementById('chat-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + className;
                messageDiv.textContent = text;
                container.appendChild(messageDiv);
                container.scrollTop = container.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

# API للوكيل الذكي
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'الرسالة مطلوبة'}), 400
        
        response_text = process_chat(message)
        return jsonify({
            'type': 'response',
            'message': response_text
        })
    except Exception as e:
        return jsonify({'message': f'خطأ: {str(e)}'})

# API لحالة النظام
@app.route('/api/status')
def status():
    return jsonify(system_data)

# صفحة اختبار
@app.route('/test')
def test():
    return jsonify({
        'message': 'النظام يعمل بمثالية!',
        'buildings': system_data['buildings'],
        'total_beds': system_data['total_beds'],
        'status': 'success'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 تشغيل النظام البسيط...")
    print(f"📊 {system_data['total_beds']} سرير في {len(system_data['buildings'])} مباني")
    print("✅ جاهز لاستقبال بيانات Excel!")
    app.run(host='0.0.0.0', port=port, debug=False)

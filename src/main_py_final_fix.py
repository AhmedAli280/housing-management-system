import os
import sys

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, session, redirect, url_for, request
from models.user import db
from routes.user import user_bp
from routes.housing import housing_bp
from routes.ai_agent import ai_agent_bp
from routes.ai_agent_enhanced import ai_agent_enhanced_bp
from routes.archive_system import archive_system_bp
from routes.dashboard_advanced import dashboard_advanced_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'housing_management_secret_key_2025'

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(housing_bp, url_prefix='/api')
app.register_blueprint(ai_agent_bp, url_prefix='/api')
app.register_blueprint(ai_agent_enhanced_bp, url_prefix='/api')
app.register_blueprint(archive_system_bp, url_prefix='/api')
app.register_blueprint(dashboard_advanced_bp, url_prefix='/api')

# إعداد قاعدة البيانات - استخدام النماذج الجديدة
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'housing_system.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# إجبار استخدام النماذج الجديدة
with app.app_context():
    # استيراد النماذج الجديدة
    from models.core import Building, Room, Bed, Student, BedAssignment, Payment, Expense, Archive
    from models.core import setup_initial_data
    
    # إنشاء الجداول
    db.create_all()
    
    # إعداد البيانات الأولية إذا لم تكن موجودة
    if Building.query.count() == 0:
        setup_initial_data()
        print("✅ تم إعداد البيانات الأولية للنظام الجديد (52 سرير، مبنيين)")
    else:
        print("✅ النظام الجديد يعمل - البيانات موجودة")

@app.route('/')
def index():
    # التحقق من تسجيل الدخول
    if not session.get('logged_in'):
        return send_from_directory(app.static_folder, 'login.html')
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/dashboard_advanced.html')
def dashboard_advanced():
    if not session.get('logged_in'):
        return redirect('/')
    return app.send_static_file('dashboard_advanced.html')

@app.route('/archive_management.html')
def archive_management():
    if not session.get('logged_in'):
        return redirect('/')
    return app.send_static_file('archive_management.html')

@app.route('/login.html')
def login_page():
    return app.send_static_file('login.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # التحقق من تسجيل الدخول للصفحات المحمية
    if path == 'index.html' and not session.get('logged_in'):
        return redirect('/login')
    
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404
    
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        # إذا لم يكن مسار دقيق، إعادة توجيه لصفحة الدخول
        return redirect('/login') if not session.get('logged_in') else send_from_directory(static_folder_path, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5003)), debug=False)


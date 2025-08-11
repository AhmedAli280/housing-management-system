import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, session, redirect, url_for, request
from src.models.user import db
from src.routes.user import user_bp
from src.routes.housing import housing_bp
from src.routes.ai_agent import ai_agent_bp
from src.routes.auth import auth_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'housing_management_secret_key_2025'

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(housing_bp, url_prefix='/api')
app.register_blueprint(ai_agent_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # التحقق من تسجيل الدخول
    if not session.get('logged_in'):
        return send_from_directory(app.static_folder, 'login.html')
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # التحقق من تسجيل الدخول للملفات المحمية
    if path == 'index.html' and not session.get('logged_in'):
        return redirect('/login')
    
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        # إذا لم يكن مسجل دخول، إعادة توجيه لصفحة تسجيل الدخول
        if not session.get('logged_in'):
            return send_from_directory(app.static_folder, 'login.html')
        
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)


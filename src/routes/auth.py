from flask import Blueprint, request, jsonify, session, redirect, url_for
from functools import wraps
import hashlib

auth_bp = Blueprint('auth', __name__)

# كلمة المرور المشفرة (يمكن تغييرها)
# كلمة المرور الافتراضية: "admin123"
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"

def hash_password(password):
    """تشفير كلمة المرور"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """ديكوريتر للتحقق من تسجيل الدخول"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'يجب تسجيل الدخول أولاً', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    data = request.get_json()
    password = data.get('password', '')
    
    if hash_password(password) == ADMIN_PASSWORD_HASH:
        session['logged_in'] = True
        return jsonify({'success': True, 'message': 'تم تسجيل الدخول بنجاح'})
    else:
        return jsonify({'success': False, 'message': 'كلمة المرور غير صحيحة'}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """تسجيل الخروج"""
    session.pop('logged_in', None)
    return jsonify({'success': True, 'message': 'تم تسجيل الخروج بنجاح'})

@auth_bp.route('/check-auth', methods=['GET'])
def check_auth():
    """التحقق من حالة تسجيل الدخول"""
    return jsonify({'logged_in': session.get('logged_in', False)})

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """تغيير كلمة المرور"""
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    global ADMIN_PASSWORD_HASH
    
    if hash_password(old_password) != ADMIN_PASSWORD_HASH:
        return jsonify({'success': False, 'message': 'كلمة المرور القديمة غير صحيحة'}), 401
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل'}), 400
    
    # في التطبيق الحقيقي، يجب حفظ كلمة المرور الجديدة في قاعدة البيانات
    ADMIN_PASSWORD_HASH = hash_password(new_password)
    
    return jsonify({'success': True, 'message': 'تم تغيير كلمة المرور بنجاح'})


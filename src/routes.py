import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Blueprint, jsonify, render_template, request,
    redirect, url_for, flash, session, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash

main_bp = Blueprint('main', __name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'quiz_app.db')
LOCK_DURATION_MINUTES = 15
MAX_FAILED_ATTEMPTS = 5
SESSION_TIMEOUT_MINUTES = 30

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo và nâng cấp bảng users, bảng login_logs"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            failed_attempts INTEGER DEFAULT 0,
            locked_until TEXT DEFAULT NULL
        )
    ''')

    # Bổ sung các cột bảo mật nếu bảng users cũ chưa có
    cursor.execute("PRAGMA table_info(users)")
    columns = [col['name'] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    if 'failed_attempts' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    if 'locked_until' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN locked_until TEXT DEFAULT NULL")

    # Bảng ghi nhận lịch sử đăng nhập an toàn (không lưu mật khẩu hay token nhạy cảm)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

def log_login_attempt(email, status, reason):
    """Ghi nhận lịch sử đăng nhập"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO login_logs (email, status, reason, ip_address, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (email, status, reason, request.remote_addr, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Tự động hủy phiên sau 30 phút không hoạt động
@main_bp.before_app_request
def check_session_timeout():
    current_app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    if 'user_id' in session:
        now = datetime.now()
        last_activity_str = session.get('last_activity')
        if last_activity_str:
            last_activity = datetime.fromisoformat(last_activity_str)
            if (now - last_activity) > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                session.clear()
                flash('Phiên làm việc đã hết hạn sau 30 phút không hoạt động. Vui lòng đăng nhập lại!', 'error')
                return redirect(url_for('main.login'))
        session['last_activity'] = now.isoformat()
        session.modified = True

# Decorator phân quyền bảo vệ tuyến đường
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Unauthorized"}), 401
                flash('Vui lòng đăng nhập để tiếp tục!', 'error')
                return redirect(url_for('main.login'))

            user_role = session.get('role')
            if allowed_roles and user_role not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Forbidden - Không có quyền truy cập"}), 403
                flash('Bạn không có quyền truy cập vào chức năng này!', 'error')
                return redirect(url_for('main.redirect_by_role'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

@main_bp.route('/')
def health_check():
    if 'user_id' in session:
        return redirect(url_for('main.redirect_by_role'))
    return redirect(url_for('main.login'))

# Task S3-02: Đăng ký tài khoản Student
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not fullname or not email or not password or not confirm_password:
            flash('Vui lòng điền đầy đủ tất cả các trường!', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự!', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        role = 'Student'

        try:
            conn = get_db_connection()
            existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
            if existing_user:
                flash('Email này đã được đăng ký trước đó!', 'error')
                conn.close()
                return render_template('register.html')

            conn.execute('''
                INSERT INTO users (fullname, email, password, role, status, failed_attempts)
                VALUES (?, ?, ?, ?, 'active', 0)
            ''', (fullname, email, hashed_password, role))
            conn.commit()
            conn.close()

            flash('Đăng ký tài khoản Student thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            flash(f'Lỗi hệ thống: {str(e)}', 'error')
            return render_template('register.html')

    return render_template('register.html')

# Task S3-03: Đăng nhập hệ thống an toàn
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Vui lòng nhập đầy đủ email và mật khẩu!', 'error')
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        # Không tiết lộ thông tin email có tồn tại hay không
        if not user:
            conn.close()
            log_login_attempt(email, 'FAILED', 'Invalid credentials')
            flash('Email hoặc mật khẩu không chính xác!', 'error')
            return render_template('login.html')

        # Kiểm tra tài khoản bị khóa hoặc vô hiệu hóa
        if user['status'] != 'active':
            conn.close()
            log_login_attempt(email, 'FAILED', 'Account inactive or locked')
            flash('Tài khoản của bạn đã bị khóa hoặc ngừng hoạt động!', 'error')
            return render_template('login.html')

        # Kiểm tra khóa tạm thời do nhập sai quá 5 lần
        now = datetime.now()
        if user['locked_until']:
            locked_until = datetime.fromisoformat(user['locked_until'])
            if now < locked_until:
                remaining_mins = int((locked_until - now).total_seconds() // 60) + 1
                conn.close()
                log_login_attempt(email, 'FAILED', 'Temporarily locked')
                flash(f'Tài khoản tạm khóa do nhập sai nhiều lần. Thử lại sau {remaining_mins} phút!', 'error')
                return render_template('login.html')
            else:
                conn.execute('UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?', (user['id'],))
                conn.commit()

        # Kiểm tra mật khẩu
        if not check_password_hash(user['password'], password):
            new_attempts = (user['failed_attempts'] or 0) + 1
            if new_attempts >= MAX_FAILED_ATTEMPTS:
                lock_time = (now + timedelta(minutes=LOCK_DURATION_MINUTES)).isoformat()
                conn.execute(
                    'UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?',
                    (new_attempts, lock_time, user['id'])
                )
                conn.commit()
                conn.close()
                log_login_attempt(email, 'FAILED', 'Locked after 5 failed attempts')
                flash(f'Bạn đã nhập sai {MAX_FAILED_ATTEMPTS} lần liên tiếp. Tài khoản bị tạm khóa {LOCK_DURATION_MINUTES} phút!', 'error')
            else:
                conn.execute('UPDATE users SET failed_attempts = ? WHERE id = ?', (new_attempts, user['id']))
                conn.commit()
                conn.close()
                log_login_attempt(email, 'FAILED', f'Wrong password ({new_attempts}/{MAX_FAILED_ATTEMPTS})')
                flash('Email hoặc mật khẩu không chính xác!', 'error')
            return render_template('login.html')

        # Đăng nhập thành công: Reset lỗi, tái sinh session chống Session Fixation
        conn.execute('UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?', (user['id'],))
        conn.commit()
        conn.close()

        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['fullname'] = user['fullname']
        session['email'] = user['email']
        session['role'] = user['role']
        session['last_activity'] = now.isoformat()

        log_login_attempt(email, 'SUCCESS', 'Login successful')
        return redirect(url_for('main.redirect_by_role'))

    return render_template('login.html')

# Điều hướng linh hoạt theo vai trò
@main_bp.route('/dashboard')
@role_required('Admin', 'Teacher', 'Student')
def redirect_by_role():
    role = session.get('role')
    if role == 'Admin':
        return redirect(url_for('main.admin_dashboard'))
    elif role == 'Teacher':
        return redirect(url_for('main.teacher_dashboard'))
    return redirect(url_for('main.student_dashboard'))

@main_bp.route('/admin/dashboard')
@role_required('Admin')
def admin_dashboard():
    return f"Chào mừng Admin: {session.get('fullname')} | <a href='/logout'>Đăng xuất</a>"

@main_bp.route('/teacher/dashboard')
@role_required('Teacher')
def teacher_dashboard():
    return f"Chào mừng Teacher: {session.get('fullname')} | <a href='/logout'>Đăng xuất</a>"

@main_bp.route('/student/dashboard')
@role_required('Student')
def student_dashboard():
    return f"Chào mừng Student: {session.get('fullname')} | <a href='/logout'>Đăng xuất</a>"

# Đăng xuất và hủy phiên làm việc an toàn
@main_bp.route('/logout')
def logout():
    session.clear()
    flash('Đăng xuất thành công!', 'success')
    return redirect(url_for('main.login'))
import os
import sqlite3
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

main_bp = Blueprint('main', __name__)

# Xác định đường dẫn lưu file database (nằm trong thư mục database/ của project)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'quiz_app.db')

def init_db():
    """Hàm tự động tạo bảng users nếu chưa tồn tại"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Khởi tạo bảng ngay khi ứng dụng nạp route
init_db()

# Route kiểm tra hệ thống
@main_bp.route('/')
def health_check():
    return jsonify({
        "status": "success",
        "message": "Ứng dụng Flask đã khởi động thành công!"
    })

# Route đăng ký tài khoản Student
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Lấy dữ liệu từ form và làm sạch khoảng trắng
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 2. Kiểm tra các trường bắt buộc
        if not fullname or not email or not password or not confirm_password:
            flash('Vui lòng điền đầy đủ tất cả các trường!', 'error')
            return render_template('register.html')

        # 3. Kiểm tra độ dài mật khẩu (tối thiểu 6 ký tự)
        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự!', 'error')
            return render_template('register.html')

        # 4. Kiểm tra mật khẩu xác nhận
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return render_template('register.html')

        # 5. Băm mật khẩu an toàn
        hashed_password = generate_password_hash(password)
        role = 'Student'

        try:
            # Kết nối tới SQLite database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # 6. Kiểm tra xem email đã tồn tại trong database chưa
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Email này đã được đăng ký trước đó!', 'error')
                conn.close()
                return render_template('register.html')

            # 7. Lưu thông tin tài khoản mới vào bảng users
            cursor.execute('''
                INSERT INTO users (fullname, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', (fullname, email, hashed_password, role))

            conn.commit()
            conn.close()

            # 8. Thông báo thành công
            flash('Đăng ký tài khoản Student thành công!', 'success')
            return redirect(url_for('main.register'))

        except Exception as e:
            flash(f'Lỗi hệ thống: {str(e)}', 'error')
            return render_template('register.html')

    return render_template('register.html')
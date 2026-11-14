from flask import Flask
from src.routes import main_bp

app = Flask(__name__, template_folder='src/templates')
app.secret_key = 'quiz_examination_secret_key'  # Khóa bảo mật cho session và flash message

# Đăng ký Blueprint
app.register_blueprint(main_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
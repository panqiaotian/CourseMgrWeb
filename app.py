# 课程管理系统 - Web版
# 基于Flask的B/S架构实现

import os
import json
import secrets
from datetime import datetime, date, time
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_wtf.csrf import CSRFProtect
try:
    from werkzeug.urls import url_parse
except ImportError:
    from urllib.parse import urlparse as url_parse
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import hashlib
import secrets
import bcrypt
import base64
import json
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from captcha_generator import captcha_generator
import csv
import io

def generate_password_hash(password, method=None):
    """
    使用bcrypt生成安全的密码哈希
    bcrypt自动处理盐值，比SHA256更安全
    """
    if isinstance(password, str):
        password = password.encode('utf-8')
    # 使用bcrypt生成哈希，cost=12提供良好的安全性和性能平衡
    return bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode('utf-8')

def check_password_hash(hash_value, password):
    """
    验证密码哈希，支持向后兼容
    """
    if not hash_value or not password:
        return False
    
    # 检查是否是bcrypt哈希（以$2b$开头）
    if hash_value.startswith('$2b$'):
        # 新的bcrypt哈希
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(hash_value, str):
            hash_value = hash_value.encode('utf-8')
        return bcrypt.checkpw(password, hash_value)
    else:
        # 旧的SHA256哈希，向后兼容
        import hashlib
        return hash_value == hashlib.sha256(password.encode()).hexdigest()

# 登录失败跟踪
login_attempts = {}  # 格式: {ip: {'count': int, 'locked_until': datetime, 'lock_count': int}}

# IP速率限制跟踪
rate_limit_attempts = {}  # 格式: {ip: [timestamp1, timestamp2, ...]}

def clean_expired_rate_limit_records():
    """清理过期的速率限制记录"""
    current_time = datetime.now()
    expired_ips = []
    
    for ip, attempts in rate_limit_attempts.items():
        # 移除超过1分钟的记录
        rate_limit_attempts[ip] = [
            timestamp for timestamp in attempts 
            if (current_time - timestamp).total_seconds() < 60
        ]
        # 如果该IP没有有效记录，标记为过期
        if not rate_limit_attempts[ip]:
            expired_ips.append(ip)
    
    # 删除过期的IP记录
    for ip in expired_ips:
        del rate_limit_attempts[ip]

def is_rate_limited(ip):
    """检查IP是否超过速率限制（每分钟5次）"""
    clean_expired_rate_limit_records()
    
    if ip not in rate_limit_attempts:
        return False
    
    current_time = datetime.now()
    # 计算过去1分钟内的尝试次数
    recent_attempts = [
        timestamp for timestamp in rate_limit_attempts[ip]
        if (current_time - timestamp).total_seconds() < 60
    ]
    
    return len(recent_attempts) >= 5

def record_rate_limit_attempt(ip):
    """记录IP的登录尝试"""
    current_time = datetime.now()
    
    if ip not in rate_limit_attempts:
        rate_limit_attempts[ip] = []
    
    rate_limit_attempts[ip].append(current_time)
    
    # 记录日志
    if len(rate_limit_attempts[ip]) >= 5:
        app.logger.warning(f'IP {ip} 触发速率限制：1分钟内尝试登录{len(rate_limit_attempts[ip])}次')

def get_client_ip():
    """获取客户端真实IP地址"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        # 如果使用了代理，获取真实IP
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR', '127.0.0.1')

def is_ip_locked(ip):
    """检查IP是否被锁定"""
    if ip not in login_attempts:
        return False
    
    attempt_info = login_attempts[ip]
    if 'locked_until' in attempt_info and attempt_info['locked_until']:
        if datetime.now() < attempt_info['locked_until']:
            return True
        else:
            # 锁定时间已过，重置计数但保留锁定历史
            attempt_info['locked_until'] = None
            attempt_info['count'] = 0
    
    return False

def record_failed_login(ip):
    """记录登录失败"""
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': None, 'lock_count': 0}
    
    login_attempts[ip]['count'] += 1
    
    # 如果失败次数达到5次，锁定IP
    if login_attempts[ip]['count'] >= 5:
        lock_count = login_attempts[ip].get('lock_count', 0) + 1
        login_attempts[ip]['lock_count'] = lock_count
        
        # 锁定时间：5分钟 * 锁定次数（叠加机制）
        lock_minutes = 5 * lock_count
        login_attempts[ip]['locked_until'] = datetime.now() + timedelta(minutes=lock_minutes)
        login_attempts[ip]['count'] = 0  # 重置失败计数
        
        return lock_minutes
    
    return 0

def reset_login_attempts(ip):
    """登录成功后重置失败计数"""
    if ip in login_attempts:
        login_attempts[ip]['count'] = 0
        # 注意：不重置lock_count，保持锁定历史用于叠加机制

# reCAPTCHA功能已移除，使用图片验证码替代

# RSA密钥管理 - 使用持久化密钥管理器
# 本地RSAKeyManager类已移除，统一使用persistent_rsa_manager

# RSA密钥管理已移除，使用简化的登录方式
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, scoped_session

# 导入数据模型
import json
from models import Base, Student, Schedule, CourseRecord, ScheduleStudent, RecordStudent, \
    ExamRecord, StudentScore, StudentGroup, GroupStudent, Payment, CourseEnrollment, User, Teacher, SemesterTag

# 分页参数验证函数
def validate_pagination_params(page, per_page, search):
    """验证和规范化分页参数"""
    # 验证页码
    if page < 1:
        page = 1
    
    # 验证每页显示数量
    if per_page not in [10, 25, 50]:
        per_page = 10
    
    # 验证搜索关键词长度
    if search and len(search) > 100:
        search = search[:100]
    
    return page, per_page, search

# ===== 成绩与名次计算工具 =====
def compute_competition_ranks(student_id_to_score):
    """
    计算竞赛排名（Competition Ranking）：并列同名次，后续名次跳过。
    例如分数 [95, 95, 93] → 名次 [1, 1, 3]
    参数: student_id_to_score: dict[int, float]
    返回: dict[int, int] 学生ID到名次
    """
    # 构造列表并按分数降序排序
    scored = [(sid, float(score)) for sid, score in student_id_to_score.items()]
    scored.sort(key=lambda x: x[1], reverse=True)

    ranks = {}
    last_score = None
    last_rank = 0
    position = 0
    for sid, score in scored:
        position += 1
        if last_score is None or score != last_score:
            # 新的分数，名次为当前位置
            last_rank = position
            last_score = score
        # 相同分数复用上一个名次（并列）
        ranks[sid] = last_rank
    return ranks

# 数据库错误处理装饰器
def handle_db_errors(f):
    """处理数据库连接和查询错误的装饰器"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # 记录错误
            print(f"数据库错误: {str(e)}")
            
            # 返回错误页面或重定向
            flash('系统暂时无法访问，请稍后重试', 'danger')
            return redirect(url_for('index'))
    
    return decorated_function

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
# 设置会话超时时间为2小时
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# 配置日志输出 - 同时输出到控制台和文件
import logging
from logging.handlers import RotatingFileHandler
import os

# 确保日志目录存在
log_dir = '.'
log_file = os.path.join(log_dir, 'app.log')

# 清除默认处理器
for handler in app.logger.handlers[:]:
    app.logger.removeHandler(handler)

# 设置日志级别
app.logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建文件处理器 - 使用RotatingFileHandler自动分割日志文件
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# 创建日志格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 添加处理器到日志器
app.logger.addHandler(console_handler)
app.logger.addHandler(file_handler)

# 记录应用启动信息
app.logger.info('Course Manager Web应用启动')

# 代理配置 - 确保应用能正确处理代理环境中的请求
from werkzeug.middleware.proxy_fix import ProxyFix
# 配置代理处理，x_for=1表示信任第一个代理的X-Forwarded-For头
# x_proto=1表示信任X-Forwarded-Proto头来确定协议(http/https)
# x_host=1表示信任X-Forwarded-Host头来确定主机名
# x_prefix=1表示信任X-Forwarded-Prefix头来确定路径前缀
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# 配置URL生成的首选方案为HTTPS
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['SERVER_NAME'] = None  # 不硬编码服务器名称，让Flask从请求中推断

# 添加额外的代理请求处理逻辑
@app.before_request
def handle_proxy_headers():
    # 确保Flask正确识别代理传递的协议和主机
    if request.headers.get('X-Forwarded-Proto'):
        request.scheme = request.headers.get('X-Forwarded-Proto')
    if request.headers.get('X-Forwarded-Host'):
        request.host = request.headers.get('X-Forwarded-Host')
    if request.headers.get('X-Forwarded-Port'):
        request.host += f":{request.headers.get('X-Forwarded-Port')}"

# 启用CSRF保护
csrf = CSRFProtect(app)

# 添加自定义Jinja2过滤器
@app.template_filter('nl2br')
def nl2br_filter(text):
    """将换行符转换为HTML的<br>标签"""
    if not text:
        return text
    # 将\n和\r\n转换为<br>标签
    import re
    from markupsafe import Markup
    text = re.sub(r'\r\n|\r|\n', '<br>', str(text))
    return Markup(text)

# CSRF错误处理
from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """处理CSRF错误"""
    app.logger.error(f"❌ CSRF错误详情: {str(e)}")
    app.logger.error(f"错误描述: {e.description}")
    app.logger.error(f"请求方法: {request.method}")
    app.logger.error(f"请求路径: {request.path}")
    app.logger.error(f"表单数据: {dict(request.form)}")
    app.logger.error(f"请求头: {dict(request.headers)}")
    
    # 检查CSRF令牌
    form_token = request.form.get('csrf_token')
    header_token = request.headers.get('X-CSRFToken')
    app.logger.error(f"表单CSRF令牌: {form_token}")
    app.logger.error(f"请求头CSRF令牌: {header_token}")
    
    flash('安全验证失败，请刷新页面重试', 'danger')
    return redirect(request.referrer or url_for('index')), 400

# HTTPS重定向（生产环境）
@app.before_request
def force_https():
    """强制HTTPS重定向（生产环境）"""
    # 在开发环境中完全禁用HTTPS重定向
    if app.debug:
        return None
    
    # 在本地环境中禁用HTTPS重定向
    if (request.host.startswith('127.0.0.1') or 
        request.host.startswith('localhost') or
        request.host.startswith('0.0.0.0')):
        return None
    
    # 只在生产环境启用HTTPS重定向
    if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        return redirect(request.url.replace('http://', 'https://'), code=301)

# 安全HTTP头配置
@app.after_request
def add_security_headers(response):
    """添加安全HTTP头"""
    # HSTS - 强制HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'DENY'
    
    # 防止MIME类型嗅探
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS保护
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # 内容安全策略
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:;"
    
    # 推荐人策略
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

# 导出应用实例供FLASK_APP识别
# 注意：实际启动配置在文件末尾

# 显式导出应用实例
app = app

# 加载配置
def load_config(config_path='config.json'):
    if not os.path.exists(config_path):
        default_config = {
            "database_path": "./data/course.db",
            "recaptcha": {
                "site_key": "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
                "secret_key": "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
            }
        }
        os.makedirs(os.path.dirname(default_config["database_path"]), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config
            
    with open(config_path, 'r') as f:
        config = json.load(f)
        return config

# 加载完整配置
config = load_config()
db_path = config.get("database_path", "./data/course.db")
# 添加数据库安全配置
engine = create_engine(
    f'sqlite:///{db_path}',
    # 启用外键约束
    connect_args={'check_same_thread': False},
    # 连接池配置
    pool_pre_ping=True,
    pool_recycle=300,
    # 启用SQL语句回显（开发环境）
    echo=False
)
Base.metadata.create_all(engine)  # 确保所有表已创建
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)  # 使用scoped_session确保线程安全

# 设置Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 管理员权限验证装饰器
def admin_required(f):
    """验证用户是否为管理员的装饰器"""
    from functools import wraps
    
    @wraps(f)
    @login_required  # 先验证登录
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    
    return decorated_function

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    db_session = Session()
    try:
        user = db_session.get(User, int(user_id))
        return user
    finally:
        db_session.close()

# 使User类兼容Flask-Login
UserMixin.is_authenticated = property(lambda self: True)
UserMixin.is_active = property(lambda self: True)
UserMixin.is_anonymous = property(lambda self: False)
UserMixin.get_id = lambda self: str(self.id)
User.__bases__ = (UserMixin,) + User.__bases__

# 安全输入验证函数
def validate_input(data, field_name, max_length=255, required=True):
    """
    通用输入验证函数
    """
    if required and (not data or not data.strip()):
        return False, f'{field_name}不能为空'
    
    if data and len(data) > max_length:
        return False, f'{field_name}长度不能超过{max_length}个字符'
    
    # 检查危险字符
    dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript:', 'onload', 'onerror']
    if data:
        data_lower = data.lower()
        for char in dangerous_chars:
            if char in data_lower:
                return False, f'{field_name}包含不安全字符'
    
    return True, ''

def sanitize_input(data):
    """
    清理输入数据
    """
    if not data:
        return data
    
    # 移除HTML标签和危险字符
    import re
    # 移除HTML标签
    data = re.sub(r'<[^>]+>', '', data)
    # 移除JavaScript相关内容
    data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
    data = re.sub(r'on\w+\s*=', '', data, flags=re.IGNORECASE)
    
    return data.strip()

# 请求前处理 - 创建数据库会话和安全检查
@app.before_request
def before_request():
    session.permanent = True
    
    # 排除登录页面和静态文件，避免会话超时检查干扰登录过程
    if request.endpoint in ['login', 'static']:
        return None
    
    # 会话超时处理
    if current_user.is_authenticated:
        # 获取当前时间戳
        current_time = datetime.now().timestamp()
        
        # 检查用户最后活动时间
        last_activity = session.get('last_activity')
        if last_activity and (current_time - last_activity > 7200):  # 2小时 = 7200秒
            # 会话超时，自动登出
            logout_user()
            session.clear()
            flash('会话已超时，请重新登录', 'info')
            return redirect(url_for('login'))
        
        # 更新最后活动时间
        session['last_activity'] = current_time
    
    # 检查请求频率限制（仅对敏感操作）
    # 排除静态文件和正常页面访问
    if request.endpoint and request.endpoint in ['login'] and request.method == 'POST':
        client_ip = get_client_ip()
        current_time = datetime.now()
        
        # 简单的请求频率限制（每分钟最多10个登录请求）
        if not hasattr(app, 'request_counts'):
            app.request_counts = {}
        
        if client_ip not in app.request_counts:
            app.request_counts[client_ip] = []
        
        # 清理1分钟前的请求记录
        app.request_counts[client_ip] = [
            req_time for req_time in app.request_counts[client_ip]
            if (current_time - req_time).total_seconds() < 60
        ]
        
        # 检查请求频率（只对登录请求）
        if len(app.request_counts[client_ip]) > 10:
            return jsonify({'error': '登录请求过于频繁，请稍后再试'}), 429
        
        app.request_counts[client_ip].append(current_time)

# 添加上文处理器，为所有模板提供now变量和config
@app.context_processor
def inject_now():
    return {'now': datetime.now(), 'config': config}

# 请求后处理 - 关闭数据库会话
@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()

# 首页路由
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html')

# 获取RSA公钥API
@app.route('/api/public-key')
def get_public_key():
    """获取RSA公钥用于客户端加密"""
    try:
        public_key_pem = rsa_manager.get_public_key_pem()
        return jsonify({
            'success': True,
            'public_key': public_key_pem
        })
    except Exception as e:
        app.logger.error(f'获取公钥失败: {str(e)}')
        return jsonify({
            'success': False,
            'error': '获取公钥失败'
        }), 500
# 获取AES密钥API (已禁用)
# @app.route('/api/aes-key')
# def get_aes_key():
#     """获取AES密钥用于客户端加密"""
#     try:
#         encryption_key = aes_manager.get_encryption_key()
#         return jsonify({
#             'success': True,
#             'key': encryption_key
#         })
#     except Exception as e:
#         app.logger.error(f'获取AES密钥失败: {str(e)}')
#         return jsonify({
#             'success': False,
#             'error': '获取加密密钥失败'
#         }), 500

@app.route('/test-recaptcha')
def test_recaptcha_page():
    """reCAPTCHA测试页面"""
    with open('test_recaptcha_simple.html', 'r', encoding='utf-8') as f:
        return f.read()

# 验证码API
@app.route('/api/captcha')
def get_captcha():
    """生成验证码图片"""
    start_time = datetime.now()
    
    # 检查验证码生成频率限制（每分钟最多10次）
    client_ip = get_client_ip()
    current_time = datetime.now()
    
    # 初始化验证码请求计数器
    if not hasattr(app, 'captcha_request_counts'):
        app.captcha_request_counts = {}
    
    if client_ip not in app.captcha_request_counts:
        app.captcha_request_counts[client_ip] = []
    
    # 清理1分钟前的请求记录
    app.captcha_request_counts[client_ip] = [
        req_time for req_time in app.captcha_request_counts[client_ip]
        if (current_time - req_time).total_seconds() < 60
    ]
    
    # 检查请求频率
    if len(app.captcha_request_counts[client_ip]) >= 10:
        app.logger.warning(f'IP {client_ip} 验证码请求过于频繁：1分钟内请求{len(app.captcha_request_counts[client_ip])}次')
        return jsonify({
            'success': False,
            'error': '验证码请求过于频繁，请稍后再试',
            'retry_after': 60  # 60秒后重试
        }), 429
    
    # 记录本次请求
    app.captcha_request_counts[client_ip].append(current_time)
    
    try:
        text, image_data = captcha_generator.generate_captcha()
        
        # 将验证码文本存储在session中
        session['captcha_text'] = text.upper()
        session['captcha_time'] = datetime.now().timestamp()
        
        # 记录性能指标
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        app.logger.info(f'验证码生成成功，耗时: {processing_time:.2f}ms，IP: {client_ip}')
        
        return jsonify({
            'success': True,
            'image': image_data,
            'processing_time': f'{processing_time:.2f}ms'
        })
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        app.logger.error(f'生成验证码失败: {str(e)}，耗时: {processing_time:.2f}ms，IP: {client_ip}')
        return jsonify({
            'success': False,
            'error': '验证码生成失败',
            'processing_time': f'{processing_time:.2f}ms'
        }), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录 - 支持reCAPTCHA验证"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        client_ip = get_client_ip()
        db_session = Session()
        
        try:
            # 检查IP是否被锁定
            if is_ip_locked(client_ip):
                flash('IP已被锁定，请稍后再试')
                return render_template('login.html')
            
            # 检查速率限制
            if is_rate_limited(client_ip):
                flash('请求过于频繁，请稍后再试')
                return render_template('login.html')
            
            # 记录登录尝试
            record_rate_limit_attempt(client_ip)
            
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            captcha_input = request.form.get('captcha', '').strip().upper()
            
            # 基本验证
            if not username or not password:
                flash('请输入用户名和密码')
                record_failed_login(client_ip)
                return render_template('login.html')
            
            # 验证图片验证码
            if not captcha_input:
                flash('请输入验证码')
                record_failed_login(client_ip)
                return render_template('login.html')
            
            # 检查验证码是否正确
            session_captcha = session.get('captcha_text', '').upper()
            captcha_time = session.get('captcha_time', 0)
            current_time = datetime.now().timestamp()
            
            # 验证码5分钟内有效
            if not session_captcha or (current_time - captcha_time) > 300:
                flash('验证码已过期，请重新获取')
                record_failed_login(client_ip)
                return render_template('login.html')
            
            if captcha_input != session_captcha:
                flash('验证码错误')
                record_failed_login(client_ip)
                # 清除验证码，强制重新获取
                session.pop('captcha_text', None)
                session.pop('captcha_time', None)
                return render_template('login.html')
            
            # 验证码正确，清除session中的验证码
            session.pop('captcha_text', None)
            session.pop('captcha_time', None)
            
            # 检查用户是否存在
            user = db_session.query(User).filter_by(username=username).first()
            if not user:
                flash('用户名或密码错误')
                record_failed_login(client_ip)
                return render_template('login.html')
            
            # 验证密码
            if check_password_hash(user.password_hash, password):
                login_user(user)
                reset_login_attempts(client_ip)  # 重置失败计数
                app.logger.info(f'用户 {username} 登录成功，IP: {client_ip}')
                
                # 初始化会话活动时间
                session['last_activity'] = datetime.now().timestamp()
                
                # 重定向到原来要访问的页面或首页
                next_page = request.args.get('next')
                if next_page and url_parse(next_page).netloc == '':
                    return redirect(next_page)
                return redirect(url_for('index'))
            else:
                flash('用户名或密码错误')
                lock_minutes = record_failed_login(client_ip)
                if lock_minutes > 0:
                    app.logger.warning(f'IP {client_ip} 登录失败过多，锁定{lock_minutes}分钟')
                return render_template('login.html')
                
        except Exception as e:
            app.logger.error(f'登录处理错误: {str(e)}')
            flash('登录处理失败，请重试')
            record_failed_login(client_ip)
            return render_template('login.html')
        finally:
            db_session.close()
    
    return render_template('login.html')


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    force_change = request.args.get('force', False)
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 输入验证
        if not current_password or not new_password or not confirm_password:
            flash('请填写所有字段！', 'danger')
            return render_template('change_password.html', force_change=force_change)
        
        if new_password != confirm_password:
            flash('新密码和确认密码不匹配！', 'danger')
            return render_template('change_password.html', force_change=force_change)
        
        if len(new_password) < 6:
            flash('新密码长度至少为6位！', 'danger')
            return render_template('change_password.html', force_change=force_change)
        
        # 检查密码强度
        if not validate_password_strength(new_password):
            flash('密码强度不够！密码应包含字母和数字，长度至少6位。', 'danger')
            return render_template('change_password.html', force_change=force_change)
        
        db_session = Session()
        try:
            user = db_session.get(User, current_user.id)
            
            # 验证当前密码
            if not check_password_hash(user.password_hash, current_password):
                flash('当前密码错误！', 'danger')
                return render_template('change_password.html', force_change=force_change)
            
            # 更新密码
            user.password_hash = generate_password_hash(new_password)
            user.must_change_password = False  # 取消强制修改标记
            user.password_changed_at = datetime.now().date()
            
            db_session.commit()
            
            # 记录密码修改日志
            app.logger.info(f'用户 {user.username} 修改了密码')
            
            flash('密码修改成功！', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db_session.rollback()
            app.logger.error(f'密码修改失败：{str(e)}')
            flash('密码修改失败，请稍后重试！', 'danger')
        finally:
            db_session.close()
    
    return render_template('change_password.html', force_change=force_change)

def validate_password_strength(password):
    """
    验证密码强度
    """
    if len(password) < 6:
        return False
    
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_letter and has_digit

# 强制修改密码中间件
@app.before_request
def check_password_change_required():
    # 跳过不需要检查的路由
    exempt_routes = ['login', 'logout', 'change_password', 'static']
    
    if (current_user.is_authenticated and 
        hasattr(current_user, 'must_change_password') and 
        current_user.must_change_password and 
        request.endpoint not in exempt_routes):
        return redirect(url_for('change_password', force=True))

# 注销路由
@app.route('/logout')
@login_required
def logout():
    username = current_user.username if current_user.is_authenticated else '用户'
    logout_user()
    flash(f'{username} 已成功注销！', 'success')
    return redirect(url_for('login'))

# 学生管理路由
@app.route('/students')
@login_required
def students():
    db_session = Session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)

        # 获取筛选参数（默认只显示应届学生）
        type_filter = request.args.get('type_filter', '应届', type=str)
        status_filter = request.args.get('status_filter', '', type=str)

        # 获取排序参数
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')

        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)

        # 构建查询
        query = db_session.query(Student)

        # 添加筛选条件
        # 默认只显示应届学生（除非明确指定查看全部）
        if type_filter:
            query = query.filter(Student.student_type == type_filter)
        if status_filter:
            query = query.filter(Student.enrollment_status == status_filter)

        # 添加搜索条件
        if search:
            query = query.filter(
                Student.name.contains(search) |
                Student.grade.contains(search)
            )

        # 获取总数（用于前端显示）
        total = query.count()

        # 定义可排序字段映射
        sort_mapping = {
            'id': Student.id,
            'name': Student.name,
            'gender': Student.gender,
            'grade': Student.grade
        }

        # 应用排序
        sort_field = sort_mapping.get(sort_by, Student.id)
        if sort_order == 'asc':
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # 应用分页
        students_list = query.limit(per_page).offset((page - 1) * per_page).all()

        # 如果是AJAX请求，返回JSON数据
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'data': [{
                    'id': s.id,
                    'name': s.name,
                    'gender': s.gender,
                    'grade': s.grade,
                    'student_type': s.student_type,
                    'enrollment_status': s.enrollment_status
                } for s in students_list],
                'total': total,
                'page': page,
                'per_page': per_page
            })

        # 普通请求返回模板（只返回当前页数据）
        return render_template('students.html',
                               students=students_list,
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               type_filter=type_filter,
                               status_filter=status_filter)
    finally:
        db_session.close()

# 添加学生路由
@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        grade = request.form.get('grade')
        student_type = request.form.get('student_type', '应届')
        enrollment_status = request.form.get('enrollment_status', '在学')

        if not name or not gender or not grade:
            flash('请填写所有必填字段！', 'danger')
            return redirect(url_for('add_student'))

        db_session = Session()
        try:
            new_student = Student(
                name=name, gender=gender, grade=grade,
                student_type=student_type, enrollment_status=enrollment_status
            )
            db_session.add(new_student)
            db_session.commit()
            flash('学生添加成功！', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            db_session.rollback()
            flash(f'添加失败: {str(e)}', 'danger')
        finally:
            db_session.close()

    return render_template('student_form.html')

# 编辑学生路由
@app.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    db_session = Session()
    try:
        student = db_session.get(Student, student_id)
        if not student:
            flash('学生不存在！', 'danger')
            return redirect(url_for('students'))

        if request.method == 'POST':
            student.name = request.form.get('name')
            student.gender = request.form.get('gender')
            student.grade = request.form.get('grade')
            student.student_type = request.form.get('student_type', '应届')
            student.enrollment_status = request.form.get('enrollment_status', '在学')

            try:
                db_session.commit()
                flash('学生信息更新成功！', 'success')
                return redirect(url_for('students'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')

        return render_template('student_form.html', student=student)
    finally:
        db_session.close()

# 删除学生路由
@app.route('/students/delete/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    db_session = Session()
    try:
        student = db_session.get(Student, student_id)
        if not student:
            flash('学生不存在！', 'danger')
            return redirect(url_for('students'))
        
        # 检查是否有关联记录
        record_count = db_session.query(RecordStudent).filter_by(student_id=student_id).count()
        if record_count > 0:
            flash('该学生有课程记录，不能删除！', 'danger')
            return redirect(url_for('students'))
        
        db_session.delete(student)
        db_session.commit()
        flash('学生删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('students'))

# 年级顺序表（用于自动升年级）
GRADE_SEQUENCE = [
    '小学一年级', '小学二年级', '小学三年级', '小学四年级', '小学五年级', '小学六年级',
    '初中一年级', '初中二年级', '初中三年级',
    '高中一年级', '高中二年级', '高中三年级'
]

# 批量更新年级路由
@app.route('/students/batch-update-grade', methods=['POST'])
@login_required
def batch_update_grade():
    student_ids = request.form.getlist('student_ids')
    mode = request.form.get('mode', 'auto')  # auto 或 manual
    target_grade = request.form.get('target_grade', '')

    if not student_ids:
        flash('请选择要更新的学生！', 'warning')
        return redirect(url_for('students'))

    db_session = Session()
    try:
        students = db_session.query(Student).filter(Student.id.in_([int(sid) for sid in student_ids])).all()

        updated = 0
        graduated = 0
        skipped = 0

        for student in students:
            # 只更新在学学生
            if student.enrollment_status != '在学':
                skipped += 1
                continue

            if mode == 'manual':
                # 手动模式：直接设置目标年级
                if target_grade:
                    student.grade = target_grade
                    updated += 1
            else:
                # 自动模式：按年级顺序升一级
                if student.grade in GRADE_SEQUENCE:
                    current_idx = GRADE_SEQUENCE.index(student.grade)
                    if current_idx < len(GRADE_SEQUENCE) - 1:
                        student.grade = GRADE_SEQUENCE[current_idx + 1]
                        updated += 1
                    else:
                        # 高三学生升年级 -> 标记为往届（毕业）
                        student.student_type = '往届'
                        graduated += 1
                else:
                    skipped += 1

        db_session.commit()
        msg = f'更新完成：{updated} 名学生升年级'
        if graduated > 0:
            msg += f'，{graduated} 名高三学生已毕业（标记为往届）'
        if skipped > 0:
            msg += f'，{skipped} 名非在学学生已跳过'
        flash(msg, 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'批量更新失败: {str(e)}', 'danger')
    finally:
        db_session.close()

    return redirect(url_for('students'))

# 批量更新状态路由
@app.route('/students/batch-update-status', methods=['POST'])
@login_required
def batch_update_status():
    student_ids = request.form.getlist('student_ids')
    field = request.form.get('field', '')  # student_type 或 enrollment_status
    value = request.form.get('value', '')

    if not student_ids:
        flash('请选择要更新的学生！', 'warning')
        return redirect(url_for('students'))

    if field not in ['student_type', 'enrollment_status']:
        flash('无效的字段！', 'danger')
        return redirect(url_for('students'))

    if value not in ['应届', '往届', '在学', '停学']:
        flash('无效的值！', 'danger')
        return redirect(url_for('students'))

    db_session = Session()
    try:
        students = db_session.query(Student).filter(Student.id.in_([int(sid) for sid in student_ids])).all()

        for student in students:
            setattr(student, field, value)

        db_session.commit()
        field_name = '类型' if field == 'student_type' else '状态'
        flash(f'已成功更新 {len(students)} 名学生的{field_name}为"{value}"', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'批量更新失败: {str(e)}', 'danger')
    finally:
        db_session.close()

    return redirect(url_for('students'))

# 课程安排路由
@app.route('/schedules')
@login_required
def schedules():
    db_session = Session()
    try:
        # 获取分页和筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        teacher_filter = request.args.get('teacher', '全部')
        search = request.args.get('search', '', type=str)
        
        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)
        
        # 构建查询
        query = db_session.query(Schedule)
        
        # 添加教师筛选
        if teacher_filter != '全部':
            query = query.filter(Schedule.teacher == teacher_filter)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                Schedule.subject.contains(search) | 
                Schedule.teacher.contains(search) |
                Schedule.date_type.contains(search) |
                Schedule.students.any(Student.name.contains(search))
            )
        
        # 获取总数
        total = query.count()
        
        # 获取排序参数
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 定义可排序字段映射
        sort_mapping = {
            'id': Schedule.id,
            'subject': Schedule.subject,
            'teacher': Schedule.teacher,
            'date_type': Schedule.date_type,
            'start_time': Schedule.start_time,
            'duration': Schedule.duration
        }
        
        # 应用排序
        sort_field = sort_mapping.get(sort_by, Schedule.id)
        if sort_order == 'asc':
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
        
        # 应用分页
        schedules_list = query.limit(per_page).offset((page - 1) * per_page).all()
        
        # 获取所有教师列表供筛选
        teachers = db_session.query(Schedule.teacher).distinct().all()
        teachers = [t[0] for t in teachers if t[0]]
        teachers.insert(0, '全部')
        
        # 如果是AJAX请求，返回JSON数据
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'data': [{
                    'id': s.id,
                    'subject': s.subject,
                    'date_type': s.date_type,
                    'teacher': s.teacher,
                    'start_time': s.start_time.strftime('%H:%M'),
                    'duration': s.duration,
                    'student_count': len(s.students)
                } for s in schedules_list],
                'total': total,
                'page': page,
                'per_page': per_page
            })
        
        # 普通请求返回模板（只返回当前页数据）
        return render_template('schedules.html', 
                               schedules=schedules_list, 
                               teachers=teachers,
                               current_teacher=teacher_filter,
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search,
                               sort_by=sort_by,
                               sort_order=sort_order)
    finally:
        db_session.close()

# 添加课程安排路由
@app.route('/schedules/add', methods=['GET', 'POST'])
@login_required
def add_schedule():
    db_session = Session()
    try:
        if request.method == 'POST':
            subject = request.form.get('subject')
            date_type = request.form.get('date_type')
            teacher = request.form.get('teacher')
            start_hour = int(request.form.get('start_hour'))
            start_minute = int(request.form.get('start_minute'))
            duration = int(request.form.get('duration'))
            student_ids = request.form.getlist('student_ids')
            
            if not subject or not date_type or not teacher:
                flash('请填写所有必填字段！', 'danger')
                return redirect(url_for('add_schedule'))
            
            try:
                start_time_obj = time(hour=start_hour, minute=start_minute)
                new_schedule = Schedule(
                    subject=subject,
                    date_type=date_type,
                    teacher=teacher,
                    start_time=start_time_obj,
                    duration=duration
                )
                
                if student_ids:
                    students = db_session.query(Student).filter(Student.id.in_(student_ids)).all()
                    new_schedule.students = students
                
                db_session.add(new_schedule)
                db_session.commit()
                flash('课程安排添加成功！', 'success')
                # 获取当前筛选和排序参数并传递
                teacher_filter = request.args.get('teacher', '全部')
                search_term = request.args.get('search', '')
                page_num = request.args.get('page', '1')
                per_page_num = request.args.get('per_page', '10')
                sort_by_param = request.args.get('sort_by', 'id')
                sort_order_param = request.args.get('sort_order', 'desc')
                return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
            except Exception as e:
                db_session.rollback()
                flash(f'添加失败: {str(e)}', 'danger')
        
        # 获取所有学生列表供选择
        students = db_session.query(Student).all()
        # 获取所有在职教师列表
        teachers = db_session.query(Teacher).filter(Teacher.status == '在职').all()
        return render_template('schedule_form.html', students=students, teachers=teachers)
    finally:
        db_session.close()

# 编辑课程安排路由
@app.route('/schedules/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id):
    db_session = Session()
    try:
        schedule = db_session.get(Schedule, schedule_id)
        if not schedule:
            flash('课程安排不存在！', 'danger')
            # 获取当前筛选和排序参数并传递
            teacher_filter = request.args.get('teacher', '全部')
            search_term = request.args.get('search', '')
            page_num = request.args.get('page', '1')
            per_page_num = request.args.get('per_page', '10')
            sort_by_param = request.args.get('sort_by', 'id')
            sort_order_param = request.args.get('sort_order', 'desc')
            return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
        
        if request.method == 'POST':
            schedule.subject = request.form.get('subject')
            schedule.date_type = request.form.get('date_type')
            schedule.teacher = request.form.get('teacher')
            schedule.start_time = time(
                hour=int(request.form.get('start_hour')),
                minute=int(request.form.get('start_minute'))
            )
            schedule.duration = int(request.form.get('duration'))
            
            # 更新关联的学生
            student_ids = request.form.getlist('student_ids')
            if student_ids:
                students = db_session.query(Student).filter(Student.id.in_(student_ids)).all()
                schedule.students = students
            else:
                schedule.students = []
            
            try:
                db_session.commit()
                flash('课程安排更新成功！', 'success')
                # 获取当前筛选和排序参数并传递
                teacher_filter = request.args.get('teacher', '全部')
                search_term = request.args.get('search', '')
                page_num = request.args.get('page', '1')
                per_page_num = request.args.get('per_page', '10')
                sort_by_param = request.args.get('sort_by', 'id')
                sort_order_param = request.args.get('sort_order', 'desc')
                return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        # 获取所有学生列表供选择
        students = db_session.query(Student).all()
        # 获取当前已选学生的ID列表
        selected_student_ids = [s.id for s in schedule.students]
        # 获取所有在职教师列表
        teachers = db_session.query(Teacher).filter(Teacher.status == '在职').all()
        
        return render_template('schedule_form.html', 
                               schedule=schedule, 
                               students=students, 
                               teachers=teachers,
                               selected_student_ids=selected_student_ids)
    finally:
        db_session.close()

# 删除课程安排路由
@app.route('/schedules/delete/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    # 验证密码
    password = request.form.get('password')
    if password:
        db_session = Session()
        try:
            user = db_session.get(User, current_user.id)
            if not check_password_hash(user.password_hash, password):
                flash('密码错误，无法执行删除操作！', 'danger')
                # 获取当前筛选和排序参数并传递
                teacher_filter = request.args.get('teacher', '全部')
                search_term = request.args.get('search', '')
                page_num = request.args.get('page', '1')
                per_page_num = request.args.get('per_page', '10')
                sort_by_param = request.args.get('sort_by', 'id')
                sort_order_param = request.args.get('sort_order', 'desc')
                return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
        finally:
            db_session.close()
    else:
        flash('请输入密码以确认删除操作！', 'danger')
        # 获取当前筛选和排序参数并传递
        teacher_filter = request.args.get('teacher', '全部')
        search_term = request.args.get('search', '')
        page_num = request.args.get('page', '1')
        per_page_num = request.args.get('per_page', '10')
        sort_by_param = request.args.get('sort_by', 'id')
        sort_order_param = request.args.get('sort_order', 'desc')
        return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
    
    # 执行删除操作
    db_session = Session()
    try:
        schedule = db_session.get(Schedule, schedule_id)
        if not schedule:
            flash('课程安排不存在！', 'danger')
            # 获取当前筛选和排序参数并传递
            teacher_filter = request.args.get('teacher', '全部')
            search_term = request.args.get('search', '')
            page_num = request.args.get('page', '1')
            per_page_num = request.args.get('per_page', '10')
            sort_by_param = request.args.get('sort_by', 'id')
            sort_order_param = request.args.get('sort_order', 'desc')
            return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
        
        db_session.delete(schedule)
        db_session.commit()
        flash('课程安排删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    # 获取当前筛选和排序参数并传递
    teacher_filter = request.args.get('teacher', '全部')
    search_term = request.args.get('search', '')
    page_num = request.args.get('page', '1')
    per_page_num = request.args.get('per_page', '10')
    sort_by_param = request.args.get('sort_by', 'id')
    sort_order_param = request.args.get('sort_order', 'desc')
    return redirect(url_for('schedules', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))

# 课程记录路由
@app.route('/records')
@login_required
def records():
    db_session = Session()
    try:
        # 获取分页和筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        teacher_filter = request.args.get('teacher', '全部')
        semester_filter = request.args.get('semester', '', type=str)
        search = request.args.get('search', '', type=str)
        
        # 构建查询
        query = db_session.query(CourseRecord)
        
        # 添加教师筛选
        if teacher_filter != '全部':
            query = query.filter(CourseRecord.teacher == teacher_filter)
        
        # 添加学期筛选
        if semester_filter:
            app.logger.info(f"学期筛选参数：semester_filter={semester_filter}")
            try:
                semester_id = int(semester_filter)
                app.logger.info(f"学期 ID: {semester_id}")
                # 通过学期 ID 获取日期范围进行筛选
                semester_tag = db_session.query(SemesterTag).filter_by(id=semester_id).first()
                if semester_tag:
                    app.logger.info(f"找到学期：{semester_tag.name}, 开始：{semester_tag.start_date}, 结束：{semester_tag.end_date}")
                    app.logger.info(f"开始日期类型：{type(semester_tag.start_date)}, 结束日期类型：{type(semester_tag.end_date)}")
                    app.logger.info(f"CourseRecord.date 类型：{type(CourseRecord.date)}")
                    query = query.filter(
                        CourseRecord.date >= semester_tag.start_date,
                        CourseRecord.date <= semester_tag.end_date
                    )
                    app.logger.info("学期筛选条件已应用")
                else:
                    app.logger.warning(f"未找到 ID 为 {semester_id} 的学期标签")
            except ValueError as e:
                app.logger.warning(f"无效的学期 ID: {semester_filter}, 错误：{e}")
                pass  # 无效的学期 ID，忽略筛选
        
        # 添加搜索条件
        if search:
            # 优化搜索查询性能：先查询学生 ID，再过滤课程记录
            student_ids_subquery = db_session.query(RecordStudent.record_id).join(
                Student, RecordStudent.student_id == Student.id
            ).filter(Student.name.contains(search)).subquery()
            
            query = query.filter(
                CourseRecord.subject.contains(search) | 
                CourseRecord.teacher.contains(search) |
                CourseRecord.content.contains(search) |
                CourseRecord.id.in_(student_ids_subquery)
            )
        
        # 获取总数
        total = query.count()
        
        # 获取排序参数
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 定义可排序字段映射
        sort_mapping = {
            'id': CourseRecord.id,
            'subject': CourseRecord.subject,
            'teacher': CourseRecord.teacher,
            'date': CourseRecord.date,
            'start_time': CourseRecord.start_time,
            'duration': CourseRecord.duration
        }
        
        # 应用排序
        sort_field = sort_mapping.get(sort_by, CourseRecord.id)
        if sort_order == 'asc':
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
        
        # 应用分页
        records_list = query.limit(per_page).offset((page - 1) * per_page).all()
        
        # 获取所有教师列表供筛选
        teachers = db_session.query(CourseRecord.teacher).distinct().all()
        teachers = [t[0] for t in teachers if t[0]]
        teachers.insert(0, '全部')
        
        # 获取所有学期标签供筛选
        semesters = db_session.query(SemesterTag).order_by(SemesterTag.start_date.desc()).all()
        
        
        default_semester_id = ""
        
        # 获取当前选中学期的名称，用于显示
        current_semester_name = '全部'
        selected_semester_id = semester_filter
        if selected_semester_id:
            try:
                sem_obj = db_session.query(SemesterTag).filter_by(id=int(selected_semester_id)).first()
                if sem_obj:
                    current_semester_name = sem_obj.name
            except ValueError:
                pass
        # 如果是 AJAX 请求，返回 JSON 数据
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'data': [{
                    'id': r.id,
                    'subject': r.subject,
                    'teacher': r.teacher,
                    'date': r.date.strftime('%Y-%m-%d'),
                    'start_time': r.start_time.strftime('%H:%M'),
                    'duration': r.duration,
                    'student_count': len(r.students),
                    'content': r.content[:50] + '...' if len(r.content) > 50 else r.content
                } for r in records_list],
                'total': total,
                'page': page,
                'per_page': per_page
            })
        
        # 普通请求返回模板（为了兼容性，但优化数据获取）
        # 只获取当前页面需要的数据，而不是全部数据
        # 优化：只获取学生 ID 和姓名，减少数据传输量
        all_students = db_session.query(Student.id, Student.name, Student.grade).all()
        all_subjects = db_session.query(CourseRecord.subject).distinct().all()
        all_subjects = [s[0] for s in all_subjects if s[0]]
        
        return render_template('records.html', 
                               records=records_list, 
                               teachers=teachers, 
                               current_teacher=teacher_filter,
                               semesters=semesters,
                               current_semester=semester_filter if semester_filter else "",
                               current_semester_name=current_semester_name,
                               default_semester_id=default_semester_id,
                               search=search,
                               all_students=all_students,
                               all_subjects=all_subjects,
                               total=total,
                               page=page,
                               per_page=per_page,
                               sort_by=sort_by,
                               sort_order=sort_order)
    finally:
        db_session.close()
@app.route('/form_test', methods=['GET', 'POST'])
@login_required
def form_test():
    if request.method == 'POST':
        # 获取表单数据
        test_input = request.form.get('test_input', '').strip()
        app.logger.info(f'收到测试表单提交: test_input={test_input}')
        
        # 简单的响应
        return render_template('form_test.html', message=f'表单提交成功! 收到的内容: {test_input}')
    
    return render_template('form_test.html')

@app.route('/test_record_form', methods=['GET'])
@login_required
def test_record_form():
    from datetime import datetime
    return render_template('test_record_form.html', now=datetime.now())

@app.route('/minimal_test_form', methods=['GET'])
@login_required
def minimal_test_form():
    return render_template('minimal_test_form.html')

@app.route('/debug_record_form', methods=['GET'])
@login_required
def debug_record_form():
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('debug_record_form.html', today_date=today_date)

@app.route('/simple_test_form', methods=['GET'])
@login_required
def simple_test_form():
    from flask_wtf import FlaskForm
    from wtforms import StringField
    from wtforms.validators import DataRequired
    
    # 创建一个简单的表单类用于CSRF保护
    class SimpleForm(FlaskForm):
        test_input = StringField('测试输入', validators=[DataRequired()])
    
    form = SimpleForm()
    return render_template('simple_test_form.html', form=form)

@app.route('/test_form_submit', methods=['POST'])
@login_required
def test_form_submit():
    # 获取表单数据
    test_input = request.form.get('test_input')
    
    # 记录日志
    app.logger.info(f'简单测试表单提交成功: {test_input}')
    
    # 显示成功消息
    flash('测试表单提交成功！', 'success')
    
    # 重定向回测试表单
    return redirect(url_for('simple_test_form'))

# 添加课程记录路由
@app.route('/records/add', methods=['GET', 'POST'])
@login_required
def add_record():
    db_session = Session()
    try:
        if request.method == 'POST':
            # 获取所有表单数据
            subject = request.form.get('subject', '').strip()
            teacher = request.form.get('teacher', '').strip()
            date_str = request.form.get('date', '').strip()
            start_hour = request.form.get('start_hour', '')
            start_minute = request.form.get('start_minute', '')
            duration = request.form.get('duration', '')
            content = request.form.get('content', '')
            homework = request.form.get('homework', '')
            notes = request.form.get('notes', '')
            student_ids = request.form.getlist('selected_students[]')
            
            # 完整日志记录 - 增强版
            app.logger.info(f'✅ 收到添加课程记录请求 (POST)')
            app.logger.info(f'📋 表单数据完整性检查: 科目={bool(subject)}, 教师={bool(teacher)}, 日期={bool(date_str)}, 学生数量={len(student_ids)}')
            app.logger.info(f'🔍 详细参数: subject={subject}, teacher={teacher}, date={date_str}, ' +
                          f'start_hour={start_hour}, start_minute={start_minute}, duration={duration}, ' +
                          f'student_ids={student_ids}')
            app.logger.info(f'👤 用户信息: username={current_user.username}, role={current_user.role}')
            app.logger.info(f'🔧 请求头信息: Content-Type={request.headers.get("Content-Type")}, ' +
                          f'CSRF-Token={request.form.get("csrf_token", "None")[:10]}..., ' +
                          f'User-Agent={request.headers.get("User-Agent")[:50]}...')
            
            # 初始化表单验证错误
            form_errors = {}
            
            # 验证必填字段
            if not subject:
                form_errors['subject'] = '请填写科目！'
            if not teacher:
                form_errors['teacher'] = '请填写教师！'
            if not date_str:
                form_errors['date'] = '请选择日期！'
            else:
                # 验证日期格式
                try:
                    record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    form_errors['date'] = '日期格式错误，请使用YYYY-MM-DD格式！'
            
            # 验证开始时间
            if not start_hour:
                form_errors['start_time'] = '请选择开始小时！'
            else:
                try:
                    start_hour_int = int(start_hour)
                    if start_hour_int < 8 or start_hour_int > 22:
                        form_errors['start_time'] = '开始时间应在8:00-22:00之间！'
                except ValueError:
                    form_errors['start_time'] = '开始小时格式错误！'
            
            if not start_minute:
                if 'start_time' not in form_errors:
                    form_errors['start_time'] = '请选择开始分钟！'
            else:
                try:
                    start_minute_int = int(start_minute)
                    if start_minute_int not in [0, 15, 30, 45]:
                        if 'start_time' not in form_errors:
                            form_errors['start_time'] = '开始分钟应为0、15、30或45！'
                except ValueError:
                    if 'start_time' not in form_errors:
                        form_errors['start_time'] = '开始分钟格式错误！'
            
            # 验证时长
            if not duration:
                form_errors['duration'] = '请选择课程时长！'
            else:
                try:
                    duration_int = int(duration)
                    if duration_int <= 0:
                        form_errors['duration'] = '课程时长必须大于0！'
                except ValueError:
                    form_errors['duration'] = '课程时长格式错误！'
            
            # 验证学生选择
            if not student_ids or len(student_ids) == 0:
                form_errors['students'] = '请至少选择一名学生！'
            
            # 如果有表单验证错误，保留表单数据并显示错误
            if form_errors:
                app.logger.warning(f'表单验证失败: {form_errors}')
                
                # 存储错误和表单数据到会话
                session['form_errors'] = form_errors
                session['form_data'] = {
                    'subject': subject,
                    'teacher': teacher,
                    'date': date_str,
                    'start_hour': start_hour,
                    'start_minute': start_minute,
                    'duration': duration,
                    'content': content,
                    'homework': homework,
                    'notes': notes,
                    'selected_students': student_ids
                }
                
                # 获取筛选参数并传递到重定向
                current_teacher = request.form.get('current_teacher', '全部')
                current_search = request.form.get('current_search', '')
                current_page = request.form.get('current_page', '1')
                current_per_page = request.form.get('current_per_page', '10')
                
                return redirect(url_for('add_record', 
                                      teacher=current_teacher, 
                                      search=current_search, 
                                      page=current_page, 
                                      per_page=current_per_page))
            
            try:
                # 处理时间相关字段
                record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_hour_int = int(start_hour)
                start_minute_int = int(start_minute)
                duration_int = int(duration)
                
                # 再次验证日期合理性
                if record_date > datetime.now().date():
                    flash('日期不能是未来时间！', 'danger')
                    return redirect(url_for('add_record', teacher=current_teacher, search=current_search, page=current_page, per_page=current_per_page))
                
                start_time_obj = time(hour=start_hour_int, minute=start_minute_int)
                
                # 创建课程记录
                new_record = CourseRecord(
                    subject=subject,
                    teacher=teacher,
                    date=record_date,
                    start_time=start_time_obj,
                    duration=duration_int,
                    content=content,
                    homework=homework,
                    notes=notes
                )
                
                # 添加到会话并获取ID
                db_session.add(new_record)
                db_session.flush()  # 获取新记录的ID
                app.logger.info(f'成功创建课程记录对象，ID: {new_record.id}')
                
                # 添加学生关联
                if student_ids:
                    app.logger.info(f'开始添加学生关联，学生数量: {len(student_ids)}')
                    for student_id in student_ids:
                        try:
                            # 验证学生ID是否有效
                            student_id_int = int(student_id)
                            
                            # 验证学生是否存在
                            student = db_session.get(Student, student_id_int)
                            if not student:
                                app.logger.warning(f'学生ID不存在: {student_id_int}')
                                continue
                            
                            # 获取该学生的出勤状态
                            attendance = request.form.get(f'student_attendance_{student_id}', '出席')
                            
                            # 确保出勤状态有效
                            valid_attendances = ['出席', '迟到', '请假', '缺席']
                            if attendance not in valid_attendances:
                                attendance = '出席'
                            
                            record_student = RecordStudent(
                                record_id=new_record.id,
                                student_id=student_id_int,
                                attendance=attendance,
                                homework_status='',
                                study_status=''
                            )
                            db_session.add(record_student)
                            app.logger.info(f'添加学生关联: student_id={student_id_int}, attendance={attendance}')
                        except (ValueError, TypeError) as e:
                            app.logger.warning(f'学生ID格式错误: {student_id}, 错误: {str(e)}')
                            # 继续处理其他学生，不中断整个过程
                
                # 提交事务
                db_session.commit()
                app.logger.info('课程记录添加成功，已提交到数据库')
                
                # 清除会话中的表单数据和错误
                if 'form_errors' in session:
                    del session['form_errors']
                if 'form_data' in session:
                    del session['form_data']
                
                flash('课程记录添加成功！', 'success')
                
                # 获取筛选参数并传递到重定向
                current_teacher = request.form.get('current_teacher', '全部')
                current_search = request.form.get('current_search', '')
                current_page = request.form.get('current_page', '1')
                current_per_page = request.form.get('current_per_page', '10')
                current_sort_by = request.form.get('current_sort_by', 'id')
                current_sort_order = request.form.get('current_sort_order', 'desc')
                current_semester = request.form.get('current_semester', '')
                
                return redirect(url_for('records', teacher=current_teacher, search=current_search, page=current_page, per_page=current_per_page, sort_by=current_sort_by, sort_order=current_sort_order, semester=current_semester))
            except Exception as e:
                db_session.rollback()
                import traceback
                error_trace = traceback.format_exc()
                app.logger.error(f'课程记录添加失败: {str(e)}\n{error_trace}')
                
                # 提供更友好的错误消息
                if 'duplicate key' in str(e).lower():
                    flash('添加失败: 已存在相同的课程记录！', 'danger')
                elif 'not null' in str(e).lower():
                    flash('添加失败: 缺少必要的字段值！', 'danger')
                elif 'foreign key' in str(e).lower():
                    flash('添加失败: 引用了不存在的学生或其他资源！', 'danger')
                else:
                    flash(f'添加失败: {str(e)}', 'danger')
                
                # 存储表单数据到会话以便回显
                session['form_data'] = {
                    'subject': subject,
                    'teacher': teacher,
                    'date': date_str,
                    'start_hour': start_hour,
                    'start_minute': start_minute,
                    'duration': duration,
                    'content': content,
                    'homework': homework,
                    'notes': notes,
                    'selected_students': student_ids
                }
                
                # 获取当前筛选参数并传递到模板（用于返回时保持筛选状态）
                current_teacher = request.form.get('current_teacher', request.args.get('teacher', '全部'))
                current_search = request.form.get('current_search', request.args.get('search', ''))
                current_page = request.form.get('current_page', request.args.get('page', '1'))
                current_per_page = request.form.get('current_per_page', request.args.get('per_page', '10'))
                current_sort_by = request.form.get('current_sort_by', request.args.get('sort_by', 'id'))
                current_sort_order = request.form.get('current_sort_order', request.args.get('sort_order', 'desc'))
                
                return redirect(url_for('add_record', teacher=current_teacher, search=current_search, page=current_page, per_page=current_per_page, sort_by=current_sort_by, sort_order=current_sort_order))
        
        # 获取会话中的表单数据和错误
        form_errors = session.pop('form_errors', {})
        form_data = session.pop('form_data', {})
        
        # 获取学生搜索关键词
        student_search = request.args.get('student_search', '')
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 10  # 默认每页显示10项
        # 获取已选学生ID，优先使用会话数据
        if form_data.get('selected_students'):
            selected_students = form_data.get('selected_students', [])
            # 确保selected_students是整数列表
            selected_students = [int(sid) if isinstance(sid, str) and sid.isdigit() else sid for sid in selected_students]
        else:
            selected_students_str = request.args.get('selected_students', '')
            selected_students = [int(sid) for sid in selected_students_str.split(',') if sid.strip()]
        
        # 获取表单字段参数，优先使用会话数据
        form_subject = form_data.get('subject', request.args.get('subject', ''))
        # 当教师筛选框选择"全部"时，教师字段不应该被自动填入"全部"
        teacher_arg = request.args.get('teacher', '')
        form_teacher = form_data.get('teacher', teacher_arg if teacher_arg != '全部' else '')
        form_date = form_data.get('date', request.args.get('date', ''))
        form_start_hour = form_data.get('start_hour', request.args.get('start_hour', ''))
        form_start_minute = form_data.get('start_minute', request.args.get('start_minute', ''))
        form_duration = form_data.get('duration', request.args.get('duration', ''))
        
        # 获取当前筛选参数并传递到模板（用于返回时保持筛选状态）
        current_teacher = request.args.get('teacher', '全部')
        current_search = request.args.get('search', '')
        current_page = request.args.get('page', '1')
        current_per_page = request.args.get('per_page', '10')
        current_semester = request.args.get('semester', '')
        current_sort_by = request.args.get('sort_by', 'id')
        current_sort_order = request.args.get('sort_order', 'desc')
        
        app.logger.info(f'渲染添加课程记录表单: ' +
                      f'has_errors={len(form_errors) > 0}, has_prefill={len(form_data) > 0}, ' +
                      f'selected_students_count={len(selected_students)}')
        
        # 查询课程安排供选择
        schedules = db_session.query(Schedule).all()
        
        # 构建学生查询，支持搜索过滤
        student_query = db_session.query(Student)
        if student_search:
            student_query = student_query.filter(Student.name.like(f'%{student_search}%'))
        
        # 返回所有学生数据用于客户端分页
        students = student_query.all()
        total_students = len(students)
        
        # 将学生数据转换为JSON格式，用于客户端分页
        import json
        all_students_json = json.dumps([{
            'id': student.id,
            'name': student.name
        } for student in students])
        
        # 获取所有科目和教师列表供下拉选择
        # 从课程安排表中获取科目和教师，如果没有则从课程记录表中获取
        schedule_subjects = db_session.query(Schedule.subject).distinct().all()
        record_subjects = db_session.query(CourseRecord.subject).distinct().all()
        all_subjects = list(set([s[0] for s in schedule_subjects if s[0]] + [s[0] for s in record_subjects if s[0]]))
        
        schedule_teachers = db_session.query(Schedule.teacher).distinct().all()
        record_teachers = db_session.query(CourseRecord.teacher).distinct().all()
        all_teachers = list(set([t[0] for t in schedule_teachers if t[0]] + [t[0] for t in record_teachers if t[0]]))
        
        # 在关闭会话前预加载所有需要的关联数据
        # 预加载每个课程安排的学生数据，防止模板渲染时会话已关闭
        for schedule in schedules:
            # 访问students属性以触发预加载
            _ = [student.id for student in schedule.students]
            
        # 渲染模板
        rendered_template = render_template('record_form.html', 
                               students=students, 
                               schedules=schedules,
                               all_subjects=all_subjects,
                               all_teachers=all_teachers,
                               student_search=student_search,
                               page=page,
                               per_page=per_page,
                               total_students=total_students,
                               selected_students=selected_students,
                               form_subject=form_subject,
                               form_teacher=form_teacher,
                               form_date=form_date,
                               form_start_hour=form_start_hour,
                               form_start_minute=form_start_minute,
                               form_duration=form_duration,
                               all_students_json=all_students_json,
                               form_errors=form_errors,
                               form_content=form_data.get('content', ''),
                               form_homework=form_data.get('homework', ''),
                               form_notes=form_data.get('notes', ''),
                               current_teacher=current_teacher,
                               current_search=current_search,
                               current_page=current_page,
                               current_per_page=current_per_page,
                               current_sort_by=current_sort_by,
                               current_sort_order=current_sort_order, current_semester=current_semester)
                                
        return rendered_template
    finally:
        db_session.close()

# 批量添加课程记录路由 - GET请求
@app.route('/records/batch_add', methods=['GET'])
@login_required
def batch_add_records_get():
    db_session = Session()
    try:
        # 获取所有课程安排供选择
        schedules = db_session.query(Schedule).all()
        
        # 获取当前筛选参数并传递到模板
        current_teacher = request.args.get('teacher', '全部')
        current_search = request.args.get('search', '')
        current_page = request.args.get('page', '1')
        current_per_page = request.args.get('per_page', '10')
        
        return render_template('batch_add_records.html', 
                               schedules=schedules,
                               current_teacher=current_teacher,
                               current_search=current_search,
                               current_page=current_page,
                               current_per_page=current_per_page)
    finally:
        db_session.close()

# 批量添加课程记录路由 - POST请求
@app.route('/records/batch_add', methods=['POST'])
@login_required
def batch_add_records():
    db_session = Session()
    try:
        # 检查是否是JSON请求
        if not request.is_json:
            # 如果不是JSON请求，尝试从表单中获取数据（用于兼容性）
            batch_date = request.form.get('batch_date')
            schedules_data_json = request.form.get('selected_schedules_data')
            
            if not batch_date or not schedules_data_json:
                return jsonify({'success': False, 'message': '缺少必要参数：日期和课程安排'})
            
            try:
                schedules_data = json.loads(schedules_data_json)
            except json.JSONDecodeError:
                return jsonify({'success': False, 'message': '课程安排数据格式错误'})
            
            data = {
                'date': batch_date,
                'schedules': schedules_data
            }
        else:
            # JSON请求处理
            data = request.get_json()
            
        # 获取请求数据
        batch_date = data.get('date')
        schedules_data = data.get('schedules', [])
        
        # 验证数据
        if not batch_date or not schedules_data:
            return jsonify({'success': False, 'message': '缺少必要参数：日期和课程安排'})
        
        try:
            # 解析日期
            record_date = datetime.strptime(batch_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': '日期格式错误，请使用YYYY-MM-DD格式'})
        
        # 统计成功和失败的数量
        success_count = 0
        failed_count = 0
        failed_records = []
        
        # 批量创建课程记录
        for schedule_info in schedules_data:
            try:
                schedule_id = schedule_info.get('id')
                subject = schedule_info.get('subject')
                teacher = schedule_info.get('teacher')
                start_hour = int(schedule_info.get('startHour', 0))
                start_minute = int(schedule_info.get('startMinute', 0))
                duration = int(schedule_info.get('duration', 45))
                
                # 检查必要字段
                if not subject or not teacher or start_hour < 0 or start_hour > 23 or start_minute < 0 or start_minute > 59:
                    failed_count += 1
                    failed_records.append(f'{subject or "未知科目"} - {teacher or "未知教师"}')
                    continue
                
                # 创建新的课程记录
                start_time_obj = time(hour=start_hour, minute=start_minute)
                new_record = CourseRecord(
                    subject=subject,
                    teacher=teacher,
                    date=record_date,
                    start_time=start_time_obj,
                    duration=duration,
                    content='',  # 内容为空，可后续编辑
                    homework='',
                    notes=''
                )
                
                db_session.add(new_record)
                db_session.flush()  # 获取新记录的ID
                
                # 添加学生关联
                try:
                    # 尝试从schedules_data中获取学生信息
                    students_data = schedule_info.get('students')
                    if students_data:
                        # 处理JSON字符串或数组格式的学生ID
                        if isinstance(students_data, str):
                            try:
                                student_ids = json.loads(students_data)
                            except json.JSONDecodeError:
                                student_ids = []
                        else:
                            student_ids = students_data
                        
                        if student_ids and isinstance(student_ids, list):
                            for student_id in student_ids:
                                try:
                                    student_id = int(student_id)
                                    # 检查学生是否存在
                                    student = db_session.get(Student, student_id)
                                    if student:
                                        record_student = RecordStudent(
                                            record_id=new_record.id,
                                            student_id=student_id,
                                            attendance='出席',
                                            homework_status='',
                                            study_status=''
                                        )
                                        db_session.add(record_student)
                                except (ValueError, TypeError):
                                    # 忽略无效的学生ID
                                    pass
                except Exception as e:
                    # 学生关联失败不影响记录创建
                    app.logger.error(f'添加学生关联失败: {str(e)}')
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                subj = schedule_info.get('subject', '未知科目')
                teach = schedule_info.get('teacher', '未知教师')
                failed_records.append(f'{subj} - {teach}')
                app.logger.error(f'批量添加课程记录失败: {str(e)}')
        
        # 提交事务
        db_session.commit()
        
        # 返回结果
        if success_count > 0:
            message = f'成功添加 {success_count} 条课程记录'
            if failed_count > 0:
                message += f'，失败 {failed_count} 条'
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': f'所有记录添加失败，请检查数据后重试'})
            
    except Exception as e:
        db_session.rollback()
        app.logger.error(f'批量添加课程记录异常: {str(e)}')
        return jsonify({'success': False, 'message': f'系统错误：{str(e)}'})
    finally:
        db_session.close()

# 编辑课程记录路由
@app.route('/records/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_record(record_id):
    db_session = Session()
    try:
        record = db_session.get(CourseRecord, record_id)
        if not record:
            flash('课程记录不存在！', 'danger')
            # 获取当前筛选和排序参数并传递
            teacher_filter = request.args.get('teacher', '全部')
            search_term = request.args.get('search', '')
            page_num = request.args.get('page', '1')
            per_page_num = request.args.get('per_page', '10')
            semester_param = request.args.get('semester', '')
            sort_by_param = request.args.get('sort_by', 'id')
            sort_order_param = request.args.get('sort_order', 'desc')
            return redirect(url_for('records', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param, semester=semester_param))
        
        if request.method == 'POST':
            record.subject = request.form.get('subject')
            record.teacher = request.form.get('teacher')
            record.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            record.start_time = time(
                hour=int(request.form.get('start_hour')),
                minute=int(request.form.get('start_minute'))
            )
            record.duration = int(request.form.get('duration'))
            record.content = request.form.get('content', '')
            record.homework = request.form.get('homework', '')
            record.notes = request.form.get('notes', '')
            
            # 更新关联的学生
            student_ids = [int(sid) for sid in request.form.getlist('selected_students[]') if sid]
            existing_records = db_session.query(RecordStudent).filter_by(record_id=record.id).all()
            existing_student_ids = set(rs.student_id for rs in existing_records)
            
            # 删除不再关联的学生
            for rs in existing_records:
                if rs.student_id not in student_ids:
                    db_session.delete(rs)
            
            # 更新或添加学生记录
            for student_id in student_ids:
                attendance = request.form.get(f'student_attendance_{student_id}', '出席')
                if student_id not in existing_student_ids:
                    # 添加新学生记录
                    record_student = RecordStudent(
                        record_id=record.id,
                        student_id=student_id,
                        attendance=attendance,
                        homework_status='',
                        study_status=''
                    )
                    db_session.add(record_student)
                else:
                    # 更新现有学生记录
                    rs = next(rs for rs in existing_records if rs.student_id == student_id)
                    rs.attendance = attendance
            
            try:
                db_session.commit()
                flash('课程记录更新成功！', 'success')
                # 获取当前筛选和排序参数并传递
                teacher_filter = request.form.get('current_teacher', '全部')
                search_term = request.form.get('current_search', '')
                page_num = request.form.get('current_page', '1')
                per_page_num = request.form.get('current_per_page', '10')
                sort_by_param = request.form.get('current_sort_by', 'id')
                semester_param = request.form.get('semester', '')
                sort_order_param = request.form.get('current_sort_order', 'desc')
                return redirect(url_for('records', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param, semester=semester_param))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
                # 获取当前筛选和排序参数并传递
                teacher_filter = request.args.get('teacher', '全部')
                search_term = request.args.get('search', '')
                page_num = request.args.get('page', '1')
                per_page_num = request.args.get('per_page', '10')
                sort_by_param = request.args.get('sort_by', 'id')
                semester_param = request.args.get('semester', '')
                sort_order_param = request.args.get('sort_order', 'desc')
                return redirect(url_for('edit_record', record_id=record_id, teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param))
        
        # 获取所有学生和课程安排供选择
        students = db_session.query(Student).all()
        schedules = db_session.query(Schedule).all()
        
        # 获取当前筛选和排序参数
        current_teacher = request.args.get('teacher', '全部')
        current_search = request.args.get('search', '')
        current_page = request.args.get('page', '1')
        current_per_page = request.args.get('per_page', '10')
        current_sort_by = request.args.get('sort_by', 'id')
        current_semester = request.args.get('semester', '')
        current_sort_order = request.args.get('sort_order', 'desc')
        
        # 获取所有科目和教师列表供下拉选择
        # 从课程安排表中获取科目和教师，如果没有则从课程记录表中获取
        schedule_subjects = db_session.query(Schedule.subject).distinct().all()
        record_subjects = db_session.query(CourseRecord.subject).distinct().all()
        all_subjects = list(set([s[0] for s in schedule_subjects if s[0]] + [s[0] for s in record_subjects if s[0]]))
        
        schedule_teachers = db_session.query(Schedule.teacher).distinct().all()
        record_teachers = db_session.query(CourseRecord.teacher).distinct().all()
        all_teachers = list(set([t[0] for t in schedule_teachers if t[0]] + [t[0] for t in record_teachers if t[0]]))
        
        # 获取当前已选学生的ID列表和出勤状态
        selected_student_ids = [rs.student_id for rs in record.students]
        attendance_records = {rs.student_id: rs.attendance for rs in record.students}
        
        # 获取已选学生的完整对象，用于在模板中显示姓名
        record_students = []
        for rs in record.students:
            student_obj = db_session.get(Student, rs.student_id)
            if student_obj:
                record_students.append({
                    'id': rs.student_id,
                    'name': student_obj.name,
                    'attendance': rs.attendance
                })
        
        # 将学生数据转换为JSON格式，用于客户端分页
        import json
        all_students_json = json.dumps([{
            'id': student.id,
            'name': student.name
        } for student in students])
        
        return render_template('record_form.html', 
                               record=record, 
                               students=students, 
                               schedules=schedules, 
                               all_subjects=all_subjects,
                               all_teachers=all_teachers,
                               selected_student_ids=selected_student_ids,
                               attendance_records=attendance_records,
                               record_students=record_students,
                               all_students_json=all_students_json,
                               current_teacher=current_teacher,
                               current_search=current_search,
                               current_page=current_page,
                               current_per_page=current_per_page,
                               current_sort_by=current_sort_by,
                               current_sort_order=current_sort_order, current_semester=current_semester)
    finally:
        db_session.close()

# 查看课程记录详情路由
@app.route('/records/view/<int:record_id>')
@login_required
def view_record(record_id):
    db_session = Session()
    try:
        record = db_session.get(CourseRecord, record_id)
        if not record:
            flash('课程记录不存在！', 'danger')
            # 获取当前筛选和排序参数并传递
            teacher_filter = request.args.get('teacher', '全部')
            search_term = request.args.get('search', '')
            page_num = request.args.get('page', '1')
            per_page_num = request.args.get('per_page', '10')
            semester_param = request.args.get('semester', '')
            sort_by_param = request.args.get('sort_by', 'id')
            sort_order_param = request.args.get('sort_order', 'desc')
            return redirect(url_for('records', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param, semester=semester_param))
        
        # 获取当前筛选和排序参数并传递到模板
        current_teacher = request.args.get('teacher', '全部')
        current_search = request.args.get('search', '')
        current_page = request.args.get('page', '1')
        current_per_page = request.args.get('per_page', '10')
        current_sort_by = request.args.get('sort_by', 'id')
        current_sort_order = request.args.get('sort_order', 'desc')
        current_semester = request.args.get('semester', '')
        
        return render_template('record_detail.html', 
                               record=record,
                               current_teacher=current_teacher,
                               current_search=current_search,
                               current_page=current_page,
                               current_per_page=current_per_page,
                               current_sort_by=current_sort_by,
                               current_sort_order=current_sort_order, current_semester=current_semester)
    finally:
        db_session.close()

# 删除课程记录路由
@app.route('/records/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    db_session = Session()
    try:
        record = db_session.get(CourseRecord, record_id)
        if not record:
            flash('课程记录不存在！', 'danger')
            # 获取当前筛选和排序参数并传递
            teacher_filter = request.args.get('teacher', '全部')
            search_term = request.args.get('search', '')
            page_num = request.args.get('page', '1')
            semester_param = request.args.get('semester', '')
            per_page_num = request.args.get('per_page', '10')
            sort_by_param = request.args.get('sort_by', 'id')
            sort_order_param = request.args.get('sort_order', 'desc')
            return redirect(url_for('records', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param, semester=semester_param))
        
        db_session.delete(record)
        db_session.commit()
        flash('课程记录删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    # 获取当前筛选和排序参数并传递
    teacher_filter = request.args.get('teacher', '全部')
    search_term = request.args.get('search', '')
    page_num = request.args.get('page', '1')
    per_page_num = request.args.get('per_page', '10')
    semester_param = request.args.get('semester', '')
    sort_by_param = request.args.get('sort_by', 'id')
    sort_order_param = request.args.get('sort_order', 'desc')
    return redirect(url_for('records', teacher=teacher_filter, search=search_term, page=page_num, per_page=per_page_num, sort_by=sort_by_param, sort_order=sort_order_param, semester=semester_param))

# 班级管理路由
@app.route('/classes')
@login_required
def classes():
    db_session = Session()
    try:
        # 获取分页和搜索参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 构建查询
        query = db_session.query(StudentGroup)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                StudentGroup.name.contains(search) | 
                StudentGroup.grade.contains(search) |
                StudentGroup.teacher.contains(search) |
                StudentGroup.subject.contains(search)
            )
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        classes_list = query.order_by(StudentGroup.id.desc()).limit(per_page).offset((page - 1) * per_page).all()
        
        # 如果是AJAX请求，返回JSON数据
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'data': [{
                    'id': c.id,
                    'name': c.name,
                    'grade': c.grade,
                    'teacher': c.teacher,
                    'subject': c.subject,
                    'student_count': len(c.students)
                } for c in classes_list],
                'total': total,
                'page': page,
                'per_page': per_page
            })
        
        # 普通请求返回模板（只返回当前页数据）
        return render_template('classes.html', 
                               classes=classes_list, 
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search)
    finally:
        db_session.close()

# 添加班级路由
@app.route('/classes/add', methods=['GET', 'POST'])
@login_required
def add_class():
    db_session = Session()
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            grade = request.form.get('grade')
            teacher = request.form.get('teacher')
            subject = request.form.get('subject')
            student_ids = request.form.getlist('selected_students[]')
            
            if not name or not grade or not teacher or not subject:
                flash('请填写所有必填字段！', 'danger')
                return redirect(url_for('add_class'))
            
            try:
                new_class = StudentGroup(
                    name=name,
                    grade=grade,
                    teacher=teacher,
                    subject=subject
                    # created_at字段已从模型中移除
                )
                
                db_session.add(new_class)
                db_session.flush()  # 获取新记录的ID
                
                # 添加学生关联
                if student_ids:
                    for student_id in student_ids:
                        group_student = GroupStudent(
                            group_id=new_class.id,
                            student_id=int(student_id)
                        )
                        db_session.add(group_student)
                
                db_session.commit()
                flash('班级添加成功！', 'success')
                return redirect(url_for('classes'))
            except Exception as e:
                db_session.rollback()
                flash(f'添加失败: {str(e)}', 'danger')
        
        # 获取所有学生供选择
        students = db_session.query(Student).all()
        
        return render_template('class_form.html', students=students)
    finally:
        db_session.close()

# 编辑班级路由
@app.route('/classes/edit/<int:class_id>', methods=['GET', 'POST'])
@login_required
def edit_class(class_id):
    db_session = Session()
    try:
        class_obj = db_session.get(StudentGroup, class_id)
        if not class_obj:
            flash('班级不存在！', 'danger')
            return redirect(url_for('classes'))
        
        if request.method == 'POST':
            class_obj.name = request.form.get('name')
            class_obj.grade = request.form.get('grade')
            class_obj.teacher = request.form.get('teacher')
            class_obj.subject = request.form.get('subject')
            
            # 更新关联的学生
            student_ids = [int(sid) for sid in request.form.getlist('selected_students[]') if sid]
            
            # 删除现有关联
            db_session.query(GroupStudent).filter_by(group_id=class_id).delete()
            
            # 添加新关联
            for student_id in student_ids:
                group_student = GroupStudent(
                    group_id=class_id,
                    student_id=student_id
                )
                db_session.add(group_student)
            
            try:
                db_session.commit()
                flash('班级更新成功！', 'success')
                return redirect(url_for('classes'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        # 获取所有学生供选择
        students = db_session.query(Student).all()
        
        # 获取当前班级的学生
        class_students = []
        for gs in db_session.query(GroupStudent).filter_by(group_id=class_id).all():
            student = db_session.get(Student, gs.student_id)
            if student:
                class_students.append(student)
        
        return render_template('class_form.html', 
                               class_obj=class_obj, 
                               students=students,
                               class_students=class_students)
    finally:
        db_session.close()

# 删除班级路由
@app.route('/classes/delete/<int:class_id>', methods=['POST'])
@login_required
def delete_class(class_id):
    db_session = Session()
    try:
        class_obj = db_session.get(StudentGroup, class_id)
        if not class_obj:
            flash('班级不存在！', 'danger')
            return redirect(url_for('classes'))
        
        db_session.delete(class_obj)
        db_session.commit()
        flash('班级删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('classes'))

# 成绩管理路由
@app.route('/grades')
@login_required
def grades():
    db_session = Session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)
        
        # 构建查询
        query = db_session.query(ExamRecord)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                ExamRecord.subject.contains(search) | 
                ExamRecord.exam_type.contains(search) |
                ExamRecord.grade.contains(search)
            )
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        grades_list = query.order_by(ExamRecord.id.desc()).limit(per_page).offset((page - 1) * per_page).all()
        
        return render_template('grades.html', 
                               grades=grades_list, 
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search)
    finally:
        db_session.close()

# 添加考试记录路由
@app.route('/grades/add_exam', methods=['GET', 'POST'])
@login_required
def add_exam():
    db_session = Session()
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            subject = request.form.get('subject')
            grade = request.form.get('grade')
            teacher = request.form.get('teacher')
            total_score = int(request.form.get('total_score'))
            exam_date_str = request.form.get('exam_date')
            group_id = request.form.get('group_id')
            
            if not name or not subject or not grade or not teacher or not exam_date_str:
                flash('请填写所有必填字段！', 'danger')
                return redirect(url_for('add_exam'))
            
            try:
                exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
                
                new_exam = ExamRecord(
                    name=name,
                    subject=subject,
                    grade=grade,
                    teacher=teacher,
                    total_score=total_score,
                    exam_date=exam_date,
                    student_group_id=int(group_id) if group_id else None
                )
                
                db_session.add(new_exam)
                db_session.commit()
                flash('考试记录添加成功！', 'success')
                return redirect(url_for('grades'))
            except Exception as e:
                db_session.rollback()
                flash(f'添加失败: {str(e)}', 'danger')
        
        # 获取所有班级供选择
        groups = db_session.query(StudentGroup).all()
        return render_template('exam_form.html', groups=groups)
    finally:
        db_session.close()

# 编辑考试记录路由
@app.route('/grades/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def edit_exam(exam_id):
    db_session = Session()
    try:
        exam = db_session.get(ExamRecord, exam_id)
        if not exam:
            flash('考试记录不存在！', 'danger')
            return redirect(url_for('grades'))
        
        if request.method == 'POST':
            exam.name = request.form.get('name')
            exam.subject = request.form.get('subject')
            exam.grade = request.form.get('grade')
            exam.teacher = request.form.get('teacher')
            exam.total_score = int(request.form.get('total_score'))
            exam.exam_date = datetime.strptime(request.form.get('exam_date'), '%Y-%m-%d').date()
            group_id = request.form.get('group_id')
            exam.student_group_id = int(group_id) if group_id else None
            
            try:
                db_session.commit()
                flash('考试记录更新成功！', 'success')
                return redirect(url_for('grades'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        # 获取所有班级供选择
        groups = db_session.query(StudentGroup).all()
        return render_template('exam_form.html', exam=exam, groups=groups)
    finally:
        db_session.close()

# 删除考试记录路由
@app.route('/grades/delete_exam/<int:exam_id>', methods=['POST'])
@login_required
def delete_exam(exam_id):
    db_session = Session()
    try:
        exam = db_session.get(ExamRecord, exam_id)
        if not exam:
            flash('考试记录不存在！', 'danger')
            return redirect(url_for('grades'))
        
        db_session.delete(exam)
        db_session.commit()
        flash('考试记录删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('grades'))

# 管理考试成绩路由
@app.route('/grades/manage/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def manage_grades(exam_id):
    db_session = Session()
    try:
        exam = db_session.get(ExamRecord, exam_id)
        if not exam:
            flash('考试记录不存在！', 'danger')
            return redirect(url_for('grades'))
        
        # 检查是否为查看模式
        view_mode = request.args.get('view', 'false').lower() == 'true'
        
        if request.method == 'POST' and not view_mode:
            # 获取所有学生成绩
            student_ids = request.form.getlist('student_id')
            scores = request.form.getlist('score')
            ranks = request.form.getlist('rank')
            grade_ranks = request.form.getlist('grade_rank')
            class_ranks = request.form.getlist('class_rank')

            # 基础校验准备
            errors = []
            valid_entries = []  # (student_id:int, score:float, rank_str:str|None, grade_rank_str:str|None, class_rank_str:str|None)

            # 逐行校验分数格式与范围
            for i in range(len(student_ids)):
                sid_raw = student_ids[i]
                score_raw = scores[i] if i < len(scores) else ''
                rank_raw = ranks[i] if i < len(ranks) else ''
                grade_rank_raw = grade_ranks[i] if i < len(grade_ranks) else ''
                class_rank_raw = class_ranks[i] if i < len(class_ranks) else ''

                try:
                    sid = int(sid_raw)
                except Exception:
                    # 跳过无效行
                    continue

                if score_raw is None or str(score_raw).strip() == '':
                    # 允许空分数（表示未录入），不写入该行
                    continue

                try:
                    score_val = float(score_raw)
                except Exception:
                    errors.append(f'学生ID {sid} 分数格式不正确: {score_raw}')
                    continue

                # 分数范围校验
                if score_val < 0 or (exam.total_score is not None and score_val > float(exam.total_score)):
                    errors.append(f'学生ID {sid} 分数越界: {score_val}')
                    continue

                valid_entries.append((sid, score_val, rank_raw.strip() if rank_raw else '', grade_rank_raw.strip() if grade_rank_raw else '', class_rank_raw.strip() if class_rank_raw else ''))

            if errors:
                flash('保存失败：' + '；'.join(errors), 'danger')
            else:
                # 若大部分未填写 rank，则根据分数计算一次并列名次
                provided_rank_count = sum(1 for _, _, r, _, _ in valid_entries if r)
                if provided_rank_count == 0 and len(valid_entries) > 0:
                    rank_map = compute_competition_ranks({sid: score for sid, score, _, _, _ in valid_entries})
                else:
                    # 用户提供了 rank，后端尊重之；为空的可不填
                    rank_map = {}

                # 覆盖写入：先清空旧记录
                db_session.query(StudentScore).filter_by(exam_id=exam_id).delete()

                # 批量写入新记录
                for sid, score_val, rank_str, grade_rank_str, class_rank_str in valid_entries:
                    final_rank = rank_str
                    if not final_rank and sid in rank_map:
                        final_rank = str(rank_map[sid])

                    db_session.add(StudentScore(
                        exam_id=exam_id,
                        student_id=sid,
                        score=score_val,
                        rank=final_rank or '',
                        grade_rank=grade_rank_str or '',
                        class_rank=class_rank_str or ''
                    ))

                try:
                    db_session.commit()
                    flash('成绩保存成功！', 'success')
                    return redirect(url_for('grades'))
                except Exception as e:
                    db_session.rollback()
                    flash(f'保存失败: {str(e)}', 'danger')
        
        # 获取当前考试的所有成绩
        scores = db_session.query(StudentScore).filter_by(exam_id=exam_id).all()
        
        # 获取相关班级的学生
        students = []
        if exam.student_group_id:
            group_students = db_session.query(GroupStudent).filter_by(group_id=exam.student_group_id).all()
            student_ids = [gs.student_id for gs in group_students]
            students = db_session.query(Student).filter(Student.id.in_(student_ids)).all()
        else:
            # 如果没有指定班级，获取所有符合年级的学生
            students = db_session.query(Student).filter_by(grade=exam.grade).all()
        
        # 创建学生ID到成绩的映射
        score_map = {score.student_id: score for score in scores}
        
        return render_template('manage_grades.html', 
                               exam=exam, 
                               students=students, 
                               score_map=score_map,
                               view_mode=view_mode)
    finally:
        db_session.close()

# 成绩导出（CSV）
@app.route('/grades/manage/<int:exam_id>/export', methods=['GET'])
@login_required
def export_grades_csv(exam_id):
    db_session = Session()
    try:
        exam = db_session.get(ExamRecord, exam_id)
        if not exam:
            flash('考试记录不存在！', 'danger')
            return redirect(url_for('grades'))

        scores = db_session.query(StudentScore).filter_by(exam_id=exam_id).all()
        student_ids = [s.student_id for s in scores]
        students = {}
        if student_ids:
            for s in db_session.query(Student).filter(Student.id.in_(student_ids)).all():
                students[s.id] = s

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['姓名', '分数', '排名', '年级排名', '班级排名'])
        for s in scores:
            name = students.get(s.student_id).name if s.student_id in students else ''
            writer.writerow([name, s.score if s.score is not None else '', s.rank or '', s.grade_rank or '', s.class_rank or ''])

        csv_data = output.getvalue()
        output.close()
        # 为兼容 Excel 正确识别 UTF-8 中文，添加 BOM（UTF-8-SIG）
        csv_with_bom = '\ufeff' + csv_data
        filename = f"exam_{exam_id}_grades.csv"
        headers = {
            'Content-Disposition': f"attachment; filename=exam_{exam_id}_grades.csv; filename*=UTF-8''exam_{exam_id}_grades.csv",
            'Content-Type': 'text/csv; charset=utf-8'
        }
        return Response(csv_with_bom, headers=headers)
    finally:
        db_session.close()

# 成绩导入（CSV，覆盖写入）
@app.route('/grades/manage/<int:exam_id>/import', methods=['POST'])
@login_required
def import_grades_csv(exam_id):
    db_session = Session()
    try:
        exam = db_session.get(ExamRecord, exam_id)
        if not exam:
            flash('考试记录不存在！', 'danger')
            return redirect(url_for('grades'))

        file = request.files.get('file')
        if not file or file.filename == '':
            flash('请选择CSV文件后再导入。', 'warning')
            return redirect(url_for('manage_grades', exam_id=exam_id))

        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
        except Exception:
            flash('CSV 文件编码需为 UTF-8。', 'danger')
            return redirect(url_for('manage_grades', exam_id=exam_id))

        reader = csv.DictReader(stream)
        # 检查CSV表头，支持新旧两种格式
        fieldnames = [c.strip() for c in reader.fieldnames or []]
        
        # 判断CSV格式：新格式（中文表头）还是旧格式（英文表头）
        is_new_format = '姓名' in fieldnames and '分数' in fieldnames
        is_old_format = 'student_id' in fieldnames and 'score' in fieldnames
        
        if not (is_new_format or is_old_format):
            flash('CSV 缺少必要列：姓名/student_id, 分数/score。', 'danger')
            return redirect(url_for('manage_grades', exam_id=exam_id))

        # 允许范围内的学生：限定在该考试班级（若有）或同年级
        allowed_student_ids = set()
        if exam.student_group_id:
            group_students = db_session.query(GroupStudent).filter_by(group_id=exam.student_group_id).all()
            allowed_student_ids = {gs.student_id for gs in group_students}
        else:
            for s in db_session.query(Student).filter_by(grade=exam.grade).all():
                allowed_student_ids.add(s.id)

        rows = list(reader)
        errors = []
        entries = []  # (sid, score_val, rank_str, grade_rank_str, class_rank_str)
        for idx, row in enumerate(rows, start=2):  # header是第1行
            # 根据CSV格式选择字段名
            if is_new_format:
                sid_raw = (row.get('姓名') or '').strip()  # 新格式使用姓名作为标识
                score_raw = (row.get('分数') or '').strip()
                rank_raw = (row.get('排名') or '').strip()
                grade_rank_raw = (row.get('年级排名') or '').strip()
                class_rank_raw = (row.get('班级排名') or '').strip()
            else:
                sid_raw = (row.get('student_id') or '').strip()
                score_raw = (row.get('score') or '').strip()
                rank_raw = (row.get('rank') or '').strip()
                grade_rank_raw = (row.get('grade_rank') or '').strip()
                class_rank_raw = (row.get('class_rank') or '').strip()

            # 学生标识处理
            if is_new_format:
                # 新格式：使用姓名查找学生ID
                student_name = sid_raw
                if not student_name:
                    errors.append(f'第{idx}行 学生姓名为空')
                    continue
                
                # 根据姓名查找学生
                matching_students = db_session.query(Student).filter(Student.name == student_name).all()
                if len(matching_students) == 0:
                    errors.append(f'第{idx}行 学生姓名"{student_name}"不存在')
                    continue
                elif len(matching_students) > 1:
                    errors.append(f'第{idx}行 学生姓名"{student_name}"存在重名，请使用学生ID格式导入')
                    continue
                
                sid = matching_students[0].id
            else:
                # 旧格式：直接使用student_id
                try:
                    sid = int(sid_raw)
                except Exception:
                    errors.append(f'第{idx}行 student_id 非法: {sid_raw}')
                    continue

            if allowed_student_ids and sid not in allowed_student_ids:
                errors.append(f'第{idx}行 学生ID {sid} 不在本班/年级范围内')
                continue

            # 分数
            if score_raw == '':
                # 允许空分数，视为跳过
                continue
            try:
                score_val = float(score_raw)
            except Exception:
                errors.append(f'第{idx}行 分数格式错误: {score_raw}')
                continue
            if score_val < 0 or (exam.total_score is not None and score_val > float(exam.total_score)):
                errors.append(f'第{idx}行 分数越界: {score_val}')
                continue

            entries.append((sid, score_val, rank_raw, grade_rank_raw, class_rank_raw))

        if errors:
            flash('导入失败：' + '；'.join(errors[:10]) + ('' if len(errors) <= 10 else f' 等 {len(errors)} 条'), 'danger')
            return redirect(url_for('manage_grades', exam_id=exam_id))

        # 生成名次（若导入没有提供 rank）
        provided_rank_count = sum(1 for _, _, r in entries if r)
        if provided_rank_count == 0 and len(entries) > 0:
            rank_map = compute_competition_ranks({sid: score for sid, score, _ in entries})
        else:
            rank_map = {}

        # 覆盖写入
        db_session.query(StudentScore).filter_by(exam_id=exam_id).delete()
        for sid, score_val, rank_str, grade_rank_str, class_rank_str in entries:
            final_rank = rank_str or (str(rank_map.get(sid)) if sid in rank_map else '')
            db_session.add(StudentScore(
                exam_id=exam_id,
                student_id=sid,
                score=score_val,
                rank=final_rank,
                grade_rank=grade_rank_str,
                class_rank=class_rank_str
            ))
        try:
            db_session.commit()
            flash(f'导入成功：共导入 {len(entries)} 条记录。', 'success')
        except Exception as e:
            db_session.rollback()
            flash(f'导入失败：{str(e)}', 'danger')
        return redirect(url_for('manage_grades', exam_id=exam_id))
    finally:
        db_session.close()
# 学费管理路由
@app.route('/payments')
@login_required
def payments():
    db_session = Session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)
        
        # 构建查询
        query = db_session.query(Payment).join(Student)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                Student.name.contains(search) | 
                Payment.payment_method.contains(search)
            )
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        payments_list = query.order_by(Payment.id.desc()).limit(per_page).offset((page - 1) * per_page).all()
        
        return render_template('payments.html', 
                               payments=payments_list, 
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search)
    finally:
        db_session.close()

# 添加缴费记录路由
@app.route('/payments/add', methods=['GET', 'POST'])
@login_required
def add_payment():
    db_session = Session()
    try:
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            amount = float(request.form.get('amount'))
            payment_date_str = request.form.get('payment_date')
            payment_method = request.form.get('payment_method')
            discount = float(request.form.get('discount', 0))
            
            if not student_id or not amount or not payment_date_str or not payment_method:
                flash('请填写所有必填字段！', 'danger')
                return redirect(url_for('add_payment'))
            
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                
                new_payment = Payment(
                    student_id=int(student_id),
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    discount=discount
                )
                
                db_session.add(new_payment)
                db_session.commit()
                flash('缴费记录添加成功！', 'success')
                return redirect(url_for('payments'))
            except Exception as e:
                db_session.rollback()
                flash(f'添加失败: {str(e)}', 'danger')
        
        # 获取所有学生供选择
        students = db_session.query(Student).all()
        return render_template('payment_form.html', students=students)
    finally:
        db_session.close()

# 编辑缴费记录路由
@app.route('/payments/edit/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def edit_payment(payment_id):
    db_session = Session()
    try:
        payment = db_session.get(Payment, payment_id)
        if not payment:
            flash('缴费记录不存在！', 'danger')
            return redirect(url_for('payments'))
        
        if request.method == 'POST':
            payment.student_id = int(request.form.get('student_id'))
            payment.amount = float(request.form.get('amount'))
            payment.payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
            payment.payment_method = request.form.get('payment_method')
            payment.discount = float(request.form.get('discount', 0))
            
            try:
                db_session.commit()
                flash('缴费记录更新成功！', 'success')
                return redirect(url_for('payments'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        # 获取所有学生供选择
        students = db_session.query(Student).all()
        return render_template('payment_form.html', payment=payment, students=students)
    finally:
        db_session.close()

# 删除缴费记录路由
@app.route('/payments/delete/<int:payment_id>', methods=['POST'])
@login_required
def delete_payment(payment_id):
    db_session = Session()
    try:
        payment = db_session.get(Payment, payment_id)
        if not payment:
            flash('缴费记录不存在！', 'danger')
            return redirect(url_for('payments'))
        
        db_session.delete(payment)
        db_session.commit()
        flash('缴费记录删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('payments'))

# 课程报名管理路由
@app.route('/enrollments')
@login_required
def enrollments():
    db_session = Session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)
        
        # 构建查询
        query = db_session.query(CourseEnrollment).join(Student)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                Student.name.contains(search) | 
                CourseEnrollment.subject.contains(search) |
                CourseEnrollment.course_type.contains(search)
            )
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        enrollments_list = query.order_by(CourseEnrollment.id.desc()).limit(per_page).offset((page - 1) * per_page).all()
        
        return render_template('enrollments.html', 
                               enrollments=enrollments_list, 
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search)
    finally:
        db_session.close()

# 添加课程报名路由
@app.route('/enrollments/add', methods=['GET', 'POST'])
@login_required
def add_enrollment():
    db_session = Session()
    try:
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            subject = request.form.get('subject')
            course_type = request.form.get('course_type')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            fee_per_lesson = float(request.form.get('fee_per_lesson'))
            total_lessons = int(request.form.get('total_lessons'))
            remaining_fee = float(request.form.get('remaining_fee', 0))
            
            if not student_id or not subject or not course_type or not start_date_str or not end_date_str:
                flash('请填写所有必填字段！', 'danger')
                return redirect(url_for('add_enrollment'))
            
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                total_fee = fee_per_lesson * total_lessons
                
                new_enrollment = CourseEnrollment(
                    student_id=int(student_id),
                    subject=subject,
                    course_type=course_type,
                    start_date=start_date,
                    end_date=end_date,
                    fee_per_lesson=fee_per_lesson,
                    total_lessons=total_lessons,
                    total_fee=total_fee,
                    remaining_fee=remaining_fee
                )
                
                db_session.add(new_enrollment)
                db_session.commit()
                flash('课程报名添加成功！', 'success')
                return redirect(url_for('enrollments'))
            except Exception as e:
                db_session.rollback()
                flash(f'添加失败: {str(e)}', 'danger')
        
        # 获取所有学生供选择
        students = db_session.query(Student).all()
        return render_template('enrollment_form.html', students=students)
    finally:
        db_session.close()

# 编辑课程报名路由
@app.route('/enrollments/edit/<int:enrollment_id>', methods=['GET', 'POST'])
@login_required
def edit_enrollment(enrollment_id):
    db_session = Session()
    try:
        enrollment = db_session.get(CourseEnrollment, enrollment_id)
        if not enrollment:
            flash('课程报名记录不存在！', 'danger')
            return redirect(url_for('enrollments'))
        
        if request.method == 'POST':
            enrollment.student_id = int(request.form.get('student_id'))
            enrollment.subject = request.form.get('subject')
            enrollment.course_type = request.form.get('course_type')
            enrollment.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            enrollment.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            enrollment.fee_per_lesson = float(request.form.get('fee_per_lesson'))
            enrollment.total_lessons = int(request.form.get('total_lessons'))
            enrollment.total_fee = enrollment.fee_per_lesson * enrollment.total_lessons
            enrollment.remaining_fee = float(request.form.get('remaining_fee', 0))
            
            try:
                db_session.commit()
                flash('课程报名记录更新成功！', 'success')
                return redirect(url_for('enrollments'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        # 获取所有学生供选择
        students = db_session.query(Student).all()
        return render_template('enrollment_form.html', enrollment=enrollment, students=students)
    finally:
        db_session.close()

# 删除课程报名路由
@app.route('/enrollments/delete/<int:enrollment_id>', methods=['POST'])
@login_required
def delete_enrollment(enrollment_id):
    db_session = Session()
    try:
        enrollment = db_session.get(CourseEnrollment, enrollment_id)
        if not enrollment:
            flash('课程报名记录不存在！', 'danger')
            return redirect(url_for('enrollments'))
        
        db_session.delete(enrollment)
        db_session.commit()
        flash('课程报名记录删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('enrollments'))

# 用户管理路由
@app.route('/users')
@login_required
def users():
    # 只允许管理员访问
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'danger')
        return redirect(url_for('index'))
        
    db_session = Session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)
        
        # 构建查询
        query = db_session.query(User)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                User.username.contains(search) | 
                User.name.contains(search)
            )
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        users_list = query.order_by(User.id.desc()).limit(per_page).offset((page - 1) * per_page).all()
        
        return render_template('users.html', 
                               users=users_list, 
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search)
    finally:
        db_session.close()

# 添加用户路由
@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    # 只允许管理员访问
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        name = request.form.get('name')
        
        if not username or not password or not role or not name:
            flash('请填写所有必填字段！', 'danger')
            return redirect(url_for('add_user'))
        
        db_session = Session()
        try:
            # 检查用户名是否已存在
            existing_user = db_session.query(User).filter_by(username=username).first()
            if existing_user:
                flash('用户名已存在！', 'danger')
                return redirect(url_for('add_user'))
                
            password_hash = generate_password_hash(password, method='sha256')
            new_user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                name=name
            )
            
            db_session.add(new_user)
            db_session.commit()
            flash('用户添加成功！', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            db_session.rollback()
            flash(f'添加失败: {str(e)}', 'danger')
        finally:
            db_session.close()
            
    return render_template('user_form.html')

# 编辑用户路由
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'danger')
        return redirect(url_for('index'))
        
    db_session = Session()
    try:
        user = db_session.get(User, user_id)
        if not user:
            flash('用户不存在！', 'danger')
            return redirect(url_for('users'))
        
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.role = request.form.get('role')
            
            # 如果提供了新密码，则更新密码
            new_password = request.form.get('password')
            if new_password:
                user.password_hash = generate_password_hash(new_password)
            
            try:
                db_session.commit()
                flash('用户信息更新成功！', 'success')
                return redirect(url_for('users'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        return render_template('user_form.html', user=user)
    finally:
        db_session.close()

# 删除用户路由
@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'danger')
        return redirect(url_for('index'))
        
    if user_id == current_user.id:
        flash('不能删除当前登录的用户！', 'danger')
        return redirect(url_for('users'))
        
    db_session = Session()
    try:
        user = db_session.get(User, user_id)
        if not user:
            flash('用户不存在！', 'danger')
            return redirect(url_for('users'))
        
        db_session.delete(user)
        db_session.commit()
        flash('用户删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('users'))

# 初始化管理员账户
def init_admin_user():
    db_session = Session()
    try:
        # 检查是否已存在管理员账户
        admin = db_session.query(User).filter_by(role='admin').first()
        if not admin:
            # 创建默认管理员账户
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                name='系统管理员'
            )
            db_session.add(admin_user)
            db_session.commit()
            print('已创建默认管理员账户: admin/admin123')
    except Exception as e:
        db_session.rollback()
        print(f'创建管理员账户失败: {str(e)}')
    finally:
        db_session.close()

# 应用启动时初始化管理员账户
init_admin_user()

# 教师管理路由
@app.route('/teachers')
@login_required
def teachers():
    db_session = Session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # 验证分页参数
        page, per_page, search = validate_pagination_params(page, per_page, search)
        
        # 构建查询
        query = db_session.query(Teacher)
        
        # 添加搜索条件
        if search:
            query = query.filter(
                Teacher.name.contains(search) | 
                Teacher.subject.contains(search)
            )
        
        # 获取总数
        total = query.count()
        
        # 应用分页和排序
        teachers_list = query.order_by(Teacher.id.desc()).limit(per_page).offset((page - 1) * per_page).all()
        
        return render_template('teachers.html', 
                               teachers=teachers_list, 
                               total=total,
                               page=page,
                               per_page=per_page,
                               search=search)
    finally:
        db_session.close()

# 添加教师路由
@app.route('/teachers/add', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        subject = request.form.get('subject')
        status = request.form.get('status', '在职')
        entry_date_str = request.form.get('entry_date')
        notes = request.form.get('notes', '')
        
        if not name:
            flash('请填写教师姓名！', 'danger')
            return redirect(url_for('add_teacher'))
        
        db_session = Session()
        try:
            entry_date = None
            if entry_date_str:
                entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                
            new_teacher = Teacher(
                name=name,
                gender=gender,
                phone=phone,
                email=email,
                subject=subject,
                status=status,
                entry_date=entry_date,
                notes=notes
            )
            
            db_session.add(new_teacher)
            db_session.commit()
            flash('教师添加成功！', 'success')
            return redirect(url_for('teachers'))
        except Exception as e:
            db_session.rollback()
            flash(f'添加失败: {str(e)}', 'danger')
        finally:
            db_session.close()
            
    return render_template('teacher_form.html')

# 编辑教师路由
@app.route('/teachers/edit/<int:teacher_id>', methods=['GET', 'POST'])
@login_required
def edit_teacher(teacher_id):
    db_session = Session()
    try:
        teacher = db_session.get(Teacher, teacher_id)
        if not teacher:
            flash('教师不存在！', 'danger')
            return redirect(url_for('teachers'))
        
        if request.method == 'POST':
            teacher.name = request.form.get('name')
            teacher.gender = request.form.get('gender')
            teacher.phone = request.form.get('phone')
            teacher.email = request.form.get('email')
            teacher.subject = request.form.get('subject')
            teacher.status = request.form.get('status')
            entry_date_str = request.form.get('entry_date')
            if entry_date_str:
                teacher.entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            teacher.notes = request.form.get('notes', '')
            
            try:
                db_session.commit()
                flash('教师信息更新成功！', 'success')
                return redirect(url_for('teachers'))
            except Exception as e:
                db_session.rollback()
                flash(f'更新失败: {str(e)}', 'danger')
        
        return render_template('teacher_form.html', teacher=teacher)
    finally:
        db_session.close()

# 删除教师路由
@app.route('/teachers/delete/<int:teacher_id>', methods=['POST'])
@login_required
def delete_teacher(teacher_id):
    # 验证密码
    password = request.form.get('password')
    if password:
        db_session = Session()
        try:
            user = db_session.get(User, current_user.id)
            if not check_password_hash(user.password_hash, password):
                flash('密码错误，无法执行删除操作！', 'danger')
                return redirect(url_for('teachers'))
        finally:
            db_session.close()
    else:
        flash('请输入密码以确认删除操作！', 'danger')
        return redirect(url_for('teachers'))
    
    # 执行删除操作
    db_session = Session()
    try:
        teacher = db_session.get(Teacher, teacher_id)
        if not teacher:
            flash('教师不存在！', 'danger')
            return redirect(url_for('teachers'))
        
        # 检查是否有关联记录
        # 这里可以添加检查逻辑，例如检查是否有课程安排或课程记录关联此教师
        
        db_session.delete(teacher)
        db_session.commit()
        flash('教师删除成功！', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    finally:
        db_session.close()
        
    return redirect(url_for('teachers'))

# 查询课程记录API（用于预览）
@app.route('/api/records/query', methods=['POST'])
@login_required
def query_records():
    db_session = Session()
    try:
        # 获取筛选条件
        student_id = request.form.get('student_id')
        subjects = request.form.getlist('subjects[]')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # 构建查询
        query = db_session.query(
            Student.name.label('student_name'),
            Student.grade.label('student_grade'),
            CourseRecord.subject,
            CourseRecord.date,
            CourseRecord.start_time,
            CourseRecord.duration
        ).join(
            RecordStudent, RecordStudent.record_id == CourseRecord.id
        ).join(
            Student, Student.id == RecordStudent.student_id
        ).filter(
            RecordStudent.attendance.notin_(['请假', '缺席'])
        )
        
        # 应用筛选条件
        if student_id:
            query = query.filter(Student.id == student_id)
        
        if subjects:
            query = query.filter(CourseRecord.subject.in_(subjects))
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(CourseRecord.date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(CourseRecord.date <= end_date_obj)
        
        # 执行查询
        results = query.order_by(CourseRecord.date, CourseRecord.start_time).all()
        
        # 格式化结果
        records = []
        for result in results:
            records.append({
                'student_name': result.student_name,
                'student_grade': result.student_grade,
                'subject': result.subject,
                'date': result.date.strftime('%Y-%m-%d'),
                'start_time': result.start_time.strftime('%H:%M'),
                'duration': result.duration
            })
        
        return jsonify({'success': True, 'records': records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        db_session.close()

# 导出课程记录API
# 简化的导出课程记录API
@app.route('/api/records/export', methods=['POST'])
@login_required
def export_records():
    print("Export API called")  # 调试信息
    
    try:
        import csv
        import io
        
        db_session = Session()
        
        # 获取筛选条件
        student_id = request.form.get('student_id')
        subjects = request.form.getlist('subjects[]')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        print(f"Filters: student_id={student_id}, subjects={subjects}, start_date={start_date}, end_date={end_date}")
        
        # 构建查询
        query = db_session.query(
            Student.name.label('student_name'),
            Student.grade.label('student_grade'),
            CourseRecord.subject,
            CourseRecord.date,
            CourseRecord.start_time,
            CourseRecord.duration
        ).join(
            RecordStudent, RecordStudent.record_id == CourseRecord.id
        ).join(
            Student, Student.id == RecordStudent.student_id
        ).filter(
            RecordStudent.attendance.notin_(['请假', '缺席'])
        )
        
        # 应用筛选条件
        if student_id and student_id.strip():
            query = query.filter(Student.id == int(student_id))
        
        if subjects and len(subjects) > 0:
            query = query.filter(CourseRecord.subject.in_(subjects))
        
        if start_date and start_date.strip():
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(CourseRecord.date >= start_date_obj)
        
        if end_date and end_date.strip():
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(CourseRecord.date <= end_date_obj)
        
        # 执行查询
        results = query.order_by(CourseRecord.date, CourseRecord.start_time).all()
        print(f"Found {len(results)} records")
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow(['学生姓名', '年级', '科目', '上课日期', '开始时间', '上课时长(分钟)'])
        
        # 写入数据行
        for result in results:
            writer.writerow([
                result.student_name,
                result.student_grade,
                result.subject,
                result.date.strftime('%Y-%m-%d'),
                result.start_time.strftime('%H:%M'),
                result.duration
            ])
        
        # 获取CSV内容
        csv_content = output.getvalue()
        output.close()
        
        # 添加BOM以支持Excel中文显示
        csv_content = '\ufeff' + csv_content
        
        print(f"CSV content length: {len(csv_content)}")
        
        # 创建响应
        response = Response(
            csv_content.encode('utf-8'),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=course_records_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
        db_session.close()
        return response
        
    except Exception as e:
        print(f"Export error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
# 测试路由
@app.route('/test')
def test_page():
    with open('test_export.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/test-config')
def test_config():
    return render_template('test_config.html', config=config)

@app.route('/test-encryption')
def test_encryption():
    with open('test_frontend_encryption.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/simple-login-test')
def simple_login_test():
    with open('simple_login_test.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/capture_encrypted_data.html')
def capture_encrypted_data():
    with open('capture_encrypted_data.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/plain_login_test.html')
def plain_login_test():
    with open('plain_login_test.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/debug_login.html')
def debug_login():
    with open('debug_login.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/extract_encrypted_data.html')
def extract_encrypted_data():
    with open('extract_encrypted_data.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/final_login_test.html')
def final_login_test():
    with open('final_login_test.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/simple_login.html')
def simple_login():
    with open('simple_login.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/aes_login_test.html')
def aes_login_test():
    with open('aes_login_test.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/simple_aes_test.html')
def simple_aes_test():
    with open('simple_aes_test.html', 'r', encoding='utf-8') as f:
        return f.read()

# 临时测试路由 - 仅用于开发测试，绕过验证码
@app.route('/test_login', methods=['GET', 'POST'])
@csrf.exempt  # 绕过CSRF保护用于测试
def test_login():
    """测试登录路由 - 绕过验证码验证（仅开发环境）"""
    if not app.debug:
        return "此路由仅在开发环境可用", 403
    
    if request.method == 'GET':
        return jsonify({'message': '请使用POST方法提交用户名和密码'})
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'message': '请输入用户名和密码'})
    
    db_session = Session()
    try:
        user = db_session.query(User).filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
        
        if check_password_hash(user.password_hash, password):
            login_user(user)
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'})
    finally:
        db_session.close()

# 测试添加课程记录路由（用于调试）
@app.route('/test_add_record', methods=['GET', 'POST'])
@login_required
@csrf.exempt  # 绕过CSRF保护用于测试
@admin_required
def test_add_record():
    """测试添加课程记录功能，用于调试"""
    if request.method == 'GET':
        db_session = Session()
        try:
            # 获取所有学生用于测试表单
            students = db_session.query(Student).all()
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>测试添加课程记录</title>
                    <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css">
                </head>
                <body>
                    <div class="container mt-5">
                        <h1>测试添加课程记录</h1>
                        <form id="test-form" method="post">
                            <div class="mb-3">
                                <label for="subject" class="form-label">科目</label>
                                <input type="text" class="form-control" id="subject" name="subject" required>
                            </div>
                            <div class="mb-3">
                                <label for="teacher" class="form-label">教师</label>
                                <input type="text" class="form-control" id="teacher" name="teacher" required>
                            </div>
                            <div class="mb-3">
                                <label for="date" class="form-label">日期</label>
                                <input type="date" class="form-control" id="date" name="date" required>
                            </div>
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label for="start_hour" class="form-label">开始时间(时)</label>
                                    <select class="form-select" id="start_hour" name="start_hour">
                                        {% for hour in range(8, 22) %}
                                        <option value="{{ hour }}">{{ hour }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label for="start_minute" class="form-label">开始时间(分)</label>
                                    <select class="form-select" id="start_minute" name="start_minute">
                                        <option value="0">00</option>
                                        <option value="15">15</option>
                                        <option value="30">30</option>
                                        <option value="45">45</option>
                                    </select>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label for="duration" class="form-label">时长(分钟)</label>
                                <input type="number" class="form-control" id="duration" name="duration" value="45">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">选择学生</label>
                                <div class="form-check">
                                    {% for student in students %}
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" value="{{ student.id }}" id="student-{{ student.id }}" name="student_ids[]">
                                        <label class="form-check-label" for="student-{{ student.id }}">{{ student.name }}</label>
                                    </div>
                                    {% endfor %}
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">提交测试</button>
                        </form>
                        <div id="result" class="mt-5"></div>
                    </div>
                    <script src="https://cdn.bootcdn.net/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
                    <script>
                        $(document).ready(function() {
                            $('#test-form').submit(function(e) {
                                e.preventDefault();
                                
                                $.ajax({
                                    url: '{{ url_for('test_add_record') }}',
                                    type: 'POST',
                                    data: $(this).serialize(),
                                    success: function(response) {
                                        if (response.success) {
                                            $('#result').html('<div class="alert alert-success">' + response.message + '</div>');
                                        } else {
                                            $('#result').html('<div class="alert alert-danger">' + response.error + '</div>');
                                            console.error(response);
                                        }
                                    },
                                    error: function(xhr) {
                                        $('#result').html('<div class="alert alert-danger">请求失败: ' + xhr.statusText + '</div>');
                                        console.error(xhr);
                                    }
                                });
                            });
                        });
                    </script>
                </body>
                </html>
            ''', students=students)
        finally:
            db_session.close()
    
    db_session = Session()
    try:
        # 获取表单数据
        subject = request.form.get('subject')
        teacher = request.form.get('teacher')
        date_str = request.form.get('date')
        start_hour = int(request.form.get('start_hour'))
        start_minute = int(request.form.get('start_minute'))
        duration = int(request.form.get('duration'))
        content = request.form.get('content', '')
        homework = request.form.get('homework', '')
        notes = request.form.get('notes', '')
        student_ids = request.form.getlist('student_ids[]')
        
        app.logger.info(f'测试添加课程记录，表单数据: subject={subject}, teacher={teacher}, date={date_str}, student_ids={student_ids}')
        
        # 验证必填字段
        if not subject or not teacher or not date_str:
            error_msg = '请填写所有必填字段'
            app.logger.warning(f'测试失败: {error_msg}')
            return jsonify({'success': False, 'error': error_msg})
        
        # 解析日期和时间
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time_obj = time(hour=start_hour, minute=start_minute)
        except ValueError as ve:
            error_msg = f'日期或时间格式错误: {str(ve)}'
            app.logger.error(f'测试失败: {error_msg}')
            return jsonify({'success': False, 'error': error_msg})
        
        # 创建课程记录
        new_record = CourseRecord(
            subject=subject,
            teacher=teacher,
            date=record_date,
            start_time=start_time_obj,
            duration=duration,
            content=content,
            homework=homework,
            notes=notes
        )
        
        db_session.add(new_record)
        db_session.flush()  # 获取新记录的ID
        app.logger.info(f'测试成功创建课程记录对象，ID: {new_record.id}')
        
        # 添加学生关联
        if student_ids:
            app.logger.info(f'测试开始添加学生关联，学生数量: {len(student_ids)}')
            for student_id in student_ids:
                attendance = '出席'  # 默认出勤状态
                
                record_student = RecordStudent(
                    record_id=new_record.id,
                    student_id=int(student_id),
                    attendance=attendance,
                    homework_status='',
                    study_status=''
                )
                db_session.add(record_student)
                app.logger.info(f'测试添加学生关联: student_id={student_id}, attendance={attendance}')
        
        # 提交到数据库
        db_session.commit()
        app.logger.info('测试课程记录添加成功，已提交到数据库')
        
        return jsonify({'success': True, 'message': '课程记录添加成功', 'record_id': new_record.id})
        
    except Exception as e:
        db_session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"测试课程记录添加失败: {str(e)}\n{error_trace}")
        return jsonify({'success': False, 'error': str(e), 'traceback': error_trace})
    finally:
        db_session.close()

# 简单的测试登录路由 - 仅用于开发环境快速登录
@app.route('/quick-test-login')
def quick_test_login():
    """简单的测试登录路由 - 仅用于开发环境快速登录"""
    if app.debug:
        db_session = Session()
        try:
            # 创建一个测试用户或使用现有用户
            test_user = db_session.query(User).filter_by(username='test').first()
            if not test_user:
                test_user = User(username='test', name='测试用户', role='admin')
                test_user.password_hash = generate_password_hash('test123')
                db_session.add(test_user)
                db_session.commit()
            
            # 直接登录用户
            login_user(test_user)
            flash('测试登录成功！', 'success')
            # 直接重定向到学生管理页面，测试修复效果
            return redirect(url_for('students'))
        except Exception as e:
            app.logger.error(f'测试登录失败: {str(e)}')
            flash('测试登录失败', 'danger')
            return redirect(url_for('login'))
        finally:
            db_session.close()
    else:
        # 非调试模式下禁用此功能
        abort(404)

# 日志查看路由（用于调试）
@app.route('/view_logs')
@login_required
@admin_required
def view_logs():
    """查看应用程序日志，仅用于调试"""
    import os
    import re
    
    # 定义日志文件路径
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
    
    # 初始化日志内容
    logs = []
    
    try:
        # 读取日志文件内容
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
        
        # 按时间倒序排列（假设日志格式包含时间戳）
        logs.reverse()
        
        # 限制显示的日志行数
        max_lines = 200
        logs = logs[:max_lines]
        
    except Exception as e:
        logs = [f"无法读取日志文件: {str(e)}"]
    
    # 格式化日志内容以便在HTML中显示
    logs_html = '<br>'.join([line.strip().replace('\n', '<br>') for line in logs])
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>查看应用日志</title>
            <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css">
            <style>
                .log-container {
                    max-height: 600px;
                    overflow-y: auto;
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: monospace;
                    white-space: pre-wrap;
                }
                .error-log {
                    color: #dc3545;
                }
                .info-log {
                    color: #198754;
                }
                .log-timestamp {
                    color: #6c757d;
                }
            </style>
        </head>
        <body>
            <div class="container mt-5">
                <h1>应用日志</h1>
                <div class="mb-3">
                    <a href="{{ url_for('view_logs') }}" class="btn btn-primary">刷新日志</a>
                    <a href="{{ url_for('index') }}" class="btn btn-secondary">返回主页</a>
                </div>
                <div class="log-container" id="logs">
                    {{ logs | safe }}
                </div>
            </div>
            <script>
                // 简单的日志分类染色
                document.addEventListener('DOMContentLoaded', function() {
                    const logContainer = document.getElementById('logs');
                    let logText = logContainer.innerHTML;
                    
                    // 对错误日志进行染色
                    logText = logText.replace(/(❌|ERROR|error|失败)/gi, function(match) {
                        return '<span class="error-log">' + match + '</span>';
                    });
                    
                    // 对信息日志进行染色
                    logText = logText.replace(/(✅|INFO|info|成功)/gi, function(match) {
                        return '<span class="info-log">' + match + '</span>';
                    });
                    
                    // 对时间戳进行染色
                    logText = logText.replace(/(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2},\\d{3})/gi, function(match) {
                        return '<span class="log-timestamp">' + match + '</span>';
                    });
                    
                    logContainer.innerHTML = logText;
                });
            </script>
        </body>
        </html>
    ''', logs=logs_html)

# 调试路由 - 表单提交测试
@app.route('/debug_form_submit')
@login_required
def debug_form_submit():
    """调试表单提交功能"""
    with open('debug_form_submit.html', 'r', encoding='utf-8') as f:
        return f.read()

# 调试路由 - 表单测试页面
@app.route('/debug_form_test')
@login_required
def debug_form_test():
    """调试表单测试页面"""
    with open('debug_form_test.html', 'r', encoding='utf-8') as f:
        return f.read()


# ============================================
# 学期管理功能
# ============================================

@app.route('/semesters')
@login_required
def semesters():
    """学期管理列表页面"""
    db_session = Session()
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '')
    
    # 验证分页参数
    page, per_page, search = validate_pagination_params(page, per_page, search)
    
    # 构建查询
    query = db_session.query(SemesterTag)
    if search:
        query = query.filter(
            or_(
                SemesterTag.name.ilike(f'%{search}%'),
                SemesterTag.tag_type.ilike(f'%{search}%')
            )
        )
    
    total = query.count()
    # 手动分页
    offset = (page - 1) * per_page
    semesters_list = query.order_by(SemesterTag.start_date.desc()).offset(offset).limit(per_page).all()
    
    db_session.close()
    
    return render_template('semesters.html',
                        semesters=semesters_list,
                        page=page,
                        per_page=per_page,
                        total=total,
                        search=search)

@app.route('/semesters/add', methods=['GET', 'POST'])
@login_required
def add_semester():
    """添加学期标签"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        tag_type = request.form.get('tag_type', '').strip()
        
        if not name or not start_date_str or not end_date_str or not tag_type:
            flash('请填写所有必填项', 'warning')
            return redirect(url_for('add_semester'))
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'warning')
            return redirect(url_for('add_semester'))
        
        if start_date > end_date:
            flash('开始日期不能晚于结束日期', 'warning')
            return redirect(url_for('add_semester'))
        
        db_session = Session()
        
        new_tag = SemesterTag(
            name=name,
            start_date=start_date,
            end_date=end_date,
            tag_type=tag_type
        )
        
        db_session.add(new_tag)
        db_session.commit()
        db_session.close()
        
        flash('学期标签添加成功', 'success')
        return redirect(url_for('semesters'))
    else:
        return render_template('semester_form.html', tag=None, editing=False)

@app.route('/semesters/edit/<int:tag_id>', methods=['GET', 'POST'])
@login_required
def edit_semester(tag_id):
    """编辑学期标签"""
    db_session = Session()
    tag = db_session.query(SemesterTag).filter(SemesterTag.id == tag_id).first()
    
    if not tag:
        flash('学期标签不存在', 'warning')
        db_session.close()
        return redirect(url_for('semesters'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        tag_type = request.form.get('tag_type', '').strip()
        
        if not name or not start_date_str or not end_date_str or not tag_type:
            flash('请填写所有必填项', 'warning')
            db_session.close()
            return redirect(url_for('edit_semester', tag_id=tag_id))
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'warning')
            db_session.close()
            return redirect(url_for('edit_semester', tag_id=tag_id))
        
        if start_date > end_date:
            flash('开始日期不能晚于结束日期', 'warning')
            db_session.close()
            return redirect(url_for('edit_semester', tag_id=tag_id))
        
        tag.name = name
        tag.start_date = start_date
        tag.end_date = end_date
        tag.tag_type = tag_type
        tag.updated_at = datetime.now().date()
        
        db_session.commit()
        db_session.close()
        
        flash('学期标签修改成功', 'success')
        return redirect(url_for('semesters'))
    else:
        return render_template('semester_form.html', tag=tag, editing=True)

@app.route('/semesters/delete/<int:tag_id>', methods=['POST'])
@login_required
def delete_semester(tag_id):
    """删除学期标签"""
    db_session = Session()
    tag = db_session.query(SemesterTag).filter(SemesterTag.id == tag_id).first()
    
    if not tag:
        flash('学期标签不存在', 'warning')
        db_session.close()
        return jsonify({'success': False, 'message': '学期标签不存在'})
    
    db_session.delete(tag)
    db_session.commit()
    db_session.close()
    
    flash('学期标签删除成功', 'success')
    return jsonify({'success': True})

if __name__ == '__main__':
    # 支持通过环境变量或命令行参数指定端口
    import os
    import sys
    
    # 默认端口
    port = 5001
    
    # 检查命令行参数
    for i, arg in enumerate(sys.argv):
        if arg == '--port' and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                print(f"无效的端口号: {sys.argv[i + 1]}")
                sys.exit(1)
    
    # 检查环境变量
    if 'PORT' in os.environ:
        try:
            port = int(os.environ['PORT'])
        except ValueError:
            print(f"无效的PORT环境变量: {os.environ['PORT']}")
            sys.exit(1)
    
    # 移除可能的环境变量
    os.environ.pop('FLASK_RUN_PORT', None)
    
    print(f"启动应用，端口: {port}")
    app.run(debug=True, port=port, host='0.0.0.0')

import os
import subprocess
import threading
import shutil
import json
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'eh-x7k9m2pLqRvWzYnBfJcDgAsTeUiOp')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elitehosting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DEPLOY_FOLDER'] = 'deploys'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# ===================== CONFIGURATIONS =====================
AUTH_LIMIT_CONFIG = {
    'ip_threshold': int(os.environ.get('AUTH_IP_THRESHOLD', 5)),
    'account_threshold': int(os.environ.get('AUTH_ACCOUNT_THRESHOLD', 3)),
    'backoff_base': float(os.environ.get('AUTH_BACKOFF_BASE', 2.0)),
    'backoff_multiplier': float(os.environ.get('AUTH_BACKOFF_MULTIPLIER', 2.0)),
    'max_backoff': float(os.environ.get('AUTH_MAX_BACKOFF', 900.0)),
    'window_minutes': int(os.environ.get('AUTH_WINDOW_MINUTES', 15))
}

PUBLIC_LIMIT_CONFIG = {
    'limit': int(os.environ.get('PUBLIC_LIMIT', 60)),
    'period': int(os.environ.get('PUBLIC_PERIOD', 60))
}

AUTH_ACTION_LIMIT_CONFIG = {
    'limit': int(os.environ.get('AUTH_ACTION_LIMIT', 120)),
    'period': int(os.environ.get('AUTH_ACTION_PERIOD', 60))
}

db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEPLOY_FOLDER'], exist_ok=True)

# ===================== MODELS =====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    password_plain = db.Column(db.String(256), nullable=True)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    wallet_balance = db.Column(db.Float, default=0.0)
    credits = db.Column(db.Integer, default=0)
    free_deploy_until = db.Column(db.DateTime, nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    plan = db.Column(db.String(20), default='free')
    last_ip = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BannedIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VpsSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_name = db.Column(db.String(50), nullable=False) # e.g. 'Micro 256MB', 'Lite 512MB', 'Pro 1GB'
    ram_mb = db.Column(db.Integer, nullable=False)       # 256, 512, 1024
    status = db.Column(db.String(20), default='idle')    # idle, running
    deployment_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    deploy_type = db.Column(db.String(20), nullable=False)
    repo_url = db.Column(db.String(500), nullable=True)
    branch = db.Column(db.String(50), default='main')
    build_command = db.Column(db.String(1000), nullable=True)
    deploy_command = db.Column(db.String(1000), nullable=True)
    env_vars = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='idle')
    is_free = db.Column(db.Boolean, default=False)
    pid = db.Column(db.Integer, nullable=True)
    logs = db.Column(db.Text, default='')
    deploy_path = db.Column(db.String(500), nullable=True)
    entry_file = db.Column(db.String(200), nullable=True)
    port = db.Column(db.Integer, nullable=True)
    vps_slot_id = db.Column(db.Integer, db.ForeignKey('vps_slot.id'), nullable=True)
    is_website = db.Column(db.Boolean, default=False)
    slug = db.Column(db.String(100), unique=True, nullable=True)
    visitor_count = db.Column(db.Integer, default=0)
    last_started_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    plan_name = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tx_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0)
    is_banned = db.Column(db.Boolean, default=False)

class RateLimit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

import time

def free_trial_monitor_loop():
    """
    Background loop that runs periodically to check and stop expired free deployments.
    Now trials are strictly limited to 15 minutes of execution time.
    """
    while True:
        try:
            with app.app_context():
                now = datetime.utcnow()
                # Query all running free deployments
                free_deps = Deployment.query.filter_by(status='running', is_free=True).all()
                for dep in free_deps:
                    user = User.query.get(dep.user_id)
                    # Check overall trial expiration date (3 hours) or 15 minutes session duration
                    is_expired_session = False
                    if dep.last_started_at and (now - dep.last_started_at) >= timedelta(minutes=15):
                        is_expired_session = True

                    if not user or user.is_banned or (user.free_deploy_until and user.free_deploy_until <= now) or is_expired_session:
                        engine = DeployEngine(dep.id)
                        engine.stop()
                        if is_expired_session:
                            engine._log("Free trial 15-minute runtime session limit reached. Deployment automatically stopped. Please restart manually to run again.")
                        else:
                            engine._log("Free trial period expired. Deployment automatically stopped by system scheduler.")
        except Exception as e:
            print(f"Free trial monitor loop warning: {e}")
        time.sleep(15) # check more frequently for precise 15 min shutoffs

with app.app_context():
    db.create_all()
    # Automated SQLite Schema Migration for password_plain and RateLimit.username
    try:
        connection = db.engine.connect()
        from sqlalchemy import text

        # User migration
        result = connection.execute(text("PRAGMA table_info(user)"))
        columns = [row[1] for row in result.fetchall()]
        if 'password_plain' not in columns:
            connection.execute(text("ALTER TABLE user ADD COLUMN password_plain VARCHAR(256)"))
            connection.commit()
        if 'last_ip' not in columns:
            connection.execute(text("ALTER TABLE user ADD COLUMN last_ip VARCHAR(50)"))
            connection.commit()

        # RateLimit migration
        result2 = connection.execute(text("PRAGMA table_info(rate_limit)"))
        rl_columns = [row[1] for row in result2.fetchall()]
        if 'username' not in rl_columns:
            connection.execute(text("ALTER TABLE rate_limit ADD COLUMN username VARCHAR(100)"))
            connection.commit()

        # Deployment migration for vps_slot_id and website columns
        result3 = connection.execute(text("PRAGMA table_info(deployment)"))
        dep_columns = [row[1] for row in result3.fetchall()]
        if 'vps_slot_id' not in dep_columns:
            connection.execute(text("ALTER TABLE deployment ADD COLUMN vps_slot_id INTEGER"))
            connection.commit()
        if 'is_website' not in dep_columns:
            connection.execute(text("ALTER TABLE deployment ADD COLUMN is_website BOOLEAN DEFAULT 0"))
            connection.commit()
        if 'slug' not in dep_columns:
            connection.execute(text("ALTER TABLE deployment ADD COLUMN slug VARCHAR(100)"))
            connection.commit()
        if 'visitor_count' not in dep_columns:
            connection.execute(text("ALTER TABLE deployment ADD COLUMN visitor_count INTEGER DEFAULT 0"))
            connection.commit()
        if 'last_started_at' not in dep_columns:
            connection.execute(text("ALTER TABLE deployment ADD COLUMN last_started_at DATETIME"))
            connection.commit()

        connection.close()
    except Exception as e:
        print(f"Migration warning: {e}")

    # Start free trial monitor background thread
    import threading
    t_monitor = threading.Thread(target=free_trial_monitor_loop, daemon=True)
    t_monitor.start()

# ===================== HELPERS =====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        user = User.query.get(session['user_id'])
        if not user or user.is_banned:
            session.clear()
            return jsonify({'error': 'Account banned'}), 403
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_logged' not in session:
            return jsonify({'error': 'Admin login required'}), 401
        return f(*args, **kwargs)
    return decorated

def rate_limit(limit_type='public'):
    """
    Configurable dynamic rate limit decorator.
    Can be 'public' (moderate limits) or 'auth_action' (looser limits).
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = get_client_ip()
            endpoint = request.path
            now = datetime.utcnow()

            if limit_type == 'auth_action':
                limit = AUTH_ACTION_LIMIT_CONFIG['limit']
                period = AUTH_ACTION_LIMIT_CONFIG['period']
            else:
                limit = PUBLIC_LIMIT_CONFIG['limit']
                period = PUBLIC_LIMIT_CONFIG['period']

            cutoff = now - timedelta(seconds=period)

            # Clean up old records occasionally
            try:
                RateLimit.query.filter(RateLimit.timestamp < (now - timedelta(hours=1))).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()

            # Count requests in current period
            count = RateLimit.query.filter(
                RateLimit.ip_address == ip,
                RateLimit.endpoint == endpoint,
                RateLimit.timestamp >= cutoff
            ).count()

            if count >= limit:
                if request.path.startswith('/api/'):
                    return jsonify({
                        'error': 'Too many requests. Please try again later.',
                        'retry_after_seconds': period
                    }), 429
                else:
                    return f"<h1>429 Too Many Requests</h1><p>Please try again in {period} seconds.</p>", 429

            # Log current request
            try:
                rl_record = RateLimit(ip_address=ip, endpoint=endpoint, timestamp=now)
                db.session.add(rl_record)
                db.session.commit()
            except Exception:
                db.session.rollback()

            return f(*args, **kwargs)
        return decorated
    return decorator

def auth_rate_limit():
    """
    Stricter rate limiting decorator for authentication endpoints.
    Checks both per-IP and per-account limits with exponential backoff.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = get_client_ip()
            endpoint = request.path
            now = datetime.utcnow()

            # Extract username/email from payload if any
            username = None
            try:
                data = request.get_json(silent=True)
                if data:
                    username = data.get('username', '').strip().lower()
            except Exception:
                pass

            # Configuration
            window_minutes = AUTH_LIMIT_CONFIG['window_minutes']
            cutoff = now - timedelta(minutes=window_minutes)

            # Clean up old records
            try:
                RateLimit.query.filter(RateLimit.timestamp < (now - timedelta(hours=2))).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()

            # Count recent failed attempts for this IP
            c_ip = RateLimit.query.filter(
                RateLimit.ip_address == ip,
                RateLimit.endpoint == endpoint,
                RateLimit.timestamp >= cutoff
            ).count()

            # Count recent failed attempts for this Account (username)
            c_acc = 0
            if username:
                c_acc = RateLimit.query.filter(
                    RateLimit.username == username,
                    RateLimit.endpoint == endpoint,
                    RateLimit.timestamp >= cutoff
                ).count()

            # Calculate backoffs
            backoff_ip = 0.0
            ip_threshold = AUTH_LIMIT_CONFIG['ip_threshold']
            if c_ip >= ip_threshold:
                backoff_ip = AUTH_LIMIT_CONFIG['backoff_base'] * (AUTH_LIMIT_CONFIG['backoff_multiplier'] ** (c_ip - ip_threshold))

            backoff_acc = 0.0
            account_threshold = AUTH_LIMIT_CONFIG['account_threshold']
            if username and c_acc >= account_threshold:
                backoff_acc = AUTH_LIMIT_CONFIG['backoff_base'] * (AUTH_LIMIT_CONFIG['backoff_multiplier'] ** (c_acc - account_threshold))

            backoff = max(backoff_ip, backoff_acc)
            if backoff > AUTH_LIMIT_CONFIG['max_backoff']:
                backoff = AUTH_LIMIT_CONFIG['max_backoff']

            if backoff > 0:
                # Find the most recent failed attempt
                filters = [RateLimit.endpoint == endpoint, RateLimit.timestamp >= cutoff]
                if username:
                    latest_record = RateLimit.query.filter(
                        db.or_(RateLimit.ip_address == ip, RateLimit.username == username),
                        *filters
                    ).order_by(RateLimit.timestamp.desc()).first()
                else:
                    latest_record = RateLimit.query.filter(
                        RateLimit.ip_address == ip,
                        *filters
                    ).order_by(RateLimit.timestamp.desc()).first()

                if latest_record:
                    next_allowed = latest_record.timestamp + timedelta(seconds=backoff)
                    if next_allowed > now:
                        retry_after = int((next_allowed - now).total_seconds())
                        if retry_after > 0:
                            return jsonify({
                                'error': f'Too many failed attempts. Please try again in {retry_after} seconds (exponential backoff).',
                                'retry_after_seconds': retry_after
                            }), 429

            # Log current attempt
            rl_record = None
            try:
                rl_record = RateLimit(ip_address=ip, endpoint=endpoint, username=username, timestamp=now)
                db.session.add(rl_record)
                db.session.commit()
            except Exception:
                db.session.rollback()

            # Execute view function
            response = f(*args, **kwargs)

            # Check response status code
            status_code = 200
            if isinstance(response, tuple) and len(response) > 1:
                status_code = response[1]
            elif hasattr(response, 'status_code'):
                status_code = response.status_code

            # If successful (status < 300), we clear failed attempts for this IP and username
            if status_code < 300:
                try:
                    filters = [RateLimit.endpoint == endpoint]
                    if username:
                        RateLimit.query.filter(
                            db.or_(RateLimit.ip_address == ip, RateLimit.username == username),
                            *filters
                        ).delete()
                    else:
                        RateLimit.query.filter(
                            RateLimit.ip_address == ip,
                            *filters
                        ).delete()
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            return response
        return decorated
    return decorator

def generate_referral_code():
    code = uuid.uuid4().hex[:8].upper()
    while User.query.filter_by(referral_code=code).first():
        code = uuid.uuid4().hex[:8].upper()
    return code

def get_client_ip():
    if request.headers.getlist('X-Forwarded-For'):
        return request.headers.getlist('X-Forwarded-For')[0]
    return request.remote_addr

def validate_payload(schema, data):
    """
    Validates input data dictionary against a strict schema.
    Returns (cleaned_data, error_msg). If valid, error_msg is None.
    """
    if not isinstance(data, dict):
        return None, "Request payload must be a JSON object"

    cleaned = {}
    for field, rules in schema.items():
        val = data.get(field)

        # Check required
        if rules.get('required') and val is None:
            return None, f"Field '{field}' is required"

        if val is not None:
            # Check type
            expected_type = rules.get('type')
            if expected_type:
                if expected_type == float and isinstance(val, int):
                    val = float(val)
                elif not isinstance(val, expected_type):
                    return None, f"Field '{field}' must be of type {expected_type.__name__}"

            # If string, strip it
            if isinstance(val, str):
                val = val.strip()

            # Check min length/value
            if 'min' in rules:
                limit = rules['min']
                if isinstance(val, str) or isinstance(val, list) or isinstance(val, dict):
                    if len(val) < limit:
                        return None, f"Field '{field}' must be at least {limit} characters/items long"
                elif isinstance(val, (int, float)):
                    if val < limit:
                        return None, f"Field '{field}' must be at least {limit}"

            # Check max length/value
            if 'max' in rules:
                limit = rules['max']
                if isinstance(val, str) or isinstance(val, list) or isinstance(val, dict):
                    if len(val) > limit:
                        return None, f"Field '{field}' must be at most {limit} characters/items long"
                elif isinstance(val, (int, float)):
                    if val > limit:
                        return None, f"Field '{field}' must be at most {limit}"

            # Check regex format
            if 'regex' in rules and isinstance(val, str):
                import re
                if not re.match(rules['regex'], val):
                    return None, f"Field '{field}' has an invalid format"

            # Check choices
            if 'choices' in rules:
                if val not in rules['choices']:
                    return None, f"Field '{field}' must be one of {rules['choices']}"

            # Check JSON content
            if rules.get('is_json') and isinstance(val, str):
                try:
                    json.loads(val)
                except Exception:
                    return None, f"Field '{field}' must be valid JSON content"

            cleaned[field] = val
        else:
            # Set default if provided
            if 'default' in rules:
                cleaned[field] = rules['default']

    return cleaned, None

def is_safe_upload_content(file_stream, filename):
    """
    Validates file content by inspecting magic bytes.
    Returns (is_safe, error_msg).
    """
    try:
        # Read the first 4 bytes
        file_stream.seek(0)
        header = file_stream.read(4)
        file_stream.seek(0) # reset pointer

        # Check executable formats (PE/ELF/Java Class)
        if header.startswith(b'MZ') or header.startswith(b'\x7fELF') or header.startswith(b'\xca\xfe\xba\xbe'):
            return False, "Executable binaries are strictly prohibited."

        # If file claims to be a ZIP or has .zip extension
        if filename.lower().endswith('.zip'):
            if not header.startswith(b'PK\x03\x04'):
                return False, "Invalid ZIP archive content (magic bytes mismatch)."

        return True, None
    except Exception as e:
        return False, f"Content verification failed: {str(e)}"

# ===================== DEPLOY ENGINE =====================

class DeployEngine:
    def __init__(self, deployment_id):
        self.deployment = Deployment.query.get(deployment_id)
        self.deploy_path = os.path.join(app.config['DEPLOY_FOLDER'], f'deploy_{deployment_id}')
        self.log_file = os.path.join(self.deploy_path, 'process.log')

    def _log(self, msg):
        clean_msg = str(msg)
        try:
            deploy_dir = os.path.abspath(app.config['DEPLOY_FOLDER'])
            upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
            clean_msg = clean_msg.replace(deploy_dir, '[DEPLOY_DIR]')
            clean_msg = clean_msg.replace(upload_dir, '[UPLOAD_DIR]')
        except Exception:
            pass

        ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        if not self.deployment.logs:
            self.deployment.logs = ""
        self.deployment.logs += f"[{ts}] {clean_msg}\n"
        db.session.commit()

    def github_deploy(self, token=None):
        repo = self.deployment.repo_url
        branch = self.deployment.branch or 'main'
        self._log(f"Cloning {repo} (branch: {branch})")

        clone_url = repo
        if token:
            if 'github.com' in repo:
                clone_url = repo.replace('https://github.com/', f'https://{token}@github.com/')
                self._log("Using authentication token for private repository")

        if os.path.exists(self.deploy_path):
            shutil.rmtree(self.deploy_path)
        os.makedirs(self.deploy_path, exist_ok=True)

        try:
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', '-b', branch, clone_url, self.deploy_path],
                capture_output=True, text=True, timeout=120
            )
            if result.stdout:
                self._log(result.stdout.strip())
            if result.stderr and 'Cloning into' not in result.stderr:
                self._log(f"GIT STDERR: {result.stderr.strip()}")
            if result.returncode != 0:
                self._log(f"Clone failed (exit {result.returncode})")
                self.deployment.status = 'error'
                db.session.commit()
                return False
        except subprocess.TimeoutExpired:
            self._log("Clone timed out (120s)")
            self.deployment.status = 'error'
            db.session.commit()
            return False
        except Exception as e:
            self._log(f"Clone exception: {str(e)}")
            self.deployment.status = 'error'
            db.session.commit()
            return False

        self.deployment.deploy_path = self.deploy_path
        db.session.commit()
        return self._run_deploy()

    def zip_deploy(self, zip_path):
        if os.path.exists(self.deploy_path):
            shutil.rmtree(self.deploy_path)
        os.makedirs(self.deploy_path, exist_ok=True)

        import zipfile
        if zipfile.is_zipfile(zip_path):
            self._log("Extracting ZIP archive safely (Zip Slip protection)...")
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for member in zip_ref.infolist():
                        member_name = member.filename
                        # Rejection of traversal characters
                        if member_name.startswith('/') or '..' in member_name or '../' in member_name:
                            raise Exception(f"Directory traversal attempt detected in ZIP: {member_name}")

                        target_path = os.path.abspath(os.path.join(self.deploy_path, member_name))
                        abs_deploy_dir = os.path.abspath(self.deploy_path)
                        if not target_path.startswith(abs_deploy_dir + os.sep) and target_path != abs_deploy_dir:
                            raise Exception(f"Directory traversal attempt detected in ZIP: {member_name}")

                    zip_ref.extractall(self.deploy_path)
            except Exception as e:
                self._log(f"ZIP extract failed: {str(e)}")
                self.deployment.status = 'error'
                db.session.commit()
                return False
        else:
            self._log("Normal file detected, copying...")
            # If it's not a zip, it's a single file (like .py)
            filename = os.path.basename(zip_path)
            # Remove the uuid prefix if it was added during upload
            # format was {uuid.uuid4().hex}_{filename}
            if '_' in filename and len(filename.split('_')[0]) == 32:
                original_name = filename.split('_', 1)[1]
            else:
                original_name = filename

            dest = os.path.join(self.deploy_path, original_name)
            shutil.copy2(zip_path, dest)
            self._log(f"File {original_name} placed in deploy directory")

        self.deployment.deploy_path = self.deploy_path
        db.session.commit()
        return self._run_deploy()

    def _setup_env(self):
        env = os.environ.copy()
        if self.deployment.env_vars:
            try:
                parsed = json.loads(self.deployment.env_vars)
                if isinstance(parsed, list):
                    # Naye style ke env vars: [{"id": "TOKEN", "key": "123"}]
                    env_data = {}
                    for item in parsed:
                        if isinstance(item, dict) and 'id' in item and 'key' in item:
                            k, v = str(item['id']), str(item['key'])
                            env[k] = v
                            env_data[k] = v
                    if env_data:
                        env_content = '\n'.join(f'{k}={v}' for k, v in env_data.items())
                        env_path = os.path.join(self.deploy_path, '.env')
                        with open(env_path, 'w') as f:
                            f.write(env_content)
                        self._log(f"Environment variables set: {len(env_data)} vars")
                elif isinstance(parsed, dict):
                    # Purana style: {"TOKEN": "123"}
                    for k, v in parsed.items():
                        env[str(k)] = str(v)
                    env_content = '\n'.join(f'{k}={v}' for k, v in parsed.items())
                    env_path = os.path.join(self.deploy_path, '.env')
                    with open(env_path, 'w') as f:
                        f.write(env_content)
                    self._log(f"Environment variables set: {len(parsed)} vars")
            except json.JSONDecodeError:
                self._log("Warning: Could not parse env vars JSON")
        return env

    def _run_deploy(self):
        if self.deployment.is_website:
            self._log("Static website deployment detected. Skipping Docker execution. Active at /site/" + (self.deployment.slug or ""))
            self.deployment.status = 'running'
            self.deployment.last_started_at = datetime.utcnow()
            db.session.commit()
            return True

        env = self._setup_env()
        files = []
        for root, dirs, filenames in os.walk(self.deploy_path):
            for fn in filenames:
                rel = os.path.relpath(os.path.join(root, fn), self.deploy_path)
                files.append(rel)
        self._log(f"Found {len(files)} files in project")

        # Single file detection
        py_files = [f for f in files if f.endswith('.py') and '/' not in f]
        has_requirements = any(f == 'requirements.txt' for f in files)

        if len(py_files) == 1 and not has_requirements and not self.deployment.build_command:
            entry = py_files[0]
            self.deployment.entry_file = entry
            self._log(f"Single file detected: {entry}")
            cmd = f'python3 {entry}'
            return self._execute(cmd, env)

        # Build command
        if self.deployment.build_command:
            self._log(f"Running build: {self.deployment.build_command}")
            self.deployment.status = 'building'
            db.session.commit()
            try:
                r = subprocess.run(
                    self.deployment.build_command, shell=True,
                    cwd=self.deploy_path, capture_output=True,
                    text=True, timeout=300, env=env
                )
                if r.stdout:
                    self._log(r.stdout.strip())
                if r.stderr:
                    self._log(f"BUILD STDERR: {r.stderr.strip()}")
                if r.returncode != 0:
                    self._log(f"Build failed (exit {r.returncode})")
                    self.deployment.status = 'error'
                    db.session.commit()
                    return False
                self._log("Build succeeded")
            except subprocess.TimeoutExpired:
                self._log("Build timed out (300s)")
                self.deployment.status = 'error'
                db.session.commit()
                return False
            except Exception as e:
                self._log(f"Build exception: {str(e)}")
                self.deployment.status = 'error'
                db.session.commit()
                return False

        # Deploy command ya auto-detect
        if self.deployment.deploy_command:
            cmd = self.deployment.deploy_command
        else:
            cmd = self._auto_detect(files, has_requirements)
            if not cmd:
                self._log("Cannot auto-detect entry point. Provide a deploy command.")
                self.deployment.status = 'error'
                db.session.commit()
                return False

        self._log(f"Deploy command: {cmd}")
        return self._execute(cmd, env)

    def _auto_detect(self, files, has_req):
        checks = [
            ('main.py', 'pip install -r requirements.txt 2>/dev/null; python3 main.py'),
            ('app.py', 'pip install -r requirements.txt 2>/dev/null; python3 app.py'),
            ('server.py', 'pip install -r requirements.txt 2>/dev/null; python3 server.py'),
            ('index.js', 'npm install 2>/dev/null; node index.js'),
            ('server.js', 'npm install 2>/dev/null; node server.js'),
            ('app.js', 'npm install 2>/dev/null; node app.js'),
        ]
        for fname, cmd in checks:
            if fname in files:
                self.deployment.entry_file = fname
                self._log(f"Auto-detected: {fname}")
                if not has_req and fname.endswith('.py'):
                    cmd = f'python3 {fname}'
                if not has_req and fname.endswith('.js'):
                    cmd = f'node {fname}'
                return cmd

        # Koi bhi .py file
        py_files = [f for f in files if f.endswith('.py') and '/' not in f]
        if py_files:
            entry = py_files[0]
            self.deployment.entry_file = entry
            self._log(f"Fallback to: {entry}")
            if has_req:
                return f'pip install -r requirements.txt 2>/dev/null; python3 {entry}'
            return f'python3 {entry}'

        return None

    def _execute(self, cmd, env):
        # Prevent double execution
        db.session.refresh(self.deployment)
        if self.deployment.status == 'running':
            self._log("Deployment is already running. Aborting duplicate.")
            return True

        self.deployment.status = 'running'
        self.deployment.last_started_at = datetime.utcnow()
        db.session.commit()
        self._log(f"Preparing secure Docker execution...")

        # Get allocated VPS slot RAM limit
        ram_limit = "256m"
        vps_slot = None
        if self.deployment.vps_slot_id:
            vps_slot = VpsSlot.query.get(self.deployment.vps_slot_id)
            if vps_slot:
                ram_limit = f"{vps_slot.ram_mb}m"
                vps_slot.status = 'running'
                db.session.commit()

        # Port assign
        port = 5000 + self.deployment.id
        self.deployment.port = port
        db.session.commit()

        container_name = f"eh_container_{self.deployment.id}"

        # Clean existing container if any
        try:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        except Exception:
            pass

        # Autodetect runtime language based on file structure
        is_node = False
        if os.path.exists(os.path.join(self.deploy_path, 'package.json')) or any(f.endswith('.js') for f in os.listdir(self.deploy_path) if os.path.isfile(os.path.join(self.deploy_path, f))):
            is_node = True

        # Generate custom secure Dockerfile to build deployment image safely
        dockerfile_path = os.path.join(self.deploy_path, "Dockerfile")

        # Determine build and deploy commands
        build_step = ""
        if self.deployment.build_command:
            build_step = f"RUN {self.deployment.build_command}"
        elif is_node:
            if os.path.exists(os.path.join(self.deploy_path, 'package.json')):
                build_step = "RUN npm install --only=production"
        else:
            if os.path.exists(os.path.join(self.deploy_path, 'requirements.txt')):
                build_step = "RUN pip install --no-cache-dir -r requirements.txt"

        # Safe custom script entryfile trigger
        run_cmd = cmd
        if not self.deployment.deploy_command:
            # If no manual run command was supplied, use auto-detected
            run_cmd = cmd

        if is_node:
            base_image = "node:18-alpine"
            default_user = "node"
            work_dir = "/home/node/app"
            copy_prefix = f"COPY --chown={default_user}:{default_user} . ."
            setup_user_cmd = ""
        else:
            base_image = "python:3.10-alpine"
            default_user = "appuser"
            work_dir = "/app"
            copy_prefix = "COPY --chown=appuser:appuser . ."
            setup_user_cmd = "RUN addgroup -S appgroup && adduser -S appuser -G appgroup"

        dockerfile_content = f"""FROM {base_image}
{setup_user_cmd}
WORKDIR {work_dir}
{copy_prefix}
{build_step}
EXPOSE {port}
USER {default_user}
ENV PORT={port}
CMD {run_cmd}
"""
        with open(dockerfile_path, "w") as df:
            df.write(dockerfile_content)

        self._log("Building container image...")
        try:
            build_args = ["docker", "build", "-t", f"eh_image_{self.deployment.id}", self.deploy_path]
            build_proc = subprocess.run(build_args, capture_output=True, text=True, timeout=300)
            if build_proc.returncode != 0:
                self._log(f"Docker Build Error:\n{build_proc.stderr}")
                self.deployment.status = 'error'
                if vps_slot:
                    vps_slot.status = 'idle'
                db.session.commit()
                return False
            self._log("Docker image built successfully.")
        except Exception as e:
            self._log(f"Docker Build exception: {str(e)}")
            self.deployment.status = 'error'
            if vps_slot:
                vps_slot.status = 'idle'
            db.session.commit()
            return False

        # Docker run flags: --memory to limit RAM, --cpus to prevent CPU exhaustion, --read-only where possible or highly secure boundaries
        # Port mapping and passing env variables safely via docker flags
        docker_run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "--memory", ram_limit,
            "--cpus", "0.5",
            "-p", f"{port}:{port}"
        ]

        # Inject environment variables securely as separate run flags instead of writing to disk
        if self.deployment.env_vars:
            try:
                parsed = json.loads(self.deployment.env_vars)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and 'id' in item and 'key' in item:
                            docker_run_cmd += ["-e", f"{item['id']}={item['key']}"]
                elif isinstance(parsed, dict):
                    for k, v in parsed.items():
                        docker_run_cmd += ["-e", f"{k}={v}"]
            except Exception:
                pass

        # Add image name
        docker_run_cmd.append(f"eh_image_{self.deployment.id}")

        self._log(f"Spinning up container with RAM limit: {ram_limit}...")
        try:
            run_proc = subprocess.run(docker_run_cmd, capture_output=True, text=True, timeout=60)
            if run_proc.returncode != 0:
                self._log(f"Docker Run Error:\n{run_proc.stderr}")
                self.deployment.status = 'error'
                if vps_slot:
                    vps_slot.status = 'idle'
                db.session.commit()
                return False

            # Save container ID or PID dummy values to persist status tracking
            self.deployment.pid = 999999 # dummy pid for legacy logic
            db.session.commit()
            self._log(f"Docker container started successfully! Running on VPS slot mapping port: {port}")
        except Exception as e:
            self._log(f"Docker Run exception: {str(e)}")
            self.deployment.status = 'error'
            if vps_slot:
                vps_slot.status = 'idle'
            db.session.commit()
            return False

        # Start background monitor thread for Docker logs and container status
        def monitor_container():
            import time
            while True:
                time.sleep(3)
                with app.app_context():
                    d = Deployment.query.get(self.deployment.id)
                    if not d or d.status != 'running':
                        break

                    # Check if container is still running
                    inspect_proc = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_name], capture_output=True, text=True)
                    if inspect_proc.returncode != 0 or inspect_proc.stdout.strip() != "true":
                        d.status = 'stopped'
                        d.pid = None
                        vs = VpsSlot.query.get(d.vps_slot_id) if d.vps_slot_id else None
                        if vs:
                            vs.status = 'idle'
                        db.session.commit()
                        self._log(f"Docker container stopped or exited.")
                        break

        t = threading.Thread(target=monitor_container, daemon=True)
        t.start()
        return True

    def stop(self):
        if self.deployment.is_website:
            self._log("Stopping static website deployment...")
            vps_slot = None
            if self.deployment.vps_slot_id:
                vps_slot = VpsSlot.query.get(self.deployment.vps_slot_id)
                if vps_slot:
                    vps_slot.status = 'idle'
            self.deployment.status = 'stopped'
            db.session.commit()
            self._log("Static website deployment stopped successfully.")
            return

        container_name = f"eh_container_{self.deployment.id}"
        self._log("Stopping container secure environment...")
        try:
            subprocess.run(["docker", "stop", container_name], capture_output=True)
            subprocess.run(["docker", "rm", container_name], capture_output=True)
        except Exception:
            pass

        vps_slot = None
        if self.deployment.vps_slot_id:
            vps_slot = VpsSlot.query.get(self.deployment.vps_slot_id)
            if vps_slot:
                vps_slot.status = 'idle'

        self.deployment.pid = None
        self.deployment.status = 'stopped'
        db.session.commit()
        self._log("Docker container stopped successfully.")

    def get_logs(self):
        container_name = f"eh_container_{self.deployment.id}"
        logs = self.deployment.logs or ''
        try:
            proc = subprocess.run(["docker", "logs", "--tail", "200", container_name], capture_output=True, text=True)
            if proc.returncode == 0 and proc.stdout:
                logs += '\n--- Container Live Output ---\n' + proc.stdout
        except Exception:
            pass
        return logs

    def start(self):
        self.stop()
        return self._run_deploy()

    def get_logs(self):
        logs = self.deployment.logs or ''
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', errors='replace') as f:
                    logs += '\n--- Live Output ---\n' + f.read()[-5000:]
            except:
                pass
        return logs

    def delete(self):
        self.stop()
        if os.path.exists(self.deploy_path):
            shutil.rmtree(self.deploy_path)

        # Release the VpsSlot back to idle if allocated
        if self.deployment.vps_slot_id:
            vs = VpsSlot.query.get(self.deployment.vps_slot_id)
            if vs:
                vs.deployment_id = None
                vs.status = 'idle'

        db.session.delete(self.deployment)
        db.session.commit()


def run_deploy_background(dep_id, dep_type, **kwargs):
    with app.app_context():
        engine = DeployEngine(dep_id)
        if dep_type == 'github':
            engine.github_deploy(kwargs.get('token'))
        elif dep_type == 'zip':
            engine.zip_deploy(kwargs.get('zip_path'))

# ===================== ROUTES — PAGES =====================

@app.route('/')
@rate_limit('public')
def index():
    return render_template('index.html')

@app.route('/login')
@rate_limit('public')
def login_page():
    return render_template('auth.html', mode='login')

@app.route('/register')
@rate_limit('public')
def register_page():
    ref = request.args.get('ref', '')
    return render_template('auth.html', mode='register', ref=ref)

@app.route('/dashboard')
@rate_limit('public')
def dashboard_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

@app.route('/raj')
@rate_limit('public')
def admin_page():
    return render_template('admin.html')

@app.route('/blogs')
@rate_limit('public')
def blogs_page():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    seo = {
        'title': 'Developer Blogs & Tech Insights | EliteHosting',
        'description': 'Read the latest technical write-ups, cloud tutorials, and developer updates from the EliteHosting Team.',
        'canonical': 'https://elitehosting.in/blogs'
    }
    return render_template('index.html', page='blogs', blogs=posts, seo=seo)

@app.route('/blogs/<string:slug>')
@rate_limit('public')
def blog_detail_page(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    seo = {
        'title': f'{post.title} | EliteHosting Developer Blog',
        'description': post.excerpt or post.content[:150],
        'canonical': f'https://elitehosting.in/blogs/{post.slug}'
    }
    return render_template('index.html', page='blog_detail', blog=post, seo=seo)

@app.route('/terms')
@rate_limit('public')
def terms_page():
    seo = {
        'title': 'Terms of Service | EliteHosting',
        'description': 'Terms of Service, deployment policies, and user agreements for the EliteHosting deployment platform.',
        'canonical': 'https://elitehosting.in/terms'
    }
    return render_template('index.html', page='terms', seo=seo)

@app.route('/privacy')
@rate_limit('public')
def privacy_page():
    seo = {
        'title': 'Privacy Policy | EliteHosting',
        'description': 'Privacy policy, cookies policies, and personal data isolation safeguards at EliteHosting.',
        'canonical': 'https://elitehosting.in/privacy'
    }
    return render_template('index.html', page='privacy', seo=seo)

@app.route('/telegram-bot-hosting')
@rate_limit('public')
def telegram_bot_hosting_page():
    return render_template('telegram-bot-hosting.html')

@app.route('/site/<string:slug>')
@app.route('/site/<string:slug>/')
@app.route('/site/<string:slug>/<path:filename>')
def serve_website(slug, filename=None):
    dep = Deployment.query.filter_by(slug=slug, is_website=True).first_or_404()
    if dep.status != 'running':
        return "<h1>404 Not Found</h1><p>This website deployment is currently stopped or not active.</p>", 404

    # Increment visitor count securely
    dep.visitor_count += 1
    db.session.commit()

    deploy_path = os.path.join(app.config['DEPLOY_FOLDER'], f'deploy_{dep.id}')
    if not os.path.exists(deploy_path):
        return "<h1>500 Internal Error</h1><p>Website deployment directory was not found on the server.</p>", 500

    # Default entry file to serve is index.html
    if not filename:
        filename = 'index.html'

    # If filename is a directory, serve index.html inside it
    target_filepath = os.path.join(deploy_path, filename)
    if os.path.isdir(target_filepath):
        filename = os.path.join(filename, 'index.html')

    # Security check to prevent path traversal
    abs_deploy_dir = os.path.abspath(deploy_path)
    abs_target_path = os.path.abspath(os.path.join(deploy_path, filename))
    if not abs_target_path.startswith(abs_deploy_dir):
        return "<h1>403 Forbidden</h1><p>Directory traversal is strictly prohibited.</p>", 403

    if not os.path.exists(abs_target_path):
        # Fall back to root index.html or raise 404
        if os.path.exists(os.path.join(deploy_path, 'index.html')):
            return send_from_directory(deploy_path, 'index.html')
        return "<h1>404 Not Found</h1><p>The requested asset was not found on this website.</p>", 404

    directory, name = os.path.split(abs_target_path)
    return send_from_directory(directory, name)

@app.route('/robots.txt')
@rate_limit('public')
def robots_txt():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/llm.txt')
@rate_limit('public')
def llm_txt():
    return send_from_directory(app.static_folder, 'llm.txt')

@app.route('/sitemap.xml')
@rate_limit('public')
def sitemap_xml():
    pages = []
    # Static pages
    now = datetime.now().strftime("%Y-%m-%d")
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:
            if not str(rule.rule).startswith(('/api', '/raj', '/dashboard')):
                pages.append(["https://elitehosting.in" + str(rule.rule), now])

    # Dynamic blog posts
    posts = BlogPost.query.all()
    for post in posts:
        pages.append(["https://elitehosting.in/blogs/" + post.slug, post.created_at.strftime("%Y-%m-%d")])

    sitemap_template = render_template('sitemap.xml', pages=pages)
    response = app.make_response(sitemap_template)
    response.headers["Content-Type"] = "application/xml"
    return response

# ===================== ROUTES — AUTH API =====================

import re

def is_valid_email(email):
    # Simple regex verification for email format
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def is_valid_username(username):
    # Only alphanumeric characters and underscores are allowed
    pattern = r'^\w+$'
    return bool(re.match(pattern, username))

@app.route('/api/auth/register', methods=['POST'])
@auth_rate_limit()
def api_register():
    data = request.get_json(silent=True) or {}
    schema = {
        'username': {'type': str, 'required': True, 'min': 3, 'max': 30, 'regex': r'^\w+$'},
        'email': {'type': str, 'required': True, 'max': 120, 'regex': r'^[\w\.-]+@[\w\.-]+\.\w+$'},
        'password': {'type': str, 'required': True, 'min': 6, 'max': 100},
        'referral': {'type': str, 'required': False, 'max': 20}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    username = cleaned.get('username').lower()
    email = cleaned.get('email').lower()
    password = cleaned.get('password')
    referral = cleaned.get('referral', '').upper() if cleaned.get('referral') else ''

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username taken'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    referrer = None
    if referral:
        referrer = User.query.filter_by(referral_code=referral).first()
        if not referrer:
            return jsonify({'error': 'Invalid referral code'}), 400

    ip = get_client_ip()
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        password_plain=password,
        referral_code=generate_referral_code(),
        referred_by=referrer.id if referrer else None,
        free_deploy_until=datetime.utcnow() + timedelta(hours=3),
        last_ip=ip
    )
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({
        'message': 'Registered successfully',
        'user': {'id': user.id, 'username': user.username, 'referral_code': user.referral_code}
    }), 201

@app.route('/api/auth/login', methods=['POST'])
@auth_rate_limit()
def api_login():
    data = request.get_json(silent=True) or {}
    schema = {
        'username': {'type': str, 'required': True, 'min': 3, 'max': 120},
        'password': {'type': str, 'required': True, 'min': 6, 'max': 100}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    username = cleaned.get('username').lower()
    password = cleaned.get('password')

    user = User.query.filter((User.username == username) | (User.email == username)).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if user.is_banned:
        return jsonify({'error': 'Account is banned'}), 403

    ip = get_client_ip()
    user.last_ip = ip
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({
        'message': 'Login successful',
        'user': {'id': user.id, 'username': user.username, 'plan': user.plan, 'wallet': user.wallet_balance, 'referral_code': user.referral_code}
    })

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_me():
    user = User.query.get(session['user_id'])
    return jsonify({
        'id': user.id, 'username': user.username, 'email': user.email,
        'plan': user.plan, 'wallet': user.wallet_balance,
        'referral_code': user.referral_code, 'created_at': user.created_at.isoformat()
    })

# ===================== ROUTES — DASHBOARD API =====================

@app.route('/api/dashboard/stats', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_stats():
    uid = session['user_id']
    deps = Deployment.query.filter_by(user_id=uid).all()
    running = sum(1 for d in deps if d.status == 'running')
    user = User.query.get(uid)

    # Calculate VPS slots summary
    slots = VpsSlot.query.filter_by(user_id=uid).all()
    slots_summary = []
    for s in slots:
        slots_summary.append({
            'id': s.id,
            'plan_name': s.plan_name,
            'ram_mb': s.ram_mb,
            'status': s.status,
            'deployment_id': s.deployment_id
        })

    # Return slots_summary and count as credits to prevent frontend UI formatting crashes
    return jsonify({
        'total_deployments': len(deps),
        'running': running,
        'stopped': len(deps) - running,
        'wallet': user.wallet_balance,
        'credits': len(slots_summary), # map total slots to credits field
        'vps_slots': slots_summary,
        'plan': user.plan,
        'free_deploy_until': user.free_deploy_until.isoformat() if user.free_deploy_until else None
    })

# ===================== ROUTES — DEPLOY API =====================

@app.route('/api/deployments', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_list_deployments():
    deps = Deployment.query.filter_by(user_id=session['user_id']).order_by(Deployment.created_at.desc()).all()
    return jsonify([{
        'id': d.id, 'name': d.name, 'type': d.deploy_type,
        'repo_url': d.repo_url, 'status': d.status, 'port': d.port,
        'entry_file': d.entry_file, 'is_website': d.is_website,
        'slug': d.slug, 'visitor_count': d.visitor_count,
        'created_at': d.created_at.isoformat()
    } for d in deps])

@app.route('/api/deploy/github', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_deploy_github():
    user = User.query.get(session['user_id'])
    data = request.get_json(silent=True) or {}
    schema = {
        'name': {'type': str, 'required': True, 'min': 3, 'max': 100},
        'repo_url': {'type': str, 'required': True, 'min': 10, 'max': 500, 'regex': r'^https?://.+'},
        'branch': {'type': str, 'required': False, 'max': 50, 'default': 'main'},
        'build_command': {'type': str, 'required': False, 'max': 1000},
        'deploy_command': {'type': str, 'required': False, 'max': 1000},
        'github_token': {'type': str, 'required': False, 'max': 200},
        'env_vars': {'type': str, 'required': False, 'max': 5000, 'is_json': True},
        'vps_slot_id': {'type': int, 'required': False}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    name = cleaned.get('name')
    repo_url = cleaned.get('repo_url')
    branch = cleaned.get('branch', 'main')
    build_cmd = cleaned.get('build_command') or None
    deploy_cmd = cleaned.get('deploy_command') or None
    token = cleaned.get('github_token') or None
    env_vars = cleaned.get('env_vars') or None
    slot_id = cleaned.get('vps_slot_id')

    # Assign a free slot if under free trial OR look for a purchased slot
    is_free = False
    vps_slot = None
    is_website = (request.form.get('is_website') == 'true')

    if user.free_deploy_until and user.free_deploy_until > datetime.utcnow():
        is_free = True
        # Check if they already have an active trial deployment
        free_deps = Deployment.query.filter_by(user_id=user.id, is_free=True).count()
        if free_deps >= 1:
            return jsonify({'error': 'Free deployment limit reached (1 trial slot max). Buy premium to deploy more.'}), 402

        # Ensure they have a trial slot allocated in DB
        vps_slot = VpsSlot.query.filter_by(user_id=user.id, plan_name='Trial 256MB').first()
        if not vps_slot:
            vps_slot = VpsSlot(user_id=user.id, plan_name='Trial 256MB', ram_mb=256, status='idle')
            db.session.add(vps_slot)
            db.session.commit()
    else:
        # Require purchased VPS slot selection
        if slot_id:
            vps_slot = VpsSlot.query.filter_by(id=slot_id, user_id=user.id).first()
        else:
            # Fall back to finding an idle slot
            vps_slot = VpsSlot.query.filter_by(user_id=user.id, status='idle').first()

        if not vps_slot:
            return jsonify({'error': 'No available VPS slots! Please purchase a VPS slot first.'}), 402

    dep = Deployment(
        user_id=user.id, name=name, deploy_type='github',
        repo_url=repo_url, branch=branch,
        build_command=build_cmd, deploy_command=deploy_cmd,
        env_vars=env_vars, is_free=is_free,
        vps_slot_id=vps_slot.id if vps_slot else None
    )
    db.session.add(dep)
    db.session.commit()

    if vps_slot:
        vps_slot.deployment_id = dep.id
        vps_slot.status = 'running'
        db.session.commit()

    t = threading.Thread(target=run_deploy_background, args=(dep.id, 'github'), kwargs={'token': token}, daemon=True)
    t.start()

    total_slots_count = VpsSlot.query.filter_by(user_id=user.id).count()
    return jsonify({'message': 'Deployment started', 'id': dep.id, 'credits': total_slots_count}), 201

@app.route('/api/deploy/zip', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_deploy_zip():
    user = User.query.get(session['user_id'])
    is_website = (request.form.get('is_website') == 'true')

    form_data = {
        'name': request.form.get('name'),
        'build_command': request.form.get('build_command'),
        'deploy_command': request.form.get('deploy_command'),
        'env_vars': request.form.get('env_vars')
    }
    schema = {
        'name': {'type': str, 'required': True, 'min': 3, 'max': 100},
        'build_command': {'type': str, 'required': False, 'max': 1000},
        'deploy_command': {'type': str, 'required': False, 'max': 1000},
        'env_vars': {'type': str, 'required': False, 'max': 5000, 'is_json': True}
    }
    cleaned, err = validate_payload(schema, form_data)
    if err:
        return jsonify({'error': err}), 400

    name = cleaned.get('name')
    build_cmd = cleaned.get('build_command') or None
    deploy_cmd = cleaned.get('deploy_command') or None
    env_vars = cleaned.get('env_vars') or None
    slot_id = request.form.get('vps_slot_id')
    if slot_id:
        try:
            slot_id = int(slot_id)
        except ValueError:
            slot_id = None

    zip_file = request.files.get('zip_file')
    if not zip_file:
        return jsonify({'error': 'ZIP/Script file required'}), 400

    # Content verification & magic bytes check
    is_safe, content_err = is_safe_upload_content(zip_file, zip_file.filename)
    if not is_safe:
        return jsonify({'error': content_err}), 400

    # Assign a free slot if under free trial OR look for a purchased slot
    is_free = False
    vps_slot = None

    if user.free_deploy_until and user.free_deploy_until > datetime.utcnow():
        is_free = True
        # Check if they already have an active trial deployment
        free_deps = Deployment.query.filter_by(user_id=user.id, is_free=True).count()
        if free_deps >= 1:
            return jsonify({'error': 'Free deployment limit reached (1 trial slot max). Buy premium to deploy more.'}), 402

        # Ensure they have a trial slot allocated in DB
        vps_slot = VpsSlot.query.filter_by(user_id=user.id, plan_name='Trial 256MB').first()
        if not vps_slot:
            vps_slot = VpsSlot(user_id=user.id, plan_name='Trial 256MB', ram_mb=256, status='idle')
            db.session.add(vps_slot)
            db.session.commit()
    else:
        # Require purchased VPS slot selection
        if slot_id:
            vps_slot = VpsSlot.query.filter_by(id=slot_id, user_id=user.id).first()
        else:
            # Fall back to finding an idle slot
            vps_slot = VpsSlot.query.filter_by(user_id=user.id, status='idle').first()

        if not vps_slot:
            return jsonify({'error': 'No available VPS slots! Please purchase a VPS slot first.'}), 402

    filename = secure_filename(zip_file.filename)
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4().hex}_{filename}')
    zip_file.save(zip_path)

    # Generate unique website slug if it is a website
    slug_val = None
    if is_website:
        slug_val = uuid.uuid4().hex[:8]

    dep = Deployment(
        user_id=user.id, name=name, deploy_type='zip',
        build_command=build_cmd, deploy_command=deploy_cmd, env_vars=env_vars,
        is_free=is_free,
        vps_slot_id=vps_slot.id if vps_slot else None,
        is_website=is_website,
        slug=slug_val,
        last_started_at=datetime.utcnow()
    )
    db.session.add(dep)
    db.session.commit()

    if vps_slot:
        vps_slot.deployment_id = dep.id
        vps_slot.status = 'running'
        db.session.commit()

    t = threading.Thread(target=run_deploy_background, args=(dep.id, 'zip'), kwargs={'zip_path': zip_path}, daemon=True)
    t.start()

    total_slots_count = VpsSlot.query.filter_by(user_id=user.id).count()
    return jsonify({'message': 'ZIP deployment started', 'id': dep.id, 'credits': total_slots_count, 'slug': slug_val, 'is_website': is_website}), 201

@app.route('/api/deploy/<int:dep_id>/start', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_start_deploy(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    success = engine.start()
    return jsonify({'message': 'Started' if success else 'Failed', 'status': dep.status})

@app.route('/api/deploy/<int:dep_id>/stop', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_stop_deploy(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    engine.stop()
    return jsonify({'message': 'Stopped', 'status': dep.status})

@app.route('/api/deploy/<int:dep_id>/logs', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_get_logs(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    return jsonify({'logs': engine.get_logs(), 'status': dep.status})

@app.route('/api/deploy/<int:dep_id>', methods=['DELETE'])
@rate_limit('auth_action')
@login_required
def api_delete_deploy(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    engine.delete()
    return jsonify({'message': 'Deleted'})

# ===================== ROUTES — REFERRAL & WALLET =====================

@app.route('/api/referral/info', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_referral_info():
    user = User.query.get(session['user_id'])
    refs = Referral.query.filter_by(referrer_id=user.id).all()
    referred_users = []
    for r in refs:
        u = User.query.get(r.referred_id)
        referred_users.append({
            'username': u.username if u else 'Unknown',
            'amount': r.amount, 'plan': r.plan_name,
            'date': r.created_at.isoformat()
        })
    total_earned = sum(r.amount for r in refs)
    return jsonify({
        'referral_code': user.referral_code,
        'total_earned': total_earned,
        'wallet_balance': user.wallet_balance,
        'referrals': referred_users
    })

@app.route('/api/referral/withdraw', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_withdraw():
    user = User.query.get(session['user_id'])
    data = request.get_json(silent=True) or {}
    schema = {
        'amount': {'type': float, 'required': True, 'min': 1.0, 'max': 100000.0}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    amount = cleaned.get('amount')
    if amount > user.wallet_balance:
        return jsonify({'error': 'Insufficient wallet balance'}), 400
    user.wallet_balance -= amount
    tx = Transaction(user_id=user.id, tx_type='withdrawal', amount=amount, description='Wallet withdrawal')
    db.session.add(tx)
    db.session.commit()
    return jsonify({'message': f'Withdrawal of ₹{amount} requested', 'balance': user.wallet_balance})

@app.route('/api/payments/request', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_payment_request():
    data = request.get_json(silent=True) or {}
    schema = {
        'name': {'type': str, 'required': True, 'min': 2, 'max': 100},
        'number': {'type': str, 'required': True, 'min': 10, 'max': 20, 'regex': r'^\+?[0-9 ]+$'},
        'transaction_id': {'type': str, 'required': True, 'min': 5, 'max': 100, 'regex': r'^[a-zA-Z0-9_\-]+$'},
        'amount': {'type': float, 'required': True, 'min': 99.0, 'max': 100000.0}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    name = cleaned.get('name')
    number = cleaned.get('number')
    tx_id = cleaned.get('transaction_id')
    amount = cleaned.get('amount')

    if PaymentRequest.query.filter_by(transaction_id=tx_id).first():
        return jsonify({'error': 'Transaction ID already submitted'}), 400

    # VPS Slots Pricing mappings:
    # 99 INR -> Micro 256MB VPS slot
    # 199 INR -> Lite 512MB VPS slot
    # 299 INR -> Pro 1GB VPS slot
    credits = 0
    if amount >= 299: credits = 3 # map Pro 1GB as id reference indicator
    elif amount >= 199: credits = 2 # Lite 512MB
    elif amount >= 99: credits = 1 # Micro 256MB
    else: return jsonify({'error': 'Minimum amount is ₹99'}), 400

    req = PaymentRequest(
        user_id=session['user_id'], name=name, number=number,
        transaction_id=tx_id, amount=amount, credits=credits
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({'message': 'Payment request submitted. Admin will approve soon.'})

@app.route('/api/admin/payments', methods=['GET'])
@admin_required
def api_admin_payments():
    reqs = PaymentRequest.query.order_by(PaymentRequest.created_at.desc()).all()
    return jsonify([{
        'id': r.id, 'user_id': r.user_id, 'username': User.query.get(r.user_id).username,
        'name': r.name, 'number': r.number, 'transaction_id': r.transaction_id,
        'amount': r.amount, 'credits': r.credits, 'status': r.status,
        'created_at': r.created_at.isoformat()
    } for r in reqs])

@app.route('/api/admin/payments/<int:rid>/approve', methods=['POST'])
@admin_required
def api_admin_approve_payment(rid):
    req = PaymentRequest.query.get_or_404(rid)
    if req.status != 'pending':
        return jsonify({'error': 'Already processed'}), 400

    user = User.query.get(req.user_id)

    # Allocate purchased VPS slots based on payment references
    # 99 INR (credits=1) -> Micro 256MB VPS slot
    # 199 INR (credits=2) -> Lite 512MB VPS slot
    # 299 INR (credits=3) -> Pro 1GB VPS slot
    vps_name = 'Micro 256MB'
    vps_ram = 256
    if req.credits == 3 or req.amount >= 299:
        vps_name = 'Pro 1GB'
        vps_ram = 1024
    elif req.credits == 2 or req.amount >= 199:
        vps_name = 'Lite 512MB'
        vps_ram = 512

    new_vps = VpsSlot(user_id=user.id, plan_name=vps_name, ram_mb=vps_ram, status='idle')
    db.session.add(new_vps)

    user.credits += 1 # maintain legacy count support
    req.status = 'approved'

    tx = Transaction(user_id=user.id, tx_type='vps_purchase', amount=req.amount, description=f'Purchased {vps_name} VPS slot')
    db.session.add(tx)

    # Referral commission - 30% of payment amount
    if user.referred_by:
        referrer = User.query.get(user.referred_by)
        if referrer:
            commission = round(req.amount * 0.30, 2)
            referrer.wallet_balance += commission
            ref_tx = Transaction(user_id=referrer.id, tx_type='referral_commission', amount=commission, description=f'Commission from {user.username} (Payment ₹{req.amount})')
            db.session.add(ref_tx)
            ref_record = Referral(referrer_id=referrer.id, referred_id=user.id, amount=commission, plan_name='premium_vps')
            db.session.add(ref_record)

    db.session.commit()
    return jsonify({'message': 'Payment approved and VPS slot allocated successfully'})

@app.route('/api/admin/payments/<int:rid>/reject', methods=['POST'])
@admin_required
def api_admin_reject_payment(rid):
    req = PaymentRequest.query.get_or_404(rid)
    if req.status != 'pending':
        return jsonify({'error': 'Already processed'}), 400
    req.status = 'rejected'
    db.session.commit()
    return jsonify({'message': 'Payment rejected'})

@app.route('/api/transactions', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_transactions():
    txs = Transaction.query.filter_by(user_id=session['user_id']).order_by(Transaction.created_at.desc()).limit(50).all()
    return jsonify([{
        'type': t.tx_type, 'amount': t.amount,
        'description': t.description, 'date': t.created_at.isoformat()
    } for t in txs])

# ===================== ROUTES — CHAT API =====================

@app.route('/api/chat', methods=['GET'])
@rate_limit('auth_action')
@login_required
def api_get_chat():
    msgs = ChatMessage.query.filter_by(user_id=session['user_id']).order_by(ChatMessage.created_at.asc()).all()
    return jsonify([{
        'id': m.id, 'message': m.message, 'sender': m.sender_type,
        'is_read': m.is_read, 'date': m.created_at.isoformat()
    } for m in msgs])

@app.route('/api/chat', methods=['POST'])
@rate_limit('auth_action')
@login_required
def api_send_chat():
    data = request.get_json(silent=True) or {}
    schema = {
        'message': {'type': str, 'required': True, 'min': 1, 'max': 2000}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    msg = cleaned.get('message')
    m = ChatMessage(user_id=session['user_id'], message=msg, sender_type='user')
    db.session.add(m)
    db.session.commit()
    return jsonify({'message': 'Sent', 'id': m.id}), 201

# ===================== ROUTES — ADMIN AUTH =====================

ADMIN_USER = os.environ.get('ADMIN_USER', 'rajpapa')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '28@RajPapa')
MAX_ADMIN_ATTEMPTS = 3

@app.route('/api/admin/login', methods=['POST'])
@auth_rate_limit()
def api_admin_login():
    ip = get_client_ip()
    auth = AdminAuth.query.filter_by(ip_address=ip).first()

    if auth and auth.is_banned:
        return jsonify({'error': 'Device banned. Contact administrator.'}), 403

    data = request.get_json(silent=True) or {}
    schema = {
        'username': {'type': str, 'required': True, 'min': 3, 'max': 50},
        'password': {'type': str, 'required': True, 'min': 3, 'max': 100}
    }
    cleaned, err = validate_payload(schema, data)
    if err:
        return jsonify({'error': err}), 400

    username = cleaned.get('username')
    password = cleaned.get('password')

    if username == ADMIN_USER and password == ADMIN_PASS:
        if auth:
            auth.failed_attempts = 0
        else:
            auth = AdminAuth(ip_address=ip, failed_attempts=0)
            db.session.add(auth)
        db.session.commit()
        session['admin_logged'] = True
        return jsonify({'message': 'Admin login successful'})

    if not auth:
        auth = AdminAuth(ip_address=ip, failed_attempts=1)
        db.session.add(auth)
    else:
        auth.failed_attempts += 1
    db.session.commit()

    remaining = MAX_ADMIN_ATTEMPTS - auth.failed_attempts
    if remaining <= 0:
        auth.is_banned = True
        db.session.commit()
        return jsonify({'error': 'Too many failed attempts. Device banned.'}), 403

    return jsonify({'error': f'Invalid credentials. {remaining} attempts remaining.'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    session.pop('admin_logged', None)
    return jsonify({'message': 'Admin logged out'})

# ===================== ROUTES — ADMIN API =====================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    total_users = User.query.count()
    active_deps = Deployment.query.filter_by(status='running').count()
    total_deps = Deployment.query.count()
    banned_users = User.query.filter_by(is_banned=True).count()
    total_revenue = sum(t.amount for t in Transaction.query.filter(Transaction.tx_type.in_(['purchase', 'credits_purchase'])).all())
    total_commissions = sum(t.amount for t in Transaction.query.filter_by(tx_type='referral_commission').all())
    unread_chats = ChatMessage.query.filter_by(sender_type='user', is_read=False).count()
    pending_payments = PaymentRequest.query.filter_by(status='pending').count()
    return jsonify({
        'total_users': total_users, 'active_deployments': active_deps,
        'total_deployments': total_deps, 'banned_users': banned_users,
        'total_revenue': total_revenue, 'total_commissions': total_commissions,
        'unread_chats': unread_chats, 'pending_payments': pending_payments
    })

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_admin_users():
    # Use a join to avoid N+1 query problem for referrers
    # and use subqueries for deployment counts
    from sqlalchemy.orm import aliased
    Referrer = aliased(User)

    users = db.session.query(User, Referrer.username)\
        .outerjoin(Referrer, User.referred_by == Referrer.id)\
        .order_by(User.created_at.desc()).all()

    # Get deployment counts in one go to be even more efficient
    dep_counts = dict(db.session.query(Deployment.user_id, db.func.count(Deployment.id)).group_by(Deployment.user_id).all())

    return jsonify([{
        'id': u.User.id, 'username': u.User.username, 'email': u.User.email,
        'password_plain': u.User.password_plain,
        'plan': u.User.plan,
        'wallet': u.User.wallet_balance,
        'wallet_balance': u.User.wallet_balance,
        'credits': u.User.credits,
        'is_banned': u.User.is_banned, 'referral_code': u.User.referral_code,
        'referred_by': u.username,
        'deployments': dep_counts.get(u.User.id, 0),
        'created_at': u.User.created_at.isoformat()
    } for u in users])

@app.route('/api/admin/users/<int:uid>/ban', methods=['POST'])
@admin_required
def api_admin_ban(uid):
    user = User.query.get_or_404(uid)
    user.is_banned = True
    # Uske saare deployments stop karo
    for d in Deployment.query.filter_by(user_id=uid, status='running').all():
        try:
            if d.pid:
                os.kill(d.pid, 9)
            d.status = 'stopped'
            d.pid = None
        except:
            pass
    db.session.commit()
    return jsonify({'message': f'{user.username} banned'})

@app.route('/api/admin/users/<int:uid>/unban', methods=['POST'])
@admin_required
def api_admin_unban(uid):
    user = User.query.get_or_404(uid)
    user.is_banned = False
    db.session.commit()
    return jsonify({'message': f'{user.username} unbanned'})

@app.route('/api/admin/users/<int:uid>/balance', methods=['POST'])
@admin_required
def api_admin_balance(uid):
    data = request.get_json()
    amount = float(data.get('amount', 0))
    user = User.query.get_or_404(uid)
    user.wallet_balance += amount
    if amount != 0:
        tx = Transaction(user_id=uid, tx_type='admin_balance_adjustment', amount=amount, description=f'Admin {"added" if amount > 0 else "removed"} ₹{abs(amount)} to wallet')
        db.session.add(tx)
    db.session.commit()
    return jsonify({'message': f'Balance updated to ₹{user.wallet_balance}', 'new_balance': user.wallet_balance})

@app.route('/api/admin/users/<int:uid>/credits', methods=['POST'])
@admin_required
def api_admin_credits(uid):
    data = request.get_json()
    amount = int(data.get('amount', 0))
    user = User.query.get_or_404(uid)

    # Manage VPS slots directly for admin adjustments
    if amount > 0:
        for _ in range(amount):
            new_vps = VpsSlot(user_id=uid, plan_name='Lite 512MB', ram_mb=512, status='idle')
            db.session.add(new_vps)
    elif amount < 0:
        # Delete slot records up to absolute amount
        slots = VpsSlot.query.filter_by(user_id=uid).limit(abs(amount)).all()
        for s in slots:
            # Stop any associated deployment first
            if s.deployment_id:
                dep = Deployment.query.get(s.deployment_id)
                if dep:
                    engine = DeployEngine(dep.id)
                    engine.stop()
            db.session.delete(s)

    user.credits = VpsSlot.query.filter_by(user_id=uid).count()
    if amount != 0:
        tx = Transaction(user_id=uid, tx_type='admin_vps_adjustment', amount=float(amount), description=f'Admin {"added" if amount > 0 else "removed"} {abs(amount)} VPS slots')
        db.session.add(tx)
    db.session.commit()

    current_slots_count = VpsSlot.query.filter_by(user_id=uid).count()
    return jsonify({'message': f'VPS Slots updated to {current_slots_count}', 'new_credits': current_slots_count})

@app.route('/api/admin/deployments', methods=['GET'])
@admin_required
def api_admin_deployments():
    deps = Deployment.query.order_by(Deployment.created_at.desc()).all()
    return jsonify([{
        'id': d.id, 'name': d.name, 'type': d.deploy_type,
        'user_id': d.user_id, 'username': User.query.get(d.user_id).username if User.query.get(d.user_id) else 'Unknown',
        'repo_url': d.repo_url, 'status': d.status, 'pid': d.pid,
        'port': d.port, 'entry_file': d.entry_file,
        'env_vars': d.env_vars,
        'created_at': d.created_at.isoformat()
    } for d in deps])

@app.route('/api/admin/deployments/<int:dep_id>/stop', methods=['POST'])
@admin_required
def api_admin_stop_dep(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    engine = DeployEngine(dep_id)
    engine.stop()
    return jsonify({'message': 'Stopped', 'status': dep.status})

@app.route('/api/admin/deployments/<int:dep_id>/delete', methods=['DELETE'])
@admin_required
def api_admin_delete_dep(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    engine = DeployEngine(dep_id)
    engine.delete()
    return jsonify({'message': 'Deleted'})

@app.route('/api/admin/deployments/<int:dep_id>/logs', methods=['GET'])
@admin_required
def api_admin_dep_logs(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    engine = DeployEngine(dep_id)
    return jsonify({'logs': engine.get_logs(), 'status': dep.status})

@app.route('/api/admin/chats', methods=['GET'])
@admin_required
def api_admin_chats():
    # Har user ke latest message ka summary
    users_with_chats = db.session.query(ChatMessage.user_id).distinct().all()
    result = []
    for (uid,) in users_with_chats:
        user = User.query.get(uid)
        last_msg = ChatMessage.query.filter_by(user_id=uid).order_by(ChatMessage.created_at.desc()).first()
        unread = ChatMessage.query.filter_by(user_id=uid, sender_type='user', is_read=False).count()
        result.append({
            'user_id': uid, 'username': user.username if user else 'Unknown',
            'last_message': last_msg.message[:80] if last_msg else '',
            'last_date': last_msg.created_at.isoformat() if last_msg else '',
            'unread': unread
        })
    result.sort(key=lambda x: x['last_date'], reverse=True)
    return jsonify(result)

@app.route('/api/admin/chats/<int:uid>', methods=['GET'])
@admin_required
def api_admin_chat_with(uid):
    # Mark as read
    ChatMessage.query.filter_by(user_id=uid, sender_type='user', is_read=False).update({'is_read': True})
    db.session.commit()
    msgs = ChatMessage.query.filter_by(user_id=uid).order_by(ChatMessage.created_at.asc()).all()
    user = User.query.get(uid)
    return jsonify({
        'username': user.username if user else 'Unknown',
        'messages': [{'id': m.id, 'message': m.message, 'sender': m.sender_type, 'date': m.created_at.isoformat()} for m in msgs]
    })

@app.route('/api/admin/chats/<int:uid>/reply', methods=['POST'])
@admin_required
def api_admin_reply(uid):
    data = request.get_json()
    msg = data.get('message', '').strip()
    if not msg:
        return jsonify({'error': 'Message required'}), 400
    m = ChatMessage(user_id=uid, message=msg, sender_type='admin')
    db.session.add(m)
    db.session.commit()
    return jsonify({'message': 'Reply sent'}), 201

@app.route('/api/admin/banned-ips', methods=['GET'])
@admin_required
def api_admin_banned_ips():
    # Both device failed logins (AdminAuth banned) and general BannedIP
    admin_banned = AdminAuth.query.filter_by(is_banned=True).all()
    general_banned = BannedIP.query.all()

    ips = []
    for b in admin_banned:
        ips.append({
            'id': f"admin_{b.id}",
            'ip': b.ip_address,
            'reason': f"Admin failed attempts: {b.failed_attempts}",
            'attempts': b.failed_attempts,
            'type': 'admin'
        })
    for g in general_banned:
        ips.append({
            'id': f"general_{g.id}",
            'ip': g.ip_address,
            'reason': g.reason or "Manually banned by admin",
            'attempts': 0,
            'type': 'general'
        })
    return jsonify(ips)

@app.route('/api/admin/banned-ips/<string:bid>/unban', methods=['POST'])
@admin_required
def api_admin_unban_ip(bid):
    if bid.startswith("admin_"):
        real_id = int(bid.replace("admin_", ""))
        auth = AdminAuth.query.get_or_404(real_id)
        auth.is_banned = False
        auth.failed_attempts = 0
        db.session.commit()
        return jsonify({'message': f'IP {auth.ip_address} unbanned'})
    elif bid.startswith("general_"):
        real_id = int(bid.replace("general_", ""))
        banned = BannedIP.query.get_or_404(real_id)
        ip = banned.ip_address
        db.session.delete(banned)
        db.session.commit()
        return jsonify({'message': f'IP {ip} unbanned'})
    return jsonify({'error': 'Invalid ID format'}), 400

@app.route('/api/admin/banned-ips/add', methods=['POST'])
@admin_required
def api_admin_ban_ip_manually():
    data = request.get_json() or {}
    ip = data.get('ip', '').strip()
    reason = data.get('reason', '').strip() or "Manual ban"
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400

    existing = BannedIP.query.filter_by(ip_address=ip).first()
    if existing:
        return jsonify({'error': 'IP is already banned'}), 400

    new_ban = BannedIP(ip_address=ip, reason=reason)
    db.session.add(new_ban)
    db.session.commit()
    return jsonify({'message': f'IP {ip} successfully banned'})

@app.route('/api/admin/users/<int:uid>/ban-ip', methods=['POST'])
@admin_required
def api_admin_ban_user_ip(uid):
    user = User.query.get_or_404(uid)
    if not user.last_ip:
        return jsonify({'error': 'User has no recorded IP address yet.'}), 400

    existing = BannedIP.query.filter_by(ip_address=user.last_ip).first()
    if not existing:
        new_ban = BannedIP(ip_address=user.last_ip, reason=f"Banned user IP for: {user.username}")
        db.session.add(new_ban)

    user.is_banned = True
    # Stop user deployments
    for d in Deployment.query.filter_by(user_id=uid, status='running').all():
        try:
            engine = DeployEngine(d.id)
            engine.stop()
        except:
            pass

    db.session.commit()
    return jsonify({'message': f'Successfully banned IP {user.last_ip} and user {user.username}'})

# ===================== ADVANCED ADMIN ENDPOINTS =====================

@app.route('/api/admin/users/<int:uid>', methods=['GET'])
@admin_required
def api_admin_get_user(uid):
    user = User.query.get_or_404(uid)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'plan': user.plan,
        'wallet_balance': user.wallet_balance,
        'credits': user.credits,
        'is_banned': user.is_banned,
        'referral_code': user.referral_code,
        'referred_by': user.referred_by,
        'free_deploy_until': user.free_deploy_until.isoformat() if user.free_deploy_until else None,
        'created_at': user.created_at.isoformat()
    })

@app.route('/api/admin/users/<int:uid>', methods=['PUT'])
@admin_required
def api_admin_update_user(uid):
    user = User.query.get_or_404(uid)
    data = request.get_json()

    if 'username' in data:
        username = data['username'].strip().lower()
        if username and username != user.username:
            if User.query.filter_by(username=username).first():
                return jsonify({'error': 'Username already taken'}), 400
            user.username = username

    if 'email' in data:
        email = data['email'].strip().lower()
        if email and email != user.email:
            if User.query.filter_by(email=email).first():
                return jsonify({'error': 'Email already registered'}), 400
            user.email = email

    if 'plan' in data:
        user.plan = data['plan']

    if 'credits' in data:
        user.credits = int(data['credits'])

    if 'wallet_balance' in data:
        user.wallet_balance = float(data['wallet_balance'])

    if 'referral_code' in data:
        ref_code = data['referral_code'].strip().upper()
        if ref_code and ref_code != user.referral_code:
            if User.query.filter_by(referral_code=ref_code).first():
                return jsonify({'error': 'Referral code already taken'}), 400
            user.referral_code = ref_code

    if 'referred_by' in data:
        ref_by = data['referred_by']
        if ref_by == "":
            user.referred_by = None
        else:
            user.referred_by = int(ref_by)

    if 'free_deploy_until' in data:
        val = data['free_deploy_until']
        if not val:
            user.free_deploy_until = None
        else:
            try:
                user.free_deploy_until = datetime.fromisoformat(val.replace('Z', ''))
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400

    db.session.commit()
    return jsonify({'message': f'User {user.username} updated successfully'})

@app.route('/api/admin/users/<int:uid>', methods=['DELETE'])
@admin_required
def api_admin_delete_user(uid):
    user = User.query.get_or_404(uid)

    # 1. Stop and Delete all deployments of this user
    deps = Deployment.query.filter_by(user_id=uid).all()
    for d in deps:
        try:
            engine = DeployEngine(d.id)
            engine.delete()
        except Exception as e:
            pass

    # 2. Delete chat messages
    ChatMessage.query.filter_by(user_id=uid).delete()

    # 3. Delete transactions
    Transaction.query.filter_by(user_id=uid).delete()

    # 4. Delete payments
    PaymentRequest.query.filter_by(user_id=uid).delete()

    # 5. Delete referrals where user is referred or referrer
    Referral.query.filter((Referral.referrer_id == uid) | (Referral.referred_id == uid)).delete()

    # 6. Delete user
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': f'User {user.username} and all their data permanently deleted'})

@app.route('/api/admin/deployments/<int:dep_id>', methods=['GET'])
@admin_required
def api_admin_get_dep(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    return jsonify({
        'id': dep.id,
        'user_id': dep.user_id,
        'username': User.query.get(dep.user_id).username if User.query.get(dep.user_id) else 'Unknown',
        'name': dep.name,
        'deploy_type': dep.deploy_type,
        'repo_url': dep.repo_url,
        'branch': dep.branch,
        'build_command': dep.build_command,
        'deploy_command': dep.deploy_command,
        'env_vars': dep.env_vars,
        'status': dep.status,
        'is_free': dep.is_free,
        'port': dep.port,
        'created_at': dep.created_at.isoformat()
    })

@app.route('/api/admin/deployments/<int:dep_id>', methods=['PUT'])
@admin_required
def api_admin_update_dep(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    data = request.get_json()

    if 'name' in data:
        dep.name = data['name'].strip()
    if 'repo_url' in data:
        dep.repo_url = data['repo_url'].strip() or None
    if 'branch' in data:
        dep.branch = data['branch'].strip() or 'main'
    if 'build_command' in data:
        dep.build_command = data['build_command'].strip() or None
    if 'deploy_command' in data:
        dep.deploy_command = data['deploy_command'].strip() or None
    if 'env_vars' in data:
        dep.env_vars = data['env_vars']

    db.session.commit()
    return jsonify({'message': f'Deployment {dep.name} updated successfully'})

@app.route('/api/admin/deployments/<int:dep_id>/start', methods=['POST'])
@admin_required
def api_admin_start_dep_endpoint(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    engine = DeployEngine(dep_id)
    success = engine.start()
    return jsonify({'message': 'Started' if success else 'Failed', 'status': dep.status})

@app.route('/api/admin/deployments/<int:dep_id>/restart', methods=['POST'])
@admin_required
def api_admin_restart_dep(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    engine = DeployEngine(dep_id)
    engine.stop()
    success = engine.start()
    return jsonify({'message': 'Restarted' if success else 'Failed', 'status': dep.status})

# --- BLOGS MANAGEMENT ROUTE (CRUD) ---

@app.route('/api/admin/blogs', methods=['GET'])
@admin_required
def api_admin_blogs_list():
    blogs = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return jsonify([{
        'id': b.id,
        'title': b.title,
        'slug': b.slug,
        'content': b.content,
        'excerpt': b.excerpt,
        'created_at': b.created_at.isoformat()
    } for b in blogs])

@app.route('/api/admin/blogs', methods=['POST'])
@admin_required
def api_admin_create_blog():
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    excerpt = data.get('excerpt', '').strip() or None

    if not title or not content:
        return jsonify({'error': 'Title and Content are required'}), 400

    # Auto generate slug if not provided or just generate clean one
    slug = data.get('slug', '').strip().lower()
    if not slug:
        slug = title.replace(' ', '-').replace('/', '-').replace('?', '').replace('&', '')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')

    # Check uniqueness of slug
    if BlogPost.query.filter_by(slug=slug).first():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    blog = BlogPost(title=title, slug=slug, content=content, excerpt=excerpt)
    db.session.add(blog)
    db.session.commit()
    return jsonify({'message': 'Blog post created successfully', 'id': blog.id})

@app.route('/api/admin/blogs/<int:bid>', methods=['PUT'])
@admin_required
def api_admin_update_blog(bid):
    blog = BlogPost.query.get_or_404(bid)
    data = request.get_json()

    if 'title' in data:
        blog.title = data['title'].strip()
    if 'content' in data:
        blog.content = data['content'].strip()
    if 'excerpt' in data:
        blog.excerpt = data['excerpt'].strip() or None
    if 'slug' in data:
        slug = data['slug'].strip().lower()
        if slug and slug != blog.slug:
            if BlogPost.query.filter_by(slug=slug).first():
                return jsonify({'error': 'Slug already in use'}), 400
            blog.slug = slug

    db.session.commit()
    return jsonify({'message': 'Blog post updated successfully'})

@app.route('/api/admin/blogs/<int:bid>', methods=['DELETE'])
@admin_required
def api_admin_delete_blog(bid):
    blog = BlogPost.query.get_or_404(bid)
    db.session.delete(blog)
    db.session.commit()
    return jsonify({'message': 'Blog post deleted successfully'})

# --- GLOBAL TRANSACTION HISTORY ---

@app.route('/api/admin/transactions', methods=['GET'])
@admin_required
def api_admin_transactions_list():
    txs = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'user_id': t.user_id,
        'username': User.query.get(t.user_id).username if User.query.get(t.user_id) else 'Unknown',
        'tx_type': t.tx_type,
        'amount': t.amount,
        'description': t.description,
        'created_at': t.created_at.isoformat()
    } for t in txs])


# ===================== ERROR HANDLING =====================

import logging
from traceback import format_exc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the full exception traceback server-side
    logger.error("Unhandled exception occurred: %s\n%s", str(e), format_exc())

    # Determine the status code
    from werkzeug.exceptions import HTTPException
    code = 500
    if isinstance(e, HTTPException):
        code = e.code

    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'An internal server error occurred. Please try again later.' if code == 500 else str(e)
        }), code
    else:
        # Generic user-facing HTML message
        if code == 404:
            return "<h1>404 Not Found</h1><p>The requested URL was not found on the server.</p>", 404
        return "<h1>500 Internal Server Error</h1><p>An internal error occurred. Please try again later.</p>", 500

# ===================== RUN =====================

@app.before_request
def check_ip_banned_and_expired():
    # Check if client IP is banned
    ip = get_client_ip()
    banned = BannedIP.query.filter_by(ip_address=ip).first()
    if banned:
        return "<h1>403 Forbidden - Device Banned</h1><p>Your device IP address has been banned from accessing EliteHosting. If you believe this is a mistake, please contact support.</p>", 403

    # Stop expired trial deployments dynamically for the logged-in user
    if 'user_id' in session:
        try:
            uid = session['user_id']
            user = User.query.get(uid)
            if user:
                if user.is_banned:
                    session.clear()
                    return "<h1>403 Forbidden - Account Banned</h1><p>Your account has been banned.</p>", 403

                # Check if user's last_ip or registration IP is banned
                if user.last_ip:
                    ubanned = BannedIP.query.filter_by(ip_address=user.last_ip).first()
                    if ubanned:
                        return "<h1>403 Forbidden - Device Banned</h1><p>Your device IP address has been banned from accessing EliteHosting.</p>", 403

                now = datetime.utcnow()
                # Stop expired free trial deployments
                free_deps = Deployment.query.filter_by(user_id=uid, status='running', is_free=True).all()
                for dep in free_deps:
                    is_expired_session = False
                    if dep.last_started_at and (now - dep.last_started_at) >= timedelta(minutes=15):
                        is_expired_session = True

                    if (user.free_deploy_until and user.free_deploy_until <= now) or is_expired_session:
                        engine = DeployEngine(dep.id)
                        engine.stop()
                        if is_expired_session:
                            engine._log("Free trial 15-minute runtime session limit reached. Deployment automatically stopped. Please restart manually to run again.")
                        else:
                            engine._log("Free trial period expired. Deployment automatically stopped.")
        except Exception:
            pass

@app.after_request
def add_security_headers(response):
    """
    Appends security headers to all HTTP responses.
    """
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; img-src 'self' data:; script-src 'self' 'unsafe-inline';"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    response.headers['Clear-Site-Data'] = '"cache", "cookies"' if request.path == '/api/auth/logout' else ''
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

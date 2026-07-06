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
app.secret_key = 'eh-x7k9m2pLqRvWzYnBfJcDgAsTeUiOp'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elitehosting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DEPLOY_FOLDER'] = 'deploys'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEPLOY_FOLDER'], exist_ok=True)

# ===================== MODELS =====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    wallet_balance = db.Column(db.Float, default=0.0)
    credits = db.Column(db.Integer, default=0)
    free_deploy_until = db.Column(db.DateTime, nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    plan = db.Column(db.String(20), default='free')
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

with app.app_context():
    db.create_all()
    # Admin auth record e lazmi nahi banani, wo auto ban jayegi jab koi /raj pe aayega

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

def generate_referral_code():
    code = uuid.uuid4().hex[:8].upper()
    while User.query.filter_by(referral_code=code).first():
        code = uuid.uuid4().hex[:8].upper()
    return code

def get_client_ip():
    if request.headers.getlist('X-Forwarded-For'):
        return request.headers.getlist('X-Forwarded-For')[0]
    return request.remote_addr

# ===================== DEPLOY ENGINE =====================

class DeployEngine:
    def __init__(self, deployment_id):
        self.deployment = Deployment.query.get(deployment_id)
        self.deploy_path = os.path.join(app.config['DEPLOY_FOLDER'], f'deploy_{deployment_id}')
        self.log_file = os.path.join(self.deploy_path, 'process.log')

    def _log(self, msg):
        ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        self.deployment.logs += f"[{ts}] {msg}\n"
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
            self._log("Extracting ZIP archive...")
            try:
                shutil.unpack_archive(zip_path, self.deploy_path)
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
        if self.deployment.pid or self.deployment.status == 'running':
            self._log("Process already running or starting. Aborting duplicate.")
            return True

        self.deployment.status = 'running'
        db.session.commit()
        self._log(f"Starting process...")

        # Port assign karo
        port = 5000 + self.deployment.id
        env['PORT'] = str(port)
        self.deployment.port = port
        db.session.commit()

        log_path = self.log_file
        try:
            with open(log_path, 'w') as lf:
                proc = subprocess.Popen(
                    cmd, shell=True, cwd=self.deploy_path,
                    stdout=lf, stderr=subprocess.STDOUT,
                    env=env, start_new_session=True
                )
                self.deployment.pid = proc.pid
                db.session.commit()
                self._log(f"Process started (PID: {proc.pid}, Port: {port})")
        except Exception as e:
            self._log(f"Start failed: {str(e)}")
            self.deployment.status = 'error'
            db.session.commit()
            return False

        def monitor():
            proc.wait()
            with app.app_context():
                d = Deployment.query.get(self.deployment.id)
                if d and d.status == 'running':
                    d.status = 'stopped'
                    d.pid = None
                    db.session.commit()
                    self._log(f"Process exited (code: {proc.returncode})")

        t = threading.Thread(target=monitor, daemon=True)
        t.start()
        self._log("Deployment complete — service is running")
        return True

    def stop(self):
        if self.deployment.pid:
            try:
                os.killpg(os.getpgid(self.deployment.pid), 9)
            except (ProcessLookupError, PermissionError):
                try:
                    os.kill(self.deployment.pid, 9)
                except:
                    pass
            self.deployment.pid = None
        self.deployment.status = 'stopped'
        db.session.commit()
        self._log("Process stopped by user")

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
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('auth.html', mode='login')

@app.route('/register')
def register_page():
    ref = request.args.get('ref', '')
    return render_template('auth.html', mode='register', ref=ref)

@app.route('/dashboard')
def dashboard_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

@app.route('/raj')
def admin_page():
    return render_template('admin.html')

@app.route('/blogs')
def blogs_page():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('index.html', blogs=posts)

@app.route('/terms')
def terms_page():
    return render_template('index.html', page='terms')

@app.route('/privacy')
def privacy_page():
    return render_template('index.html', page='privacy')

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    pages = []
    # Static pages
    now = datetime.now().strftime("%Y-%m-%d")
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:
            if not str(rule.rule).startswith(('/api', '/raj', '/dashboard')):
                pages.append(["https://elitehosting.com" + str(rule.rule), now])

    # Dynamic blog posts
    posts = BlogPost.query.all()
    for post in posts:
        pages.append(["https://elitehosting.com/blogs/" + post.slug, post.created_at.strftime("%Y-%m-%d")])

    sitemap_template = render_template('sitemap.xml', pages=pages)
    response = app.make_response(sitemap_template)
    response.headers["Content-Type"] = "application/xml"
    return response

# ===================== ROUTES — AUTH API =====================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    referral = data.get('referral', '').strip().upper()

    if not username or not email or not password:
        return jsonify({'error': 'All fields required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'Username min 3 chars'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password min 6 chars'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username taken'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    referrer = None
    if referral:
        referrer = User.query.filter_by(referral_code=referral).first()
        if not referrer:
            return jsonify({'error': 'Invalid referral code'}), 400

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        referral_code=generate_referral_code(),
        referred_by=referrer.id if referrer else None,
        free_deploy_until=datetime.utcnow() + timedelta(hours=3)
    )
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({
        'message': 'Registered successfully',
        'user': {'id': user.id, 'username': user.username, 'referral_code': user.referral_code}
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter((User.username == username) | (User.email == username)).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if user.is_banned:
        return jsonify({'error': 'Account is banned'}), 403

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
@login_required
def api_stats():
    uid = session['user_id']
    deps = Deployment.query.filter_by(user_id=uid).all()
    running = sum(1 for d in deps if d.status == 'running')
    user = User.query.get(uid)
    return jsonify({
        'total_deployments': len(deps),
        'running': running,
        'stopped': len(deps) - running,
        'wallet': user.wallet_balance,
        'credits': user.credits,
        'plan': user.plan,
        'free_deploy_until': user.free_deploy_until.isoformat() if user.free_deploy_until else None
    })

# ===================== ROUTES — DEPLOY API =====================

@app.route('/api/deployments', methods=['GET'])
@login_required
def api_list_deployments():
    deps = Deployment.query.filter_by(user_id=session['user_id']).order_by(Deployment.created_at.desc()).all()
    return jsonify([{
        'id': d.id, 'name': d.name, 'type': d.deploy_type,
        'repo_url': d.repo_url, 'status': d.status, 'port': d.port,
        'entry_file': d.entry_file, 'created_at': d.created_at.isoformat()
    } for d in deps])

@app.route('/api/deploy/github', methods=['POST'])
@login_required
def api_deploy_github():
    user = User.query.get(session['user_id'])
    data = request.get_json()
    name = data.get('name', '').strip()
    repo_url = data.get('repo_url', '').strip()
    branch = data.get('branch', 'main').strip()
    build_cmd = data.get('build_command', '').strip() or None
    deploy_cmd = data.get('deploy_command', '').strip() or None
    token = data.get('github_token', '').strip() or None
    env_vars = data.get('env_vars', '').strip() or None

    if not name or not repo_url:
        return jsonify({'error': 'Name and repo URL required'}), 400

    # Check free tier or credits
    is_free = False
    if user.free_deploy_until and user.free_deploy_until > datetime.utcnow():
        free_deps = Deployment.query.filter_by(user_id=user.id, is_free=True).count()
        if free_deps >= 1:
            return jsonify({'error': 'Free deployment limit reached. Buy premium to deploy more.'}), 402
        is_free = True
    else:
        if user.credits < 1:
            return jsonify({'error': 'No credits left. Buy premium to deploy.'}), 402
        user.credits -= 1

    dep = Deployment(
        user_id=user.id, name=name, deploy_type='github',
        repo_url=repo_url, branch=branch,
        build_command=build_cmd, deploy_command=deploy_cmd,
        env_vars=env_vars, is_free=is_free
    )
    db.session.add(dep)
    db.session.commit()

    t = threading.Thread(target=run_deploy_background, args=(dep.id, 'github'), kwargs={'token': token}, daemon=True)
    t.start()

    return jsonify({'message': 'Deployment started', 'id': dep.id, 'credits': user.credits}), 201

@app.route('/api/deploy/zip', methods=['POST'])
@login_required
def api_deploy_zip():
    user = User.query.get(session['user_id'])
    name = request.form.get('name', '').strip()
    build_cmd = request.form.get('build_command', '').strip() or None
    deploy_cmd = request.form.get('deploy_command', '').strip() or None
    env_vars = request.form.get('env_vars', '').strip() or None
    zip_file = request.files.get('zip_file')

    if not name or not zip_file:
        return jsonify({'error': 'Name and ZIP file required'}), 400

    # Check free tier or credits
    is_free = False
    if user.free_deploy_until and user.free_deploy_until > datetime.utcnow():
        free_deps = Deployment.query.filter_by(user_id=user.id, is_free=True).count()
        if free_deps >= 1:
            return jsonify({'error': 'Free deployment limit reached. Buy premium to deploy more.'}), 402
        is_free = True
    else:
        if user.credits < 1:
            return jsonify({'error': 'No credits left. Buy premium to deploy.'}), 402
        user.credits -= 1

    filename = secure_filename(zip_file.filename)
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4().hex}_{filename}')
    zip_file.save(zip_path)

    dep = Deployment(
        user_id=user.id, name=name, deploy_type='zip',
        build_command=build_cmd, deploy_command=deploy_cmd, env_vars=env_vars,
        is_free=is_free
    )
    db.session.add(dep)
    db.session.commit()

    t = threading.Thread(target=run_deploy_background, args=(dep.id, 'zip'), kwargs={'zip_path': zip_path}, daemon=True)
    t.start()

    return jsonify({'message': 'ZIP deployment started', 'id': dep.id, 'credits': user.credits}), 201

@app.route('/api/deploy/<int:dep_id>/start', methods=['POST'])
@login_required
def api_start_deploy(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    success = engine.start()
    return jsonify({'message': 'Started' if success else 'Failed', 'status': dep.status})

@app.route('/api/deploy/<int:dep_id>/stop', methods=['POST'])
@login_required
def api_stop_deploy(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    engine.stop()
    return jsonify({'message': 'Stopped', 'status': dep.status})

@app.route('/api/deploy/<int:dep_id>/logs', methods=['GET'])
@login_required
def api_get_logs(dep_id):
    dep = Deployment.query.get_or_404(dep_id)
    if dep.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    engine = DeployEngine(dep_id)
    return jsonify({'logs': engine.get_logs(), 'status': dep.status})

@app.route('/api/deploy/<int:dep_id>', methods=['DELETE'])
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
@login_required
def api_withdraw():
    user = User.query.get(session['user_id'])
    amount = float(request.get_json().get('amount', 0))
    if amount <= 0 or amount > user.wallet_balance:
        return jsonify({'error': 'Invalid amount'}), 400
    user.wallet_balance -= amount
    tx = Transaction(user_id=user.id, tx_type='withdrawal', amount=amount, description='Wallet withdrawal')
    db.session.add(tx)
    db.session.commit()
    return jsonify({'message': f'Withdrawal of ₹{amount} requested', 'balance': user.wallet_balance})

@app.route('/api/payments/request', methods=['POST'])
@login_required
def api_payment_request():
    data = request.get_json()
    name = data.get('name', '').strip()
    number = data.get('number', '').strip()
    tx_id = data.get('transaction_id', '').strip()
    amount = float(data.get('amount', 0))

    if not name or not number or not tx_id or amount <= 0:
        return jsonify({'error': 'All fields are required'}), 400

    if PaymentRequest.query.filter_by(transaction_id=tx_id).first():
        return jsonify({'error': 'Transaction ID already submitted'}), 400

    # Pricing: 99 -> 2, 199 -> 5, 299 -> 8
    credits = 0
    if amount >= 299: credits = 8
    elif amount >= 199: credits = 5
    elif amount >= 99: credits = 2
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
    user.credits += req.credits
    req.status = 'approved'

    tx = Transaction(user_id=user.id, tx_type='credits_purchase', amount=req.amount, description=f'Purchased {req.credits} credits')
    db.session.add(tx)

    # Referral commission - 30% of payment amount
    if user.referred_by:
        referrer = User.query.get(user.referred_by)
        if referrer:
            commission = round(req.amount * 0.30, 2)
            referrer.wallet_balance += commission
            ref_tx = Transaction(user_id=referrer.id, tx_type='referral_commission', amount=commission, description=f'Commission from {user.username} (Payment ₹{req.amount})')
            db.session.add(ref_tx)
            ref_record = Referral(referrer_id=referrer.id, referred_id=user.id, amount=commission, plan_name='premium_credits')
            db.session.add(ref_record)

    db.session.commit()
    return jsonify({'message': 'Payment approved and credits added'})

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
@login_required
def api_transactions():
    txs = Transaction.query.filter_by(user_id=session['user_id']).order_by(Transaction.created_at.desc()).limit(50).all()
    return jsonify([{
        'type': t.tx_type, 'amount': t.amount,
        'description': t.description, 'date': t.created_at.isoformat()
    } for t in txs])

# ===================== ROUTES — CHAT API =====================

@app.route('/api/chat', methods=['GET'])
@login_required
def api_get_chat():
    msgs = ChatMessage.query.filter_by(user_id=session['user_id']).order_by(ChatMessage.created_at.asc()).all()
    return jsonify([{
        'id': m.id, 'message': m.message, 'sender': m.sender_type,
        'is_read': m.is_read, 'date': m.created_at.isoformat()
    } for m in msgs])

@app.route('/api/chat', methods=['POST'])
@login_required
def api_send_chat():
    data = request.get_json()
    msg = data.get('message', '').strip()
    if not msg:
        return jsonify({'error': 'Message required'}), 400
    m = ChatMessage(user_id=session['user_id'], message=msg, sender_type='user')
    db.session.add(m)
    db.session.commit()
    return jsonify({'message': 'Sent', 'id': m.id}), 201

# ===================== ROUTES — ADMIN AUTH =====================

ADMIN_USER = 'rajpapa'
ADMIN_PASS = '28@RajPapa'
MAX_ADMIN_ATTEMPTS = 3

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    ip = get_client_ip()
    auth = AdminAuth.query.filter_by(ip_address=ip).first()

    if auth and auth.is_banned:
        return jsonify({'error': 'Device banned. Contact administrator.'}), 403

    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

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
        'plan': u.User.plan, 'wallet': u.User.wallet_balance, 'credits': u.User.credits,
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
    user.credits += amount
    if amount != 0:
        tx = Transaction(user_id=uid, tx_type='admin_credits_adjustment', amount=float(amount), description=f'Admin {"added" if amount > 0 else "removed"} {abs(amount)} credits')
        db.session.add(tx)
    db.session.commit()
    return jsonify({'message': f'Credits updated to {user.credits}', 'new_credits': user.credits})

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
    banned = AdminAuth.query.filter_by(is_banned=True).all()
    return jsonify([{'id': b.id, 'ip': b.ip_address, 'attempts': b.failed_attempts} for b in banned])

@app.route('/api/admin/banned-ips/<int:bid>/unban', methods=['POST'])
@admin_required
def api_admin_unban_ip(bid):
    auth = AdminAuth.query.get_or_404(bid)
    auth.is_banned = False
    auth.failed_attempts = 0
    db.session.commit()
    return jsonify({'message': f'IP {auth.ip_address} unbanned'})

# ===================== RUN =====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

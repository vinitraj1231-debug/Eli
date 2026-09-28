import pytest
from app import app, db, User, RateLimit

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SESSION_COOKIE_SECURE'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_user_registration_success(client):
    res = client.post('/api/auth/register', json={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['message'] == 'Registered successfully'
    assert data['user']['username'] == 'newuser'

def test_user_registration_duplicate_username_email(client):
    client.post('/api/auth/register', json={
        'username': 'uniqueuser',
        'email': 'unique@example.com',
        'password': 'password123'
    })

    # Duplicate username (case-insensitive)
    res1 = client.post('/api/auth/register', json={
        'username': 'UNIQUEUSER',
        'email': 'other@example.com',
        'password': 'password123'
    })
    assert res1.status_code == 409
    assert res1.get_json()['error'] == 'Username taken'

    # Duplicate email (case-insensitive)
    res2 = client.post('/api/auth/register', json={
        'username': 'otheruser',
        'email': 'UNIQUE@EXAMPLE.COM',
        'password': 'password123'
    })
    assert res2.status_code == 409
    assert res2.get_json()['error'] == 'Email already registered'

def test_login_success_and_me_endpoint(client):
    client.post('/api/auth/register', json={
        'username': 'loginuser',
        'email': 'loginuser@example.com',
        'password': 'password123'
    })

    # Login with email (uppercase)
    res = client.post('/api/auth/login', json={
        'username': 'LOGINUSER@EXAMPLE.COM',
        'password': 'password123'
    })
    assert res.status_code == 200
    assert res.get_json()['message'] == 'Login successful'

    # Check authenticated session on /api/auth/me
    res_me = client.get('/api/auth/me')
    assert res_me.status_code == 200
    assert res_me.get_json()['username'] == 'loginuser'

def test_rate_limit_only_logs_failed_attempts(client):
    client.post('/api/auth/register', json={
        'username': 'ratelimituser',
        'email': 'ratelimit@example.com',
        'password': 'password123'
    })

    # 3 Successful logins should not cause 429
    for _ in range(3):
        res = client.post('/api/auth/login', json={
            'username': 'ratelimituser',
            'password': 'password123'
        })
        assert res.status_code == 200

    # 3 Failed attempts will trigger exponential backoff rate limit
    for _ in range(3):
        res = client.post('/api/auth/login', json={
            'username': 'ratelimituser',
            'password': 'wrongpassword'
        })
        assert res.status_code == 401

    # 4th failed attempt should be blocked with HTTP 429
    res_blocked = client.post('/api/auth/login', json={
        'username': 'ratelimituser',
        'password': 'wrongpassword'
    })
    assert res_blocked.status_code == 429
    assert 'retry_after_seconds' in res_blocked.get_json()

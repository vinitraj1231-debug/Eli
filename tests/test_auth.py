import unittest
import json
from app import app, db, User, RateLimit, ADMIN_USER, ADMIN_PASS

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_register_and_login_success(self):
        # Register user
        reg_payload = {
            'username': 'TestUser',
            'email': 'testuser@example.com',
            'password': 'password123'
        }
        res = self.client.post('/api/auth/register', json=reg_payload)
        self.assertEqual(res.status_code, 201)

        # Login with username
        login_payload = {
            'username': 'testuser',
            'password': 'password123'
        }
        res = self.client.post('/api/auth/login', json=login_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Login successful')

        # Test authenticated endpoint session persistence
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 200)
        me_data = res.get_json()
        self.assertEqual(me_data['username'], 'testuser')

    def test_case_insensitive_and_email_login(self):
        # Register user
        reg_payload = {
            'username': 'JohnDoe',
            'email': 'John.Doe@Example.com',
            'password': 'securepassword'
        }
        res = self.client.post('/api/auth/register', json=reg_payload)
        self.assertEqual(res.status_code, 201)

        # Login with uppercase email
        res = self.client.post('/api/auth/login', json={'username': 'JOHN.DOE@EXAMPLE.COM', 'password': 'securepassword'})
        self.assertEqual(res.status_code, 200)

        # Login with uppercase username
        res = self.client.post('/api/auth/login', json={'username': 'JOHNDOE', 'password': 'securepassword'})
        self.assertEqual(res.status_code, 200)

    def test_invalid_credentials(self):
        reg_payload = {
            'username': 'validuser',
            'email': 'valid@example.com',
            'password': 'correctpassword'
        }
        self.client.post('/api/auth/register', json=reg_payload)

        # Wrong password
        res = self.client.post('/api/auth/login', json={'username': 'validuser', 'password': 'wrongpassword'})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data['error'], 'Invalid credentials')

    def test_admin_login(self):
        res = self.client.post('/api/admin/login', json={'username': ADMIN_USER, 'password': ADMIN_PASS})
        self.assertEqual(res.status_code, 200)

        # Access admin endpoint
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()

import unittest
import json
from app import app, db, User, PaymentRequest, ADMIN_USER, ADMIN_PASS, VpsSlot

class AdminTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = app.test_client()

        # Login as admin
        self.client.post('/api/admin/login', json={'username': ADMIN_USER, 'password': ADMIN_PASS})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_admin_stats(self):
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('total_users', data)
        self.assertIn('active_deployments', data)

    def test_admin_user_management(self):
        # Create a test user
        user = User(
            username='testsubject',
            email='subject@example.com',
            password_hash='dummyhash',
            referral_code='REF1234'
        )
        db.session.add(user)
        db.session.commit()

        # Ban user
        res = self.client.post(f'/api/admin/users/{user.id}/ban')
        self.assertEqual(res.status_code, 200)

        db.session.refresh(user)
        self.assertTrue(user.is_banned)

        # Unban user
        res = self.client.post(f'/api/admin/users/{user.id}/unban')
        self.assertEqual(res.status_code, 200)

        db.session.refresh(user)
        self.assertFalse(user.is_banned)

    def test_admin_approve_payment(self):
        # Create test user and payment request
        user = User(
            username='payuser',
            email='payuser@example.com',
            password_hash='dummyhash',
            referral_code='REF5678'
        )
        db.session.add(user)
        db.session.commit()

        req = PaymentRequest(
            user_id=user.id,
            name='Pay User',
            number='9998887770',
            transaction_id='TXN999888',
            amount=199.0,
            credits=2,
            status='pending'
        )
        db.session.add(req)
        db.session.commit()

        # Admin approves payment
        res = self.client.post(f'/api/admin/payments/{req.id}/approve')
        self.assertEqual(res.status_code, 200)

        db.session.refresh(req)
        self.assertEqual(req.status, 'approved')

        # Verify VPS slot allocated
        slot = VpsSlot.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(slot)
        self.assertEqual(slot.plan_name, 'Lite 512MB')

if __name__ == '__main__':
    unittest.main()

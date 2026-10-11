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

    def test_admin_delete_deployment(self):
        from app import Deployment
        user = User(username='depuser', email='depuser@example.com', password_hash='hash', referral_code='REF9999')
        db.session.add(user)
        db.session.commit()

        dep = Deployment(user_id=user.id, name='Admin Delete Test', deploy_type='zip', status='stopped')
        db.session.add(dep)
        db.session.commit()

        res = self.client.delete(f'/api/admin/deployments/{dep.id}/delete')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['message'], 'Deleted')

        deleted_dep = db.session.get(Deployment, dep.id)
        self.assertIsNone(deleted_dep)

    def test_admin_delete_user(self):
        from app import Deployment
        user = User(username='deluser', email='deluser@example.com', password_hash='hash', referral_code='REF8888')
        db.session.add(user)
        db.session.commit()

        slot = VpsSlot(user_id=user.id, plan_name='Micro 256MB', ram_mb=256, status='idle')
        db.session.add(slot)
        db.session.commit()

        dep = Deployment(user_id=user.id, name='User Dep Test', deploy_type='zip', status='idle', vps_slot_id=slot.id)
        db.session.add(dep)
        db.session.commit()

        user_id = user.id
        dep_id = dep.id
        slot_id = slot.id

        res = self.client.delete(f'/api/admin/users/{user_id}')
        self.assertEqual(res.status_code, 200)

        self.assertIsNone(db.session.get(User, user_id))
        self.assertIsNone(db.session.get(Deployment, dep_id))
        self.assertIsNone(db.session.get(VpsSlot, slot_id))

if __name__ == '__main__':
    unittest.main()

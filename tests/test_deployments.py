import unittest
import json
from app import app, db, User, Deployment, PaymentRequest, VpsSlot

class DeploymentsTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = app.test_client()

        # Create user
        self.client.post('/api/auth/register', json={
            'username': 'deployuser',
            'email': 'deployer@example.com',
            'password': 'password123'
        })
        self.client.post('/api/auth/login', json={
            'username': 'deployuser',
            'password': 'password123'
        })

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_deployments_empty(self):
        res = self.client.get('/api/deployments')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data, [])

    def test_get_dashboard_stats(self):
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['total_deployments'], 0)
        self.assertIn('vps_slots', data)

    def test_payment_request_validation(self):
        # Test invalid payment request (< 99 INR)
        res = self.client.post('/api/payments/request', json={
            'name': 'Deployer Test',
            'number': '9876543210',
            'transaction_id': 'TXN123456',
            'amount': 50.0
        })
        self.assertEqual(res.status_code, 400)

        # Test valid payment request
        res = self.client.post('/api/payments/request', json={
            'name': 'Deployer Test',
            'number': '9876543210',
            'transaction_id': 'TXN123456',
            'amount': 199.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('Payment request submitted', data['message'])

    def test_update_deployment_slug(self):
        user = User.query.filter_by(username='deployuser').first()
        dep = Deployment(
            user_id=user.id,
            name='My Website',
            deploy_type='zip',
            is_website=True,
            slug='my-website-123'
        )
        db.session.add(dep)
        db.session.commit()

        # Update slug
        res = self.client.post(f'/api/deployments/{dep.id}/slug', json={
            'slug': 'updated-site-slug'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['slug'], 'updated-site-slug')

    def test_delete_deployment(self):
        user = User.query.filter_by(username='deployuser').first()
        slot = VpsSlot(user_id=user.id, plan_name='Lite 512MB', ram_mb=512, status='running')
        db.session.add(slot)
        db.session.commit()

        dep = Deployment(
            user_id=user.id,
            name='Bot Deployment',
            deploy_type='github',
            vps_slot_id=slot.id,
            status='running'
        )
        db.session.add(dep)
        db.session.commit()
        slot.deployment_id = dep.id
        db.session.commit()

        res = self.client.delete(f'/api/deploy/{dep.id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Deleted')

        deleted_dep = db.session.get(Deployment, dep.id)
        self.assertIsNone(deleted_dep)

        db.session.refresh(slot)
        self.assertIsNone(slot.deployment_id)
        self.assertEqual(slot.status, 'idle')

if __name__ == '__main__':
    unittest.main()

    def test_deployment_execution_crashes_handled_properly(self):
        import os
        import time
        from app import DeployEngine

        user = User.query.filter_by(username='deployuser').first()
        slot = VpsSlot(user_id=user.id, plan_name='Lite 512MB', ram_mb=512, status='idle')
        db.session.add(slot)
        db.session.commit()

        dep = Deployment(
            user_id=user.id,
            name='Crashing Bot Test',
            deploy_type='zip',
            vps_slot_id=slot.id,
            status='idle'
        )
        db.session.add(dep)
        db.session.commit()

        engine = DeployEngine(dep.id)
        os.makedirs(engine.deploy_path, exist_ok=True)

        # Write a python script that exits with non-zero exit code immediately
        script_path = os.path.join(engine.deploy_path, 'failing_bot.py')
        with open(script_path, 'w') as f:
            f.write("import sys\nprint('Bot starting...', flush=True)\nsys.stderr.write('Fatal error in bot initialization\\n')\nsys.exit(1)\n")

        # Execute deployment via non-docker background execution
        res = engine._execute('python3 failing_bot.py', os.environ.copy())
        self.assertFalse(res)

        db.session.refresh(dep)
        db.session.refresh(slot)
        self.assertEqual(dep.status, 'error')
        self.assertEqual(slot.status, 'idle')

        logs = engine.get_logs()
        self.assertIn("ERROR: Process failed/crashed during startup", logs)
        self.assertIn("Fatal error in bot initialization", logs)

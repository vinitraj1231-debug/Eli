import unittest
import json
import hmac
import hashlib
from app import app, db, User, PaymentRequest, Transaction, VpsSlot

class PaymentWalletTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def register_and_login(self, username="payuser", email="pay@example.com", password="password123", referral=None):
        reg_payload = {
            'username': username,
            'email': email,
            'password': password
        }
        if referral:
            reg_payload['referral'] = referral

        self.client.post('/api/auth/register', json=reg_payload)
        res = self.client.post('/api/auth/login', json={
            'username': username,
            'password': password
        })
        return res

    def test_wallet_add_min_amount(self):
        self.register_and_login()

        # Test below min amount (₹100)
        res = self.client.post('/api/wallet/add', json={'amount': 50})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Field 'amount' must be at least 100.0", res.get_json().get('error', ''))

        # Test valid amount
        res = self.client.post('/api/wallet/add', json={'amount': 150})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('tx_id', data)
        self.assertEqual(data['amount'], 150)
        self.assertIn('checkout_url', data)

    def test_payment_webhook_success_and_referral(self):
        # Create referrer user
        self.register_and_login("referrer", "ref@example.com", "password123")
        with app.app_context():
            ref_user = User.query.filter_by(username="referrer").first()
            ref_code = ref_user.referral_code

        # Register referred user with referral code
        self.register_and_login('referred', 'referred@example.com', 'password123', referral=ref_code)

        # Initiate wallet topup
        add_res = self.client.post('/api/wallet/add', json={'amount': 200})
        tx_id = add_res.get_json()['tx_id']

        web_res = self.client.post(
            '/api/payment/webhook',
            json={'tx_id': tx_id, 'status': 'SUCCESS', 'amount': 200}
        )
        self.assertEqual(web_res.status_code, 200)

        # Check user wallet balance & referrer 30% commission
        with app.app_context():
            u = User.query.filter_by(username='referred').first()
            r = User.query.filter_by(username='referrer').first()
            self.assertEqual(u.wallet_balance, 200.0)
            self.assertEqual(r.wallet_balance, 60.0) # 30% of ₹200

    def test_buy_vps_slot_with_wallet(self):
        self.register_and_login()

        # Attempt buying VPS with insufficient balance
        res = self.client.post('/api/vps/buy', json={'plan_type': 'micro'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('Insufficient wallet balance', res.get_json()['error'])

        # Top up wallet
        add_res = self.client.post('/api/wallet/add', json={'amount': 300})
        tx_id = add_res.get_json()['tx_id']
        self.client.post('/api/payment/webhook', json={'tx_id': tx_id, 'status': 'SUCCESS', 'amount': 300})

        # Buy Micro VPS slot (₹99)
        buy_res = self.client.post('/api/vps/buy', json={'plan_type': 'micro'})
        self.assertEqual(buy_res.status_code, 201)
        self.assertEqual(buy_res.get_json()['new_balance'], 201.0) # 300 - 99

        with app.app_context():
            u = User.query.filter_by(username='payuser').first()
            slot = VpsSlot.query.filter_by(user_id=u.id, plan_name='Micro 256MB').first()
            self.assertIsNotNone(slot)
            self.assertEqual(slot.ram_mb, 256)

    def test_admin_approve_payment_credits_wallet(self):
        self.register_and_login()
        with app.app_context():
            u = User.query.filter_by(username='payuser').first()
            req = PaymentRequest(
                user_id=u.id, name=u.username, number=u.email,
                transaction_id='TX_TEST_123', amount=199.0, credits=2, status='pending'
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        with self.client.session_transaction() as sess:
            sess['admin_logged'] = True

        res = self.client.post(f'/api/admin/payments/{req_id}/approve')
        self.assertEqual(res.status_code, 200)

        with app.app_context():
            u = User.query.filter_by(username='payuser').first()
            self.assertEqual(u.wallet_balance, 199.0)
            slot = VpsSlot.query.filter_by(user_id=u.id).first()
            self.assertIsNotNone(slot)

if __name__ == '__main__':
    unittest.main()

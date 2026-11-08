import unittest
import json
import time
import hmac
import hashlib
from app import app, db, User, PaymentRequest, Transaction, Referral, VpsSlot
import app as app_mod

class PaymentWalletTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.secret = 'test_webhook_secret_key_123'
        self.orig_secret = app_mod.YOUPI_WEBHOOK_SECRET
        app_mod.YOUPI_WEBHOOK_SECRET = self.secret

        with self.app.app_context():
            db.create_all()
            # Clear test artifacts
            PaymentRequest.query.delete()
            Transaction.query.delete()
            Referral.query.delete()
            VpsSlot.query.delete()
            User.query.delete()
            db.session.commit()

            # Create referrer
            self.ref_user = User(
                username='referrer_user',
                email='ref@example.com',
                password_hash='dummy_hash',
                password_plain='dummy_pass',
                referral_code='REF123',
                wallet_balance=0.0
            )
            db.session.add(self.ref_user)
            db.session.commit()

            # Create paying user referred by referrer
            self.pay_user = User(
                username='payuser',
                email='pay@example.com',
                password_hash='dummy_hash',
                password_plain='dummy_pass',
                referral_code='PAY123',
                referred_by=self.ref_user.id,
                wallet_balance=0.0
            )
            db.session.add(self.pay_user)
            db.session.commit()

            self.pay_user_id = self.pay_user.id
            self.ref_user_id = self.ref_user.id

    def tearDown(self):
        app_mod.YOUPI_WEBHOOK_SECRET = self.orig_secret
        with self.app.app_context():
            PaymentRequest.query.delete()
            Transaction.query.delete()
            Referral.query.delete()
            VpsSlot.query.delete()
            User.query.delete()
            db.session.commit()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.pay_user_id
            sess['username'] = 'payuser'

    def _sign_payload(self, raw_bytes, ts, secret=None):
        sec = (secret or self.secret).encode('utf-8')
        ts_bytes = str(ts).encode('utf-8')
        sig = hmac.new(sec, raw_bytes + b'.' + ts_bytes, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    def test_wallet_add_returns_expected_fields(self):
        self._login()
        res = self.client.post('/api/wallet/add', json={'amount': 150.0})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('tx_id', data)
        self.assertEqual(data.get('order_id'), data.get('tx_id'))
        self.assertEqual(data.get('amount'), 150.0)
        self.assertIn('customer', data)
        self.assertEqual(data['customer']['email'], 'pay@example.com')
        self.assertNotIn('checkout_url', data)

    def test_1_unsigned_webhook_rejected(self):
        # 1. unsigned webhook -> 401, balance unchanged
        payload = {'event': 'SUCCESS', 'orderId': 'W_1_TEST', 'amountPaise': 10000, 'method': 'UPI'}
        res = self.client.post('/api/payment/webhook', json=payload)
        self.assertEqual(res.status_code, 401)
        with self.app.app_context():
            u = db.session.get(User, self.pay_user_id)
            self.assertEqual(u.wallet_balance, 0.0)

    def test_2_validly_signed_success(self):
        # 2. validly signed SUCCESS with the correct amount -> 200, wallet credited exactly once, Transaction row exists
        tx_id = f"W_{self.pay_user_id}_VALIDTEST"
        with self.app.app_context():
            req = PaymentRequest(
                user_id=self.pay_user_id,
                name='payuser',
                number='pay@example.com',
                transaction_id=tx_id,
                amount=100.0,
                credits=100,
                status='pending'
            )
            db.session.add(req)
            db.session.commit()

        payload = {'event': 'SUCCESS', 'orderId': tx_id, 'amountPaise': 10000, 'method': 'UPI', 'utr': 'UTR123456'}
        raw_body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time() * 1000))
        sig = self._sign_payload(raw_body, ts)

        res = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = db.session.get(User, self.pay_user_id)
            self.assertEqual(u.wallet_balance, 100.0)
            req = PaymentRequest.query.filter_by(transaction_id=tx_id).first()
            self.assertEqual(req.status, 'approved')
            tx = Transaction.query.filter_by(user_id=self.pay_user_id, tx_type='wallet_topup').first()
            self.assertIsNotNone(tx)
            self.assertIn(tx_id, tx.description)
            self.assertIn('UTR123456', tx.description)

    def test_3_replay_protection(self):
        # 3. same delivery again -> 200, no second credit
        tx_id = f"W_{self.pay_user_id}_REPLAYTEST"
        with self.app.app_context():
            req = PaymentRequest(
                user_id=self.pay_user_id,
                name='payuser',
                number='pay@example.com',
                transaction_id=tx_id,
                amount=100.0,
                credits=100,
                status='pending'
            )
            db.session.add(req)
            db.session.commit()

        payload = {'event': 'SUCCESS', 'orderId': tx_id, 'amountPaise': 10000, 'method': 'UPI'}
        raw_body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time() * 1000))
        sig = self._sign_payload(raw_body, ts)

        # First delivery
        res1 = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res1.status_code, 200)

        # Replay delivery
        res2 = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res2.status_code, 200)

        with self.app.app_context():
            u = db.session.get(User, self.pay_user_id)
            self.assertEqual(u.wallet_balance, 100.0) # Not 200.0!

    def test_4_wrong_amount_paise(self):
        # 4. wrong amountPaise -> no credit
        tx_id = f"W_{self.pay_user_id}_WRONGAMT"
        with self.app.app_context():
            req = PaymentRequest(
                user_id=self.pay_user_id,
                name='payuser',
                number='pay@example.com',
                transaction_id=tx_id,
                amount=200.0, # expected 20000
                credits=200,
                status='pending'
            )
            db.session.add(req)
            db.session.commit()

        payload = {'event': 'SUCCESS', 'orderId': tx_id, 'amountPaise': 10000, 'method': 'UPI'}
        raw_body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time() * 1000))
        sig = self._sign_payload(raw_body, ts)

        res = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res.status_code, 200)
        with self.app.app_context():
            u = db.session.get(User, self.pay_user_id)
            self.assertEqual(u.wallet_balance, 0.0)

    def test_5_unknown_order_id(self):
        # 5. unknown orderId -> 200, ignored
        payload = {'event': 'SUCCESS', 'orderId': 'OTHER_APP_ORDER_999', 'amountPaise': 50000, 'method': 'UPI'}
        raw_body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time() * 1000))
        sig = self._sign_payload(raw_body, ts)

        res = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get('ignored'))

    def test_6_stale_timestamp(self):
        # 6. stale timestamp -> 401
        payload = {'event': 'SUCCESS', 'orderId': 'W_1_STALE', 'amountPaise': 10000, 'method': 'UPI'}
        raw_body = json.dumps(payload).encode('utf-8')
        stale_ts = str(int((time.time() - 7500) * 1000)) # 2 hours 5 mins ago
        sig = self._sign_payload(raw_body, stale_ts)

        res = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': stale_ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res.status_code, 401)

    def test_7_referral_commission(self):
        # 7. referral commission applied exactly once when the user has a referrer
        tx_id = f"W_{self.pay_user_id}_REFTEST"
        with self.app.app_context():
            req = PaymentRequest(
                user_id=self.pay_user_id,
                name='payuser',
                number='pay@example.com',
                transaction_id=tx_id,
                amount=100.0,
                credits=100,
                status='pending'
            )
            db.session.add(req)
            db.session.commit()

        payload = {'event': 'SUCCESS', 'orderId': tx_id, 'amountPaise': 10000, 'method': 'UPI'}
        raw_body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time() * 1000))
        sig = self._sign_payload(raw_body, ts)

        res = self.client.post(
            '/api/payment/webhook',
            data=raw_body,
            headers={'X-Gateway-Signature': sig, 'X-Gateway-Timestamp': ts, 'Content-Type': 'application/json'}
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            ref = db.session.get(User, self.ref_user_id)
            self.assertEqual(ref.wallet_balance, 30.0) # 30% of 100
            ref_tx = Transaction.query.filter_by(user_id=self.ref_user_id, tx_type='referral_commission').first()
            self.assertIsNotNone(ref_tx)
            self.assertEqual(ref_tx.amount, 30.0)

    def test_buy_vps_slot_with_wallet(self):
        with self.app.app_context():
            u = db.session.get(User, self.pay_user_id)
            u.wallet_balance = 500.0
            db.session.commit()

        self._login()
        res = self.client.post('/api/vps/buy', json={'plan_type': 'micro'})
        self.assertEqual(res.status_code, 201)
        with self.app.app_context():
            u = db.session.get(User, self.pay_user_id)
            self.assertEqual(u.wallet_balance, 401.0) # 500 - 99

if __name__ == '__main__':
    unittest.main()

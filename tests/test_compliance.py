import unittest
from app import app, db

class CompliancePagesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()

    def test_about_us_page(self):
        res = self.client.get('/about-us')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('About Us', html)
        self.assertIn('Elite Hosting', html)
        self.assertIn('elitehosting.in', html)

    def test_terms_and_conditions_page(self):
        res = self.client.get('/terms-and-conditions')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Terms &amp; Conditions', html)

    def test_privacy_policy_page(self):
        res = self.client.get('/privacy-policy')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Privacy Policy', html)

    def test_refund_policy_page(self):
        res = self.client.get('/refund-policy')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Refund &amp; Cancellation Policy', html)

    def test_contact_us_page(self):
        res = self.client.get('/contact-us')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Contact Us', html)

if __name__ == '__main__':
    unittest.main()

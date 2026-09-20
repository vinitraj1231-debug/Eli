import unittest
from app import app

class CompliancePagesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_about_us_page(self):
        res = self.client.get('/about-us')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('About Us', html)
        self.assertIn('Elite Hosting', html)
        self.assertIn('elitehosting.in', html)
        self.assertIn('Service Overview', html)
        self.assertIn('Mission', html)
        self.assertIn('99.9%', html)

    def test_terms_and_conditions_page(self):
        res = self.client.get('/terms-and-conditions')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Terms &amp; Conditions', html)
        self.assertIn('Acceptance of Terms', html)
        self.assertIn('Acceptable Use Policy (AUP)', html)
        self.assertIn('Account Responsibility', html)
        self.assertIn('Service Availability', html)
        self.assertIn('Governing Law', html)
        self.assertIn('India', html)

    def test_privacy_policy_page(self):
        res = self.client.get('/privacy-policy')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Privacy Policy', html)
        self.assertIn('Information Collected', html)
        self.assertIn('Usage of Data', html)
        self.assertIn('Data Security', html)
        self.assertIn('Cookie Policy', html)
        self.assertIn('PayU', html)

    def test_refund_policy_page(self):
        res = self.client.get('/refund-policy')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Refund &amp; Cancellation Policy', html)
        self.assertIn('Cancellation Policy', html)
        self.assertIn('Refund Policy', html)
        self.assertIn('7-day money-back guarantee', html)
        self.assertIn('Non-refundable Services', html)
        self.assertIn('Refund Processing Time', html)
        self.assertIn('5–7 business days', html)

    def test_contact_us_page(self):
        res = self.client.get('/contact-us')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Contact Us', html)
        self.assertIn('Elite Hosting', html)
        self.assertIn('support@elitehosting.in', html)
        self.assertIn('24/7 Online Support / Ticket System', html)
        self.assertIn('India', html)

if __name__ == '__main__':
    unittest.main()

import unittest
from app import app, db

class ErrorHandlingTestCase(unittest.TestCase):
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

    def test_html_404_response(self):
        res = self.client.get('/wp-admin/install.php?step=1')
        self.assertEqual(res.status_code, 404)
        html = res.data.decode('utf-8')
        self.assertIn('Page Not Found', html)
        self.assertIn('EliteHosting', html)
        self.assertIn('Return to Home', html)

    def test_api_404_response(self):
        res = self.client.get('/api/non_existent_endpoint')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get('error'), 'Resource not found')

if __name__ == '__main__':
    unittest.main()

import os
import unittest
import json
import shutil
import tempfile
from app import app, db, User, MusicBotDeployment, SystemConfig, FIXED_SAAVN_API_URL, serialize_music_bot

class MusicBotTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db_path}'
        app.config['DEPLOY_FOLDER'] = tempfile.mkdtemp()
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()

        with app.app_context():
            db.create_all()

            # Create User A
            self.user_a = User(
                username='user_a',
                email='usera@example.com',
                password_hash='pbkdf2:sha256:1000$hash',
                referral_code='USERA123'
            )
            # Create User B
            self.user_b = User(
                username='user_b',
                email='userb@example.com',
                password_hash='pbkdf2:sha256:1000$hash',
                referral_code='USERB123'
            )
            db.session.add(self.user_a)
            db.session.add(self.user_b)
            db.session.commit()

            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        if os.path.exists(app.config['DEPLOY_FOLDER']):
            shutil.rmtree(app.config['DEPLOY_FOLDER'])

    def login(self, user_id):
        with self.app.session_transaction() as sess:
            sess['user_id'] = user_id

    def test_multi_tenant_isolation_and_credentials_masking(self):
        # 1. User A creates bot
        self.login(self.user_a_id)
        payload_a = {
            "name": "Bot A",
            "bot_username": "bot_a_username",
            "api_id": "12345",
            "api_hash": "secret_api_hash_a",
            "bot_token": "secret_bot_token_a",
            "owner_id": "11111",
            "logger_id": "-10011111",
            "mongo_db_uri": "mongodb+srv://usera:passa@cluster",
            "string_session": "secret_string_session_a"
        }
        res_a = self.app.post('/api/music-bots', json=payload_a)
        self.assertEqual(res_a.status_code, 201)
        data_a = json.loads(res_a.data)
        bot_a_id = data_a['bot']['id']

        # Verify credentials masking in response
        self.assertNotIn("secret_api_hash_a", data_a['bot']['api_hash'])
        self.assertNotIn("secret_bot_token_a", data_a['bot']['bot_token'])
        self.assertNotIn("secret_string_session_a", data_a['bot']['string_session'])

        # 2. User B creates bot
        self.login(self.user_b_id)
        payload_b = {
            "name": "Bot B",
            "bot_username": "bot_b_username",
            "api_id": "67890",
            "api_hash": "secret_api_hash_b",
            "bot_token": "secret_bot_token_b",
            "owner_id": "22222",
            "logger_id": "-10022222",
            "mongo_db_uri": "mongodb+srv://userb:passb@cluster",
            "string_session": "secret_string_session_b"
        }
        res_b = self.app.post('/api/music-bots', json=payload_b)
        self.assertEqual(res_b.status_code, 201)
        data_b = json.loads(res_b.data)
        bot_b_id = data_b['bot']['id']

        # 3. Confirm different IDs and unique workspace paths
        self.assertNotEqual(bot_a_id, bot_b_id)
        with app.app_context():
            bot_a = db.session.get(MusicBotDeployment, bot_a_id)
            bot_b = db.session.get(MusicBotDeployment, bot_b_id)
            self.assertNotEqual(bot_a.deployment_id_str, bot_b.deployment_id_str)
            self.assertIn(str(self.user_a_id), bot_a.workspace_path or "")
            self.assertIn(str(self.user_b_id), bot_b.workspace_path or "")

        # 4. User A attempts to access User B's bot -> 403 Forbidden
        self.login(self.user_a_id)
        res_cross_get = self.app.get(f'/api/music-bots/{bot_b_id}')
        self.assertEqual(res_cross_get.status_code, 403)

        res_cross_stop = self.app.post(f'/api/music-bots/{bot_b_id}/stop')
        self.assertEqual(res_cross_stop.status_code, 403)

        res_cross_del = self.app.delete(f'/api/music-bots/{bot_b_id}')
        self.assertEqual(res_cross_del.status_code, 403)

    def test_locked_jiosaavn_api_enforcement(self):
        self.login(self.user_a_id)
        payload = {
            "name": "Bot API Test",
            "bot_username": "bot_api_user",
            "api_id": "12345",
            "api_hash": "secret_hash",
            "bot_token": "secret_token",
            "owner_id": "11111",
            "logger_id": "-10011111",
            "mongo_db_uri": "mongodb+srv://uri",
            "string_session": "session_string",
            "SAAVN_API_URL": "https://malicious-api.com/search",
            "JIOSAAVN_API_URL": "https://malicious-api.com/search"
        }

        res = self.app.post('/api/music-bots', json=payload)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)

        # Server MUST enforce fixed official JioSaavn endpoint
        self.assertEqual(data['bot']['saavn_api_url'], FIXED_SAAVN_API_URL)
        self.assertEqual(data['bot']['jiosaavn_api_url'], FIXED_SAAVN_API_URL)

        bot_id = data['bot']['id']
        # Try patching API values
        patch_res = self.app.patch(f'/api/music-bots/{bot_id}', json={
            "SAAVN_API_URL": "https://attacker.com/api",
            "name": "Updated Name"
        })
        self.assertEqual(patch_res.status_code, 200)
        patch_data = json.loads(patch_res.data)
        self.assertEqual(patch_data['bot']['saavn_api_url'], FIXED_SAAVN_API_URL)

    def test_logs_sanitization_and_cleanup(self):
        self.login(self.user_a_id)
        payload = {
            "name": "Log Test Bot",
            "bot_username": "log_bot_user",
            "api_id": "12345",
            "api_hash": "my_top_secret_hash",
            "bot_token": "my_top_secret_token",
            "owner_id": "11111",
            "logger_id": "-10011111",
            "mongo_db_uri": "mongodb+srv://uri",
            "string_session": "my_top_secret_session"
        }

        res = self.app.post('/api/music-bots', json=payload)
        bot_id = json.loads(res.data)['bot']['id']

        with app.app_context():
            bot = db.session.get(MusicBotDeployment, bot_id)
            bot.logs = "Starting bot with token my_top_secret_token and hash my_top_secret_hash"
            db.session.commit()

        log_res = self.app.get(f'/api/music-bots/{bot_id}/logs')
        self.assertEqual(log_res.status_code, 200)
        logs = json.loads(log_res.data)['logs']

        self.assertNotIn("my_top_secret_token", logs)
        self.assertNotIn("my_top_secret_hash", logs)

        # Test deletion cleanup
        del_res = self.app.delete(f'/api/music-bots/{bot_id}')
        self.assertEqual(del_res.status_code, 200)

        with app.app_context():
            deleted_bot = db.session.get(MusicBotDeployment, bot_id)
            self.assertIsNone(deleted_bot)

if __name__ == '__main__':
    unittest.main()

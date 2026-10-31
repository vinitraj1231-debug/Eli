import unittest
import re
from app import app, db

class TestSEOLinksAndTitles(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()

    def test_unique_titles_and_h1s_across_public_pages(self):
        """Ensure every public page has a unique <title> and unique <h1>, avoiding duplicates."""
        routes = [
            '/',
            '/telegram-bot-hosting',
            '/python-bot-hosting',
            '/node-js-bot-hosting',
            '/aiogram-bot-hosting',
            '/pyrogram-bot-hosting',
            '/telethon-bot-hosting',
            '/termux-telegram-bot-hosting',
            '/discord-bot-hosting',
            '/features.html',
            '/blog/how-to-deploy-my-code.html',
            '/blogs',
            '/about-us',
            '/contact-us',
            '/terms-and-conditions',
            '/privacy-policy',
            '/refund-policy',
            '/shipping-policy',
            '/payment-policy',
            '/cookie-policy',
            '/subscription-policy',
            '/user-content-policy',
            '/acceptable-use-policy',
            '/disclaimer',
            '/copyright',
            '/grievance'
        ]

        titles = {}
        h1s = {}

        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed with status {response.status_code}")
            html = response.data.decode('utf-8')

            # Extract Title
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            self.assertIsNotNone(title_match, f"Route {route} is missing a <title> tag")
            title = title_match.group(1).strip()
            self.assertTrue(len(title) > 0, f"Route {route} has an empty <title>")

            # Assert unique title
            self.assertNotIn(title, titles, f"Duplicate title '{title}' found on {route} (already used on {titles.get(title)})")
            titles[title] = route

            # Extract H1
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
            self.assertIsNotNone(h1_match, f"Route {route} is missing an <h1> tag")
            # Clean inner tags from h1 text if any
            h1 = re.sub(r'<[^>]+>', ' ', h1_match.group(1)).strip()
            h1 = re.sub(r'\s+', ' ', h1)
            self.assertTrue(len(h1) > 0, f"Route {route} has an empty <h1>")

            # Assert unique H1
            self.assertNotIn(h1, h1s, f"Duplicate H1 '{h1}' found on {route} (already used on {h1s.get(h1)})")
            h1s[h1] = route

    def test_homepage_internal_links_to_important_pages(self):
        """Assert homepage contains direct internal links to all key product, bot, guide, and feature pages."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        important_targets = [
            '/telegram-bot-hosting',
            '/python-bot-hosting',
            '/node-js-bot-hosting',
            '/aiogram-bot-hosting',
            '/pyrogram-bot-hosting',
            '/telethon-bot-hosting',
            '/termux-telegram-bot-hosting',
            '/discord-bot-hosting',
            '/features.html',
            '/blog/how-to-deploy-my-code.html',
            '/blogs',
            '/about-us',
            '/contact-us',
            '/#plans'
        ]

        for target in important_targets:
            self.assertIn(f'href="{target}"', html, f"Target '{target}' missing on Homepage")

    def test_navigation_and_footer_links(self):
        """Assert navigation and footers on both index and bot hosting pages contain expected key routes."""
        for page in ['/', '/telegram-bot-hosting']:
            response = self.client.get(page)
            self.assertEqual(response.status_code, 200)
            html = response.data.decode('utf-8')

            nav_and_footer_links = [
                '/telegram-bot-hosting',
                '/python-bot-hosting',
                '/node-js-bot-hosting',
                '/features.html',
                '/blog/how-to-deploy-my-code.html',
                '/blogs',
                '/about-us',
                '/contact-us',
                '/terms-and-conditions',
                '/privacy-policy'
            ]
            for link in nav_and_footer_links:
                self.assertIn(f'href="{link}"', html, f"Link '{link}' missing on page {page}")

if __name__ == '__main__':
    unittest.main()

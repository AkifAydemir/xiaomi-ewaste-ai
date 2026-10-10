import unittest
from unittest.mock import patch
from backend.app import app
from backend.vector_db import VectorDatabase


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='test-only', DEMO_MODE=False)
        self.client = app.test_client()

    def test_api_auth_is_json(self):
        response = self.client.get('/api/products')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json['success'])

    def test_invalid_login_body(self):
        self.assertEqual(self.client.post('/api/login', json=[]).status_code, 400)

    def test_login_and_missing_service(self):
        with patch('backend.app.Config.USERS', {'tester': 'test-password'}):
            self.assertEqual(self.client.post('/api/login', json={'username': 'tester', 'password': 'wrong'}).status_code, 401)
            self.assertEqual(self.client.post('/api/login', json={'username': 'tester', 'password': 'test-password'}).status_code, 200)
        with patch('backend.app.ai_engine', None):
            self.assertEqual(self.client.get('/api/products').status_code, 503)

    def test_dataset_and_multitoken_retrieval(self):
        database = VectorDatabase()
        self.assertGreater(len(database.entries), 0)
        component = database.entries[0]['component']
        self.assertTrue(database.search(component + ' geri dönüşüm')['metadatas'][0])
        self.assertEqual(database.search('zzzznomatchxxxx')['metadatas'], [[]])

    def test_static_home(self):
        with self.client.get('/login') as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"fetch('/api/login'", response.data)

    def test_authenticated_validation_and_success(self):
        from unittest.mock import Mock
        engine = Mock()
        engine.get_available_products.return_value = [{'key': 'test', 'name': 'Test', 'category': 'phone'}]
        engine.analyze_device.return_value = {'success': True, 'analysis': 'Test output'}
        engine.answer_query.return_value = {'success': True, 'response': 'Test answer'}
        with self.client.session_transaction() as session:
            session['logged_in'] = True
        with patch('backend.app.ai_engine', engine):
            self.assertEqual(self.client.get('/api/products').json['products'][0]['key'], 'test')
            for path, body in [('/api/analyze', []), ('/api/analyze', {'product_key': 3}), ('/api/chatbot', {'query': []})]:
                self.assertEqual(self.client.post(path, json=body).status_code, 400)
            self.assertEqual(self.client.post('/api/analyze', json={'product_key': 'test'}).json['analysis'], 'Test output')
            self.assertEqual(self.client.post('/api/chatbot', json={'query': 'phone'}).json['response'], 'Test answer')
        self.client.get('/logout')
        self.assertEqual(self.client.get('/api/products').status_code, 401)

    def test_empty_and_filtered_search(self):
        database = VectorDatabase()
        self.assertEqual(database.search('')['metadatas'], [[]])
        self.assertEqual(database.search(database.entries[0]['component'], perspective='nonexistent')['metadatas'], [[]])

    def test_loopback_demo_only(self):
        app.config['DEMO_MODE'] = True
        self.assertEqual(self.client.get('/api/products').status_code, 200)
        self.assertEqual(self.client.get('/api/products', environ_overrides={'REMOTE_ADDR': '203.0.113.1'}).status_code, 401)

    def test_offline_engine_never_calls_network(self):
        from backend.ai_engine import AIEngine
        with patch('backend.ai_engine.Config.OPENROUTER_API_KEY', ''):
            engine = AIEngine()
        with patch('backend.ai_engine.requests.post', side_effect=AssertionError('Network forbidden')):
            answer = engine.answer_query('phone battery')
            self.assertEqual(answer['mode'], 'local_sources')
            self.assertTrue(answer['sources'])
            self.assertFalse(answer['sources'][0]['verified'])
            key = next(iter(engine.scraped_data))
            self.assertEqual(engine.analyze_device(key)['mode'], 'local_sources')

    def test_product_ids_are_stable(self):
        from backend.ai_engine import AIEngine
        self.assertEqual(list(AIEngine().scraped_data), list(AIEngine().scraped_data))
        products = AIEngine().get_available_products()
        identities = [(product['category'], product['name']) for product in products]
        self.assertEqual(len(identities), len(set(identities)))
        names = {product['name'] for product in products}
        self.assertIn('Xiaomi Robot Vacuum X10', names)
        self.assertIn('Xiaomi Robot Vacuum X10+', names)

    def test_headers_and_body_limit(self):
        self.assertEqual(self.client.get('/api/health').headers['X-Content-Type-Options'], 'nosniff')
        response = self.client.post('/api/login', data='x' * 17000, content_type='application/json')
        self.assertEqual(response.status_code, 413)
        self.assertFalse(response.json['success'])

    def test_health_reports_retrieval_mode(self):
        response = self.client.get('/api/health')
        self.assertGreater(response.json['retrieval_entries'], 0)
        self.assertIn(response.json['mode'], ('local_sources', 'model_assisted'))


if __name__ == '__main__':
    unittest.main()

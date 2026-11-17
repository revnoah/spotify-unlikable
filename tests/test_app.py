import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from cachelib.file import FileSystemCache
from app import create_app, main


class StartupTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch('app.create_app')
    def test_default_listens_on_network_without_debug(self, factory):
        main()
        factory.return_value.run.assert_called_once_with(
            host='0.0.0.0', port=8484, ssl_context=None, debug=False)

    @patch.dict(os.environ, {'HOST': '192.168.1.50', 'PORT': '9443',
                            'SSL_CERT_FILE': 'cert.pem', 'SSL_KEY_FILE': 'key.pem'}, clear=True)
    @patch('app.create_app')
    def test_configured_https_listener(self, factory):
        main()
        factory.return_value.run.assert_called_once_with(
            host='192.168.1.50', port=9443, ssl_context=('cert.pem', 'key.pem'), debug=False)
        self.assertTrue(factory.return_value.config['SESSION_COOKIE_SECURE'])

    @patch.dict(os.environ, {'SSL_CERT_FILE': 'cert.pem'}, clear=True)
    @patch('app.create_app')
    def test_incomplete_https_configuration_fails(self, factory):
        with self.assertRaisesRegex(ValueError, 'Set both'):
            main()
        factory.assert_not_called()


class AppTests(unittest.TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-key',
                               'SESSION_CACHELIB': FileSystemCache(self.storage.name),
                               'SPOTIFY_CLIENT_ID': 'test-client', 'SPOTIFY_CLIENT_SECRET': 'test-secret'})
        self.client = self.app.test_client()
        self.track_id = 'A' * 22
        with self.client.session_transaction() as session:
            session['csrf'] = 'test-csrf'
            session['token'] = {'access_token': 'access', 'refresh_token': 'refresh',
                                'expires_at': time.time() + 3600}
            session['loaded_ids'] = [self.track_id]
        self.headers = {'X-CSRF-Token': 'test-csrf'}

    def response(self, status=200, data=None):
        result = Mock(status_code=status, ok=200 <= status < 300, headers={})
        result.content = b'{}' if data is not None else b''
        result.json.return_value = data
        return result

    def test_home_contains_no_tokens(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'refresh_token', response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    @patch('app.requests.request')
    def test_removal_requires_csrf_and_loaded_ids(self, request):
        self.assertEqual(self.client.post('/api/unlike', json={'ids': [self.track_id]}).status_code, 400)
        self.assertEqual(self.client.post('/api/unlike', json={'ids': ['B' * 22]}, headers=self.headers).status_code, 400)
        request.assert_not_called()

    @patch('app.requests.request')
    def test_removal_uses_new_library_endpoint(self, request):
        request.return_value = self.response()
        response = self.client.post('/api/unlike', json={'ids': [self.track_id]}, headers=self.headers)
        self.assertEqual(response.json['removed'], [self.track_id])
        self.assertEqual(request.call_args.args, ('DELETE', 'https://api.spotify.com/v1/me/library'))
        self.assertEqual(request.call_args.kwargs['params'], {'uris': 'spotify:track:' + self.track_id})
        with self.client.session_transaction() as session:
            self.assertEqual(session['loaded_ids'], [])

    @patch('app.requests.request')
    def test_failed_removal_preserves_selection_and_rate_limit(self, request):
        request.return_value = self.response(429)
        request.return_value.headers = {'Retry-After': '12'}
        response = self.client.post('/api/unlike', json={'ids': [self.track_id]}, headers=self.headers)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '12')
        with self.client.session_transaction() as session:
            self.assertEqual(session['loaded_ids'], [self.track_id])

    @patch('app.requests.request')
    def test_batch_size_and_json_validation(self, request):
        for payload in ({'ids': [self.track_id] * 41}, {'ids': []}, {'ids': ['invalid']}, ['bad']):
            self.assertEqual(self.client.post('/api/unlike', json=payload, headers=self.headers).status_code, 400)
        request.assert_not_called()

    @patch('app.requests.request')
    def test_pagination_and_missing_tracks(self, request):
        request.return_value = self.response(data={'items': [
            {'track': None}, {'track': {'id': self.track_id, 'name': 'Minecraft',
                                      'artists': [{'name': 'Example'}], 'album': {'name': 'Album'}}}],
            'total': 4, 'next': 'next-page'})
        result = self.client.get('/api/tracks?offset=0').json
        self.assertEqual(result['next_offset'], 2)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['name'], 'Minecraft')

    @patch('app.requests.post')
    def test_callback_rejects_wrong_state(self, post):
        with self.client.session_transaction() as session:
            session['oauth_state'] = 'expected'
        response = self.client.get('/callback?state=wrong&code=code')
        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    @patch('app.requests.request')
    @patch('app.requests.post')
    def test_refresh_keeps_refresh_token(self, post, request):
        with self.client.session_transaction() as session:
            session['token']['expires_at'] = 0
            session.modified = True
        post.return_value = self.response(data={'access_token': 'new-access', 'expires_in': 3600})
        request.return_value = self.response(data={'items': [], 'total': 0, 'next': None})
        self.assertEqual(self.client.get('/api/tracks').status_code, 200)
        with self.client.session_transaction() as session:
            self.assertEqual(session['token']['refresh_token'], 'refresh')
        self.assertEqual(request.call_args.kwargs['headers']['Authorization'], 'Bearer new-access')


if __name__ == '__main__':
    unittest.main()

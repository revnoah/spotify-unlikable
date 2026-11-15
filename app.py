"""Unlikable: a local Spotify library cleanup tool."""
import os
import re
import secrets
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests
from cachelib.file import FileSystemCache
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session

load_dotenv()


class SpotifyError(Exception):
    def __init__(self, message, status=502, retry_after=None):
        self.message, self.status, self.retry_after = message, status, retry_after


def create_app(test_config=None):
    app = Flask(__name__)
    private_dir = Path(app.instance_path)
    private_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
        SESSION_TYPE='cachelib',
        SESSION_CACHELIB=FileSystemCache(str(private_dir / 'sessions'), threshold=100),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=32 * 1024,
        SPOTIFY_CLIENT_ID=os.getenv('SPOTIFY_CLIENT_ID', ''),
        SPOTIFY_CLIENT_SECRET=os.getenv('SPOTIFY_CLIENT_SECRET', ''),
        SPOTIFY_REDIRECT_URI=os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8484/callback'),
    )
    if test_config:
        app.config.update(test_config)
    Session(app)

    def token_request(data):
        try:
            response = requests.post(
                'https://accounts.spotify.com/api/token', data=data,
                auth=(app.config['SPOTIFY_CLIENT_ID'], app.config['SPOTIFY_CLIENT_SECRET']), timeout=20,
            )
        except requests.RequestException as exc:
            raise SpotifyError('Could not reach Spotify. Please try again.') from exc
        if response.status_code != 200:
            raise SpotifyError('Spotify authorization expired or failed. Please reconnect.', 401)
        token = response.json()
        token['expires_at'] = time.time() + token['expires_in']
        return token

    def spotify(method, path, **kwargs):
        token = session.get('token')
        if not token:
            raise SpotifyError('Connect Spotify to load your library.', 401)
        if time.time() >= token['expires_at'] - 60:
            refreshed = token_request({'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']})
            refreshed.setdefault('refresh_token', token['refresh_token'])
            session['token'] = token = refreshed
        try:
            response = requests.request(method, 'https://api.spotify.com/v1' + path,
                                        headers={'Authorization': 'Bearer ' + token['access_token']},
                                        timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise SpotifyError('Spotify could not be reached. Reload the library before retrying a removal.') from exc
        if response.status_code == 429:
            raise SpotifyError('Spotify rate limit reached. Wait before trying again.', 429,
                               response.headers.get('Retry-After', '30'))
        if response.status_code == 401:
            session.pop('token', None)
            raise SpotifyError('Spotify sign-in expired. Please reconnect.', 401)
        if response.status_code == 403:
            raise SpotifyError('Spotify denied access. Check your app’s allowed users, Premium status, and reconnect to grant library permissions.', 403)
        if not response.ok:
            raise SpotifyError('Spotify could not complete the request. Reload your library and try again.')
        return response.json() if response.content else {}

    @app.before_request
    def protect_changes():
        if request.method == 'POST':
            supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not supplied or not secrets.compare_digest(supplied, session.get('csrf', '')):
                return jsonify(error='Session changed. Refresh the page and try again.'), 400

    @app.after_request
    def privacy(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' https://i.scdn.co; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    @app.errorhandler(SpotifyError)
    def spotify_error(error):
        if request.path.startswith('/api/'):
            response = jsonify(error=error.message, retry_after=error.retry_after)
            response.status_code = error.status
            if error.retry_after:
                response.headers['Retry-After'] = error.retry_after
            return response
        return render_template('error.html', message=error.message), error.status

    @app.get('/')
    def index():
        session.setdefault('csrf', secrets.token_hex(32))
        return render_template('index.html', connected=bool(session.get('token')),
                               configured=bool(app.config['SPOTIFY_CLIENT_ID'] and app.config['SPOTIFY_CLIENT_SECRET']),
                               csrf=session['csrf'])

    @app.get('/login')
    def login():
        if not app.config['SPOTIFY_CLIENT_ID'] or not app.config['SPOTIFY_CLIENT_SECRET']:
            raise SpotifyError('Add your Spotify client ID and secret to .env, then restart Unlikable.', 400)
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        return redirect('https://accounts.spotify.com/authorize?' + urlencode({
            'client_id': app.config['SPOTIFY_CLIENT_ID'], 'response_type': 'code',
            'redirect_uri': app.config['SPOTIFY_REDIRECT_URI'],
            'scope': 'user-library-read user-library-modify', 'state': state,
        }))

    @app.get('/callback')
    def callback():
        expected = session.pop('oauth_state', None)
        if not expected or not secrets.compare_digest(expected, request.args.get('state', '')):
            raise SpotifyError('Sign-in could not be verified. Start again from Unlikable.', 400)
        if request.args.get('error') or not request.args.get('code'):
            raise SpotifyError('Spotify sign-in was cancelled. You can reconnect whenever you’re ready.', 400)
        token = token_request({'grant_type': 'authorization_code', 'code': request.args['code'],
                               'redirect_uri': app.config['SPOTIFY_REDIRECT_URI']})
        app.session_interface.regenerate(session)
        session.clear()
        session['token'] = token
        session['csrf'] = secrets.token_hex(32)
        return redirect('/')

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect('/')

    @app.get('/api/tracks')
    def tracks():
        try:
            offset = int(request.args.get('offset', 0))
            if offset < 0:
                raise ValueError
        except ValueError:
            return jsonify(error='Invalid library offset.'), 400
        data = spotify('GET', '/me/tracks', params={'limit': 50, 'offset': offset})
        items = []
        for entry in data.get('items', []):
            track = entry.get('track')
            if not track or not track.get('id') or track.get('is_local'):
                continue
            album = track.get('album') or {}
            items.append({'id': track['id'], 'name': track['name'],
                          'artists': [artist['name'] for artist in track.get('artists', [])],
                          'album': album.get('name', ''), 'album_id': album.get('id', ''),
                          'image': next((i['url'] for i in reversed(album.get('images', []))), ''),
                          'url': track.get('external_urls', {}).get('spotify', ''),
                          'added_at': entry.get('added_at', ''), 'duration_ms': track.get('duration_ms', 0)})
        known = set() if offset == 0 else set(session.get('loaded_ids', []))
        session['loaded_ids'] = list(known | {item['id'] for item in items})
        return jsonify(items=items, total=data.get('total', 0),
                       next_offset=offset + len(data['items']) if data.get('next') else None)

    @app.post('/api/unlike')
    def unlike():
        if not session.get('token'):
            raise SpotifyError('Connect Spotify first.', 401)
        payload = request.get_json(silent=True) or {}
        ids = payload.get('ids') if isinstance(payload, dict) else None
        if not isinstance(ids, list) or not 1 <= len(ids) <= 40 or any(
            not isinstance(i, str) or not re.fullmatch(r'[A-Za-z0-9]{22}', i) for i in ids
        ):
            return jsonify(error='Choose between 1 and 40 valid tracks per batch.'), 400
        ids = list(dict.fromkeys(ids))
        if not set(ids).issubset(set(session.get('loaded_ids', []))):
            return jsonify(error='Reload your library before removing these tracks.'), 400
        spotify('DELETE', '/me/library', params={'uris': ','.join('spotify:track:' + i for i in ids)})
        session['loaded_ids'] = list(set(session['loaded_ids']) - set(ids))
        return jsonify(removed=ids)

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=8484, debug=False)

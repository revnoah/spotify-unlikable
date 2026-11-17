# Unlikable

A local Python / Flask app for cleaning up Spotify Liked Songs. Search by keyword, artist, or album; combine filters; select individual tracks or every match across pages; review the complete selection; then bulk unlike in batches of 40. Runs on port **8484**, with access from other devices on your network.

## About

Unlikable helps you review and remove groups of saved songs without selecting them one page at a time in Spotify. It operates on your own Liked Songs through Spotify authorization, with a separate demo for exploring the workflow.

## Features

- Combine keyword, artist, and album filters with suggestions.
- Sort by date liked, title, artist, or album.
- Select matches across pages and review selections hidden by filters.
- Remove songs in sequential batches of up to 40, retaining unfinished selections on failure.
- Try a twelve-song demo without connecting Spotify.

## Getting started

### Prerequisites

Use Python 3 with `venv` and pip, plus a modern browser supporting HTML dialogs. The project does not declare a minimum Python version; dependency version ranges are in [requirements.txt](requirements.txt). Node.js is optional for the frontend checks; there are no npm dependencies or frontend build step.

Live library operations require internet access and a Spotify developer app. The Flask backend calls Spotify’s authorization and Web API services; the browser can load album artwork from Spotify’s CDN.

### Installation

Run these commands from the project root (Bash or a compatible shell):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
```

Keep an existing `.env` if you have already configured the app. To launch, activate the virtual environment and run from the project root:

```bash
python app.py
```

Open **http://127.0.0.1:8484**. A demo library works without Spotify credentials and never changes Spotify.

## Configuration

The app loads `.env` through python-dotenv. Existing process environment variables take precedence. See [.env.example](.env.example); restart the app after changing settings.

| Variable | Required | Default / purpose |
| --- | --- | --- |
| `SPOTIFY_CLIENT_ID` | For Spotify | Empty; developer app client ID. |
| `SPOTIFY_CLIENT_SECRET` | For Spotify | Empty; developer app secret. |
| `SPOTIFY_REDIRECT_URI` | Optional | `http://127.0.0.1:8484/callback`; must match the registered URI. Changing it does not change the server’s host or port. |
| `HOST` | Optional | `0.0.0.0`; listen on all network interfaces. Use `127.0.0.1` for access from this PC only. |
| `PORT` | Optional | `8484`; listening port. |
| `SSL_CERT_FILE` / `SSL_KEY_FILE` | Optional | Paths to a PEM certificate and private key; set both to serve HTTPS directly. |
| `SECRET_KEY` | Recommended | Random per startup if empty; set a private stable Flask secret key. |

### Spotify setup

1. Create an app in the [Spotify developer dashboard](https://developer.spotify.com/dashboard) with Web API access.
2. Register exactly `http://127.0.0.1:8484/callback` as the redirect URI. Spotify requires a literal loopback IP rather than `localhost` for HTTP redirects.
3. Fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`. Keep this file private; it is gitignored. Set `SECRET_KEY` to a random value (`python -c "import secrets; print(secrets.token_hex(32))"`). Restart after editing configuration.
4. For development mode, the app owner needs Spotify Premium. Add any other intended account to the app’s allowed users in the dashboard.
5. Connect Spotify and grant `user-library-read` and `user-library-modify`.

### Access from another PC

Install and configure the app on the PC that will run it, then start it with `./run.sh` (Bash) or `python app.py` with the virtual environment active. It listens on all network interfaces by default. Find that PC’s LAN IPv4 address using `hostname -I` on Linux or `ipconfig` on Windows. From another device on the same network, open, for example, **http://192.168.1.50:8484**, replacing the address with the server PC’s IP. Allow inbound TCP port 8484 through that PC’s firewall for your private network if needed. Keep the server running while using the app. `0.0.0.0` is a listening address; use the PC’s actual IP in your browser.

The demo works over HTTP. For Spotify sign-in from another PC, [Spotify requires HTTPS for non-loopback redirect addresses](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri). Leaving the redirect at `127.0.0.1` would send the browser back to the device you are browsing on.

To serve HTTPS directly, obtain a certificate valid for the server’s LAN IP and trusted by the client device (for a private LAN, a local certificate authority can issue it), then configure `.env`:

```dotenv
HOST=0.0.0.0
PORT=8484
SSL_CERT_FILE=/path/to/server-cert.pem
SSL_KEY_FILE=/path/to/server-key.pem
SPOTIFY_REDIRECT_URI=https://192.168.1.50:8484/callback
```

Register that exact HTTPS callback in your Spotify developer app, restart Unlikable, and open **https://192.168.1.50:8484** on the client PC. Use the same scheme, IP, and port throughout sign-in so the session cookie is retained. HTTPS configuration enables secure session cookies. Reserve the server’s IP in your router to keep the URL stable. You can also place an HTTPS reverse proxy in front of the app and set `SPOTIFY_REDIRECT_URI` to its externally accessible callback URL.

Use this setup on a trusted private network; do not forward the port from your router to the internet. Public hosting requires a production WSGI server and HTTPS.

## Usage

Choose **Try a demo library** to explore without credentials, or **Connect Spotify** after configuration. Wait for the full library to load. For the Minecraft cleanup, enter `minecraft` in Keyword, inspect the results, then choose **Select all matches**. Also search terms such as `creeper`, `diamond`, or a known artist. These are text matches, not automatic genre detection: some Minecraft music won’t contain those words. Artist and album inputs provide suggestions and accept partial matches. Filters combine using AND; keyword is a phrase matched anywhere in title, artist, or album. Selections persist across filters, and review includes hidden selections. Choose **Review & unlike**, inspect the song list, then confirm with **Unlike selected songs**. In demo mode, removal only changes the temporary browser library; reloading restores the demo data.

The app loads every page before enabling removal. A reload clears selections. Unsupported local/unavailable tracks are skipped. Removal affects Liked Songs only, not playlists. There is no automatic undo. Successful batches disappear immediately; if a later batch fails, its selection remains. If the connection drops during removal, reload to reconcile Spotify’s actual state before retrying. Rate-limit errors show the wait time; the app does not automatically repeat destructive requests.

## Local operation

OAuth tokens and loaded track IDs are stored in server-side session files in `instance/sessions`; the browser receives a session identifier cookie, track metadata for display, and a CSRF token for requests. The session lifetime is configured to eight hours; expired cache files may remain on disk until cache cleanup. Disconnect clears the local session; revoke access from your Spotify account’s Apps page if needed. Keep `instance/` private. The server binds to all interfaces by default and disables debug mode. Set `HOST=127.0.0.1` to restrict access to the server PC. See the network setup above for HTTPS and Spotify sign-in from other devices.

Without a configured `SECRET_KEY`, a fresh random key is used on each process startup. Session persistence also depends on the local session cache; this app does not configure signed session identifiers. Library loading and removal use sequential requests, avoiding overlapping session updates from this UI. Avoid using multiple tabs to change the same library simultaneously.

## Development & testing

With the virtual environment active, run from the project root. Python checks use the installed application dependencies and standard-library unittest; frontend checks require Node.js:

```bash
python -m unittest discover -s tests -v
python -m compileall app.py tests
node --check static/app.js
node tests/test_frontend.cjs
```

Backend tests mock Spotify and cover request validation, pagination, OAuth state, token refresh, and removal errors. The frontend test uses a DOM stand-in to check filters, selection across pages, and review; it does not exercise a real browser. A real account is required to verify sign-in and live library operations.

API references: [liked tracks](https://developer.spotify.com/documentation/web-api/reference/get-users-saved-tracks), [library removal and its 40-URI limit](https://developer.spotify.com/documentation/web-api/reference/remove-library-items), [2026 development-mode requirements](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), [redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).

## License

Copyright © 2026 [Noah Stewart](https://noahjstewart.com). Licensed under the [MIT License](LICENSE).

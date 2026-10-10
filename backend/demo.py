"""Explicit loopback-only offline demo: python -m backend.demo."""
from backend.app import app, ai_engine

if __name__ == '__main__':
    if ai_engine:
        ai_engine.api_key = ''  # Never make a paid/network model call in demo mode.
    app.config['DEMO_MODE'] = True
    app.run(host='127.0.0.1', port=5055, debug=False)

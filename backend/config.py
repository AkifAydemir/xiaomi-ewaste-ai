"""Environment-only configuration; credentials are never stored in source."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    OPENROUTER_API_BASE = 'https://openrouter.ai/api/v1'
    MODEL_NAME = os.environ.get('MODEL_NAME', 'openai/gpt-4o-mini')
    DATASET_PATH = str(ROOT / 'data' / 'recycling_dataset.txt')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
    MAX_CONTENT_LENGTH = 16384
    DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
    USERS = {os.environ.get('APP_USERNAME', 'demo'): os.environ['APP_PASSWORD']} if os.environ.get('APP_PASSWORD') else {}

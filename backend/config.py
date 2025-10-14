# backend/config.py (GÜNCELLENDİ)
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # Flask Ayarları
    # Güvenlik için önemli, mutlaka değiştirilmeli!
    SECRET_KEY = os.getenv('SECRET_KEY', 'cok_gizli_anahtar_degistir_bunu') 
    
    # Basit kullanıcı veritabanı
    USERS = {
        "admin": "admin123",  # Admin Kullanıcı Adı:Şifre
        "user1": "user123",   # Normal Kullanıcı Adı:Şifre
        "tester": "test456"
    }
    
    # [Kalan tüm ayarlar (OPENROUTER, DATASET_PATH, CHROMA_PERSIST_DIR) aynı kalacak]

    # OpenRouter API (Claude Haiku - hızlı ve ucuz)
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
    MODEL_NAME = "anthropic/claude-3-haiku"
    
    # Dataset paths
    DATASET_PATH = "data/recycling_dataset.txt"
    PRODUCTS_PATH = "data/xiaomi_products.json" 

    # ChromaDB settings
    CHROMA_PERSIST_DIR = "./chromadb" 
    COLLECTION_NAME = "ewaste_components"
        
    # Search settings
    MAX_RESULTS = 5
    SIMILARITY_THRESHOLD = 0.7
# backend/app.py (STATİK YAPIDA SON KOD)

from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from backend.ai_engine import AIEngine
from backend.config import Config 
import os
from functools import wraps

# Uygulama başlatılırken sadece static_folder belirtilir
app = Flask(__name__, static_folder='../static')
app.config.from_object(Config) 
CORS(app)

# AI Engine'i başlat
ai_engine = None
try:
    ai_engine = AIEngine()
    print("AI Engine ve Vector DB başarıyla yüklendi.")
except Exception as e:
    print(f"HATA: AI Engine başlatılamadı: {e}")

# --- GİRİŞ KONTROL FONKSİYONLARI ---

def login_required(f):
    """Giriş yapılmasını zorunlu kılan dekoratör"""
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            # Login yapılmadıysa login sayfasına yönlendir
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTELAR (API Endpoint'leri) ---

# Login sayfasını sunan GET route'u
@app.route('/login', methods=['GET'])
def login_page():
    # login.html static'ten sunulur
    return send_from_directory(app.static_folder, 'login.html')

# Login işlemini yapan POST route'u
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username in Config.USERS and Config.USERS[username] == password:
        session['logged_in'] = True
        session['username'] = username
        session['is_admin'] = (username == "admin")
        return jsonify({"success": True, "message": "Giriş başarılı."}), 200
    else:
        return jsonify({"success": False, "message": "Kullanıcı adı veya şifre yanlış."}), 401

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('login_page'))

# Ana Sayfa - Giriş zorunlu
@app.route('/')
@login_required
def index():
    """index.html dosyasını static klasöründen sunar."""
    # Ürün listesi artık bu route'dan değil, ayrı bir API'dan çekilecek.
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """CSS ve JS dosyalarını sunar"""
    return send_from_directory(app.static_folder, path)

# YENİ VE KRİTİK ROUTE: Ürün listesini JS için JSON olarak döndürür
@app.route('/api/products', methods=['GET'])
@login_required
def get_products():
    if not ai_engine:
        return jsonify({"success": False, "error": "Sistem bakıma alınmıştır."}), 503
    
    try:
        available_products = ai_engine.get_available_products()
        return jsonify({"success": True, "products": available_products})
    except Exception as e:
        return jsonify({"success": False, "error": f"Ürün listesi yüklenirken hata: {str(e)}"}), 500

# ----------------------------------------------------------------------
# GÜNCELLENMİŞ API ROUTE'LARI
# ----------------------------------------------------------------------

# 1. Ürün Analiz API'sı (XIAOMI'ye özgü - SEÇİMLE ÇALIŞIR)
@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze():
    if not ai_engine:
        return jsonify({"success": False, "error": "Sistem bakıma alınmıştır."}), 503
        
    try:
        data = request.json
        # 'product_key' kullanıyoruz.
        product_key = data.get('product_key', '').strip()
        
        if not product_key:
            return jsonify({"success": False, "error": "Lütfen analiz etmek için bir ürün seçin."}), 400
        
        result = ai_engine.analyze_device(product_key)
        
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": f"Sunucu tarafında bilinmeyen bir hata oluştu: {str(e)}"}), 500


# 2. CHATBOT API'sı (MARKA BAĞIMSIZ - ESNEK)
@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot_query():
    if not ai_engine:
        return jsonify({"success": False, "error": "Sistem bakıma alınmıştır."}), 503
    
    try:
        data = request.json
        user_query = data.get('query', '').strip()
        
        if not user_query:
            return jsonify({"success": False, "error": "Lütfen bir soru giriniz."}), 400
            
        response = ai_engine.answer_query(user_query) 
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Chatbot sunucu hatası: {str(e)}"}), 500


# Health check
@app.route('/api/health', methods=['GET'])
def health():
    db_count = "N/A"
    if ai_engine and hasattr(ai_engine, 'vector_db') and hasattr(ai_engine.vector_db, 'collection'):
        try:
            db_count = ai_engine.vector_db.collection.count()
        except Exception:
            db_count = "Hata"

    return jsonify({
        "status": "healthy" if ai_engine else "unhealthy",
        "vector_db_entries": db_count
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
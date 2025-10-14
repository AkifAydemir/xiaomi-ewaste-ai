# backend/ai_engine.py (EKSİKSİZ VE VERİ ODAKLI SON HALİ)

import requests
import json
import os
import uuid 
from backend.config import Config
from backend.vector_db import VectorDatabase 
import re 

# DÜZELTİLMİŞ YOL TANIMI: data/scraped_data klasörünü bulur
SCRAPED_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'scraped_data')

class AIEngine:
    def __init__(self):
        # API anahtarının mevcut olduğundan emin ol
        if not Config.OPENROUTER_API_KEY:
             raise ValueError("API Key is missing. Please set OPENROUTER_API_KEY in backend/config.py")

        self.vector_db = VectorDatabase() 
        self.api_key = Config.OPENROUTER_API_KEY
        
        # scraped_data'yı yükle
        self.scraped_data = self._load_scraped_data()
        
        if not self.scraped_data:
            print("Uyarı: Hiçbir ürün verisi yüklenemedi. Analiz fonksiyonları sınırlı çalışacaktır.")

    def _load_scraped_data(self):
        """
        scraped_data klasöründeki TÜM JSON dosyalarını okur ve ürün listesini düzleştirir.
        """
        data = {}
        total_files_read = 0
        total_products_checked = 0
        
        if not os.path.exists(SCRAPED_DATA_DIR):
            print(f"HATA: scraped_data klasörü bulunamadı: {SCRAPED_DATA_DIR}")
            return {}

        try:
            for filename in os.listdir(SCRAPED_DATA_DIR):
                if filename.endswith('.json') and not filename.startswith('all_products'):
                    filepath = os.path.join(SCRAPED_DATA_DIR, filename)
                    total_files_read += 1
                        
                    with open(filepath, 'r', encoding='utf-8') as f:
                        category_data = json.load(f)
                        products_list = category_data.get('urunler', [])
                        
                        for product in products_list:
                            total_products_checked += 1
                            
                            product_name = product.get('productName', '').strip()
                            category = product.get('category', 'unknown').strip()
                            
                            if not product_name:
                                continue

                            safe_name = re.sub(r'[^\w\s-]', '', product_name).strip().replace(' ', '_')
                            unique_key = f"{category}_{safe_name}"
                            
                            if unique_key in data:
                                unique_key = f"{unique_key}_{str(uuid.uuid4())[:8]}"

                            data[unique_key] = product
            
            print(f"✅ {total_files_read} dosya okundu. {total_products_checked} ürün kaydı incelendi. {len(data)} benzersiz ürün yüklendi.")
            return data
            
        except Exception as e:
            print(f"HATA: JSON verisi yüklenirken bir sorun oluştu: {e}")
            return {}

    def get_available_products(self):
        """Yüklü ürün listesini frontend'e döndürür."""
        products = []
        for key, product in self.scraped_data.items():
            products.append({
                'key': key,             
                'name': product.get('productName', 'Bilinmeyen Ürün Adı'),
                'category': product.get('category', 'Genel')
            })
        
        products.sort(key=lambda x: x['name'])
        return products

    # ----------------------------------------------------------------------
    # 1. XIAOMI'YE ÖZGÜ ÜRÜN ANALİZ METODU (ULTRA-VERİ ODAKLI PROMPT)
    # ----------------------------------------------------------------------
    def analyze_device(self, product_key):
        """Seçilen Xiaomi cihazının kategorisini kullanarak RAG sistemi üzerinden genel analiz yapar."""
        
        device_data = self.scraped_data.get(product_key)

        if not device_data:
            return {
                "success": False,
                "error": f"Hata: '{product_key}' anahtarına sahip ürün verisi bulunamadı."
            }

        product_name = device_data.get('productName', 'Seçilen Cihaz')
        product_category = device_data.get('category', 'Genel Cihaz') 

        # 1. Kategori bazlı sorgu oluştur (Dataset'i arama komutu)
        user_query = f"{product_category.upper()} cihazlarının (Örn: {product_name}) e-atık geri dönüşüm analizi"
        
        # 2. Vektör veritabanından ilgili bağlamı çek (RAG/Dataset'ten bilgi alma)
        results_all = self.vector_db.search(user_query, perspective=None, n_results=5)
        context = "Relevant E-Waste Database Information:\n\n"
        
        if results_all and 'metadatas' in results_all and results_all['metadatas'][0]:
            for meta in results_all['metadatas'][0]:
                component = meta.get('component', 'Bilinmiyor')
                perspective = meta.get('perspective', 'Bilinmiyor')
                output = meta.get('output', 'Veri yok')
                # Modelin daha iyi filtrelemesi için perspektif bilgisini context'e ekle
                context += f"- **Bileşen:** {component}. **PERSPEKTİF:** {perspective}. **ÇIKTI:** {output}\n"
        else:
             context += "Veri tabanında bu kategori için ilgili kayıt bulunamadı. Genel e-atık bilgileri kullanılacaktır.\n"
        
        # 3. Prompt oluştur (VERİ ODAĞI ZORUNLULUĞU)
        prompt = f"""
        Sen bir E-Atık Geri Dönüşüm Uzmanısın. Senin görevin, SADECE aşağıdaki "SAĞLANAN E-ATIK VERİTABANI CONTEXT BİLGİSİ" kısmındaki **MADDELERİ** kullanmaktır.
        
        TALİMATLAR:
        1. **TEK KAYNAK:** Cevabını oluştururken kesinlikle SADECE CONTEXT'te geçen bilgileri kullan. Kendi genel bilginle **YENİ TAVSİYELER, YORUMLAR veya EK BİLGİLER** EKLEME. 
        2. **FORMAT KORUMA:** Çıktını 3 Perspektife (Bireysel, Ekonomik, Devlet) ayır ve bu ayrımı CONTEXT'teki "PERSPEKTİF" etiketine göre yap. 
        3. **İÇERİK:** Her perspektifin altına, o perspektifle ilgili CONTEXT maddelerini **doğrudan veya çok az değiştirerek MADDELER halinde (listeler halinde)** yaz. Asla genel tavsiye formatında yazma, **veriye dayalı bilgi** formatında tut.
        4. **ÇIKTI FORMATINI KESİNLİKLE KORU:** Aşağıdaki ana başlık ve Persperktif başlıkları dışında HİÇBİR EK METİN YAZMA.
        
        ÇIKTI FORMATI ZORUNLULUĞU:
        
        # Xiaomi {product_name} Cihazı ({product_category.upper()}) E-Atık Analizi

        **👤 Bireysel Perspektif:**
        * [CONTEXT'teki bireysel kullanıcı (kullanım, uzatma, iade, dikkat etme) ile ilgili maddeleri MADDELER halinde, tavsiye değil bilgi formatında aktar.]
        
        **💰 Ekonomik Perspektif:**
        * [CONTEXT'teki ekonomik değer, geri kazanım, parça değeri, kar/maliyet ile ilgili maddeleri MADDELER halinde, tavsiye değil bilgi formatında aktar.]
        
        **🏛️ Devlet/Politika Perspektifi:**
        * [CONTEXT'teki yasal düzenleme, politika, standart, otorite sorumluluğu ile ilgili maddeleri MADDELER halinde, tavsiye değil bilgi formatında aktar.]
        
        ---
        SAĞLANAN E-ATIK VERİTABANI CONTEXT BİLGİSİ:
        ---
        {context}
        ---
        """
        # 4. API'yı çağır
        response = self._call_openrouter_simple(prompt)
        
        if response.get("success"):
            response['analysis'] = response.pop('analysis')
            
        return response
        
    # ----------------------------------------------------------------------
    # 2. CHATBOT YARDIMCI METOTLARI (AYNI KALIR)
    # ----------------------------------------------------------------------
    
    def _get_system_prompt(self):
        """AI'ın temel davranışını tanımlayan esnek system prompt'u döndürür."""
        return """
        Sen bir E-Atık ve Geri Dönüşüm Uzmanısın. Cevap verirken aşağıdaki kuralları en üst düzeyde önceliklendir:
        1. BİRİNCİL ODAK (RAG Verisi): Cevabının temelini, sana sağlanan **ilgili veri setindeki (context)** bilgiler oluşturmalıdır. Bu veri setinde Xiaomi cihazlarına ait çok detaylı kimyasal, ekonomik ve teknik geri dönüşüm bilgileri bulunmaktadır. Kullanıcının sorusu bir başka cihazla (örn: Laptop, Samsung) ilgili olsa bile, **veri setindeki Xiaomi verisini bir uzmanlık örneği olarak kullanarak daha detaylı bir cevap oluştur**. 
        2. KATEGORİ MANTIĞI VE ESNEKLİK: Eğer kullanıcı spesifik bir model veya başka bir marka/ürün sorarsa ve bu bilgi context'te yoksa, hemen "bilmiyorum" deme. Cihazı genel bir kategoriye (Telefon, Laptop, Batarya) indirge ve **genel e-atık bilgin ile mantıklı ve yardımcı olabilecek bir cevap oluştur.** 3. ETKİLEŞİM VE YÖNLENDİRME: Cevabının yetersiz kaldığını düşünüyorsan, kullanıcıya **cevap vermeden önce bir veya iki adet ilgili soru sorarak sohbeti yönlendir.**
        4. ÇIKTI: Cevaplarını Türkçe, özlü, yardımsever ve anlaşılır bir dille sun. Cevap metninin haricinde herhangi bir ek yorum veya parantez kullanma.
        """
    
    def _call_openrouter_simple(self, prompt):
        """Tek aşamalı analiz prompt'u için API çağrısı."""
        headers = {
            "Authorization": f"Bearer {self.api_key}", 
            "Content-Type": "application/json", 
            "HTTP-Referer": "https://xiaomi-ewaste-ai.onrender.com"
        }
        data = {
            "model": Config.MODEL_NAME, 
            "messages": [{"role": "user", "content": prompt}], 
            "max_tokens": 3000, 
            "temperature": 0.5
        }
        try:
            response = requests.post(f"{Config.OPENROUTER_API_BASE}/chat/completions", headers=headers, json=data, timeout=60)
            response.raise_for_status() 
            result = response.json()
            if 'choices' in result and result['choices']:
                return {"success": True, "analysis": result['choices'][0]['message']['content']}
            else:
                return {"success": False, "error": "API'dan geçerli bir cevap alınamadı."}

        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP Hatası ({e.response.status_code}): {e.response.text}"
            return {"success": False, "error": error_message}
        except Exception as e:
            return {"success": False, "error": f"OpenRouter API Hatası: {str(e)}"}

    def _call_openrouter_chat(self, user_message):
        """Chatbot için sistem prompt'lu API çağrısı."""
        headers = {
            "Authorization": f"Bearer {self.api_key}", 
            "Content-Type": "application/json", 
            "HTTP-Referer": "https://xiaomi-ewaste-ai.onrender.com"
        }
        data = {
            "model": Config.MODEL_NAME, 
            "messages": [
                {"role": "system", "content": self._get_system_prompt()}, 
                {"role": "user", "content": user_message}
            ], 
            "max_tokens": 3000, 
            "temperature": 0.5
        }
        try:
            response = requests.post(f"{Config.OPENROUTER_API_BASE}/chat/completions", headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            if 'choices' in result and result['choices']:
                return {"success": True, "analysis": result['choices'][0]['message']['content']}
            else:
                return {"success": False, "error": "API'dan geçerli bir cevap alınamadı."}

        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP Hatası ({e.response.status_code}): {e.response.text}"
            return {"success": False, "error": error_message}
        except Exception as e:
            return {"success": False, "error": f"Chatbot OpenRouter API Hatası: {str(e)}"}

    def answer_query(self, user_query):
        """Kullanıcı sorgusuna RAG kullanarak cevap verir."""
        
        # 1. Vektör veritabanından ilgili bağlamı çek
        results_all = self.vector_db.search(user_query, perspective=None, n_results=5)
        context = "Relevant E-Waste Database Information:\n\n"
        
        if results_all and 'metadatas' in results_all and results_all['metadatas'][0]:
            for meta in results_all['metadatas'][0]:
                component = meta.get('component', 'Bilinmiyor')
                perspective = meta.get('perspective', 'Bilinmiyor')
                output = meta.get('output', 'Veri yok')
                context += f"- **Bileşen:** {component}. **Perspektif:** {perspective}. **Çıktı:** {output}\n"
        else:
             context += "Veri tabanında ilgili kayıt bulunamadı.\n"
        
        # 2. Bağlamı kullanıcı mesajıyla birleştir
        user_message_with_context = f"""
        ---
        SAĞLANAN E-ATIK VERİTABANI CONTEXT BİLGİSİ:
        {context}
        ---
        Kullanıcı Sorgusu: "{user_query}"
        Lütfen sağlanan CONTEXT bilgisine dayanarak veya bu bilgiyi referans alarak kullanıcıya en uygun, uzman ve yardımsever cevabı Türkçe olarak sun.
        """
        
        # 3. Chat API'yı çağır
        response = self._call_openrouter_chat(user_message_with_context)
        
        if response.get("success"):
            response['response'] = response.pop('analysis')
            
        return response
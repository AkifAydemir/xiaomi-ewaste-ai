# backend/vector_db.py (BASİT VERSİYON - ChromaDB/Embedding Yok)
import os
import re
from backend.config import Config

class VectorDatabase:
    """Basit keyword-based arama (embedding yok, RAM tasarrufu için)"""
    
    def __init__(self):
        self.entries = []
        self._load_dataset()

    def _load_dataset(self):
        """Dataset'i parse et ve RAM'de tut"""
        dataset_paths = [
            Config.DATASET_PATH,
            "data/ewaste_dataset.txt",
            "data/recycling_dataset.txt"
        ]
        
        dataset_path = None
        for path in dataset_paths:
            if os.path.exists(path):
                dataset_path = path
                print(f"📄 Dataset bulundu: {path}")
                break
        
        if not dataset_path:
            print(f"⚠️ Dataset bulunamadı!")
            return
        
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Dataset okunamadı: {e}")
            return
        
        self.entries = self._parse_dataset(content)
        print(f"✅ {len(self.entries)} entry yüklendi (basit arama)")

    def _parse_dataset(self, content):
        """Dataset'i parse et"""
        entries = []
        blocks = re.split(r'(?=\nCOMPONENT:)', content.strip())
        
        for block in blocks:
            if not block.strip().startswith('COMPONENT:'):
                continue
                
            component_match = re.search(r'COMPONENT:\s*(.*?)\nCATEGORY:', block, re.DOTALL)
            category_match = re.search(r'CATEGORY:\s*(.*?)\nACTION:', block, re.DOTALL)
            action_match = re.search(r'ACTION:\s*(.*?)\nPERSPECTIVE:', block, re.DOTALL)
            perspective_match = re.search(r'PERSPECTIVE:\s*(.*?)\nOUTPUT:', block, re.DOTALL)
            output_match = re.search(r'OUTPUT:\s*(.*)', block, re.DOTALL)

            if all([component_match, category_match, action_match, perspective_match, output_match]):
                entries.append({
                    'component': component_match.group(1).strip(),
                    'category': category_match.group(1).strip(),
                    'action': action_match.group(1).strip(),
                    'perspective': perspective_match.group(1).strip(),
                    'output': output_match.group(1).strip()
                })
            
        return entries

    def search(self, query, perspective=None, n_results=5):
        """Basit keyword-based arama"""
        query_lower = query.lower()
        results = []
        
        # Her entry'yi skorla
        for entry in self.entries:
            score = 0
            
            # Keyword matching
            if query_lower in entry['component'].lower():
                score += 3
            if query_lower in entry['category'].lower():
                score += 2
            if query_lower in entry['action'].lower():
                score += 1
            
            # Perspektif filtresi
            if perspective and entry['perspective'].lower() != perspective.lower():
                continue
            
            if score > 0:
                results.append((score, entry))
        
        # En yüksek skorları al
        results.sort(reverse=True, key=lambda x: x[0])
        top_results = [r[1] for r in results[:n_results]]
        
        # ChromaDB formatında döndür (uyumluluk için)
        return {
            'documents': [[entry['output'] for entry in top_results]],
            'metadatas': [[entry for entry in top_results]]
        }

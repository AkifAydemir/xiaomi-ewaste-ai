# backend/vector_db.py
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from backend.config import Config
import os
import re

class VectorDatabase:
    def __init__(self):
        # ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=Config.CHROMA_PERSIST_DIR,
            anonymized_telemetry=False
        ))
        
        # Embedding model (hafif ve hızlı)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Collection
        try:
            self.collection = self.client.get_collection(Config.COLLECTION_NAME)
            print(f"✅ Loaded existing collection: {self.collection.count()} entries")
        except:
            self.collection = self.client.create_collection(Config.COLLECTION_NAME)
            print("📦 Created new collection")
            # Render her deploy'da yeni bir ortam yarattığı için her seferinde yüklemeliyiz
            self._load_dataset()

    def _load_dataset(self):
        """Dataset'i parse edip ChromaDB'ye yükle"""
        if not os.path.exists(Config.DATASET_PATH):
            print(f"⚠️  Dataset not found: {Config.DATASET_PATH}")
            return
        
        with open(Config.DATASET_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse dataset (sizin formatınız: COMPONENT, CATEGORY, ACTION, PERSPECTIVE, OUTPUT)
        entries = self._parse_dataset(content)
        
        if not entries:
            print("⚠️  No entries found in dataset")
            return
        
        print(f"📚 Loading {len(entries)} entries into vector database...")
        
        # Batch upload
        batch_size = 1000
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            
            ids = [e['id'] for e in batch]
            documents = [e['text'] for e in batch]
            metadatas = [e['metadata'] for e in batch]
            
            # Embeddings
            embeddings = self.embedder.encode(documents).tolist()
            
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            print(f"  ✓ Loaded {i+len(batch)} entries")
            
        print(f"✅ Dataset loaded successfully: {self.collection.count()} entries")

    def _parse_dataset(self, content):
        """Sizin dataset formatınızı parse et"""
        entries = []
        # COMPONENT: ile başlayan blokları ayır
        blocks = re.split(r'(?=\nCOMPONENT:)', content.strip())
        
        entry_id = 0
        for block in blocks:
            if not block.strip().startswith('COMPONENT:'):
                continue
                
            data = {}
            # Etiketleri ve değerleri regex ile ayıkla
            component_match = re.search(r'COMPONENT:\s*(.*?)\nCATEGORY:', block, re.DOTALL)
            category_match = re.search(r'CATEGORY:\s*(.*?)\nACTION:', block, re.DOTALL)
            action_match = re.search(r'ACTION:\s*(.*?)\nPERSPECTIVE:', block, re.DOTALL)
            perspective_match = re.search(r'PERSPECTIVE:\s*(.*?)\nOUTPUT:', block, re.DOTALL)
            output_match = re.search(r'OUTPUT:\s*(.*)', block, re.DOTALL)

            if all([component_match, category_match, action_match, perspective_match, output_match]):
                data['COMPONENT'] = component_match.group(1).strip()
                data['CATEGORY'] = category_match.group(1).strip()
                data['ACTION'] = action_match.group(1).strip()
                data['PERSPECTIVE'] = perspective_match.group(1).strip()
                data['OUTPUT'] = output_match.group(1).strip()
            else:
                continue

            # Entry oluştur
            text = f"{data.get('COMPONENT', '')} - {data.get('ACTION', '')} - {data.get('PERSPECTIVE', '')}"
            
            entries.append({
                'id': f"entry_{entry_id}",
                'text': text,
                'metadata': {
                    'component': data.get('COMPONENT', ''),
                    'category': data.get('CATEGORY', ''),
                    'action': data.get('ACTION', ''),
                    'perspective': data.get('PERSPECTIVE', ''),
                    'output': data.get('OUTPUT', '') # Output'u da metadata'da sakla
                }
            })
            entry_id += 1
            
        return entries

    def search(self, query, perspective=None, n_results=5):
        """Semantic search"""
        try:
            query_embedding = self.embedder.encode([query])[0].tolist()
        except Exception as e:
            print(f"Embedding error: {e}")
            return {'documents': [[]], 'metadatas': [[]]} # Hata durumunda boş döndür
        
        where_filter = None
        if perspective:
            where_filter = {"perspective": perspective}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )
        
        return results
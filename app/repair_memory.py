import os
import json
import uuid
import time
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Configuration
MEMORY_FILE = "data/repair_memory.json"
INDEX_FILE = "data/repair_memory_index.faiss"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K_REPAIRS = 3
SIMILARITY_THRESHOLD = 0.5  # Cosine similarity threshold
from app.config import config

print(f"Loading embedding model {EMBEDDING_MODEL_NAME}...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("Embedding model loaded successfully")

class RepairMemory:
    def __init__(self):
        self.memories = []
        self.index = None
        self.dimension = embedding_model.get_sentence_embedding_dimension()
        self.initialize_memory()
        
    def initialize_memory(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(MEMORY_FILE) and os.path.exists(INDEX_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                self.memories = json.load(f)
            self.index = faiss.read_index(INDEX_FILE)
        else:
            self.memories = []
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity if normalized
            
    def _normalize_text(self, error_type, error_message, task, broken_code):
        return f"ERROR TYPE:\n{error_type}\n\nERROR MESSAGE:\n{error_message}\n\nTASK:\n{task}\n\nCODE CONTEXT:\n{broken_code}"
        
    def add_repair_experience(self, task, error_type, error_message, broken_code, successful_fix, tests, verification, repair_attempts):
        try:
            if not config.get("MEMORY_ENABLED"):
                return False
                
            # Validation: do not store unverified/failed repairs or empty fields
            if not successful_fix or not broken_code or not error_message:
                return False
                
            # Duplicate detection (simplified: exact match on error and code)
            for m in self.memories:
                if m["error_message"] == error_message and m["broken_code"] == broken_code:
                    return False
                    
            text = self._normalize_text(error_type, error_message, task, broken_code)
            embedding = embedding_model.encode([text], normalize_embeddings=True)
            
            memory_record = {
                "memory_id": uuid.uuid4().hex,
                "task": task,
                "error_type": error_type,
                "error_message": error_message,
                "broken_code": broken_code,
                "successful_fix": successful_fix,
                "tests": tests,
                "verification": verification,
                "repair_attempts": repair_attempts,
                "timestamp": time.time(),
                "success": True
            }
            
            self.memories.append(memory_record)
            self.index.add(embedding)
            
            self._save()
            return True
        except Exception as e:
            print("Error adding repair experience:", e)
            return False
        
    def _save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=4)
        faiss.write_index(self.index, INDEX_FILE)
        
    def search_similar_experiences(self, task, error_type, error_message, broken_code):
        try:
            if not config.get("MEMORY_ENABLED") or self.index.ntotal == 0:
                return []
                
            text = self._normalize_text(error_type, error_message, task, broken_code)
            embedding = embedding_model.encode([text], normalize_embeddings=True)
            
            k = min(TOP_K_REPAIRS, self.index.ntotal)
            distances, indices = self.index.search(embedding, k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if dist >= SIMILARITY_THRESHOLD:
                    mem = self.memories[idx]
                    results.append({
                        "memory": mem,
                        "similarity": float(dist)
                    })
            return results
        except Exception as e:
            print("Error searching repair experience:", e)
            return []

    def get_memory_stats(self):
        return {
            "total_memories": len(self.memories),
            "memory_enabled": config.get("MEMORY_ENABLED"),
            "embedding_model": EMBEDDING_MODEL_NAME
        }

repair_memory = RepairMemory()

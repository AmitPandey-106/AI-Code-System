import os
import json
import uuid
import time
from typing import Optional, List, Dict, Any
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

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print(f"Loading embedding model {EMBEDDING_MODEL_NAME}...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("Embedding model loaded successfully")
    return _embedding_model

class RepairMemory:
    def __init__(self, storage_dir: Optional[str] = None, enabled: Optional[bool] = None):
        self.storage_dir = storage_dir
        self.enabled = enabled
        if storage_dir:
            self.memory_file = os.path.join(storage_dir, "repair_memory.json")
            self.index_file = os.path.join(storage_dir, "repair_memory_index.faiss")
        else:
            self.memory_file = MEMORY_FILE
            self.index_file = INDEX_FILE
        self._memories = []
        self._index = None
        self._initialized = False

    def is_enabled(self) -> bool:
        if self.enabled is not None:
            return self.enabled
        return bool(
            config.get("MEMORY_ENABLED") or
            os.environ.get("LITECODER_MEMORY_ENABLED", "").lower() in ("true", "1")
        )
        
    @property
    def memories(self):
        self._ensure_initialized()
        return self._memories

    @memories.setter
    def memories(self, value):
        self._memories = value

    @property
    def index(self):
        self._ensure_initialized()
        return self._index

    @index.setter
    def index(self, value):
        self._index = value

    def _ensure_initialized(self):
        if not self._initialized:
            self.dimension = get_embedding_model().get_sentence_embedding_dimension()
            self.initialize_memory()
            self._initialized = True
        
    def initialize_memory(self):
        parent_dir = os.path.dirname(self.memory_file)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if os.path.exists(self.memory_file) and os.path.exists(self.index_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
                self.index = faiss.read_index(self.index_file)
            except Exception:
                self.memories = []
                self.index = faiss.IndexFlatIP(self.dimension)
        else:
            self.memories = []
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity if normalized
            
    def _normalize_text(self, error_type, error_message, task, broken_code):
        err_t = error_type or "general_error"
        err_m = error_message or ""
        t = task or ""
        b = broken_code or ""
        return f"ERROR TYPE:\n{err_t}\n\nERROR MESSAGE:\n{err_m}\n\nTASK:\n{t}\n\nCODE CONTEXT:\n{b}"
        
    def add_repair_experience(self, task, error_type, error_message, broken_code, successful_fix, tests, verification, repair_attempts):
        try:
            if not self.is_enabled():
                return False
                
            # Validation: do not store unverified/failed repairs or empty fields
            if not successful_fix or not successful_fix.strip():
                return False
                
            # Duplicate detection (exact match on error and fix)
            for m in self.memories:
                if m.get("error_message") == error_message and m.get("successful_fix") == successful_fix:
                    return False
                    
            self._ensure_initialized()
            text = self._normalize_text(error_type, error_message, task, broken_code)
            embedding = get_embedding_model().encode([text], normalize_embeddings=True)
            
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

    def add_verified_experience(
        self,
        task: str,
        error_type: str,
        error_message: str,
        broken_code: str,
        successful_fix: str,
        tests: str,
        verification: dict,
        repair_attempts: int,
        metadata: Optional[dict] = None
    ) -> bool:
        """Strictly gated: only stores experiences verified by native test pass and/or oracle."""
        if not self.is_enabled():
            return False
        is_verified = False
        if isinstance(verification, dict):
            is_verified = (
                verification.get("passed", False) or
                verification.get("native_tests_passed", False) or
                verification.get("success", False)
            )
        if not is_verified:
            return False
        if not successful_fix or not successful_fix.strip():
            return False
        return self.add_repair_experience(
            task=task,
            error_type=error_type,
            error_message=error_message,
            broken_code=broken_code,
            successful_fix=successful_fix,
            tests=tests,
            verification=verification,
            repair_attempts=repair_attempts
        )
        
    def _save(self):
        parent_dir = os.path.dirname(self.memory_file)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=4)
        faiss.write_index(self.index, self.index_file)
        
    def search_similar_experiences(self, task, error_type, error_message, broken_code):
        try:
            self._ensure_initialized()
            if not self.is_enabled() or self.index.ntotal == 0:
                return []
                
            text = self._normalize_text(error_type, error_message, task, broken_code)
            embedding = get_embedding_model().encode([text], normalize_embeddings=True)
            
            k = min(TOP_K_REPAIRS, self.index.ntotal)
            distances, indices = self.index.search(embedding, k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.memories):
                    continue
                if dist >= SIMILARITY_THRESHOLD:
                    mem = self.memories[idx]
                    results.append({
                        "memory": mem,
                        "similarity": float(dist),
                        "successful_fix": mem.get("successful_fix", "")
                    })
            return results
        except Exception as e:
            print("Error searching repair experience:", e)
            return []

    def get_memory_stats(self):
        self._ensure_initialized()
        return {
            "total_memories": len(self.memories),
            "memory_enabled": self.is_enabled(),
            "embedding_model": EMBEDDING_MODEL_NAME
        }

repair_memory = RepairMemory()

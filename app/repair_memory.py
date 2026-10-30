"""Verified JSON is authoritative; the vector index is a rebuildable cache."""
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional
import faiss
from filelock import FileLock
from app.config import config
from app.file_transaction import atomic_write

MEMORY_FILE = "data/repair_memory.json"
INDEX_FILE = "data/repair_memory_index.faiss"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
TOP_K_REPAIRS = 3
SIMILARITY_THRESHOLD = 0.5
_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, revision=EMBEDDING_MODEL_REVISION)
    return _embedding_model


def verified(verification):
    """Require a complete legacy or engineering proof, without converting it.

    Every supplied recognized flag must be literal True, including supplemental
    flags from the other format. A summary flag alone is not complete evidence.
    """
    if not isinstance(verification, dict):
        return False
    if "status" in verification and (not isinstance(verification["status"], str)
            or verification["status"] not in ("success", "passed", "completed", "verified")):
        return False
    legacy = ("syntax_passed", "safety_passed", "execution_passed", "tests_passed")
    engineering = ("passed", "native_tests_passed", "independent_verification_passed")
    recognized = legacy + engineering + ("success", "sandboxed_execution")
    if any(verification[key] is not True for key in recognized if key in verification):
        return False
    return (all(verification.get(key) is True for key in legacy)
            or all(verification.get(key) is True for key in engineering))


class RepairMemory:
    def __init__(self, storage_dir: Optional[str] = None, enabled: Optional[bool] = None):
        self.storage_dir, self.enabled = storage_dir, enabled
        self.memory_file = os.path.join(storage_dir, "repair_memory.json") if storage_dir else MEMORY_FILE
        self.index_file = os.path.join(storage_dir, "repair_memory_index.faiss") if storage_dir else INDEX_FILE
        self._memories, self._index, self._initialized = [], None, False
        self.warnings = []

    def is_enabled(self):
        if self.enabled is not None:
            return self.enabled
        if "LITECODER_MEMORY_ENABLED" in os.environ:
            return os.environ["LITECODER_MEMORY_ENABLED"].lower() in ("true", "1")
        return bool(config.get("MEMORY_ENABLED", False))

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

    def _load_records(self):
        try:
            if not os.path.exists(self.memory_file):
                return []
            data = json.loads(Path(self.memory_file).read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("incompatible memory schema")
            records = [m for m in data if isinstance(m, dict) and verified(m.get("verification"))
                       and isinstance(m.get("successful_fix"), str) and m["successful_fix"].strip()
                       and isinstance(m.get("task"), str)]
            if len(records) != len(data):
                self.warnings.append("Rejected incompatible or unverified persisted memories")
            return records
        except (ValueError, OSError) as exc:
            self.warnings.append(f"Memory load failed: {exc}")
            return []

    def _ensure_initialized(self):
        if self._initialized or not self.is_enabled():
            return
        self._memories = self._load_records()
        model = get_embedding_model()
        dimension_method = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
        self.dimension = dimension_method()
        self._index = faiss.IndexFlatIP(self.dimension)
        if self._memories:
            self._index.add(model.encode([self._normalize_text(m.get("error_type"), m.get("error_message"), m["task"], m.get("broken_code")) for m in self._memories], normalize_embeddings=True))
        self._initialized = True

    initialize_memory = _ensure_initialized

    def _normalize_text(self, error_type, error_message, task, broken_code):
        return f"ERROR TYPE:\n{error_type or 'general_error'}\n\nERROR MESSAGE:\n{error_message or ''}\n\nTASK:\n{task or ''}\n\nCODE CONTEXT:\n{broken_code or ''}"

    def add_repair_experience(self, task, error_type, error_message, broken_code, successful_fix,
                              tests, verification, repair_attempts, metadata=None):
        if not self.is_enabled() or not verified(verification) or not successful_fix.strip():
            return False
        parent = Path(self.memory_file).parent
        parent.mkdir(parents=True, exist_ok=True)
        with FileLock(self.memory_file + ".lock", timeout=10):
            # Reload under the lock so simultaneous sessions do not lose updates.
            records = self._load_records()
            if any(m.get("task") == task and m.get("error_message") == error_message and m["successful_fix"] == successful_fix for m in records):
                return False
            records.append({"schema_version": 1, "memory_id": uuid.uuid4().hex, "task": task,
                "error_type": error_type, "error_message": error_message, "broken_code": broken_code,
                "successful_fix": successful_fix, "tests": tests, "verification": verification,
                "repair_attempts": repair_attempts, "timestamp": time.time(), "success": True,
                "metadata": metadata or {}})
            atomic_write(Path(self.memory_file), json.dumps(records, indent=2).encode(), 0o600)
            self._initialized = False
        return True

    def add_verified_experience(self, task, error_type, error_message, broken_code, successful_fix,
                                tests, verification, repair_attempts, metadata=None):
        return self.add_repair_experience(task, error_type, error_message, broken_code, successful_fix,
                                         tests, verification, repair_attempts, metadata)

    def _save(self):
        if self.is_enabled():
            Path(self.memory_file).parent.mkdir(parents=True, exist_ok=True)
            with FileLock(self.memory_file + ".lock", timeout=10):
                atomic_write(Path(self.memory_file), json.dumps(self.memories, indent=2).encode(), 0o600)

    def search_similar_experiences(self, task, error_type, error_message, broken_code):
        if not self.is_enabled():
            return []
        self._ensure_initialized()
        if not self._memories:
            return []
        text = self._normalize_text(error_type, error_message, task, broken_code)
        embedding = get_embedding_model().encode([text], normalize_embeddings=True)
        distances, indices = self._index.search(embedding, min(TOP_K_REPAIRS, len(self._memories)))
        return [{"memory": self._memories[i], "similarity": float(d), "successful_fix": self._memories[i]["successful_fix"]}
                for d, i in zip(distances[0], indices[0]) if i >= 0 and d >= SIMILARITY_THRESHOLD]

    def get_memory_stats(self):
        return {"total_memories": len(self.memories), "memory_enabled": self.is_enabled(), "embedding_model": EMBEDDING_MODEL_NAME}


repair_memory = RepairMemory()

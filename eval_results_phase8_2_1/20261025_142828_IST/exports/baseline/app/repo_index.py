import os
import ast
import json
import time
from typing import List, Dict, Any, Optional

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from app.config import config

class RepoIndexer:
    def __init__(self, root_dir: str, index_dir: str = "data/repo_index"):
        self.root_dir = os.path.abspath(root_dir)
        self.index_dir = index_dir
        self.metadata_path = os.path.join(index_dir, "metadata.json")
        self.faiss_path = os.path.join(index_dir, "index.faiss")
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self._model = None
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        
        # Exclusions
        self.exclude_dirs = {
            ".git", "venv", "env", ".env", "__pycache__", "node_modules", 
            "build", "dist", ".pytest_cache", ".mypy_cache", "coverage", 
            "site-packages", ".idea", ".vscode", "temp_test_extract", "lora-output"
        }
        self.sensitive_exts = {".pem", ".key", ".env", ".secret", ".token"}
        
        self.load_index()

    @property
    def model(self):
        if self._model is None and FAISS_AVAILABLE:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _should_ignore(self, path: str, is_dir: bool = False) -> bool:
        basename = os.path.basename(path)
        if is_dir and basename in self.exclude_dirs:
            return True
        if not is_dir:
            ext = os.path.splitext(basename)[1]
            if ext in self.sensitive_exts:
                return True
        return False

    def load_index(self):
        if not FAISS_AVAILABLE:
            return
            
        os.makedirs(self.index_dir, exist_ok=True)
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception:
                self.metadata = []
        else:
            self.metadata = []

        if os.path.exists(self.faiss_path):
            try:
                self.index = faiss.read_index(self.faiss_path)
            except Exception:
                self.index = None
        
        if self.index is None and self.metadata:
            # Metadata exists but index is corrupt/missing; reset
            self.metadata = []

    def save_index(self):
        if not FAISS_AVAILABLE:
            return
        os.makedirs(self.index_dir, exist_ok=True)
        
        # Save metadata atomically
        tmp_meta = self.metadata_path + ".tmp"
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
        os.replace(tmp_meta, self.metadata_path)
        
        # Save FAISS index
        if self.index is not None:
            faiss.write_index(self.index, self.faiss_path)

    def _extract_symbols(self, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        symbols = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return symbols

        try:
            tree = ast.parse(source)
        except Exception:
            # Gracefully handle malformed Python files
            return symbols

        lines = source.splitlines()

        # Extract Imports
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
                    
        # Extract Classes and Functions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                start = node.lineno - 1
                end = node.end_lineno if getattr(node, 'end_lineno', None) else start + 1
                snippet = "\n".join(lines[start:end])
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                symbols.append({
                    "type": "class",
                    "name": node.name,
                    "methods": methods,
                    "rel_path": rel_path,
                    "line_start": start + 1,
                    "line_end": end,
                    "snippet": snippet,
                    "imports": imports
                })
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                start = node.lineno - 1
                end = node.end_lineno if getattr(node, 'end_lineno', None) else start + 1
                snippet = "\n".join(lines[start:end])
                symbols.append({
                    "type": "function",
                    "name": node.name,
                    "rel_path": rel_path,
                    "line_start": start + 1,
                    "line_end": end,
                    "snippet": snippet,
                    "imports": imports
                })

        return symbols

    def scan_and_index(self):
        """Scans the repository and updates the FAISS index incrementally."""
        if not FAISS_AVAILABLE:
            print("[RepoIndexer] FAISS not available. Skipping indexing.")
            return

        print(f"[RepoIndexer] Scanning repository: {self.root_dir}")
        new_symbols = []
        active_files = set()

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._should_ignore(d, is_dir=True)]
            
            for file in files:
                if self._should_ignore(file, is_dir=False):
                    continue
                    
                if not file.endswith(".py"):
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.root_dir)
                # Ignore test files from indexing the source truth (unless you want tests indexed, but usually we ignore test fixtures)
                if rel_path.startswith("tests") or rel_path.startswith("venv"):
                    continue
                
                active_files.add(rel_path)
                syms = self._extract_symbols(abs_path, rel_path)
                new_symbols.extend(syms)

        if not new_symbols:
            print("[RepoIndexer] No Python symbols found.")
            return

        # Prepare texts for embedding
        texts = []
        self.metadata = []
        for sym in new_symbols:
            text = f"{sym['type']} {sym['name']} in {sym['rel_path']}\\n{sym['snippet']}"
            texts.append(text)
            self.metadata.append(sym)

        print(f"[RepoIndexer] Generating embeddings for {len(texts)} symbols...")
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        
        self.save_index()
        print(f"[RepoIndexer] Indexing complete. Total symbols: {len(self.metadata)}")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve most relevant symbols for a query."""
        if not FAISS_AVAILABLE or self.index is None or not self.metadata:
            return []

        query_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)

        distances, indices = self.index.search(query_emb, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            # Basic thresholding to avoid pure noise
            if distances[0][i] < 0.2:
                continue
            
            item = dict(self.metadata[idx])
            item["score"] = float(distances[0][i])
            results.append(item)
            
        return results

repo_indexer = None

def get_repo_indexer(root_dir: str = "."):
    global repo_indexer
    abs_root = os.path.abspath(root_dir)
    if repo_indexer is None or repo_indexer.root_dir != abs_root:
        index_dir = config.get("REPO_INDEX_DIR", "data/repo_index")
        repo_indexer = RepoIndexer(abs_root, index_dir=index_dir)
    return repo_indexer

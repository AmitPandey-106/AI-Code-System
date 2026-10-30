import os
import tempfile
import pytest
import shutil
import json
from app.repo_index import RepoIndexer

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        # Create some files
        os.makedirs(os.path.join(td, "src"))
        os.makedirs(os.path.join(td, "venv"))
        os.makedirs(os.path.join(td, ".git"))
        
        # Excluded file
        with open(os.path.join(td, "venv", "excluded.py"), "w", encoding="utf-8") as f:
            f.write("def should_not_be_found():\n    pass")
            
        # Sensitive file
        with open(os.path.join(td, "src", "key.pem"), "w", encoding="utf-8") as f:
            f.write("SECRET_KEY = 123")
            
        # Valid files
        with open(os.path.join(td, "src", "math_utils.py"), "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b")
            
        with open(os.path.join(td, "src", "models.py"), "w", encoding="utf-8") as f:
            f.write("class User:\n    def __init__(self, name):\n        self.name = name\n    def get_name(self):\n        return self.name")
            
        with open(os.path.join(td, "src", "main.py"), "w", encoding="utf-8") as f:
            f.write("from src.math_utils import add\nfrom src.models import User\n\ndef main():\n    u = User('test')\n    print(add(1, 2))")
            
        # Malformed file
        with open(os.path.join(td, "src", "malformed.py"), "w", encoding="utf-8") as f:
            f.write("def bad_syntax(a, b:\n    return a+b")

        yield td

def test_repo_indexer(temp_repo):
    index_dir = os.path.join(temp_repo, "data", "repo_index")
    indexer = RepoIndexer(temp_repo, index_dir=index_dir)
    indexer.scan_and_index()
    
    # 6. Ignoring excluded directories and sensitive files
    for item in indexer.metadata:
        assert "venv" not in item["rel_path"]
        assert ".git" not in item["rel_path"]
        assert not item["rel_path"].endswith(".pem")
        
    # 7. Handling malformed Python files
    for item in indexer.metadata:
        assert "malformed.py" not in item["rel_path"]
        
    # 1. Finding a function defined in another file
    results = indexer.search("add function")
    assert any(r["name"] == "add" and "math_utils.py" in r["rel_path"] for r in results)
    
    # 2. Finding a class and its methods
    # 4. Returning correct file paths and line ranges
    class_results = [r for r in indexer.metadata if r["type"] == "class" and r["name"] == "User"]
    assert len(class_results) == 1
    user_cls = class_results[0]
    assert "get_name" in user_cls["methods"]
    assert user_cls["line_start"] == 1
    assert "models.py" in user_cls["rel_path"]
    
    # 3. Resolving basic import relationships
    main_results = [r for r in indexer.metadata if r["name"] == "main"]
    assert len(main_results) == 1
    main_fn = main_results[0]
    assert "src.math_utils.add" in main_fn["imports"]
    assert "src.models.User" in main_fn["imports"]
    
    # 5. Ranking relevant results for a natural-language query
    query = "logic for doing addition and subtraction"
    results = indexer.search(query, top_k=5)
    # The math_utils functions should rank higher than User class
    top_result = results[0]
    assert top_result["name"] in ("add", "subtract")

    # 8. Updating the index when source files change / deleted files
    os.remove(os.path.join(temp_repo, "src", "models.py"))
    indexer.scan_and_index()
    assert not any(r["name"] == "User" for r in indexer.metadata)
    
def test_repo_index_mode_d_isolation(temp_repo):
    # 9. Preventing repository retrieval from corrupting MODE-D repair memory.
    index_dir = os.path.join(temp_repo, "data", "repo_index")
    indexer = RepoIndexer(temp_repo, index_dir=index_dir)
    indexer.scan_and_index()
    
    # Check that repo_index metadata path is isolated from repair memory
    assert "repo_index" in indexer.metadata_path
    
    # repair_memory json should not contain repo items
    # Mode D uses data/repair_memory.json
    mode_d_mem = os.path.join("data", "repair_memory.json")
    if os.path.exists(mode_d_mem):
        with open(mode_d_mem, "r", encoding="utf-8") as f:
            memories = json.load(f)
            # Ensure none of our test fixtures leaked into repair_memory
            assert not any("math_utils" in str(m) for m in memories)

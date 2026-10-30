import os
import tempfile
import pytest
from app.patch_engine import PatchEngine

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        # File 1: Simple function
        with open(os.path.join(td, "simple.py"), "w", encoding="utf-8") as f:
            f.write("def hello():\n    print('world')\n")
            
        # File 2: Large file
        with open(os.path.join(td, "large.py"), "w", encoding="utf-8") as f:
            lines = [f"# Line {i}" for i in range(100)]
            lines.insert(50, "def target():\n    return False")
            f.write("\n".join(lines) + "\n")
            
        # File 3: Another file for multi-file patch
        with open(os.path.join(td, "other.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\ny = 2\n")
            
        # Symlink for escape test (if supported)
        try:
            out_dir = tempfile.mkdtemp()
            os.symlink(out_dir, os.path.join(td, "symlink_dir"))
        except:
            pass # Symlinks might require admin on Windows

        yield td

def test_simple_function_change(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/simple.py
+++ b/simple.py
@@ -1,2 +1,2 @@
 def hello():
-    print('world')
+    print('LITE')
"""
    res = engine.apply_patch(diff)
    assert res["success"] is True
    with open(os.path.join(temp_repo, "simple.py"), "r") as f:
        assert "print('LITE')" in f.read()

def test_targeted_change_large_file(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/large.py
+++ b/large.py
@@ -49,3 +49,3 @@
 # Line 49
 def target():
-    return False
+    return True
 # Line 50
"""
    res = engine.apply_patch(diff)
    assert res["success"] is True
    with open(os.path.join(temp_repo, "large.py"), "r") as f:
        content = f.read()
        assert "return True" in content
        assert "# Line 0" in content # Unrelated lines preserved
        
def test_multi_file_patch(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/simple.py
+++ b/simple.py
@@ -1,2 +1,2 @@
 def hello():
-    print('world')
+    print('multi')
--- a/other.py
+++ b/other.py
@@ -1,2 +1,2 @@
-x = 1
+x = 10
 y = 2
"""
    res = engine.apply_patch(diff)
    assert res["success"] is True
    assert len(res["modified_files"]) == 2
    
def test_new_file_creation(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/new_file.py
+++ b/new_file.py
@@ -0,0 +1,2 @@
+def fresh():
+    pass
"""
    res = engine.apply_patch(diff)
    assert res["success"] is True
    assert os.path.exists(os.path.join(temp_repo, "new_file.py"))

def test_malformed_diff_rejection(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = "--- a/simple.py\n+++ b/simple.py\n@@ invalid @@\n+print('bad')"
    res = engine.apply_patch(diff)
    assert res["success"] is False

def test_stale_source_mismatch(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/simple.py
+++ b/simple.py
@@ -1,2 +1,2 @@
 def missing():
-    pass
+    print('LITE')
"""
    res = engine.apply_patch(diff)
    assert res["success"] is False
    assert "Context mismatch" in str(res["errors"])

def test_path_traversal_rejection(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/../out.py
+++ b/../out.py
@@ -0,0 +1,1 @@
+bad
"""
    res = engine.apply_patch(diff)
    assert res["success"] is False
    assert "SecurityViolation" in str(res["errors"])

def test_symlink_escape_rejection(temp_repo):
    engine = PatchEngine(temp_repo)
    if not os.path.exists(os.path.join(temp_repo, "symlink_dir")):
        return # Skip if symlinks not supported
    diff = """--- a/symlink_dir/out.py
+++ b/symlink_dir/out.py
@@ -0,0 +1,1 @@
+bad
"""
    res = engine.apply_patch(diff)
    assert res["success"] is False

def test_multiple_hunks_one_file(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/large.py
+++ b/large.py
@@ -1,2 +1,2 @@
-# Line 0
+# Line ZERO
 # Line 1
@@ -49,3 +49,3 @@
 # Line 49
 def target():
-    return False
+    return True
 # Line 50
"""
    res = engine.apply_patch(diff)
    assert res["success"] is True
    with open(os.path.join(temp_repo, "large.py"), "r") as f:
        content = f.read()
        assert "# Line ZERO" in content
        assert "return True" in content

def test_dry_run(temp_repo):
    engine = PatchEngine(temp_repo)
    diff = """--- a/simple.py
+++ b/simple.py
@@ -1,2 +1,2 @@
 def hello():
-    print('world')
+    print('LITE')
"""
    res = engine.apply_patch(diff, dry_run=True)
    assert res["success"] is True
    assert len(res["modified_files"]) == 1
    # Ensure not actually modified
    with open(os.path.join(temp_repo, "simple.py"), "r") as f:
        assert "print('world')" in f.read()

def test_rejected_patch_leaves_files_unmodified(temp_repo):
    engine = PatchEngine(temp_repo)
    # Valid hunk 1, invalid hunk 2
    diff = """--- a/simple.py
+++ b/simple.py
@@ -1,2 +1,2 @@
 def hello():
-    print('world')
+    print('LITE')
--- a/other.py
+++ b/other.py
@@ -1,2 +1,2 @@
-z = 99
+z = 100
"""
    res = engine.apply_patch(diff)
    assert res["success"] is False
    # Ensure simple.py wasn't partially modified
    with open(os.path.join(temp_repo, "simple.py"), "r") as f:
        assert "print('world')" in f.read()

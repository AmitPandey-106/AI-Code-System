"""
package_colab.py
================
Packages the LITE-Coder Q1 Evaluation Suite into a clean, self-contained zip file
ready for upload and one-shot execution on Google Colab with GPU acceleration.
"""

import os
import zipfile
import sys

def package_project(zip_filename="litecoder_q1_eval.zip"):
    print(f"[*] Packaging LITE-Coder Q1 Benchmark Suite into '{zip_filename}'...")

    # Include patterns and directories
    include_dirs = ["app", "benchmarks"]
    include_files = ["colab_runner.py"]

    # Files / patterns to exclude
    exclude_extensions = {".pyc", ".pyo", ".pyd", ".git", ".log"}
    exclude_dirs = {"__pycache__", ".pytest_cache", ".git", "venv", "models", "package_output"}

    total_files = 0
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add root files
        for f in include_files:
            if os.path.exists(f):
                zipf.write(f, f)
                total_files += 1
                print(f"  + Added: {f}")

        # Add directories
        for d in include_dirs:
            if not os.path.exists(d):
                continue
            for root, dirs, files in os.walk(d):
                # Prune excluded dirs in-place
                dirs[:] = [sub for sub in dirs if sub not in exclude_dirs]

                for file in files:
                    ext = os.path.splitext(file)[1]
                    if ext in exclude_extensions:
                        continue
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ".")
                    zipf.write(full_path, rel_path)
                    total_files += 1

    size_mb = round(os.path.getsize(zip_filename) / (1024 * 1024), 2)
    print(f"\n[+] Successfully created '{zip_filename}' ({total_files} files, {size_mb} MB)!")
    print(f"[+] Ready to upload to Google Colab.")

if __name__ == "__main__":
    package_project()

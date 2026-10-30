#!/bin/bash
echo "Installing required dependencies for LITE-CODER Colab experiments..."
# Historical environment evidence provided:
pip install torch==2.11.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install transformers==5.16.1
pip install sentence-transformers==5.7.0
pip install faiss-cpu==1.15.1
pip install peft==0.20.0
pip install accelerate>=0.26.0
pip install datasets>=2.14.0 filelock>=3.12.0 pydantic>=2.0.0 fastapi>=0.100.0 psutil>=5.9.0
echo "Setup complete."

"""
run_frontend.py
===============
Convenience runner for the LITE-Coder Neural Studio Frontend.
Zero changes to core research code or model weights.
"""
import sys
import os

if __name__ == "__main__":
    from frontend.server import start_server, DEFAULT_PORT, DEFAULT_BACKEND
    import argparse
    
    parser = argparse.ArgumentParser(description="Launch LITE-Coder Studio Frontend")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run the UI server on (default: 8500)")
    parser.add_argument("--backend", type=str, default=DEFAULT_BACKEND, help="Backend URL (default: http://127.0.0.1:8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()
    
    start_server(port=args.port, backend=args.backend, open_browser=not args.no_browser)

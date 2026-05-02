#!/usr/bin/env python3
"""
Quick setup script for SINTEL Browser Console
Installs dependencies and starts the server.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd: str, description: str = ""):
    """Run a shell command"""
    print(f"\n{'='*60}")
    if description:
        print(f"  {description}")
    print(f"{'='*60}")
    print(f"$ {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0

def main():
    print("\n" + "="*60)
    print("  SINTEL Browser Console - Setup")
    print("="*60)
    
    # Get project root
    project_root = Path(__file__).parent
    print(f"\nProject root: {project_root}")
    
    # Step 1: Install dependencies
    print("\n[1/3] Installing dependencies...")
    requirements_file = project_root / "requirements-console.txt"
    
    if requirements_file.exists():
        success = run_command(
            f"{sys.executable} -m pip install -r requirements-console.txt",
            "Installing FastAPI, Uvicorn, and dependencies"
        )
        
        if not success:
            print("[ERROR] Failed to install dependencies")
            return 1
    else:
        print(f"[WARN] {requirements_file} not found")
        print("Installing manually...")
        run_command(
            f"{sys.executable} -m pip install fastapi uvicorn aiofiles",
            "Installing FastAPI, Uvicorn, and dependencies (manual)"
        )
    
    # Step 2: Verify imports
    print("\n[2/3] Verifying imports...")
    try:
        import fastapi
        import uvicorn
        import aiofiles
        print("[OK] FastAPI:", fastapi.__version__)
        print("[OK] Uvicorn:", uvicorn.__version__)
        print("[OK] aiofiles: available")
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return 1
    
    # Step 3: Start server
    print("\n[3/3] Starting SINTEL Browser Console...")
    print("\n" + "="*60)
    print("  Server Information")
    print("="*60)
    print("\nURL: http://localhost:8000")
    print("REST API: http://localhost:8000/api/")
    print("WebSocket: ws://localhost:8000/ws")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    os.chdir(project_root)
    run_command(
        f"{sys.executable} browser_console_server.py",
        "Starting server"
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

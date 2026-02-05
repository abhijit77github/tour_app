"""
Tour App Backend Entry Point

Run with: 
  From backend directory: python run.py
  Or: uvicorn main:app --reload
"""
import sys
from pathlib import Path

# Add parent directory to Python path so we can import backend package
backend_dir = Path(__file__).parent
parent_dir = backend_dir.parent
sys.path.insert(0, str(parent_dir))

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    from backend.config import settings
    
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

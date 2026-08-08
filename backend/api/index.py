import sys
import os

# Añadir posibles rutas de directorio para Vercel Serverless
curr_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(curr_dir)
root_dir = os.path.dirname(parent_dir)

for path in [curr_dir, parent_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from app.main import app
except ImportError:
    from backend.app.main import app

import sys
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(curr_dir)
grandparent_dir = os.path.dirname(parent_dir)
root_dir = os.path.dirname(grandparent_dir)

for path in [curr_dir, parent_dir, grandparent_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from mangum import Mangum

try:
    from app.main import app
except ImportError:
    from backend.app.main import app

handler = Mangum(app, lifespan="off")

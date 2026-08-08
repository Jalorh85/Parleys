import sys
import os

# Añadir el directorio raíz del backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mangum import Mangum
from app.main import app

# Handler para Netlify Functions / AWS Lambda
handler = Mangum(app, lifespan="off")

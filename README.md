<div align="center">

# ⚡ PARLEYS AI & ALOR 2026 ⚡
### *Motor Inteligente de Pronósticos Deportivos y Análisis de Apuestas (+EV)*

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.5-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-Ensemble-22C55E?style=for-the-badge)
![Deploy](https://img.shields.io/badge/Deploy-Vercel%20%7C%20Netlify%20%7C%20Railway-00F2FE?style=for-the-badge)

<p align="center">
  <b>Plataforma Full-Stack de Machine Learning Meta-Ensemble para la predicción de eventos deportivos (Liga MX, Leagues Cup 2026, NBA, MLB, WNBA, KBO) y optimización de apuestas combinadas (Parleys) con detección de valor +EV en tiempo real.</b>
</p>

</div>

---

## 📋 Contenido

- [🌟 Aspectos Destacados](#-aspectos-destacados)
- [🤖 Arquitectura del Meta-Ensemble de IA](#-arquitectura-del-meta-ensemble-de-ia)
- [⚽ Ligas Soportadas y Datos en Vivo (ESPN API & TheSportsDB API)](#-ligas-soportadas-y-datos-en-vivo-espn-api--thesportsdb-api)
- [🛠️ Tecnologías Utilizadas](#️-tecnologías-utilizadas)
- [📂 Estructura del Proyecto](#-estructura-del-proyecto)
- [🚀 Instalación y Ejecución Local](#-instalación-y-ejecución-local)
- [🌐 Despliegue en la Nube (Vercel, Netlify, Railway)](#-despliegue-en-la-nube-vercel-netlify-railway)
- [📡 API Endpoints](#-api-endpoints)
- [👤 Autor](#-autor)

---

## 🌟 Aspectos Destacados

- 🧠 **Meta-Ensemble Ponderado:** Combina 5 modelos de IA avanzados para maximizar la precisión de predicción en probabilidad de victoria, hándicap, totales Over/Under y córners.
- 📈 **Detección de Apuestas con Valor (+EV):** Algoritmo automatizado que calcula el *Expected Value* comparando probabilidades de IA contra las cuotas implícitas de las casas de apuestas.
- 🌐 **Integración Dual (ESPN API + TheSportsDB API):** Descarga partidos en vivo, resultados históricos, horarios UTC y logotipos oficiales de los equipos para todas las ligas.
- 🇲🇽 **Soporte Especializado para Fútbol (Liga MX y Leagues Cup 2026):** Incluye modelo dedicado de regresión para predicción de **Córners Totales** en partidos de fútbol.
- 🧮 **Calculadora e Creador de Parleys:** Genera apuestas combinadas personalizadas calculando cuotas compuestas, rendimiento estimado y evaluación de riesgo.
- 📊 **Backtester & Batalla de Modelos:** Módulo visual para comparar el rendimiento histórico de cada modelo individual (SVM vs Red Neuronal vs Random Forest vs XGBoost vs LightGBM).
- 🎨 **Diseño Moderno & Glassmorphism:** Interfaz futurista optimizada en modo oscuro con respuestas dinámicas de estado e iconos interactivos.

---

## 🤖 Arquitectura del Meta-Ensemble de IA

El motor predictivo no depende de una sola métrica, sino de una arquitectura de **Meta-Ensemble Ponderado**:

```mermaid
graph TD
    A[Datos del Partido + ESPN API & TheSportsDB] --> B[Feature Engineering Engine]
    B --> C[SVM Classifier & Regressor]
    B --> D[Multi-Layer Perceptron Neural Net]
    B --> E[Random Forest Ensemble]
    B --> F[XGBoost Gradient Boosting]
    B --> G[LightGBM Gradient Boosting]
    
    C -->|Peso: 15%| H[Meta-Ensemble Engine]
    D -->|Peso: 20%| H
    E -->|Peso: 15%| H
    F -->|Peso: 25%| H
    G -->|Peso: 25%| H
    
    H --> I[Predicción Final: Ganador, Margin, Total & Córners]
    H --> J[Detección de Valor +EV]
```

### Modelos Integrados y Pesos:
| Modelo | Algoritmo | Propósito Principal | Peso Ensemble |
| :--- | :--- | :--- | :---: |
| **XGBoost** | Extreme Gradient Boosting | Margen y Spread | `25%` |
| **LightGBM** | Light Gradient Boosting Machine | Totales Over/Under | `25%` |
| **Neural Network** | Multi-Layer Perceptron (MLP) | Probabilidad de victoria | `20%` |
| **SVM** | Support Vector Machines (Kernel RBF) | Clasificación de límites rígidos | `15%` |
| **Random Forest** | Bagging Ensemble Trees & Corners Regressor | Control de varianza y Córners | `15%` |

---

## ⚽ Ligas Soportadas y Datos en Vivo (ESPN API & TheSportsDB API)

El sistema procesa información en tiempo real combinando las APIs de **ESPN** y **TheSportsDB**:

| Liga | Deporte | Cobertura / APIs | Targets Predichos |
| :--- | :--- | :--- | :--- |
| 🇲🇽 **Liga MX (`MX`)** | Fútbol | ESPN API + TheSportsDB | Ganador, Margen, Goles Totales, **Córners Totales** |
| 🏆 **Leagues Cup 2026 (`LCUP`)** | Fútbol | ESPN API + TheSportsDB | Ganador, Margen, Goles Totales |
| 🏀 **NBA (`NBA`)** | Baloncesto | ESPN API + TheSportsDB | Ganador, Hándicap/Spread, Puntos Totales |
| ⚾ **MLB (`MLB`)** | Béisbol | ESPN API + TheSportsDB (30 Equipos) | Ganador, Runline, Carrera Totales, ERA Pitcher |
| ⛹️‍♀️ **WNBA (`WNBA`)** | Baloncesto | ESPN API (Incluye expansión 2026) | Ganador, Hándicap/Spread, Puntos Totales |
| ⚾ **KBO (`KBO`)** | Béisbol | TheSportsDB + Fallback Simulado | Ganador, Runline, Carrera Totales |

---

## 🛠️ Tecnologías Utilizadas

### Backend (Python / FastAPI)
- **FastAPI 0.111** — Framework web asíncrono de alto rendimiento.
- **Scikit-Learn 1.5** — Preprocesamiento, escalado y modelos SVM / Random Forest / MLP.
- **Pandas & NumPy** — Manipulación matricial y feature engineering de vectores deportivos.
- **HTTPX** — Cliente HTTP asíncrono para consumo de **ESPN API** y **TheSportsDB API**.
- **Mangum** — Adaptador ASGI a AWS Lambda / Netlify Serverless Functions.
- **Uvicorn** — Servidor ASGI ultrarrápido para entorno local.

### Frontend (React / Vite)
- **React 19** — Interfaz declarativa basada en componentes funcionales y Hooks.
- **Vite 6** — Empaquetador y entorno de desarrollo ultra veloz.
- **Lucide React** — Colección de iconos vectoriales modernos.
- **Vanilla CSS3** — Sistema de diseño personalizado con Glassmorphism y temas Neón.

---

## 📂 Estructura del Proyecto

```text
parleys/
├── 📄 README.md                    # Documentación principal del proyecto
├── 📄 netlify.toml                # Configuración de despliegue Frontend en Netlify
├── 📄 deploy.bat                  # Script automatizado de despliegue local/cloud
├── 📄 run_app.bat                 # Lanzador rápido de servidores local (Backend + Frontend)
│
├── 📂 backend/                    # Core del Servidor API y Motor ML
│   ├── 📄 requirements.txt        # Dependencias de Python para Serverless/Cloud
│   ├── 📄 vercel.json             # Configuración Serverless para Vercel (@vercel/python)
│   ├── 📄 netlify.toml            # Configuración Serverless para Netlify Functions
│   ├── 📂 api/
│   │   └── 📄 index.py            # Punto de entrada Vercel Serverless Function
│   ├── 📂 netlify/
│   │   └── 📂 functions/
│   │       └── 📄 api.py          # Handler Mangum para Netlify Functions
│   └── 📂 app/
│       ├── 📄 main.py             # Aplicación principal FastAPI & Endpoints
│       └── 📂 ml/
│           ├── 📄 sports_api.py   # Conector ESPN API + TheSportsDB API + mapeo de logos
│           ├── 📄 kbo_thesportsdb.py # Módulo especializado para datos TheSportsDB
│           ├── 📄 ensemble_model.py # Meta-Ensemble ML (XGB, LGBM, SVM, NN, RF)
│           ├── 📄 feature_engineering.py # Extracción de vectores de características
│           ├── 📄 data_generator.py # Perfiles de equipos y fallback simulado
│           ├── 📄 backtester.py   # Motor de simulación histórica
│           └── 📄 svm_model.py    # Sub-modelo SVM
│
└── 📂 frontend/                   # Interfaz de Usuario React + Vite
    ├── 📄 package.json            # Dependencias del Frontend
    ├── 📄 vite.config.js          # Configuración del empaquetador Vite
    ├── 📄 vercel.json             # Configuración SPA Routing para Vercel
    ├── 📄 .env.production         # URL base para conectar con el backend en la nube
    └── 📂 src/
        ├── 📄 App.jsx             # Contenedor principal y enrutado de pestañas
        ├── 📄 index.css           # Tokens de diseño, gradientes y animaciones
        ├── 📂 components/
        │   ├── 📄 Header.jsx      # Selector de liga (MX, LCUP, NBA, MLB, WNBA, KBO)
        │   ├── 📄 DailyFixtures.jsx # Tarjetas de partidos en vivo y cuotas +EV
        │   ├── 📄 TeamIcon.jsx    # Renderizador inteligente de logos ESPN / TheSportsDB
        │   ├── 📄 MatchPredictor.jsx # Simulador de partidos 1v1 personalizado
        │   ├── 📄 ParlayBuilder.jsx # Creador y calculadora de apuestas combinadas
        │   ├── 📄 ModelComparison.jsx # Comparador de precisión entre modelos
        │   ├── 📄 BacktestSimulator.jsx # Rendimiento histórico y simulación ROI
        │   └── 📄 ModelTrainerUI.jsx # Interfaz para re-entrenar modelos
        └── 📂 services/
            └── 📄 api.js          # Cliente HTTP para comunicación con FastAPI
```

---

## 🚀 Instalación y Ejecución Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/Jalorh85/Parleys.git
cd Parleys
```

### 2. Iniciar Backend y Frontend automáticamente (Windows)
Ejecuta el script incluido en la raíz:
```cmd
run_app.bat
```

### 3. Iniciar manualmente (Opción Alternativa)

#### Backend:
```bash
cd backend
py -3 -m venv .venv
# En Windows activar: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

> 🌐 Abrir en el navegador: `http://localhost:5173`

---

## 🌐 Despliegue en la Nube (Vercel, Netlify, Railway)

El proyecto está 100% preparado con archivos de configuración serverless independientes:

### 🔺 Despliegue en Vercel
- **Backend:** Conecta tu repo en Vercel y establece el *Root Directory* en `backend`. Utilizará [`backend/vercel.json`](file:///C:/Users/JuaN/Desktop/parleys/backend/vercel.json) automáticamente.
- **Frontend:** Crea un proyecto en Vercel estableciendo el *Root Directory* en `frontend`.

### 🌐 Despliegue en Netlify
- **Backend:** Importa el proyecto en Netlify configurando el *Base Directory* en `backend`. Procesará [`backend/netlify.toml`](file:///C:/Users/JuaN/Desktop/parleys/backend/netlify.toml) y [`backend/netlify/functions/api.py`](file:///C:/Users/JuaN/Desktop/parleys/backend/netlify/functions/api.py).
- **Frontend:** El archivo raíz [`netlify.toml`](file:///C:/Users/JuaN/Desktop/parleys/netlify.toml) compilará automáticamente la app desde la carpeta `frontend`.

### 🚂 Despliegue en Railway
- El directorio `backend` incluye `Procfile` y `railway.toml` para despliegue en contenedor Docker continuo.

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
| :---: | :--- | :--- |
| `GET` | `/api/leagues` | Obtiene la lista de ligas soportadas (`MX`, `LCUP`, `NBA`, `MLB`, `WNBA`, `KBO`) |
| `GET` | `/api/fixtures?league=MX&date=YYYY-MM-DD` | Devuelve los partidos del día con predicciones del Meta-Ensemble (incluye córners para Liga MX) |
| `POST` | `/api/predict` | Realiza una predicción personalizada 1v1 entre dos equipos |
| `GET` | `/api/backtest?league=MLB` | Ejecuta la simulación de rendimiento histórico (+EV ROI) |
| `POST` | `/api/train?league=WNBA` | Re-entrena el Meta-Ensemble con datos actualizados de ESPN / TheSportsDB |

---

## 👤 Autor

Desarrollado con pasión por los datos y el deporte:

**MSC. Juan Antonio Alor Hernández**  
*Especialista en IA & Arquitectura de Software*  
© 2026 Todos los derechos reservados.

---
<div align="center">
  <sub>Construido con ❤️ usando FastAPI, React 19, ESPN API, TheSportsDB API y Machine Learning.</sub>
</div>

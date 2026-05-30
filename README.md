# 🔥 Wildfire Risk Assessment Framework

A full-stack platform for satellite-based wildfire risk prediction using a Variational Autoencoder (VAE) trained on 7-band GeoTIFF imagery.

## Architecture

```
wildfire-risk-framework/
├── backend/          — FastAPI/Flask REST API + VAE inference
├── frontend/         — React/Vue dashboard + risk map visualisation
└── docker-compose.yml
```

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI / Flask (Python) |
| Frontend | React / Vue |
| ML Model | PyTorch VAE (court term) / ConvLSTM_GCN_Transformer(long term) |
| Database | PostgreSQL + PostGIS + mongo DB |
| Container | Docker + Docker Compose |

## Quick start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### Run with Docker

```bash
git clone https://github.com/ghaithsm10/wildfire-risk-framework.git
cd wildfire-risk-framework
cp backend/.env.example backend/.env       # configure your env vars
docker-compose up --build
```

Services:
- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API docs → http://localhost:8000/docs

### Run locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Model — VAE Fire Risk (7 bands)

The VAE takes 7-band GeoTIFF images as input:

| Band | Description |
|------|-------------|
| NDVI | Vegetation density |
| Humidity | Atmospheric / soil humidity |
| Temperature | Surface temperature |
| Altitude | Digital elevation |
| Slope | Terrain slope |
| Aspect | Solar exposure |
| Land Cover | Vegetation type |


## API endpoints (backend)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/predict` | Upload GeoTIFF → get risk map |
| `GET` | `/predictions/{id}` | Retrieve a past prediction |
| `GET` | `/predictions` | List all predictions |

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
MODEL_PATH=./model/outputs/best_model_checkpoint.pth
DATABASE_URL=postgresql://wildfire_user:wildfire_pass@localhost:5432/wildfire_db
SECRET_KEY=your-secret-key
```

## Project structure

```
backend/
├── main.py           — FastAPI app entry point
├── routers/          — API routes
├── services/         — Business logic + model inference
├── models/           — DB models (SQLAlchemy)
├── schemas/          — Pydantic schemas
├── requirements.txt
└── Dockerfile

frontend/
├── src/
│   ├── components/   — UI components (map, charts, forms)
│   ├── views/        — Pages
│   ├── stores/       — State management
│   └── api/          — API client
├── package.json
└── Dockerfile

```

## License

MIT

# AeroPulse — Air Quality Analysis & Prediction

A production-ready full-stack platform for analysing air quality datasets, comparing ML models, and predicting AQI.

## Features
- CSV upload with drag-and-drop + auto schema detection
- Exploratory data analysis: histograms, correlation, monthly/yearly trends, radar
- Data cleaning + feature engineering reports
- Train 5 ML regressors (Linear, Decision Tree, Random Forest, Gradient Boosting, XGBoost) with metrics comparison
- Auto best-model selection, one-click prediction with AQI classification + health advice
- 7-day AQI forecast, city comparison
- Built-in dataset insights with no external AI service requirement
- PDF and CSV report exports
- Admin dashboard (users, datasets, analytics)
- Dark / light mode toggle

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Recharts, Framer Motion, Phosphor Icons
- **Backend**: FastAPI, Motor (async MongoDB), scikit-learn, XGBoost, reportlab
- **Auth**: JWT httpOnly cookies + bcrypt
- **Insights**: Deterministic local dataset summaries

## Installation

### Backend
```bash
cd backend
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
yarn install
```

## Environment Variables

### `backend/.env`
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
JWT_SECRET=<64-char-hex>
ADMIN_EMAIL=admin@aqi.io
ADMIN_PASSWORD=admin123
FRONTEND_URL=http://localhost:3000
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### `frontend/.env`
```
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_OPENWEATHER_API_KEY=<openweather-api-key>
```

## Running

### Backend
```bash
cd backend
.\run_backend.ps1
```

On Windows, use the backend virtual environment. Running plain `python server.py` with the system Python can fail if ML packages such as `scikit-learn` are not installed globally.

### Frontend
```bash
cd frontend && yarn start
```

## Folder Structure
```
/app
├── backend/
│   ├── server.py              # FastAPI app with all routes
│   ├── auth.py                # JWT + bcrypt helpers
│   ├── aqi_utils.py           # AQI classification
│   ├── eda_service.py         # EDA computations
│   ├── ml_service.py          # ML training & prediction
│   ├── reports_service.py     # PDF generation
│   ├── insights_service.py    # LLM insights
│   ├── sample_data.py         # synthetic Indian AQI dataset
│   ├── uploads/               # user datasets (persisted CSV)
│   └── models/                # trained model pickles
└── frontend/
    └── src/
        ├── pages/             # Landing, Login, Dashboard, Upload, DatasetDetail, Train, Predict, Reports, Admin
        ├── components/        # AppLayout, AQIBadge, AQIGauge, ProtectedRoute, Page
        ├── context/           # AuthContext, ThemeContext
        └── lib/               # api.js, aqi.js
```

## Default Credentials
- Admin: `admin@aqi.io` / `admin123` (auto-seeded on startup)

## API Endpoints (selected)
- `POST /api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `GET /api/auth/me`, `POST /api/auth/refresh`
- `POST /api/datasets/upload`, `/api/datasets/seed-sample`
- `GET /api/datasets`, `GET /api/datasets/{id}`, `DELETE /api/datasets/{id}`
- `GET /api/datasets/{id}/eda`, `POST /api/datasets/{id}/clean`
- `POST /api/datasets/{id}/train`, `GET /api/datasets/{id}/models`
- `POST /api/predict`, `GET /api/history`, `POST /api/forecast/{dataset_id}`
- `POST /api/datasets/{id}/insights`
- `GET /api/reports/prediction/{id}`, `GET /api/reports/model/{dataset_id}`
- `GET /api/admin/users`, `/api/admin/analytics`, `/api/admin/datasets`

## Deployment
- Frontend: Vercel / Netlify
- Backend: Render / Railway / Fly.io (any container host)
- Database: MongoDB Atlas

## Future Improvements
- Real-time OpenAQ live widget
- Interactive Leaflet map for location comparison
- City-comparison dedicated page
- Custom AQI scales (Indian CPCB alongside US EPA)
- Model download / import

## License
MIT

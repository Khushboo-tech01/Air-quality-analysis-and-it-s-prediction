# AeroPulse — Air Quality Analysis & Prediction

## Original Problem Statement
Build a complete production-ready web application called "Air Quality Analysis & Prediction" that lets users analyze historical air quality datasets, visualize pollution trends, predict AQI, compare ML models, download reports, and provides an admin dashboard.

## Architecture (implemented)
- **Backend**: FastAPI + MongoDB (Motor) + scikit-learn + XGBoost + reportlab
- **Frontend**: React 19 (CRA) + TailwindCSS + Shadcn UI + Recharts + Framer Motion + Phosphor Icons + React-Dropzone + Leaflet
- **Auth**: JWT httpOnly cookies + bcrypt + brute-force lockout + admin seeding
- **AI Insights**: Claude Sonnet 4.5 via Emergent Universal Key (emergentintegrations)

## User Personas
1. **Data Science Student / Intern** — Uploads AQI CSV, needs EDA + model comparison + PDF report for submission
2. **Environmental Analyst** — Compares cities, downloads insights, needs AI-generated summaries
3. **Admin** — Manages users, datasets, and monitors platform analytics

## Core Requirements (Static)
- CSV upload with schema auto-detection (date, location, pollutant columns)
- Exploratory data analysis: histograms, correlations, monthly/yearly trends, AQI distribution
- Data cleaning (dupes, nulls, outliers) & feature engineering (date parts, lag, rolling)
- Train 5 regressors (Linear, Decision Tree, Random Forest, Gradient Boosting, XGBoost) and auto-select best on R²
- Prediction form (PM2.5, PM10, NO2, SO2, CO, O3, Temperature, Humidity, Wind, Pressure) with AQI classification + health advice
- 7-day AQI forecast
- City comparison
- AI-powered natural-language insights (Claude Sonnet 4.5)
- PDF & CSV reports (predictions, model metrics, raw dataset)
- Admin dashboard (users, datasets, predictions, analytics)
- Dark/light mode toggle

## Implementation Log
### 2026-07-08 — MVP
- Backend: 7 modules (server, auth, aqi_utils, eda_service, ml_service, reports_service, insights_service, sample_data)
- Frontend: Landing + auth (login/register/forgot) + protected app shell with sidebar
- Pages: Dashboard, Upload (dropzone), DatasetDetail (6-tab: preview/eda/correlation/trends/cleaning/features), Train, Predict (gauge), Reports, Admin
- Design: dark-first, Space Grotesk display + Inter body + JetBrains Mono data, Vercel/Linear-style grid backgrounds, glassmorphism nav, semantic AQI colour tokens

## What's Implemented
- ✅ JWT cookie auth, bcrypt hashing, admin seed, brute-force lockout
- ✅ CSV upload with progress, sample-dataset seeding
- ✅ EDA: histograms, correlation heatmap, monthly/yearly trends, radar, pie, location bars
- ✅ Data cleaning report + feature engineering report
- ✅ ML training of 5 regressors with RMSE/MAE/R²/CV/timing metrics
- ✅ Best model auto-selection + saved artifact (pickle)
- ✅ Prediction API with AQI classification + health advice + semi-circular gauge
- ✅ 7-day forecast
- ✅ AI Insights via Claude Sonnet 4.5
- ✅ PDF (prediction, model metrics) + CSV report exports
- ✅ Admin: users/datasets/predictions CRUD + analytics
- ✅ Landing page, testimonials, AQI scale reference

## Prioritized Backlog
### P0 (post-MVP polish)
- City-comparison UI page (backend endpoint exists)
- Interactive Leaflet map on visualization dashboard
- Reset-password confirmation UI (backend exists)

### P1
- Real-time AQI widget (fetch OpenAQ live)
- Weather integration on prediction (auto-fetch temp/humidity by city)
- Prediction favourites / bookmarks
- Notification bell for AI-generated alerts

### P2
- Multi-user dataset sharing
- Model export (.pkl download)
- Custom AQI scale (Indian CPCB alongside US EPA)

## Test Credentials
See `/app/memory/test_credentials.md`

## Next Action Items
1. Testing agent regression pass
2. UI polish: City-comparison page + Leaflet map
3. Deployment health check

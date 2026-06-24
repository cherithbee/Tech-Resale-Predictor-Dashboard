# Tech Resale Predictor & Valuation Engine

A full-stack predictive analytics dashboard that forecasts the depreciation curves of consumer tech assets using multi-variable regression modeling. This application features a containerized relational database, an asynchronous REST API backend, and a responsive frontend data visualization dashboard localized for the Thai market (THB).

## 🛠️ System Architecture

- **Frontend:** Single-page dashboard engineered with HTML5, Tailwind CSS, and Chart.js for interactive timeline graphs.
- **Backend API:** Built with FastAPI (Python) implementing asynchronous endpoints to handle database queries and execute machine learning models on demand.
- **Machine Learning Engine:** Powered by `scikit-learn` and `pandas` utilizing a **Degree 2 Polynomial Regression** model to calculate non-linear asset depreciation curves.
- **Database Layer:** PostgreSQL instance containerized via Docker to store device specifications and historical marketplace logs.

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Desktop
- Python 3.10+

### 1. Database Setup
Spin up the containerized PostgreSQL instance and let it initialize the schema:
```bash
docker-compose up -d
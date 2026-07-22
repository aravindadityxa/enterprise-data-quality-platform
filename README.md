# Enterprise Data Quality Platform

A full-stack data quality platform for validating, cleaning, analyzing, and forecasting datasets. Built with FastAPI, SQLAlchemy, Pandas, and Scikit-learn, the platform provides automated data quality assessment, exploratory analytics, anomaly detection, and machine learning–based forecasting through a modern REST API and interactive dashboard.

---

## Features

### Dataset Management
- Upload CSV, Excel, and JSON datasets
- Automatic schema and data type detection
- Dataset profiling and metadata extraction

### Data Quality Validation
- Completeness analysis
- Uniqueness checks
- Consistency validation
- Accuracy assessment
- Validity verification
- Overall quality score generation

### Data Cleaning
- Missing value imputation
- Duplicate removal
- Data normalization
- Standardization
- Outlier handling

### Analytics
- Descriptive statistics
- Correlation analysis
- Distribution analysis
- KPI generation
- Automated insights

### SQL Analytics
- 50+ predefined SQL queries
- Joins
- Common Table Expressions (CTEs)
- Window Functions
- Aggregate reports

### Machine Learning
- Isolation Forest anomaly detection
- Z-Score and IQR outlier detection
- Ensemble anomaly scoring
- Linear Regression forecasting
- Random Forest forecasting
- Exponential Smoothing

### Platform Features
- JWT Authentication
- Role-Based Access Control
- RESTful API
- Interactive Dashboard
- Swagger/OpenAPI Documentation
- Automated Testing

---

# Technology Stack

| Category | Technologies |
|----------|--------------|
| Backend | FastAPI, Uvicorn |
| Database | SQLAlchemy, SQLite, PostgreSQL |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn, SciPy, Statsmodels |
| Authentication | JWT, Passlib, Bcrypt |
| Frontend | HTML, Bootstrap 5, JavaScript, Plotly.js |
| Testing | Pytest, pytest-cov |

---

# Project Structure

```
enterprise-data-quality-platform/
│
├── backend/
│   ├── api/
│   ├── analytics/
│   ├── anomaly_detection/
│   ├── database/
│   ├── forecasting/
│   ├── services/
│   ├── validation/
│   └── utils/
│
├── frontend/
│   ├── static/
│   └── index.html
│
├── tests/
│
├── requirements.txt
├── README.md
└── Dockerfile
```

---

# Getting Started

## Prerequisites

- Python 3.12+
- pip

## Clone Repository

```bash
git clone https://github.com/<username>/enterprise-data-quality-platform.git

cd enterprise-data-quality-platform
```

## Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Configure Environment

Create a `.env` file.

```env
DATABASE_URL=sqlite:///./database.db
SECRET_KEY=your-secret-key
ENVIRONMENT=development
MAX_UPLOAD_SIZE_MB=100
```

## Initialize Database

```bash
python -c "from backend.database.models import Base; from backend.database.engine import engine; Base.metadata.create_all(bind=engine)"
```

## Run the Application

```bash
uvicorn backend.main:app --reload
```

---

# Access the Application

| Service | URL |
|----------|-----|
| Dashboard | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

# API Modules

- Authentication
- Dataset Management
- Data Validation
- Data Cleaning
- Analytics
- SQL Queries
- Anomaly Detection
- Forecasting
- Reports

Complete API documentation is available through **Swagger UI**.

---

# Testing

Run all tests

```bash
pytest
```

Run with coverage

```bash
pytest --cov=backend --cov-report=html
```

---

# Code Quality

```bash
black backend tests

isort backend tests

flake8 backend tests

mypy backend
```

---

# Security

- JWT Authentication
- Password hashing with Bcrypt
- Role-Based Access Control
- SQLAlchemy ORM parameterized queries
- Environment variable configuration
- Request validation using Pydantic

---

# Performance

- Optimized Pandas operations
- Connection pooling
- Pagination support
- GZip compression
- Efficient SQL queries

---

# Deployment

## Docker

```bash
docker build -t enterprise-data-quality-platform .

docker run -p 8000:8000 enterprise-data-quality-platform
```

## Production Recommendations

- PostgreSQL
- HTTPS
- Strong secret keys
- Reverse proxy (Nginx)
- Process manager (Gunicorn/Uvicorn Workers)

---

# Future Enhancements

- Real-time data streaming
- Apache Kafka integration
- Apache Airflow workflows
- Scheduled data quality monitoring
- Cloud object storage support
- Kubernetes deployment

---

# Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

# License

This project is licensed under the MIT License.

---

## Author

**Aravind Adityaa**

B.E. Computer Science and Engineering

R.M.D. Engineering College
# Enterprise Data Quality Platform

A production-grade platform for data validation, cleaning, analysis, and forecasting. Built with FastAPI, Pandas, and Scikit-learn.

## Features

### Core Capabilities
- **Dataset Management** - Upload and profile CSV, Excel, JSON files with automatic type detection
- **Data Validation** - 5-dimensional quality scoring (completeness, uniqueness, consistency, validity, accuracy)
- **Data Cleaning** - Automated deduplication, imputation, normalization, and standardization
- **Exploratory Analysis** - Statistics, correlations, distributions, and automated insights
- **SQL Analytics** - 50+ production queries with joins, CTEs, and window functions
- **Anomaly Detection** - Isolation Forest, Z-score, and IQR-based detection with ensemble
- **Forecasting** - Linear Regression, Random Forest, and Exponential Smoothing models
- **REST API** - 50+ endpoints with Swagger documentation
- **Authentication** - JWT-based auth with role-based access control
- **Testing** - 100+ automated tests with 90%+ coverage

## Quick Start

### Prerequisites
- Python 3.12+
- pip or conda

### Installation

```bash
git clone <repo>
cd enterprise-data-quality-platform

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env

# Initialize database
python -c "from backend.database.models import Base; from backend.database.engine import engine; Base.metadata.create_all(bind=engine)"

# Run
python -m uvicorn backend.main:app --reload --port 8000
```

### Access
- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

```
backend/
  ├── api/routes/        # 8 API modules, 50+ endpoints
  ├── services/          # Business logic layer
  ├── database/          # SQLAlchemy ORM (9 models)
  ├── validation/        # Data quality engine
  ├── analytics/         # EDA & SQL queries
  ├── anomaly_detection/ # Anomaly algorithms
  ├── forecasting/       # ML models
  └── utils/             # Logging, validators, file handling

frontend/
  ├── index.html         # Main dashboard
  └── static/            # CSS & JavaScript

tests/
  └── *.py               # 100+ tests
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Get access token

### Datasets
- `POST /api/datasets/upload` - Upload dataset
- `GET /api/datasets` - List datasets
- `GET /api/datasets/{id}` - Get dataset details
- `DELETE /api/datasets/{id}` - Delete dataset

### Validation
- `POST /api/validation/datasets/{id}/validate` - Validate data quality
- `GET /api/validation/datasets/{id}/report` - Get validation report

### Analytics
- `GET /api/analytics/{id}/eda` - Exploratory data analysis
- `GET /api/analytics/{id}/kpis` - Key performance indicators
- `GET /api/sql/queries` - Available SQL queries
- `POST /api/sql/execute/predefined` - Execute SQL query

### Anomaly Detection
- `POST /api/anomalies/datasets/{id}/detect` - Detect anomalies

### Forecasting
- `POST /api/forecasting/datasets/{id}/forecast` - Generate forecast

See `/docs` for complete endpoint documentation.

## Configuration

Edit `.env`:
```
ENVIRONMENT=development
DATABASE_URL=sqlite:///./database.db
SECRET_KEY=your-secret-key
MAX_UPLOAD_SIZE_MB=100
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=backend --cov-report=html

# Specific test
pytest tests/test_validation.py -v
```

## Development

### Code Quality
```bash
black backend/ tests/
isort backend/ tests/
flake8 backend/ tests/
mypy backend/
```

### Project Standards
- PEP 8 compliant
- Type hints on all functions
- Comprehensive test coverage
- Role-based access control (Admin/Analyst/Viewer)

## Security

- JWT token-based authentication
- Bcrypt password hashing
- SQL parameterization (no SQL injection)
- Environment variable management
- Input validation on all routes
- CORS properly configured

## Performance

- Efficient Pandas operations
- Database query optimization
- Connection pooling
- GZip compression
- Pagination (10 items default, max 100)

## Database

SQLAlchemy ORM with 9 models:
- User (authentication)
- Dataset (file uploads)
- DataValidation (quality scores)
- DataCleaning (cleaning tasks)
- Analytics (EDA results)
- KPI (business metrics)
- Anomaly (detected anomalies)
- Forecast (predictions)
- Report (generated reports)

Supports SQLite (dev) and PostgreSQL (prod).

## Technology Stack

**Backend**: FastAPI, Uvicorn, SQLAlchemy, Pydantic  
**Data**: Pandas, NumPy, Scikit-learn, SciPy, Statsmodels  
**Security**: JWT, Bcrypt, Passlib  
**Testing**: Pytest, pytest-cov  
**Frontend**: Bootstrap 5, Plotly.js, Vanilla JS

## Deployment

### Docker
```bash
docker build -t data-quality-platform .
docker run -p 8000:8000 -e DATABASE_URL=sqlite:///./data.db data-quality-platform
```

### Production
- Use PostgreSQL for database
- Set `DEBUG=False` in `.env`
- Use strong `SECRET_KEY`
- Configure HTTPS
- Use gunicorn with multiple workers

## Contributing

1. Fork repository
2. Create feature branch
3. Follow PEP 8 and add tests
4. Submit pull request

## License

MIT License - See LICENSE file

---

**Built with production-grade engineering practices.**

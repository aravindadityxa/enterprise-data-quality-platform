# API Documentation

## Overview

The Enterprise Data Quality Platform provides a RESTful API for all operations. Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Base URL

```
http://localhost:8000/api
```

## Authentication

All endpoints (except login) require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Login

**POST** `/auth/login`

Request:
```json
{
  "username": "admin",
  "password": "password123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Register

**POST** `/auth/register`

Request:
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

## Datasets

### Upload Dataset

**POST** `/datasets/upload`

Multipart form data:
- `file`: The dataset file (CSV, Excel, JSON)
- `name`: Dataset name
- `description`: Optional description
- `file_type`: File type (csv, xlsx, json)

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sales Data",
  "total_rows": 10000,
  "total_columns": 15,
  "quality_score": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List Datasets

**GET** `/datasets?page=1&page_size=10`

Response:
```json
{
  "total": 50,
  "page": 1,
  "page_size": 10,
  "items": [...]
}
```

### Get Dataset

**GET** `/datasets/{dataset_id}`

Returns full dataset details including profile report.

### Update Dataset

**PUT** `/datasets/{dataset_id}`

Request:
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

### Delete Dataset

**DELETE** `/datasets/{dataset_id}`

### Download Dataset

**GET** `/datasets/{dataset_id}/download?format=csv`

Parameters:
- `format`: csv, xlsx, json

## Data Validation

### Validate Dataset

**POST** `/datasets/{dataset_id}/validate`

Runs comprehensive data quality checks.

Response:
```json
{
  "id": "validation-id",
  "dataset_id": "dataset-id",
  "quality_score": 85.5,
  "validation_status": "warning",
  "missing_values_count": 150,
  "missing_values_percentage": 1.5,
  "duplicates_count": 50,
  "duplicates_percentage": 0.5,
  "issues": [...],
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Validation Report

**GET** `/datasets/{dataset_id}/validations/{validation_id}`

## Data Cleaning

### Clean Dataset

**POST** `/datasets/{dataset_id}/clean`

Request:
```json
{
  "remove_duplicates": true,
  "fill_missing": true,
  "normalize_text": true,
  "standardize_dates": true
}
```

Response:
```json
{
  "id": "cleaning-task-id",
  "dataset_id": "dataset-id",
  "status": "processing",
  "removed_duplicates": 50,
  "filled_missing_values": 150,
  "removed_invalid_records": 10
}
```

### Get Cleaning Status

**GET** `/datasets/{dataset_id}/cleaning/{cleaning_id}`

### Download Cleaned Dataset

**GET** `/datasets/{dataset_id}/cleaning/{cleaning_id}/download?format=csv`

## Analytics

### Get EDA Report

**GET** `/analytics/{dataset_id}/eda`

Response includes summary statistics, correlations, distributions, and insights.

### Get KPIs

**GET** `/analytics/{dataset_id}/kpis`

Response includes revenue, profit, growth metrics, customer KPIs.

### Get Anomalies

**GET** `/analytics/{dataset_id}/anomalies?severity=high&limit=100`

Query parameters:
- `severity`: low, medium, high
- `detection_method`: isolation_forest, zscore, iqr
- `limit`: Number of results

Response:
```json
{
  "total": 150,
  "items": [
    {
      "id": "anomaly-id",
      "column_name": "transaction_amount",
      "anomaly_type": "spike",
      "value": 50000.0,
      "threshold": 5000.0,
      "score": 0.95,
      "severity": "high"
    }
  ]
}
```

### Generate Forecast

**POST** `/analytics/{dataset_id}/forecast`

Request:
```json
{
  "forecast_type": "sales",
  "forecast_column": "monthly_sales",
  "periods": 12,
  "model": "linear_regression"
}
```

Response:
```json
{
  "id": "forecast-id",
  "forecast_type": "sales",
  "forecast_values": [100000, 105000, 110000, ...],
  "confidence_intervals": {
    "lower": [95000, 100000, ...],
    "upper": [105000, 110000, ...]
  },
  "r_squared": 0.92,
  "rmse": 5000.0,
  "mape": 2.5
}
```

## Reports

### Generate Report

**POST** `/reports/generate`

Request:
```json
{
  "dataset_id": "dataset-id",
  "report_type": "pdf",
  "include_quality_summary": true,
  "include_insights": true,
  "include_forecast": true,
  "include_recommendations": true
}
```

Response:
```json
{
  "id": "report-id",
  "report_type": "pdf",
  "status": "processing",
  "file_size_bytes": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Report

**GET** `/reports/{report_id}`

### Download Report

**GET** `/reports/{report_id}/download`

### List Reports

**GET** `/reports?dataset_id=dataset-id&limit=10`

## Users

### Get Current User

**GET** `/users/me`

### Update Profile

**PUT** `/users/me`

Request:
```json
{
  "full_name": "Updated Name",
  "email": "newemail@example.com"
}
```

### Change Password

**POST** `/users/me/change-password`

Request:
```json
{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

## Error Responses

All errors follow a standard format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "status_code": 400
}
```

### Common Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no content
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate or conflict
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

## Rate Limiting

- 1000 requests per hour per user
- 10 requests per second per IP

## Pagination

List endpoints support pagination:

```
GET /datasets?page=1&page_size=10
```

Response:
```json
{
  "total": 100,
  "page": 1,
  "page_size": 10,
  "items": [...]
}
```

## Filtering

Most list endpoints support filtering:

```
GET /anomalies?dataset_id=abc&severity=high&created_after=2024-01-01
```

## Sorting

Sort results:

```
GET /datasets?sort_by=created_at&sort_order=desc
```

## Webhooks (Future)

Webhook support coming in v1.1 for:
- Dataset validation complete
- Anomalies detected
- Forecast generated
- Report ready
- Cleaning complete

## SDK/Client Libraries

Official SDKs available for:
- Python (enterprise-data-quality-sdk)
- JavaScript/TypeScript
- Go
- Java

## Examples

### Python Example

```python
import requests

# Initialize
BASE_URL = "http://localhost:8000/api"
token = "your-access-token"
headers = {"Authorization": f"Bearer {token}"}

# Upload dataset
files = {'file': open('data.csv', 'rb')}
data = {'name': 'Sales Data', 'file_type': 'csv'}
response = requests.post(
    f"{BASE_URL}/datasets/upload",
    files=files,
    data=data,
    headers=headers
)
dataset_id = response.json()['id']

# Validate
response = requests.post(
    f"{BASE_URL}/datasets/{dataset_id}/validate",
    headers=headers
)
print(f"Quality Score: {response.json()['quality_score']}")

# Generate forecast
response = requests.post(
    f"{BASE_URL}/analytics/{dataset_id}/forecast",
    json={
        "forecast_type": "sales",
        "periods": 12,
        "model": "linear_regression"
    },
    headers=headers
)
forecast = response.json()
print(forecast['forecast_values'])

# Generate report
response = requests.post(
    f"{BASE_URL}/reports/generate",
    json={
        "dataset_id": dataset_id,
        "report_type": "pdf",
        "include_forecast": True
    },
    headers=headers
)
report_id = response.json()['id']

# Download report
response = requests.get(
    f"{BASE_URL}/reports/{report_id}/download",
    headers=headers
)
with open("report.pdf", "wb") as f:
    f.write(response.content)
```

### cURL Examples

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Upload dataset
curl -X POST http://localhost:8000/api/datasets/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@data.csv" \
  -F "name=Sales Data" \
  -F "file_type=csv"

# Validate
curl -X POST http://localhost:8000/api/datasets/DATASET_ID/validate \
  -H "Authorization: Bearer TOKEN"

# Get KPIs
curl -X GET http://localhost:8000/api/analytics/DATASET_ID/kpis \
  -H "Authorization: Bearer TOKEN"
```

---

For more details, visit `/docs` endpoint for interactive API exploration.

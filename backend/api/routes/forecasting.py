"""Forecasting API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.dataset_service import DatasetService
from backend.forecasting.forecaster import Forecaster
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger
from backend.api.dependencies import get_current_user, get_analyst_user

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/forecasting", tags=["Forecasting"])


class ForecastRequest(BaseModel):
    """Forecast request schema."""
    date_column: str
    value_column: str
    periods: int = 12
    method: str = "combined"


@router.post("/datasets/{dataset_id}/forecast")
async def generate_forecast(
    dataset_id: str,
    request: ForecastRequest,
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db),
):
    """Generate forecast for dataset."""
    try:
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

        df = FileHandler.load_dataframe(dataset.file_path)

        if request.method == "linear_regression":
            results = Forecaster.linear_regression_forecast(
                df, request.date_column, request.value_column, request.periods
            )
        elif request.method == "random_forest":
            results = Forecaster.random_forest_forecast(
                df, request.date_column, request.value_column, request.periods
            )
        elif request.method == "exponential_smoothing":
            results = Forecaster.exponential_smoothing_forecast(
                df, request.date_column, request.value_column, request.periods
            )
        else:
            results = Forecaster.combined_forecast(
                df, request.date_column, request.value_column, request.periods
            )

        return {"dataset_id": dataset_id, "forecast_results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecasting error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Forecast failed")

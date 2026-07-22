"""Anomaly Detection API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.dataset_service import DatasetService
from backend.anomaly_detection.detector import AnomalyDetector
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger
from backend.api.dependencies import get_current_user, get_analyst_user

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/anomalies", tags=["Anomaly Detection"])


@router.post("/datasets/{dataset_id}/detect")
async def detect_anomalies(
    dataset_id: str,
    method: str = Query("combined", regex="^(isolation_forest|z_score|iqr|combined|spikes)$"),
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db),
):
    """Detect anomalies in dataset."""
    try:
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

        df = FileHandler.load_dataframe(dataset.file_path)

        if method == "isolation_forest":
            results = AnomalyDetector.isolation_forest(df)
        elif method == "z_score":
            results = AnomalyDetector.z_score_method(df)
        elif method == "iqr":
            results = AnomalyDetector.iqr_method(df)
        elif method == "spikes":
            results = AnomalyDetector.detect_sales_spikes(df)
        else:
            results = AnomalyDetector.combined_detection(df)

        return {"dataset_id": dataset_id, "detection_results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Detection failed")

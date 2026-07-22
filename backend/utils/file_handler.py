"""
File handling utilities for dataset upload and processing.

Supports CSV, Excel, and JSON formats with automatic type detection.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Union
import pandas as pd
import json
from backend.config import get_settings
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


class FileHandler:
    """Handle file uploads and operations."""

    @staticmethod
    def ensure_upload_directory() -> str:
        """
        Create upload directory if it doesn't exist.

        Returns:
            str: Path to upload directory
        """
        upload_dir = settings.upload_directory
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    @staticmethod
    def save_upload_file(file_path: str, destination: str) -> bool:
        """
        Save uploaded file to destination.

        Args:
            file_path: Source file path
            destination: Destination file path

        Returns:
            bool: Success status
        """
        try:
            FileHandler.ensure_upload_directory()
            shutil.copy2(file_path, destination)
            logger.info(f"File saved: {destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return False

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        Get file extension.

        Args:
            filename: Filename

        Returns:
            str: File extension without dot
        """
        return Path(filename).suffix.lower().lstrip(".")

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """
        Validate file extension against allowed types.

        Args:
            filename: Filename to validate

        Returns:
            bool: True if allowed, False otherwise
        """
        ext = FileHandler.get_file_extension(filename)
        return ext in settings.allowed_extensions_list

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            int: File size in bytes
        """
        try:
            return os.path.getsize(file_path)
        except OSError as e:
            logger.error(f"Error getting file size: {e}")
            return 0

    @staticmethod
    def load_dataframe(file_path: str) -> Optional[pd.DataFrame]:
        """
        Load file into pandas DataFrame.

        Args:
            file_path: Path to file

        Returns:
            Optional[pd.DataFrame]: DataFrame or None if error

        Raises:
            ValueError: If file format not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = FileHandler.get_file_extension(file_path)

        try:
            if ext == "csv":
                df = pd.read_csv(file_path)
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(file_path)
            elif ext == "json":
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Unsupported file format: {ext}")

            logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns from {file_path}")
            return df

        except Exception as e:
            logger.error(f"Error loading file: {e}")
            raise

    @staticmethod
    def save_dataframe(df: pd.DataFrame, file_path: str, file_format: str = "csv") -> bool:
        """
        Save DataFrame to file.

        Args:
            df: DataFrame to save
            file_path: Destination path
            file_format: Format (csv, xlsx, json)

        Returns:
            bool: Success status
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            if file_format == "csv":
                df.to_csv(file_path, index=False)
            elif file_format == "xlsx":
                df.to_excel(file_path, index=False)
            elif file_format == "json":
                df.to_json(file_path, orient="records")
            else:
                raise ValueError(f"Unsupported format: {file_format}")

            logger.info(f"Saved DataFrame to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete file safely.

        Args:
            file_path: Path to file

        Returns:
            bool: Success status
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    @staticmethod
    def get_unique_filename(original_name: str, folder: str = None) -> str:
        """
        Generate unique filename if file already exists.

        Args:
            original_name: Original filename
            folder: Target folder

        Returns:
            str: Unique filename
        """
        if folder is None:
            folder = settings.upload_directory

        full_path = os.path.join(folder, original_name)

        if not os.path.exists(full_path):
            return original_name

        name, ext = os.path.splitext(original_name)
        counter = 1
        while os.path.exists(os.path.join(folder, f"{name}_{counter}{ext}")):
            counter += 1

        return f"{name}_{counter}{ext}"

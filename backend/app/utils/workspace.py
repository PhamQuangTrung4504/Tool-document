"""Secure temporary workspace management for job execution and automatic cleanup."""

import shutil
import uuid
from pathlib import Path
from typing import Optional

from app.config import config
from app.core.logging import logger


class TempWorkspace:
    """Manages isolated job directories: input/, intermediate/, and output/.

    Guarantees cleanup of intermediate and sensitive temporary files on exit.
    """

    def __init__(self, job_id: Optional[str] = None, base_dir: Optional[Path] = None) -> None:
        self.job_id = job_id or str(uuid.uuid4())
        self.base_dir = Path(base_dir or config.paths.temp_dir)
        self.root_dir = self.base_dir / self.job_id

        self.input_dir = self.root_dir / "input"
        self.intermediate_dir = self.root_dir / "intermediate"
        self.output_dir = self.root_dir / "output"

    def setup(self) -> "TempWorkspace":
        """Creates the directory hierarchy."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self

    def cleanup_intermediate(self) -> None:
        """Deletes intermediate files (rendered page images, temp crops, raw OCR arrays)."""
        if self.intermediate_dir.exists():
            try:
                shutil.rmtree(self.intermediate_dir, ignore_errors=True)
                self.intermediate_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Cleaned intermediate workspace for job '{self.job_id}'")
            except Exception as e:
                logger.warning(f"Failed to cleanup intermediate dir for job '{self.job_id}': {e}")

    def cleanup_all(self, keep_output: bool = False) -> None:
        """Removes the entire job workspace."""
        if not self.root_dir.exists():
            return

        try:
            if keep_output:
                if self.input_dir.exists():
                    shutil.rmtree(self.input_dir, ignore_errors=True)
                if self.intermediate_dir.exists():
                    shutil.rmtree(self.intermediate_dir, ignore_errors=True)
            else:
                shutil.rmtree(self.root_dir, ignore_errors=True)
                logger.debug(f"Completely removed workspace for job '{self.job_id}'")
        except Exception as e:
            logger.warning(f"Error purging workspace '{self.root_dir}': {e}")

    def __enter__(self) -> "TempWorkspace":
        return self.setup()

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[object]) -> None:
        # Always cleanup intermediate files to avoid disk leaks and protect privacy
        self.cleanup_intermediate()

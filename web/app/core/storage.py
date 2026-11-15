"""一時ファイル保存およびジョブ状態管理モジュール。"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Literal, Optional

OUTPUT_DIR: Path = Path(__file__).resolve().parent.parent / "static" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JobState = Literal["pending", "running", "completed", "failed"]


@dataclass
class JobInfo:
    """非同期生成ジョブの状態。"""

    job_id: str
    status: JobState = "pending"
    progress: float = 0.0  # 0.0 〜 100.0
    message_key: str = "status.queued"
    output_filename: Optional[str] = None
    output_format: Optional[str] = None
    file_size_bytes: int = 0
    error_detail: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class JobManager:
    """スレッドセーフなジョブおよび出力ファイル管理。"""

    def __init__(self, output_dir: Path = OUTPUT_DIR, ttl_seconds: int = 3600) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_seconds
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()

    def create_job(self) -> JobInfo:
        self.cleanup_expired()
        job_id = uuid.uuid4().hex[:12]
        job = JobInfo(job_id=job_id)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[JobState] = None,
        progress: Optional[float] = None,
        message_key: Optional[str] = None,
        output_filename: Optional[str] = None,
        output_format: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        error_detail: Optional[str] = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0.0, min(100.0, progress))
            if message_key is not None:
                job.message_key = message_key
            if output_filename is not None:
                job.output_filename = output_filename
            if output_format is not None:
                job.output_format = output_format
            if file_size_bytes is not None:
                job.file_size_bytes = file_size_bytes
            if error_detail is not None:
                job.error_detail = error_detail

    def get_output_path(self, filename: str) -> Optional[Path]:
        """ディレクトリトラバーサルを防ぎつつ出力ファイルパスを返す。"""
        safe_name = Path(filename).name
        target = self._output_dir / safe_name
        if target.exists() and target.is_file():
            return target
        return None

    def allocate_output_path(self, prefix: str, ext: str) -> Path:
        unique_id = uuid.uuid4().hex[:10]
        clean_ext = ext.lstrip(".")
        return self._output_dir / f"{prefix}_{unique_id}.{clean_ext}"

    def cleanup_expired(self) -> int:
        """TTLを超過したジョブと出力ファイルを削除する。"""
        now = time.time()
        removed = 0
        with self._lock:
            expired_ids = [
                jid for jid, job in self._jobs.items()
                if now - job.created_at > self._ttl_seconds
            ]
            for jid in expired_ids:
                job = self._jobs.pop(jid, None)
                if job and job.output_filename:
                    p = self._output_dir / Path(job.output_filename).name
                    if p.exists():
                        p.unlink(missing_ok=True)
                        removed += 1

        # ジョブ管理外の古い一時ファイルも削除
        for p in self._output_dir.iterdir():
            if p.is_file() and (now - p.stat().st_mtime > self._ttl_seconds):
                p.unlink(missing_ok=True)
                removed += 1

        return removed


job_manager = JobManager()

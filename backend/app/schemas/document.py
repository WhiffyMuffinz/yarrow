"""Document, job and upload models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str | None = None
    current_stage: str | None = None
    pages_processed: int | None = None
    total_pages: int | None = None
    error_message: str | None = None


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    status: str | None = None
    width: float | None = None
    height: float | None = None
    error_message: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    file_size_bytes: int
    file_type: str
    page_count: int | None = None
    status: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class DocumentDetail(DocumentOut):
    jobs: list[JobOut] = []
    pages: list[PageOut] = []


class UploadAccepted(BaseModel):
    """One accepted file. Bulk upload returns a list of these (backlog #8)."""

    document_id: UUID
    job_id: UUID
    task_id: str
    filename: str
    file_size_bytes: int


class UploadRejected(BaseModel):
    """One file that was not accepted, so a bulk upload can report per file."""

    filename: str
    reason: str


class UploadResponse(BaseModel):
    accepted: list[UploadAccepted] = []
    rejected: list[UploadRejected] = []

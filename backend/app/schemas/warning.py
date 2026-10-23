from uuid import UUID

from pydantic import BaseModel


class WarningEntry(BaseModel):
    document_id: UUID
    filename: str
    page_number: int
    warning_type: str | None = None
    message: str | None = None

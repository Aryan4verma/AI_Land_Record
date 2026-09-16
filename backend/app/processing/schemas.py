"""Processing schemas."""
from uuid import UUID

from pydantic import BaseModel


class ProcessAcceptedOut(BaseModel):
    job_id: UUID
    status: str

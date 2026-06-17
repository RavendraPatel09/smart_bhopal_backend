from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    badge: str
    points_snapshot: int
    issued_at: datetime

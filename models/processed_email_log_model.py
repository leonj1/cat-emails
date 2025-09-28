from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProcessedEmailLogModel(BaseModel):
    id: int
    account_email: str
    message_id: str
    processed_at: datetime

    # Enable validation from SQLAlchemy ORM instances
    model_config = ConfigDict(from_attributes=True)

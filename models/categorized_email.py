from models.email_category import EmailCategory
from pydantic import BaseModel, Field

class CategorizedEmail(BaseModel):
    contents: str = Field(description="The contents of the email")
    category: EmailCategory = Field(description="The category of the email.")

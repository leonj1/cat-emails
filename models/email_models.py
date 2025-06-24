from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Union, Any
from enum import Enum


class EmailAddress(BaseModel):
    """Model representing an email address with optional display name."""
    email: EmailStr = Field(description="The email address")
    name: Optional[str] = Field(None, description="The display name for the email address")
    
    def to_string(self) -> str:
        """Convert to standard email format: 'Name <email>' or just 'email'."""
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class Attachment(BaseModel):
    """Model representing an email attachment."""
    filename: str = Field(description="The filename of the attachment")
    content: str = Field(description="Base64 encoded content of the attachment")
    content_type: Optional[str] = Field("application/octet-stream", description="MIME type of the attachment")
    disposition: Optional[str] = Field("attachment", description="Content disposition (attachment or inline)")
    content_id: Optional[str] = Field(None, description="Content ID for inline attachments")


class EmailMessage(BaseModel):
    """Model representing a complete email message."""
    sender: EmailAddress = Field(description="The sender of the email")
    to: List[EmailAddress] = Field(description="List of primary recipients")
    cc: Optional[List[EmailAddress]] = Field(default_factory=list, description="List of CC recipients")
    bcc: Optional[List[EmailAddress]] = Field(default_factory=list, description="List of BCC recipients")
    subject: str = Field(description="The subject line of the email")
    text: Optional[str] = Field(None, description="Plain text content of the email")
    html: Optional[str] = Field(None, description="HTML content of the email")
    attachments: Optional[List[Attachment]] = Field(default_factory=list, description="List of attachments")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Custom email headers")
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Template variables for providers that support them")
    reply_to: Optional[EmailAddress] = Field(None, description="Reply-to address")
    
    def model_post_init(self, __context):
        """Validate that at least one content type is provided."""
        if not self.text and not self.html:
            raise ValueError("Email must have either text or html content")


class EmailSendStatus(str, Enum):
    """Status of email send operation."""
    SUCCESS = "success"
    FAILED = "failed"
    QUEUED = "queued"
    PENDING = "pending"


class EmailSendResponse(BaseModel):
    """Successful email send response."""
    status: EmailSendStatus = Field(description="Status of the email send operation")
    message_id: str = Field(description="Unique identifier for the sent message")
    provider: str = Field(description="The email provider used to send the message")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider-specific response details")


class EmailErrorResponse(BaseModel):
    """Error response for failed email operations."""
    status: EmailSendStatus = Field(default=EmailSendStatus.FAILED, description="Status indicating failure")
    error_code: str = Field(description="Error code identifying the type of error")
    error_message: str = Field(description="Human-readable error message")
    provider: str = Field(description="The email provider that returned the error")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional error details")


# Type alias for email operation results
EmailOperationResult = Union[EmailSendResponse, Optional[EmailErrorResponse]]
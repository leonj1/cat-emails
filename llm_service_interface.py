from abc import ABC, abstractmethod
from typing import Union
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    error_type: str


class ILLMService(ABC):
    """
    Interface for LLM service implementations.
    This interface defines the contract for services that interact with Large Language Models.
    """

    @abstractmethod
    def query(self, message: str, response_model: type[BaseModel]) -> Union[BaseModel, ErrorResponse]:
        """
        Query the LLM with a message and return a structured Pydantic response.

        Args:
            message: The message/prompt to send to the LLM
            response_model: Pydantic model class to parse the response into

        Returns:
            Union[BaseModel, ErrorResponse]: Either the parsed response model or an error response
        """
        pass
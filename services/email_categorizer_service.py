import logging
from services.email_categorizer_interface import EmailCategorizerInterface
from services.categorize_emails_llm import LLMCategorizeEmails
from services.categorize_emails_interface import SimpleEmailCategory
from services.llm_service_interface import LLMServiceInterface

logger = logging.getLogger(__name__)


class EmailCategorizerService(EmailCategorizerInterface):
    """Service for categorizing emails using LLM with resilient error handling."""

    def __init__(self, llm_service_factory):
        """
        Initialize the email categorizer service.

        Args:
            llm_service_factory: Factory to create LLM service instances
        """
        self.llm_service_factory = llm_service_factory

    def categorize(self, contents: str, model: str) -> str:
        """
        Categorize email using the LLMCategorizeEmails interface (OpenAI-compatible / Ollama gateway).

        Args:
            contents: The email content to categorize
            model: The model identifier to use for categorization

        Returns:
            str: The category name, defaults to "Other" on errors
        """
        try:
            llm_service = self.llm_service_factory.create_service(model)
            categorizer = LLMCategorizeEmails(llm_service=llm_service)
            result = categorizer.category(contents)

            if isinstance(result, SimpleEmailCategory):
                return result.value

            logger.warning(f"Categorization returned error or unexpected result: {result}")
            return "Other"
        except Exception as e:
            logger.error(f"Failed to categorize email via LLMCategorizeEmails: {str(e)}")
            return "Other"

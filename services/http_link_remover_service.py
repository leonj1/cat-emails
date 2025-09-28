"""
Service for removing HTTP/HTTPS links from text.
"""

import re
from typing import Pattern


class HttpLinkRemoverService:
    """
    Concrete class encapsulating logic to strip http/https URLs from a string.
    Compiles the regex once for efficiency.
    """

    _pattern_str = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

    def __init__(self) -> None:
        self._pattern: Pattern[str] = re.compile(self._pattern_str)

    def remove(self, text: str) -> str:
        """
        Remove all http/https links from the given text.

        Args:
            text: Input text possibly containing URLs.

        Returns:
            str: Text with all http/https URLs removed.
        """
        return self._pattern.sub('', text)

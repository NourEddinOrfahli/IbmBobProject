"""
AI provider abstraction.

Defines the AIProvider interface that every concrete provider must
implement.  The rest of the application only imports this module;
it never depends on a specific provider implementation directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(Exception):
    """Raised when an AI provider call fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AIProvider(ABC):
    """Abstract base class for all AI provider implementations."""

    @abstractmethod
    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send a prompt to the underlying model and return a parsed JSON dict.

        Parameters
        ----------
        system_prompt:
            The system-role message that configures the AI's behaviour.
        user_prompt:
            The user-role message containing the actual request.
        max_tokens:
            Maximum number of tokens the model may generate.
        temperature:
            Sampling temperature (0 = deterministic, 1 = very creative).

        Returns
        -------
        dict
            Parsed JSON from the model response.

        Raises
        ------
        AIProviderError
            On connection failure, model error, or unparseable output.
        """
        ...

    @abstractmethod
    async def analyze_image(
        self,
        image_b64: str,
        image_mime: str,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send an image (base64-encoded) plus text prompt to a vision-capable model
        and return a parsed JSON dict.

        Parameters
        ----------
        image_b64:
            Base64-encoded image content (no data-URI prefix).
        image_mime:
            MIME type string, e.g. "image/jpeg".
        system_prompt:
            System-role message.
        user_prompt:
            User-role text accompanying the image.
        max_tokens:
            Maximum tokens for the response.
        temperature:
            Sampling temperature.

        Returns
        -------
        dict
            Parsed JSON from the model response.

        Raises
        ------
        AIProviderError
            On connection failure, model error, or unparseable output.
        """
        ...

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 600,
        temperature: float = 0.5,
    ) -> str:
        """
        Send a multi-turn chat conversation to the model and return the
        assistant's plain-text reply.

        Parameters
        ----------
        messages:
            List of {role, content} dicts including the system message.
        max_tokens:
            Maximum tokens for the reply.
        temperature:
            Sampling temperature.

        Returns
        -------
        str
            The assistant's reply text.

        Raises
        ------
        AIProviderError
            On connection failure or model error.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any resources held by the provider (e.g. HTTP clients)."""
        ...

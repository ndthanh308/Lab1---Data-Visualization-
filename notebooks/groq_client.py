"""
Groq API Client with automatic API key rotation on rate limit errors.

Usage:
    from groq_client import GroqRotatingClient

    client = GroqRotatingClient(api_keys=[
        "gsk_key1...",
        "gsk_key2...",
        "gsk_key3...",
    ])

    # Use it exactly like the normal Groq client
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        model="llama-3.3-70b-versatile",
        temperature=0
    )
    print(response)  # returns the content string
"""

import time
from groq import Groq


class GroqRotatingClient:
    """
    A wrapper around the Groq client that supports multiple API keys.
    When a rate limit error (429) is encountered, it automatically
    switches to the next API key and retries the request.
    """

    def __init__(self, api_keys: list[str]):
        """
        Args:
            api_keys: List of Groq API keys to rotate through.
        """
        if not api_keys:
            raise ValueError("Phải cung cấp ít nhất 1 API key.")

        self.api_keys = api_keys
        self.current_index = 0
        self.client = Groq(api_key=self.api_keys[self.current_index])
        print(f"[GroqRotatingClient] Khởi tạo với {len(api_keys)} API key(s). Đang dùng key #{self.current_index + 1}")

    def _switch_key(self):
        """Switch to the next API key in the list."""
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        self.client = Groq(api_key=self.api_keys[self.current_index])
        print(f"[GroqRotatingClient] Chuyển từ key #{old_index + 1} sang key #{self.current_index + 1}")

    def chat_completion(self, messages, model="llama-3.3-70b-versatile",
                        temperature=0, max_retries=None, retry_delay=2, **kwargs):
        """
        Call chat completions with automatic key rotation on rate limit errors.

        Args:
            messages: List of message dicts (same as Groq API).
            model: Model name to use.
            temperature: Temperature setting.
            max_retries: Max number of retries. Defaults to len(api_keys) * 2.
            retry_delay: Seconds to wait before retrying after switching keys.
            **kwargs: Additional keyword arguments passed to the Groq API.

        Returns:
            The content string from the first choice of the completion.

        Raises:
            Exception: If all API keys are exhausted or a non-rate-limit error occurs.
        """
        if max_retries is None:
            max_retries = len(self.api_keys) * 2

        last_error = None

        for attempt in range(max_retries):
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    **kwargs
                )
                return chat_completion.choices[0].message.content.strip()

            except Exception as e:
                error_str = str(e)
                last_error = e

                # Check if it's a rate limit error (HTTP 429)
                if "429" in error_str or "rate_limit" in error_str.lower():
                    print(f"[GroqRotatingClient] Rate limit hit trên key #{self.current_index + 1} "
                          f"(lần thử {attempt + 1}/{max_retries})")

                    # Switch to next key
                    self._switch_key()

                    # Small delay to avoid hammering
                    time.sleep(retry_delay)
                else:
                    # Non-rate-limit error, raise immediately
                    raise e

        # If we've exhausted all retries
        raise Exception(
            f"[GroqRotatingClient] Đã thử {max_retries} lần nhưng tất cả API key đều bị rate limit. "
            f"Lỗi cuối: {last_error}"
        )

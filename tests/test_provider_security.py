import unittest
from unittest.mock import patch

from ruller_ai.providers import OllamaProvider, OpenAICompatibleProvider, ProviderError, validate_api_base


class ProviderSecurityValidationTests(unittest.TestCase):
    def test_api_url_and_key_transport_validation(self):
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider(api_base="http://localhost:8000/v1", api_key="token")
        for url in ("http://remote.example/v1", "https://user:pass@example.com", "https://good.test/?x=1", "https://example.com/\nX: y"):
            with self.subTest(url=url), self.assertRaises(ProviderError):
                validate_api_base(url)
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider(model="--help")
        with self.assertRaises(ProviderError):
            OllamaProvider("../model")

    def test_prompt_size_is_bounded_before_request(self):
        provider = OpenAICompatibleProvider(api_base="http://127.0.0.1:8000/v1")
        with patch("ruller_ai.providers._open_no_redirect") as open_url:
            with self.assertRaises(ProviderError):
                provider.generate("x" * 16_001)
            open_url.assert_not_called()

    @patch("ruller_ai.providers._open_no_redirect")
    def test_redirect_is_not_followed_and_key_not_retransmitted(self, open_url):
        import urllib.error
        open_url.side_effect = urllib.error.HTTPError("https://example.test/v1/models", 307, "redirect", {}, None)
        provider = OpenAICompatibleProvider(api_base="https://example.test/v1", api_key="dummy-token")
        ok, text = provider.health_check()
        self.assertFalse(ok)
        self.assertIn("redirects are not followed", text)
        open_url.assert_called_once()


if __name__ == "__main__":
    unittest.main()

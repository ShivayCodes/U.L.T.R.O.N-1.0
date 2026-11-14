import unittest
from unittest.mock import patch

from ruller_ai.providers import OllamaProvider, OpenAICompatibleProvider


class ProviderHealthTests(unittest.TestCase):
    @patch("ruller_ai.providers.subprocess.run")
    def test_ollama_health_reports_model_and_missing_model(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "NAME ID SIZE\nllama3.1 abc 4 GB\n"
        self.assertEqual(OllamaProvider("llama3.1").health_check(), (True, "Ollama is running and model 'llama3.1' is installed."))
        self.assertFalse(OllamaProvider("missing").health_check()[0])

    def test_online_health_requires_key_without_network(self):
        provider = OpenAICompatibleProvider(api_base="https://api.example.test/v1", api_key=None)
        provider.api_key = None
        with patch("ruller_ai.providers.urllib.request.urlopen") as open_url:
            ok, detail = provider.health_check()
        self.assertFalse(ok)
        self.assertIn("API key is missing", detail)
        open_url.assert_not_called()

    @patch("ruller_ai.providers.urllib.request.urlopen")
    def test_online_health_uses_models_endpoint(self, open_url):
        response = open_url.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = b'{"data": []}'
        provider = OpenAICompatibleProvider(api_base="https://api.example.test/v1", api_key="test-key")
        self.assertTrue(provider.health_check()[0])
        self.assertIn("/models", open_url.call_args.args[0].full_url)


if __name__ == "__main__":
    unittest.main()

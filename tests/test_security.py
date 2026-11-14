import json
import tempfile
import unittest
from pathlib import Path

from ruller_ai import RullerAI
from ruller_ai.config import Settings
from ruller_ai.knowledge import KnowledgeBase
from ruller_ai.providers import OpenAICompatibleProvider, ProviderError, validate_api_base
from ruller_ai.security import (
    InputValidationError,
    contains_sensitive_value,
    redact_secrets,
    secure_system_instructions,
    validate_chat_input,
    validate_model_name,
    validate_model_output,
)


class SecurityHardeningTests(unittest.TestCase):
    def test_chat_input_is_bounded_and_rejects_control_characters(self):
        self.assertEqual(validate_chat_input("  hello  "), "hello")
        self.assertEqual(validate_chat_input("line one\nline two"), "line one\nline two")
        with self.assertRaises(InputValidationError):
            validate_chat_input("x" * 9, max_chars=8)
        with self.assertRaises(InputValidationError):
            validate_chat_input("hello\x00world")
        with self.assertRaises(InputValidationError):
            validate_chat_input(None)

    def test_model_name_and_output_are_validated(self):
        self.assertEqual(validate_model_name("llama3.1:8b"), "llama3.1:8b")
        with self.assertRaises(ValueError):
            validate_model_name("bad model; rm -rf")
        with self.assertRaises(ValueError):
            validate_model_name("")
        self.assertEqual(validate_model_output(" answer "), "answer")
        with self.assertRaises(ValueError):
            validate_model_output({"content": "not a string"})
        with self.assertRaises(ValueError):
            validate_model_output("x" * 32_001)

    def test_remote_http_is_rejected_but_https_and_loopback_are_allowed(self):
        self.assertEqual(validate_api_base("https://api.example.com/v1").scheme, "https")
        self.assertEqual(validate_api_base("http://127.0.0.1:11434/v1").hostname, "127.0.0.1")
        with self.assertRaises(ProviderError):
            validate_api_base("http://api.example.com/v1")
        with self.assertRaises(ProviderError):
            validate_api_base("https://user:pass@example.com/v1")
        with self.assertRaises(ProviderError):
            validate_api_base("https://example.com/v1?token=secret")

    def test_api_key_is_never_allowed_over_loopback_http(self):
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider(
                api_base="http://127.0.0.1:11434/v1",
                api_key="local-test-key",
            )

    def test_secret_patterns_are_detected_and_redacted(self):
        raw = "api_key=sk-test-value Authorization: Bearer token-value"
        self.assertTrue(contains_sensitive_value(raw))
        safe = redact_secrets(raw)
        self.assertNotIn("sk-test-value", safe)
        self.assertNotIn("token-value", safe)
        self.assertIn("[REDACTED]", safe)

    def test_json_credentials_are_detected_and_redacted_without_breaking_json(self):
        raw = json.dumps({
            "api_key": "sk-live-secret",
            "nested": {"password": "correct-horse"},
            "Authorization": "Bearer bearer-secret",
        })
        self.assertTrue(contains_sensitive_value(raw))
        safe = redact_secrets(raw)
        self.assertNotIn("sk-live-secret", safe)
        self.assertNotIn("correct-horse", safe)
        self.assertNotIn("bearer-secret", safe)
        parsed = json.loads(safe)
        self.assertEqual(parsed["api_key"], "[REDACTED]")
        self.assertEqual(parsed["nested"]["password"], "[REDACTED]")
        self.assertEqual(parsed["Authorization"], "Bearer [REDACTED]")

    def test_settings_reject_invalid_provider_and_resource_limits(self):
        with self.assertRaises(ValueError):
            Settings(provider="unknown-backend")
        with self.assertRaises(ValueError):
            Settings(max_input_chars=0)
        with self.assertRaises(ValueError):
            Settings(model="invalid model name")

    def test_model_instructions_define_untrusted_data_boundary(self):
        policy = secure_system_instructions("Base policy")
        self.assertIn("untrusted data", policy)
        self.assertIn("no authority to execute code", policy)

    def test_sensitive_prompt_is_not_sent_to_remote_provider_or_saved_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            ai = RullerAI(Settings(data_dir=Path(directory)))
            class NeverCallProvider:
                name = "test-provider"
                def generate(self, *args, **kwargs):
                    raise AssertionError("Sensitive prompt must not reach provider.")
            ai.provider = NeverCallProvider()
            answer = ai.chat("api_key=super-secret-value")
            self.assertIn("transmission was blocked", answer)
            self.assertNotIn("super-secret-value", answer)
            saved = ai.memory.recent(10)
            self.assertTrue(saved)
            self.assertNotIn("super-secret-value", saved[-2]["content"])

    def test_json_credential_prompt_is_blocked_and_knowledge_is_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ai = RullerAI(Settings(data_dir=root))
            class NeverCallProvider:
                name = "test-provider"
                def generate(self, *args, **kwargs):
                    raise AssertionError("JSON credentials must not reach provider.")
            ai.provider = NeverCallProvider()
            prompt = '{"api_key":"json-secret-value"}'
            answer = ai.chat(prompt)
            self.assertIn("transmission was blocked", answer)
            self.assertNotIn("json-secret-value", answer)
            self.assertNotIn("json-secret-value", (root / "memory" / "conversation.json").read_text(encoding="utf-8"))

            knowledge = KnowledgeBase(root / "knowledge" / "items.json")
            knowledge.add_text(prompt, "imported.json")
            stored = (root / "knowledge" / "items.json").read_text(encoding="utf-8")
            self.assertNotIn("json-secret-value", stored)
            self.assertIn("[REDACTED]", stored)


if __name__ == "__main__":
    unittest.main()

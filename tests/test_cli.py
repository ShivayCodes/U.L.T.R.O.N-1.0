import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class CliTests(unittest.TestCase):
    def test_direct_script_execution_explains_package_invocation(self):
        repository_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, str(repository_root / "ruller_ai" / "cli.py")],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("python -m ruller_ai", result.stderr)
        self.assertNotIn("attempted relative import", result.stderr)

    def test_api_key_command_line_option_is_not_supported(self):
        repository_root = Path(__file__).resolve().parent.parent
        secret = "never-print-this-token"
        result = subprocess.run(
            [sys.executable, "-m", "ruller_ai", "--api-key", secret],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()

import base64
import os
import tempfile
from pathlib import Path

test_data_dir = Path(tempfile.mkdtemp(prefix="voice-evals-tests-"))
os.environ.setdefault("VOICE_EVALS_ENV", "test")
os.environ.setdefault("VOICE_EVALS_DATABASE_URL", f"sqlite:///{test_data_dir / 'test.db'}")
os.environ.setdefault("VOICE_EVALS_ENABLE_TEST_PROVIDER", "true")
os.environ.setdefault(
    "VOICE_EVALS_ENCRYPTION_KEY",
    base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode(),
)

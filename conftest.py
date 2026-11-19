import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def trained_model():
    """Train the model once if models/risk_model.joblib does not exist yet."""
    import risk_model

    if not risk_model.MODEL_PATH.exists():
        subprocess.run([sys.executable, "train_model.py", "--data", "data/labeled_descriptions.csv"],
                       cwd=ROOT, check=True, capture_output=True)


@pytest.fixture()
def client():
    import ratelimit
    from fastapi.testclient import TestClient
    from main import app

    ratelimit.reset()
    with TestClient(app) as test_client:  # "with" runs the startup (model loading)
        yield test_client

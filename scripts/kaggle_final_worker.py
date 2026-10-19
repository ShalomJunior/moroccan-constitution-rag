"""Run the pinned PyTorch evaluation without XLA claiming the Kaggle GPUs."""

import json
import os
import sys
from pathlib import Path

# Kaggle includes JAX and TensorFlow. Keep their backends off the CUDA devices
# before importing the evaluation code or any of its dependencies.
os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["USE_FLAX"] = "0"
os.environ["USE_TF"] = "0"

from scripts.kaggle_final_runtime import execute  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.kaggle_final_worker ROOT")
    print(json.dumps(execute(Path(sys.argv[1]).resolve()), ensure_ascii=False, indent=2))

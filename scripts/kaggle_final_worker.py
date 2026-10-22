"""Run one resumable batch without XLA claiming the Kaggle GPUs."""

import argparse
import json
import os
from pathlib import Path

# Kaggle includes JAX and TensorFlow. Keep their backends off the CUDA devices
# before importing the evaluation code or any of its dependencies.
os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["USE_FLAX"] = "0"
os.environ["USE_TF"] = "0"

from scripts.kaggle_final_runtime import execute  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(execute(args.root.resolve(), max_new_fulltext=args.batch_size),
                     ensure_ascii=False, indent=2))

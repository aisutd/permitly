"""Run the statute demo with ``python -m permitly_rag`` from the repo root."""

from pathlib import Path
import runpy
import sys


if __name__ == '__main__':
    demo_dir = Path(__file__).resolve().parent / 'rag-model-ss-demo'
    sys.path.insert(0, str(demo_dir))
    runpy.run_path(str(demo_dir / 'main.py'), run_name='__main__')

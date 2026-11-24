"""Console entry point for the bundled offline Gateway."""
from pathlib import Path
import runpy
import sys


def main():
    gateway = Path(__file__).resolve().parent / "_bundle" / "discovery-kit"
    # Match the module search path of running the original script directly.
    sys.path.insert(0, str(gateway))
    runpy.run_path(str(gateway / "gateway_stdio.py"), run_name="__main__")

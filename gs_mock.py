import os
import sys

GS_BIN = os.path.join(os.path.dirname(__file__), "gs_bin.txt")
print("CHECK_GS_ENV", os.environ.get("PATH"), sys.executable)

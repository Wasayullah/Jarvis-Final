import os
import subprocess
import sys

ps = os.path.join("screenshots", "jarvis_ui_review.ps")
png = os.path.join("screenshots", "jarvis_ui_review.png")

cmd = ["magick", ps, "-resize", "1440x860", png]
print("Running:", " ".join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True)
print("exit:", r.returncode)
if r.stdout:
    print("stdout:", r.stdout)
if r.stderr:
    print("stderr:", r.stderr)
print("png exists:", os.path.exists(png))
if os.path.exists(png):
    print("size:", os.path.getsize(png))

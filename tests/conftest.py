import os
# Use offscreen rendering so widget tests run without a display (CI, headless Windows)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

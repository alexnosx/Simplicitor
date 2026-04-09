@echo off
REM Simplicitor build script (Windows convenience wrapper).
REM Run from the repository root.  Requires Python and Nuitka:
REM     pip install -r requirements-build.txt

python "%~dp0build.py" %*

@echo off
REM Builds standalone payload, current-user NSIS installer, and portable ZIP.
REM Requires Python and the pinned Nuitka build dependencies:
REM     pip install -r requirements-build.txt

pushd "%~dp0"
python "%~dp0build.py" %*
set "BUILD_RESULT=%ERRORLEVEL%"
popd
exit /b %BUILD_RESULT%

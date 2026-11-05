@echo off
REM Build LAN Share Hub for Windows. Requires Python 3.9+ (python.org) and optionally Inno Setup 6.
setlocal
cd /d "%~dp0"

if not exist .venv-win (
    python -m venv .venv-win || goto :error
)
call .venv-win\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || goto :error

pyinstaller --noconfirm --clean --distpath dist --workpath build build_tools\lan_share_hub.spec || goto :error
powershell -NoProfile -Command "Compress-Archive -Force -Path dist\LANShareHub -DestinationPath dist\LANShareHub-Windows-Portable.zip" || goto :error
echo  Portable: dist\LANShareHub-Windows-Portable.zip

set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    if defined APP_VERSION (
        %ISCC% /DAppVersion=%APP_VERSION% build_tools\installer.iss || goto :error
    ) else (
        %ISCC% build_tools\installer.iss || goto :error
    )
    echo  Installer: dist\LANShareHub-Windows-Setup.exe
) else (
    echo  Inno Setup not found - skipping installer. Get it from https://jrsoftware.org/isdl.php
)
exit /b 0

:error
echo Build failed.
exit /b 1

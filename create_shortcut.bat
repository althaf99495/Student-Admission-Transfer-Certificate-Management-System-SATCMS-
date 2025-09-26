@echo off

REM Set variables
set "VENV_PATH=C:\Users\altha\OneDrive\Documents\PROJECT\tc project\venv"
set "FLASK_APP_PATH=C:\Users\altha\OneDrive\Documents\PROJECT\tc project\app.py"
set "DESKTOP_PATH=C:\Users\altha\OneDrive\Desktop"
set "SHORTCUT_NAME= Student Registration & tc generation portal.lnk"
set "ICON_PATH=C:\Users\altha\OneDrive\Documents\PROJECT\tc project\app.ico"

REM Create temporary VBS file to create the shortcut
set "VBS_FILE=%TEMP%\create_shortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo sLinkFile = "%DESKTOP_PATH%\%SHORTCUT_NAME%" >> "%VBS_FILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_FILE%"
echo oLink.TargetPath = "cmd.exe" >> "%VBS_FILE%"
echo oLink.Arguments = "/k ""cd C:\Users\altha\OneDrive\Documents\PROJECT\tc project\ && call venv\Scripts\activate && waitress-serve --listen=0.0.0.0:8000 wsgi:app""" >> "%VBS_FILE%"
echo oLink.WorkingDirectory = "C:\Users\altha\OneDrive\Documents\PROJECT\tc project" >> "%VBS_FILE%"
echo oLink.WindowStyle = 1 >> "%VBS_FILE%"
echo oLink.IconLocation = "%ICON_PATH%" >> "%VBS_FILE%"
echo oLink.Save >> "%VBS_FILE%"

REM Run the VBS to create shortcut
cscript //nologo "%VBS_FILE%"

REM Clean up
del "%VBS_FILE%"

echo Shortcut created successfully on your desktop.
pause

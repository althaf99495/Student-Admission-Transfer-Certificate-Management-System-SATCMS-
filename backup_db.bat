@echo off
REM Change directory to the project folder to avoid issues with spaces in the path
pushd "c:\Users\altha\OneDrive\Documents\PROJECT\tc project"

REM Create Year and Month variables
set YEAR=%DATE:~10,4%
set MONTH=%DATE:~4,2%

REM Define the new year/month destination directory and create it
set DEST_DIR=.\backups\%YEAR%\%MONTH%
mkdir "%DEST_DIR%" >nul 2>nul

REM Set the source and full destination file paths with the new format: dbName_month_year.db
set SOURCE_DB=.\college.db
set DEST_DB=%DEST_DIR%\college_%MONTH%_%YEAR%.db

REM --- 1. Local Backup ---
echo Creating local backup...
copy "%SOURCE_DB%" "%DEST_DB%"
if %errorlevel% neq 0 (
    echo Local backup failed!
    popd
    exit /b %errorlevel%
)
echo Local backup complete: %DEST_DB%

REM --- 2. Google Drive Upload ---
echo Uploading to Google Drive...
REM Execute python script using relative paths, which is more robust
".\venv\Scripts\python.exe" ".\upload_to_drive.py" "%DEST_DB%"
if %errorlevel% neq 0 (
    echo Google Drive upload failed!
    popd
    exit /b %errorlevel%
)

echo All backup tasks complete.

REM Return to the original directory
popd

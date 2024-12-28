@echo off
setlocal EnableDelayedExpansion

rem ------------------------------------------------------------
rem LOGGING
rem ------------------------------------------------------------
set "LOG_FILE=build_log.txt"
echo -------------------- Build Started at %DATE% %TIME% -------------------- > "%LOG_FILE%"

rem ------------------------------------------------------------
rem 0. CONFIGURATION
rem ------------------------------------------------------------
set "ENV_NAME=abp_env"

rem List all required packages (space-separated).
set "PACKAGES=numpy plotly scipy wfdb PyWavelets PySide6 pyqtgraph pyinstaller python-dotenv"

rem ------------------------------------------------------------
rem 1. CHECK IF SCRIPT IS RUNNING INSIDE AN ACTIVE VIRTUAL ENV
rem ------------------------------------------------------------
rem Determine if a virtual environment is active
for /f "usebackq tokens=*" %%i in (`python -c "import sys; print(sys.prefix == sys.base_prefix)"`) do set "VENV_ACTIVE=%%i"

if "!VENV_ACTIVE!"=="True" (
    echo [INFO] A virtual environment is currently active.
    echo [INFO] A virtual environment is currently active. >> "%LOG_FILE%"
    rem Proceed without setting up a new environment
) else (
    echo [INFO] No virtual environment is active. Proceeding to set up "%ENV_NAME%"...
    echo [INFO] No virtual environment is active. Proceeding to set up "%ENV_NAME%"... >> "%LOG_FILE%"

    rem ------------------------------------------------------------
    rem 2. FORCE CURRENT WORKING DIRECTORY TO SCRIPT LOCATION
    rem ------------------------------------------------------------
    cd /d "%~dp0" || (
        echo [ERROR] Failed to change directory to script location.
        echo [ERROR] Failed to change directory to script location. >> "%LOG_FILE%"
        exit /b 1
    )
    
    rem ------------------------------------------------------------
    rem 3. CHECK SYSTEM PYTHON VERSION
    rem ------------------------------------------------------------
    where python > nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH. Please install Python 3.7 or later.
        echo [ERROR] Python is not installed or not in PATH. Please install Python 3.7 or later. >> "%LOG_FILE%"
        exit /b 1
    )

    rem Verify Python version is 3.7 or later
    for /f "tokens=1,2 delims=." %%a in ('python -c "import sys; print(sys.version_info.major, sys.version_info.minor)"') do (
        set "PY_MAJOR=%%a"
        set "PY_MINOR=%%b"
    )

    if "!PY_MAJOR!"=="" (
        echo [ERROR] Unable to determine Python version.
        echo [ERROR] Unable to determine Python version. >> "%LOG_FILE%"
        exit /b 1
    )

    if !PY_MAJOR! LSS 3 (
        echo [ERROR] Python 3.7 or later is required. Detected version: !PY_MAJOR!.!PY_MINOR!
        echo [ERROR] Python 3.7 or later is required. Detected version: !PY_MAJOR!.!PY_MINOR! >> "%LOG_FILE%"
        exit /b 1
    )

    if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 7 (
        echo [ERROR] Python 3.7 or later is required. Detected version: !PY_MAJOR!.!PY_MINOR!
        echo [ERROR] Python 3.7 or later is required. Detected version: !PY_MAJOR!.!PY_MINOR! >> "%LOG_FILE%"
        exit /b 1
    )

    echo [INFO] Detected Python version: !PY_MAJOR!.!PY_MINOR!
    echo [INFO] Detected Python version: !PY_MAJOR!.!PY_MINOR! >> "%LOG_FILE%"

    rem ------------------------------------------------------------
    rem 4. CREATE VIRTUAL ENV IF NEEDED
    rem ------------------------------------------------------------
    if exist "%ENV_NAME%\Scripts\python.exe" (
        echo [INFO] Virtual environment "%ENV_NAME%" already exists. Skipping creation...
        echo [INFO] Virtual environment "%ENV_NAME%" already exists. Skipping creation... >> "%LOG_FILE%"
    ) else (
        echo [INFO] Creating virtual environment: "%ENV_NAME%"...
        echo [INFO] Creating virtual environment: "%ENV_NAME%"... >> "%LOG_FILE%"
        python -m venv "%ENV_NAME%"
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to create virtual environment.
            echo [ERROR] Failed to create virtual environment. >> "%LOG_FILE%"
            exit /b 1
        )
    )

    rem ------------------------------------------------------------
    rem 5. UPGRADE PIP, SETUPTOOLS, AND WHEEL
    rem ------------------------------------------------------------
    echo [INFO] Upgrading pip, setuptools, and wheel in "%ENV_NAME%"...
    echo [INFO] Upgrading pip, setuptools, and wheel in "%ENV_NAME%"... >> "%LOG_FILE%"
    "%ENV_NAME%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to upgrade pip, setuptools, or wheel.
        echo [ERROR] Failed to upgrade pip, setuptools, or wheel. >> "%LOG_FILE%"
        exit /b 1
    )

    rem ------------------------------------------------------------
    rem 6. CHECK / INSTALL REQUIRED PACKAGES
    rem ------------------------------------------------------------
    set "NEED_INSTALL=0"

    echo [INFO] Checking required packages...
    echo [INFO] Checking required packages... >> "%LOG_FILE%"
    for %%I in (%PACKAGES%) do (
        "%ENV_NAME%\Scripts\python.exe" -m pip show %%I > nul 2>&1
        if !errorlevel! neq 0 (
            echo [INFO] Package "%%I" is missing.
            echo [INFO] Package "%%I" is missing. >> "%LOG_FILE%"
            set "NEED_INSTALL=1"
        )
    )

    if "!NEED_INSTALL!"=="1" (
        echo [INFO] Installing missing packages in "%ENV_NAME%"...
        echo [INFO] Installing missing packages in "%ENV_NAME%"... >> "%LOG_FILE%"
        "%ENV_NAME%\Scripts\python.exe" -m pip install %PACKAGES%
        set "PIP_EXIT_CODE=%errorlevel%"
        if !PIP_EXIT_CODE! neq 0 (
            echo [ERROR] Failed to install required packages with exit code !PIP_EXIT_CODE!.
            echo [ERROR] Failed to install required packages with exit code !PIP_EXIT_CODE!. >> "%LOG_FILE%"
            exit /b 1
        )
    ) else (
        echo [INFO] All required packages are already installed. Skipping installation...
        echo [INFO] All required packages are already installed. Skipping installation... >> "%LOG_FILE%"
    )

    rem ------------------------------------------------------------
    rem 7. ACTIVATE THE ENVIRONMENT
    rem ------------------------------------------------------------
    echo [INFO] Activating virtual environment...
    echo [INFO] Activating virtual environment... >> "%LOG_FILE%"
    call "%ENV_NAME%\Scripts\activate"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to activate the virtual environment.
        echo [ERROR] Failed to activate the virtual environment. >> "%LOG_FILE%"
        exit /b 1
    )

    echo [INFO] Virtual environment activated successfully!
    echo [INFO] Virtual environment activated successfully! >> "%LOG_FILE%"
)

rem ------------------------------------------------------------
rem PRESENT OPTIONS TO THE USER
rem ------------------------------------------------------------
:MENU
echo.
echo ================================================
echo          ABP Signal Viewer Setup
echo ================================================
echo Please choose an option:
echo   1. Run the application
echo   2. Build the executable
echo   3. Exit
set /p choice=Enter your choice (1/2/3): 

if "%choice%"=="1" goto RUN_APP
if "%choice%"=="2" goto BUILD_EXE
if "%choice%"=="3" goto END
echo [WARN] Invalid choice. Please select 1, 2, or 3.
echo [WARN] Invalid choice. Please select 1, 2, or 3. >> "%LOG_FILE%"
goto MENU

:RUN_APP
echo [INFO] Running the application...
echo [INFO] Running the application... >> "%LOG_FILE%"
if "!VENV_ACTIVE!"=="True" (
    rem Use the active virtual environment's Python
    python main.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to run main.py.
        echo [ERROR] Failed to run main.py. >> "%LOG_FILE%"
        pause
        exit /b 1
    )
) else (
    rem Use the script-managed virtual environment's Python
    "%ENV_NAME%\Scripts\python.exe" main.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to run main.py.
        echo [ERROR] Failed to run main.py. >> "%LOG_FILE%"
        pause
        exit /b 1
    )
)
goto END

:BUILD_EXE
echo [INFO] Building executable with PyInstaller...
echo [INFO] Building executable with PyInstaller... >> "%LOG_FILE%"

rem ------------------------------------------------------------
rem CLEAN PREVIOUS BUILDS (OPTIONAL)
rem ------------------------------------------------------------
echo [INFO] Cleaning previous PyInstaller builds (if any)...
echo [INFO] Cleaning previous PyInstaller builds (if any)... >> "%LOG_FILE%"
rmdir /s /q build > nul 2>&1
rmdir /s /q dist > nul 2>&1
del SignalViewer.spec > nul 2>&1

rem ------------------------------------------------------------
rem 8. BUILD EXE WITH PYINSTALLER
rem ------------------------------------------------------------
if exist "main.py" (
    echo [INFO] Found "main.py". Building exe with PyInstaller...
    echo [INFO] Found "main.py". Building exe with PyInstaller... >> "%LOG_FILE%"
    
    rem Ensure PyInstaller is installed
    if "!VENV_ACTIVE!"=="True" (
        rem Use active environment
        python -m pip show pyinstaller > nul 2>&1
        if %errorlevel% neq 0 (
            echo [INFO] PyInstaller not found in the active environment. Installing PyInstaller...
            echo [INFO] PyInstaller not found in the active environment. Installing PyInstaller... >> "%LOG_FILE%"
            python -m pip install pyinstaller
            if %errorlevel% neq 0 (
                echo [ERROR] Failed to install PyInstaller.
                echo [ERROR] Failed to install PyInstaller. >> "%LOG_FILE%"
                exit /b 1
            )
        )
    ) else (
        rem Use script-managed environment
        "%ENV_NAME%\Scripts\python.exe" -m pip show pyinstaller > nul 2>&1
        if %errorlevel% neq 0 (
            echo [INFO] PyInstaller not found. Installing PyInstaller...
            echo [INFO] PyInstaller not found. Installing PyInstaller... >> "%LOG_FILE%"
            "%ENV_NAME%\Scripts\python.exe" -m pip install pyinstaller
            if %errorlevel% neq 0 (
                echo [ERROR] Failed to install PyInstaller.
                echo [ERROR] Failed to install PyInstaller. >> "%LOG_FILE%"
                exit /b 1
            )
        )
    )
    
    rem Build the executable
    echo [INFO] Building the executable...
    echo [INFO] Building the executable... >> "%LOG_FILE%"
    
    if "!VENV_ACTIVE!"=="True" (
        rem Use active environment's PyInstaller
        pyinstaller --onefile --windowed --noupx --name "SignalViewer" main.py
    ) else (
        rem Use script-managed environment's PyInstaller
        "%ENV_NAME%\Scripts\pyinstaller.exe" --onefile --windowed --noupx --name "SignalViewer" main.py
    )
    
    if %errorlevel% neq 0 (
        echo [ERROR] PyInstaller build failed.
        echo [ERROR] PyInstaller build failed. >> "%LOG_FILE%"
        pause
        exit /b 1
    ) else (
        echo [INFO] Build complete! Check the "dist" folder for the exe.
        echo [INFO] Build complete! Check the "dist" folder for the exe. >> "%LOG_FILE%"
    )
) else (
    echo [WARN] "main.py" not found in this directory. Skipping build.
    echo [WARN] "main.py" not found in this directory. Skipping build. >> "%LOG_FILE%"
)

goto END

:END
echo.
echo [INFO] Process completed.
echo [INFO] Process completed. >> "%LOG_FILE%"
echo To activate this environment manually in the future, run:
echo   call "%ENV_NAME%\Scripts\activate"
echo To activate this environment manually in the future, run: >> "%LOG_FILE%"
echo   call "%ENV_NAME%\Scripts\activate" >> "%LOG_FILE%"
echo.
pause

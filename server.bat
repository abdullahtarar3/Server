@echo off
setlocal enabledelayedexpansion
title File Server Startup

:: ============================================================================
::                           FILE SERVER STARTUP SCRIPT
:: ============================================================================
:: Author: Abdullah Tarar
:: GitHub: https://github.com/abdullahtarar3
:: Instagram: @abdullahtarar.3
:: 
:: This script automates the setup and launch of a Flask-based file server
:: with interactive network configuration and dependency management.
:: ============================================================================

:: Display header with developer information
echo.
echo ============================================================================
echo                           FILE SERVER STARTUP
echo ============================================================================
echo.
echo Developer: Abdullah Tarar
echo GitHub   : https://github.com/abdullahtarar3
echo Instagram: @abdullahtarar.3
echo.
echo ============================================================================
echo.

:: Step 1: Python Verification
echo [STEP 1/7] Checking Python installation...
echo ----------------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python from https://python.org and ensure it's added to PATH
    echo Press any key to exit...
    pause >nul
    exit /b 1
) else (
    echo [SUCCESS] Python is installed:
    python --version
    echo.
)

:: Step 2: Dependency Management
echo [STEP 2/7] Installing/Updating dependencies...
echo ----------------------------------------------------------------------------
echo Installing Flask...
pip install flask --quiet --upgrade
if errorlevel 1 (
    echo [WARNING] Failed to install Flask. Continuing anyway...
) else (
    echo [SUCCESS] Flask installed/updated successfully
)
echo.

:: Step 3: Network Interface Detection
echo [STEP 3/7] Detecting network interfaces...
echo ----------------------------------------------------------------------------
set count=0
set /a optionCount=0

echo Available network interfaces:
echo.

:: Parse ipconfig output to find IPv4 addresses
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set ip=%%a
    set ip=!ip: =!
    if not "!ip!"=="" (
        set /a count+=1
        set ip!count!=!ip!
        echo !count!. !ip!
    )
)

if !count! equ 0 (
    echo [ERROR] No network interfaces found!
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo.
set /a count+=1
echo !count!. Enter custom IP address
echo.

:: Step 4: Interactive IP Selection
echo [STEP 4/7] Network configuration...
echo ----------------------------------------------------------------------------
:ip_selection
set /p choice="Select network interface (1-!count!): "

:: Validate choice
if "!choice!"=="" goto ip_selection
if !choice! lss 1 goto invalid_ip_choice
if !choice! gtr !count! goto invalid_ip_choice

:: Handle custom IP entry
if !choice! equ !count! (
    echo.
    set /p custom_ip="Enter IP address: "
    if "!custom_ip!"=="" goto ip_selection
    set selected_ip=!custom_ip!
    goto port_selection
)

:: Use selected predefined IP
set selected_ip=!ip%choice%!
goto port_selection

:invalid_ip_choice
echo [ERROR] Invalid choice. Please select a number between 1 and !count!
goto ip_selection

:: Step 5: Port Configuration
:port_selection
echo.
echo [STEP 5/7] Port configuration...
echo ----------------------------------------------------------------------------
set /p port="Enter port number (default: 50588): "
if "!port!"=="" set port=50588

:: Validate port number
echo !port! | findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo [ERROR] Invalid port number. Using default port 50588
    set port=50588
)

if !port! lss 1024 (
    echo [WARNING] Port !port! is below 1024. This may require administrator privileges.
)

if !port! gtr 65535 (
    echo [ERROR] Port number too high. Using default port 50588
    set port=50588
)

echo [SUCCESS] Selected configuration:
echo   IP Address: !selected_ip!
echo   Port: !port!
echo.

:: Step 6: Configuration File Creation
echo [STEP 6/7] Creating configuration file...
echo ----------------------------------------------------------------------------
(
    echo {
    echo   "host": "!selected_ip!",
    echo   "port": !port!,
    echo   "debug": false,
    echo   "created_at": "!date! !time!",
    echo   "created_by": "File Server Startup Script v1.0"
    echo }
) > server_config.json

if exist server_config.json (
    echo [SUCCESS] Configuration saved to server_config.json
) else (
    echo [ERROR] Failed to create configuration file
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo.

:: Step 7: Application Management and Launch
echo [STEP 7/7] Starting file server...
echo ----------------------------------------------------------------------------

:: Check for main application file
if not exist app.py (
    echo [INFO] app.py not found. Checking for enhanced_file_server.py...
    if exist enhanced_file_server.py (
        echo [INFO] Copying enhanced_file_server.py to app.py...
        copy enhanced_file_server.py app.py >nul
        if errorlevel 1 (
            echo [ERROR] Failed to copy enhanced_file_server.py
            goto missing_app_error
        )
        echo [SUCCESS] File copied successfully
    ) else (
        goto missing_app_error
    )
)

:: Final server launch information
echo.
echo ============================================================================
echo                              SERVER STARTING
echo ============================================================================
echo.
echo Server Configuration:
echo   Host: !selected_ip!
echo   Port: !port!
echo.
echo Access URLs:
echo   Local:   http://localhost:!port!
echo   Network: http://!selected_ip!:!port!
echo.
echo Default Credentials:
echo   Username: admin
echo   Password: 1234
echo.
echo Instructions:
echo   - Open the URL in your web browser
echo   - Use Ctrl+C to stop the server
echo   - Close this window to terminate the server
echo.
echo ============================================================================
echo.

:: Launch the Flask server
echo [INFO] Launching Flask server...
echo.
python app.py
goto end

:missing_app_error
echo [ERROR] Required Python application files not found!
echo.
echo Missing files:
echo   - app.py (main application)
echo   - enhanced_file_server.py (backup application)
echo.
echo Please ensure the Flask application file is present in this directory.
echo.
goto end

:end
echo.
echo ============================================================================
echo                              SERVER STOPPED
echo ============================================================================
echo.
echo Server has been terminated.
echo Configuration saved in: server_config.json
echo.
echo Thank you for using File Server!
echo.
echo Developer: Abdullah Tarar
echo GitHub   : https://github.com/abdullahtarar3
echo Instagram: @abdullahtarar.3
echo.
echo Press any key to exit...
pause >nul
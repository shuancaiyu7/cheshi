@echo off
setlocal
cd /d "%~dp0"

echo Starting ecommerce dashboard...
start "Streamlit" cmd /c python -m streamlit run app.py

powershell -NoProfile -Command "$ready=$false; for ($i=0; $i -lt 30; $i++) { try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8501' -TimeoutSec 1; if ($response.StatusCode -ge 200) { $ready = $true; break } } catch { Start-Sleep -Seconds 1 } }; if ($ready) { Start-Process 'http://localhost:8501' } else { Write-Host 'Streamlit did not become ready in time.'; exit 1 }"

if errorlevel 1 (
    echo.
    echo Failed to start or open the browser. Check the Streamlit window for errors.
    pause
)

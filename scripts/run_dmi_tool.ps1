# PowerShell launcher script for DMI Tool using virtual environment
Set-Location (Split-Path $PSScriptRoot)
& ".venv\Scripts\python.exe" mainApp.pyw


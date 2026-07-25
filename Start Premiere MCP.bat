@echo off
REM Double-click to launch Premiere Pro with the MCP bridge and start the
REM backend services. See scripts\launch-premiere-mcp.ps1 for what it does
REM and why the CEP cache has to be cleared first.
REM
REM If Premiere is already open this stops and tells you to quit it first,
REM because CEP decides whether the extension may load during startup.
REM Add -Force to close Premiere automatically (save your work first).

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-premiere-mcp.ps1" %*
pause

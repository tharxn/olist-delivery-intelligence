param([string]$PythonPath = "")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $PythonPath) {
    $projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $workspacePython = Join-Path $PSScriptRoot '..\..\work\.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $projectPython) { $PythonPath = $projectPython }
    elseif (Test-Path -LiteralPath $workspacePython) { $PythonPath = (Resolve-Path -LiteralPath $workspacePython).Path }
    else { $PythonPath = 'python' }
}
if (-not (Test-Path -LiteralPath 'data\processed\olist.duckdb')) {
    & $PythonPath run_project.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $PythonPath -m streamlit run app.py

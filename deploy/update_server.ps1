# Push the CURRENT local code to the live server and rebuild. No password (uses deploy\.vultr_deploy_key).
#   powershell -ExecutionPolicy Bypass -File deploy\update_server.ps1
param([string]$Ip = "137.220.52.182")
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$key = (Resolve-Path "deploy\.vultr_deploy_key").Path
icacls $key /inheritance:r | Out-Null
icacls $key /grant:r "$($env:USERNAME):(R)" | Out-Null
$sshOpts = @("-i", $key, "-o", "IdentitiesOnly=yes", "-o", "PasswordAuthentication=no", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR")
$keyArgs = ($sshOpts | ForEach-Object { "`"$_`"" }) -join " "

Write-Host "==> Packing code (data/ and .env stay on the server)" -ForegroundColor Yellow
if (Test-Path servaai_code.tgz) { Remove-Item servaai_code.tgz }
tar -czf servaai_code.tgz --exclude=node_modules --exclude=.venv --exclude=__pycache__ --exclude=.git --exclude=data --exclude=backend/.env --exclude=deploy/.vultr_deploy_key --exclude=servaai_code.tgz --exclude=servaai_payload.tgz .
if ($LASTEXITCODE -ne 0) { throw "Packing failed." }

Write-Host "==> Uploading and unpacking on the server" -ForegroundColor Yellow
cmd /c "ssh $keyArgs root@$Ip ""cd /opt/servaai && tar xzf -"" < servaai_code.tgz"
if ($LASTEXITCODE -ne 0) { throw "Upload failed. Scroll up for the error." }

Write-Host "==> Rebuilding (a minute or two)" -ForegroundColor Yellow
ssh -t @sshOpts "root@$Ip" "cd /opt/servaai && docker compose up -d --build && for i in `$(seq 1 36); do curl -fsS http://127.0.0.1:8000/api/health && exit 0; sleep 5; done; docker compose logs --tail 60; exit 1"
if ($LASTEXITCODE -ne 0) { throw "Rebuild failed. Scroll up; run: ssh -i deploy\.vultr_deploy_key root@$Ip 'cd /opt/servaai && docker compose logs --tail 80'" }
Remove-Item servaai_code.tgz -ErrorAction SilentlyContinue
Write-Host "`nDone. https://servaai.us is running the new code." -ForegroundColor Green

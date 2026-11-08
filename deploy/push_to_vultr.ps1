# One command from the repo folder on your PC (PowerShell). No password needed: it uses deploy\.vultr_deploy_key.
#   powershell -ExecutionPolicy Bypass -File deploy\push_to_vultr.ps1 -Email you@example.com
param(
  [Parameter(Mandatory = $true)][string]$Email,
  [string]$Ip = "137.220.52.182"
)
$ErrorActionPreference = "Continue"  # native-command warnings on stderr must not abort; exit codes are checked below
Set-Location (Split-Path $PSScriptRoot -Parent)
foreach ($f in @("data\monthly_summary.csv", "backend\.env", "deploy\.vultr_deploy_key")) {
  if (-not (Test-Path $f)) { throw "Missing $f. Run this from the repo folder that has data\, backend\.env and the deploy key." }
}
$key = (Resolve-Path "deploy\.vultr_deploy_key").Path
# OpenSSH on Windows refuses keys other users can read
icacls $key /inheritance:r | Out-Null
icacls $key /grant:r "$($env:USERNAME):(R)" | Out-Null
$sshOpts = @("-i", $key, "-o", "IdentitiesOnly=yes", "-o", "PasswordAuthentication=no", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR")

Write-Host "==> Packing data and .env" -ForegroundColor Yellow
if (Test-Path servaai_payload.tgz) { Remove-Item servaai_payload.tgz }
tar -czf servaai_payload.tgz data backend/.env

Write-Host "==> Waiting for the server to accept the key" -ForegroundColor Yellow
$ok = $false
for ($i = 0; $i -lt 20 -and -not $ok; $i++) {
  ssh @sshOpts "root@$Ip" "echo ready" 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $ok = $true } else { Start-Sleep -Seconds 6 }
}
if (-not $ok) { throw "Server never accepted the key. Check the IP and that the instance shows Running in Vultr." }

Write-Host "==> Uploading (about 30 MB)" -ForegroundColor Yellow
$keyArgs = ($sshOpts | ForEach-Object { "`"$_`"" }) -join " "
cmd /c "ssh $keyArgs root@$Ip ""mkdir -p /opt/servaai && tar xzf - -C /opt/servaai"" < servaai_payload.tgz"
if ($LASTEXITCODE -ne 0) { throw "Upload failed. Scroll up for the error." }

Write-Host "==> Installing and starting (first Docker build takes a few minutes)" -ForegroundColor Yellow
$remote = "test -f /opt/servaai/data/monthly_summary.csv && curl -fsSLo /root/setup_vultr.sh https://raw.githubusercontent.com/SqualidRat560/servaai/main/deploy/setup_vultr.sh && bash /root/setup_vultr.sh $Email"
ssh -t @sshOpts "root@$Ip" $remote
if ($LASTEXITCODE -ne 0) { throw "Setup failed on the server. Scroll up for the error." }
Remove-Item servaai_payload.tgz -ErrorAction SilentlyContinue
Write-Host "Done. Open http://$Ip  (https://servaai.us once DNS has caught up)." -ForegroundColor Green

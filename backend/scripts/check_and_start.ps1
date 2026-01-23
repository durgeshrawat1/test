# Usage: run from repository root; script will run in this folder
try {
  # Quick health check
  $h = Invoke-RestMethod -UseBasicParsing http://127.0.0.1:8000/healthz -TimeoutSec 2 -ErrorAction Stop
  Write-Output "HEALTH_OK"
  $h | ConvertTo-Json -Depth 5 | Write-Output
} catch {
  Write-Output "Backend not responding, starting uvicorn..."
  Start-Process -FilePath python -ArgumentList '-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Get-Location) -NoNewWindow -PassThru | Out-Null
  Start-Sleep -Seconds 3
  try {
    $h = Invoke-RestMethod -UseBasicParsing http://127.0.0.1:8000/healthz -TimeoutSec 5 -ErrorAction Stop
    Write-Output "HEALTH_OK"
    $h | ConvertTo-Json -Depth 5 | Write-Output
  } catch {
    Write-Output "HEALTH_FAIL"
  }
}

# Prepare a test token (unsigned) and call metadata/groups
$p='{"username":"tester","email":"tester@example.com","cognito:groups":["Finance"]}'
$b=[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($p))
$b=$b.Replace('+','-').Replace('/','_').TrimEnd('=')
$tok = 'aaa.'+$b+'.bbb'
try {
  $res = Invoke-RestMethod -UseBasicParsing -Headers @{ 'x-amzn-oidc-data' = $tok } http://127.0.0.1:8000/api/metadata/groups -TimeoutSec 10 -ErrorAction Stop
  $res | ConvertTo-Json -Depth 5 | Write-Output
} catch {
  Write-Output 'GROUPS_FAIL'
  $_ | Out-String | Write-Output
}

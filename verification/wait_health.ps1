while ($true) {
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
        if ($res.StatusCode -eq 200) {
            Write-Host "Health OK!"
            break
        }
    } catch {}
    Start-Sleep -Seconds 5
}

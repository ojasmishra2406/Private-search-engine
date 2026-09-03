docker compose build backend
docker compose up -d

Write-Host "Waiting for health..."
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

Write-Host "Crawling..."
$body = @{ url="https://docs.pytest.org/en/stable/"; max_pages=10; max_depth=2; same_domain_only=$true } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8000/crawl" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing

Write-Host "Searching immediately..."
Invoke-WebRequest -Uri "http://localhost:8000/search?q=pytest&top_k=2" -UseBasicParsing | Select-Object -ExpandProperty Content

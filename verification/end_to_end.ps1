Write-Host "Waiting for backend health..."
while ($true) {
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
        if ($res.StatusCode -eq 200) {
            Write-Host "Backend is healthy!"
            Write-Host $res.Content
            break
        }
    } catch {}
    Start-Sleep -Seconds 5
}

Write-Host "
--- Crawling Pytest Docs ---"
$body = @{ url="https://docs.pytest.org/en/stable/"; max_pages=10; max_depth=2; same_domain_only=$true } | ConvertTo-Json
$crawlRes = Invoke-WebRequest -Uri "http://localhost:8000/crawl" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
Write-Host $crawlRes.Content

Write-Host "
--- Testing Immediate Search ---"
$searchRes = Invoke-WebRequest -Uri "http://localhost:8000/search?q=pytest" -UseBasicParsing
Write-Host "BM25 Results:" ($searchRes.Content | ConvertFrom-Json).results.Length

$denseRes = Invoke-WebRequest -Uri "http://localhost:8000/dense-search?q=pytest" -UseBasicParsing
Write-Host "Dense Results:" ($denseRes.Content | ConvertFrom-Json).results.Length

$hybridRes = Invoke-WebRequest -Uri "http://localhost:8000/hybrid-search?q=pytest" -UseBasicParsing
Write-Host "Hybrid Results:" ($hybridRes.Content | ConvertFrom-Json).results.Length

$rerankRes = Invoke-WebRequest -Uri "http://localhost:8000/reranked-search?q=pytest" -UseBasicParsing
Write-Host "Reranked Results:" ($rerankRes.Content | ConvertFrom-Json).results.Length

Write-Host "
--- Checking Parity ---"
python verification/test_parity.py


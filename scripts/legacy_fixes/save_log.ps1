$log = "C:\Users\mishr\.gemini\antigravity\brain\78c48645-cd75-42a9-829c-292a3f81fa24\.system_generated\tasks\task-7015.log"
while ($true) {
    if (Select-String -Path $log -Pattern "256 passed" -Quiet) {
        Copy-Item $log "docs/proofs/perfect_suite.txt"
        break
    }
    Start-Sleep -Seconds 2
}

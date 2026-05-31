param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$SessionId = "manual-demo",
    [string]$Query = "legal citation risk"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-ResearchOSJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $params = @{
        Method = $Method
        Uri = "$BaseUrl$Path"
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    Invoke-RestMethod @params
}

Write-Step "Checking API readiness"
$ready = Invoke-ResearchOSJson -Method Get -Path "/readyz"
$ready | ConvertTo-Json -Depth 10

Write-Step "Creating a corpus document"
$created = Invoke-ResearchOSJson -Method Post -Path "/v1/corpus/documents" -Body @{
    path = "demo/legal-citation-risk.md"
    title = "Legal Citation Risk"
    text = "Unsupported citations create legal research risk. Citation verification reduces hallucinated legal claims."
    overwrite = $true
}
$created | ConvertTo-Json -Depth 10

Write-Step "Listing corpus files"
$corpus = Invoke-ResearchOSJson -Method Get -Path "/v1/corpus"
$corpus | ConvertTo-Json -Depth 10

Write-Step "Reading the corpus document"
$encodedPath = [System.Uri]::EscapeDataString("demo/legal-citation-risk.md")
$content = Invoke-ResearchOSJson -Method Get -Path "/v1/corpus/content?path=$encodedPath"
$content | ConvertTo-Json -Depth 10

Write-Step "Creating a research run that includes the corpus"
$runResponse = Invoke-ResearchOSJson -Method Post -Path "/v1/research-runs" -Body @{
    session_id = $SessionId
    query = $Query
    options = @{
        include_corpus = $true
    }
}
$runResponse | ConvertTo-Json -Depth 10

$runId = $runResponse.run_id
Write-Step "Polling research run: $runId"
do {
    Start-Sleep -Milliseconds 500
    $run = Invoke-ResearchOSJson -Method Get -Path "/v1/research-runs/$runId"
    Write-Host "status=$($run.status) step=$($run.current_step)"
} while ($run.status -notin @("completed", "failed", "cancelled"))

Write-Step "Workflow trace"
$trace = Invoke-ResearchOSJson -Method Get -Path "/v1/research-runs/$runId/trace"
$trace.summary | ConvertTo-Json -Depth 10

Write-Step "Evidence sources"
$sources = Invoke-ResearchOSJson `
    -Method Get `
    -Path "/v1/research-runs/$runId/artifacts/content?path=evidence%2Fsources.json"
$sources | ConvertTo-Json -Depth 10

Write-Step "Report markdown"
$report = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/v1/research-runs/$runId/artifacts/content?path=outputs%2Freport.md"
$report

Write-Step "Done"
Write-Host "Run ID: $runId"

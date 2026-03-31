param(
    [Parameter(Mandatory=$true)][string]$InputPath
)

$data = Get-Content $InputPath | ConvertFrom-Json

Write-Host ("total " + $data.Count)

Write-Host "quality counts:"
$data | Group-Object quality_tier | ForEach-Object {
    Write-Host ("  " + $_.Name + ": " + $_.Count)
}

Write-Host "top states:"
$data | Group-Object state | Sort-Object Count -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Host ("  " + $_.Name + ": " + $_.Count)
}

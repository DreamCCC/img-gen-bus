$dst = "C:\Users\Administrator\mgs-code-01\nba-tactics\spurs_g4\film\assets\music"
$titles = "Long Note Three", "Ominous Intro", "Montauk Point", "Loopster", "Invariance", "Industrial Cinematic",
          "The Escalation", "Constance", "Stay the Course", "Enter the Maze", "Calmant", "Danse Morialta"
foreach ($t in $titles) {
    $file = Join-Path $dst (($t -replace ' ', '_') + ".mp3")
    if (Test-Path $file) { "have $t"; continue }
    $url = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + [uri]::EscapeDataString($t) + ".mp3"
    curl.exe -s -L -f -o $file $url
    if ($LASTEXITCODE -eq 0) { "ok   $t  " + (Get-Item $file).Length } else { "FAIL $t ($url)"; Remove-Item $file -ErrorAction SilentlyContinue }
}

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
Set-Location C:\Users\Administrator\mgs-code-01\nba-tactics\spurs_g4
$py = "C:\Users\Administrator\mgs-code-01\nba-tactics\.venv\Scripts\python.exe"
$rp = "..\tools\render_play.py"
Copy-Item work/e13/mix.wav work/e13/mix.wav.bak -Force
Copy-Item work/e88/mix.wav work/e88/mix.wav.bak -Force

$chains = @(
  @('e676w_s08_edl.json', 'e676w_s06_edl.json'),
  @('e727w_s16_edl.json', 'e727w_s01_edl.json'),
  @('e13_s04r_edl.json'), @('e88_s04r_edl.json'),
  @('s09r_613_edl.json'), @('s09r_554_edl.json')
)
$jobs = foreach ($c in $chains) {
  Start-Job -ArgumentList $py, $rp, $c, (Get-Location).Path -ScriptBlock {
    param($py, $rp, $c, $wd)
    Set-Location $wd
    $env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
    foreach ($e in $c) { & $py $rp $e 2>&1 | Select-Object -Last 1 | ForEach-Object { "$e : $_" } }
  }
}
$jobs | Wait-Job | Receive-Job
Move-Item work/e13/mix.wav.bak work/e13/mix.wav -Force
Move-Item work/e88/mix.wav.bak work/e88/mix.wav -Force
& $py film/out/s04r/_tools/montage_fz.py s04r_montage.json 2>&1 | Select-Object -Last 1
& $py work/s09r/assemble.py film/out/s09r/s09r.mp4 2>&1 | Select-Object -Last 1
foreach ($f in 'film/out/s01_ar/s01_ar.mp4','film/out/s04r/s04r.mp4','film/out/s06_ar/s06_ar.mp4','film/out/s08_ar/s08_ar.mp4','film/out/s09r/s09r.mp4','film/out/s16_ar/s16_ar.mp4') {
  "$f " + ((ffprobe -v error -show_entries stream=codec_type,nb_frames -of csv=p=0 $f) -join ' ')
}

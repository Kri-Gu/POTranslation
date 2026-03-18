# Compile all translated .po files to .mo files using polib
# Run from the project root with the venv activated

$python = "c:\01. Development\translate_poedit\venv\Scripts\python.exe"

$folders = @(
    "c:\01. Development\translate_poedit\Internal_documentation\Language files\ariens-lang\Translated",
    "c:\01. Development\translate_poedit\Internal_documentation\Language files\as-motor-lang\Translated"
)

$compiled = 0
$skipped  = 0
$failed   = 0

foreach ($folder in $folders) {
    $label = Split-Path (Split-Path $folder -Parent) -Leaf
    Write-Host "`n========================================" -ForegroundColor Yellow
    Write-Host " $label" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow

    $poFiles = Get-ChildItem -Path $folder -Filter "*.po" -File
    foreach ($file in $poFiles) {
        $moFile = [System.IO.Path]::ChangeExtension($file.FullName, ".mo")

        if (Test-Path $moFile) {
            Write-Host "  SKIP  $($file.Name) (already compiled)" -ForegroundColor DarkGray
            $skipped++
            continue
        }

        # Use polib via Python to compile
        $result = & $python -c @"
import polib, sys
try:
    po = polib.pofile(r'$($file.FullName)', encoding='utf-8')
    po.save_as_mofile(r'$moFile')
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK    $($file.Name) -> $([System.IO.Path]::GetFileName($moFile))" -ForegroundColor Green
            $compiled++
        } else {
            Write-Host "  FAIL  $($file.Name): $result" -ForegroundColor Red
            $failed++
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Compiled : $compiled" -ForegroundColor Green
Write-Host "  Skipped  : $skipped" -ForegroundColor DarkGray
Write-Host "  Failed   : $failed" $(if ($failed -gt 0) { "[ForegroundColor]Red" }) -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "White" })
Write-Host ""

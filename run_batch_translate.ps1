# Batch translation runner
# Usage: run in project root with the venv activated

$python = "c:\01. Development\translate_poedit\venv\Scripts\python.exe"
$script = "c:\01. Development\translate_poedit\src\po_translate_en_to_nb.py"
$model  = "gpt-5.2"
$batch  = "20"

# ── Helper: extract language code from filename stem ──────────────────────────
function Get-LangCode([string]$stem) {
    # e.g. cs_CZ → cs  |  el_GR → el  |  hr → hr  |  me_ME → me
    return $stem.ToLower().Split("_")[0]
}

# ── Process one folder ────────────────────────────────────────────────────────
function Translate-Folder([string]$inputDir, [string]$outputDir) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $poFiles = Get-ChildItem -Path $inputDir -Filter "*.po" -File
    foreach ($file in $poFiles) {
        $stem    = $file.BaseName                    # e.g. cs_CZ
        $lang    = Get-LangCode $stem                # e.g. cs
        $outFile = Join-Path $outputDir "translated_${lang}_${stem}.po"

        Write-Host ""

        if (Test-Path $outFile) {
            Write-Host "=== [$lang] $($file.Name) -> SKIPPED (already exists) ===" -ForegroundColor DarkGray
            continue
        }

        Write-Host "=== [$lang] $($file.Name) -> $outFile ===" -ForegroundColor Cyan

        & $python $script $file.FullName $outFile `
            --model       $model `
            --batch-size  $batch `
            --source-lang auto `
            --target-lang $lang

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  !! FAILED for $($file.Name) (exit $LASTEXITCODE)" -ForegroundColor Red
        }
    }
}

# ── Ariens-lang ───────────────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host " ARIENS-LANG" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Translate-Folder `
    "c:\01. Development\translate_poedit\Internal_documentation\Language files\ariens-lang" `
    "c:\01. Development\translate_poedit\Internal_documentation\Language files\ariens-lang\Translated"

# ── AS-Motor-lang ─────────────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host " AS-MOTOR-LANG" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Translate-Folder `
    "c:\01. Development\translate_poedit\Internal_documentation\Language files\as-motor-lang" `
    "c:\01. Development\translate_poedit\Internal_documentation\Language files\as-motor-lang\Translated"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host " ALL DONE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

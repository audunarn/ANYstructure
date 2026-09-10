param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repository = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$setupText = Get-Content -LiteralPath (Join-Path $repository "setup.py") -Raw
$versionMatch = [regex]::Match($setupText, "version='([^']+)'")
if (-not $versionMatch.Success) {
    throw "Unable to read the ANYstructure version from setup.py"
}
$version = $versionMatch.Groups[1].Value
$distRoot = Join-Path $repository "dist"
$workRoot = Join-Path $repository "build\pyinstaller"
$bundle = Join-Path $distRoot "ANYstructure"
$archive = Join-Path $repository "dist\ANYstructure-$version-windows-x86_64.zip"
$checksum = "$archive.sha256"

Push-Location $repository
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath $distRoot `
        --workpath $workRoot `
        ANYstructure.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    $selfTest = Start-Process `
        -FilePath (Join-Path $bundle "ANYstructure.exe") `
        -ArgumentList "--self-test" `
        -Wait `
        -PassThru `
        -WindowStyle Hidden
    if ($selfTest.ExitCode -ne 0) {
        throw "Packaged self-test failed with exit code $($selfTest.ExitCode)"
    }

    Compress-Archive -LiteralPath $bundle -DestinationPath $archive -CompressionLevel Optimal -Force
    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $([IO.Path]::GetFileName($archive))" | Set-Content -LiteralPath $checksum -Encoding ascii

    Write-Output "Bundle: $bundle"
    Write-Output "Archive: $archive"
    Write-Output "SHA256: $hash"
}
finally {
    Pop-Location
}

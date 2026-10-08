# Installer qualification is destructive to its test installation. Never run on a local PC.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_OS -cne 'Windows' -or
    $env:RUNNER_ENVIRONMENT -cne 'github-hosted') {
    throw 'Installer qualification requires a hosted GitHub Actions Windows runner.'
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $repoRoot 'dist'
$setup = Join-Path $dist 'Simplicitor-setup.exe'
$installDir = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs/Simplicitor'))
$installedExe = Join-Path $installDir 'Simplicitor.exe'
$uninstaller = Join-Path $installDir 'uninstall.exe'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Simplicitor'
$settingsPath = Join-Path $env:APPDATA 'Simplicitor/settings.json'
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'Simplicitor.lnk'
$startShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Simplicitor.lnk'
$checks = [Collections.Generic.List[string]]::new()

function Assert-Check([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $checks.Add($Name)
    Write-Host "PASS: $Name"
}

function Invoke-Setup {
    $process = Start-Process -FilePath $setup -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    Assert-Check ($process.ExitCode -eq 0) 'Silent installer exited successfully'
}

function Assert-Installation {
    Assert-Check (Test-Path -LiteralPath $installedExe -PathType Leaf) 'Dedicated per-user install exists'
    Assert-Check (Test-Path -LiteralPath $uninstaller -PathType Leaf) 'Uninstaller exists'
    Assert-Check ((Get-Item -LiteralPath $installedExe).VersionInfo.ProductVersion -eq '2.0.0.0') `
        'Installed product version is 2.0.0.0'
    $registration = Get-ItemProperty -LiteralPath $uninstallKey
    Assert-Check ([IO.Path]::GetFullPath($registration.InstallLocation) -eq $installDir) `
        'HKCU uninstall entry points to dedicated folder'
    Assert-Check ($registration.DisplayVersion -eq '2.0.0.0') 'HKCU uninstall version matches'
    $shell = New-Object -ComObject WScript.Shell
    foreach ($shortcut in @($desktopShortcut, $startShortcut)) {
        Assert-Check (Test-Path -LiteralPath $shortcut -PathType Leaf) 'Installer shortcut exists'
        Assert-Check ($shell.CreateShortcut($shortcut).TargetPath -eq $installedExe) `
            'Installer shortcut targets installed app'
    }
}

# Refuse pre-existing state rather than cleaning up an unrelated installation/profile.
foreach ($path in @($installDir, $uninstallKey, $settingsPath, $desktopShortcut, $startShortcut)) {
    if (Test-Path -LiteralPath $path) { throw 'Qualification requires a fresh runner profile.' }
}
$manifest = Get-Content -LiteralPath (Join-Path $dist 'SHA256SUMS.json') -Raw | ConvertFrom-Json
$artifactHashes = [ordered]@{}
foreach ($name in @('Simplicitor-setup.exe', 'Simplicitor-portable.zip')) {
    $hash = (Get-FileHash -LiteralPath (Join-Path $dist $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    Assert-Check ($hash -eq $manifest.artifacts.$name) "Artifact hash matches: $name"
    $artifactHashes[$name] = $hash
}

# No Ollama install or service manipulation. The app must survive its absence.
$client = [Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(2)
$client.DefaultRequestHeaders.ConnectionClose = $true
$ollamaResponds = $false
try {
    $response = $client.GetAsync('http://127.0.0.1:11434/api/version').GetAwaiter().GetResult()
    $ollamaResponds = $true
    $response.Dispose()
} catch [Net.Http.HttpRequestException] {
    # Connection refused: the expected runner state.
} catch [Threading.Tasks.TaskCanceledException] {
    # No response within the short probe timeout.
} finally {
    $client.Dispose()
}
Assert-Check (-not $ollamaResponds) 'Ollama endpoint is unavailable'

Invoke-Setup
Assert-Installation
$exeHash = (Get-FileHash -LiteralPath $installedExe -Algorithm SHA256).Hash
Assert-Check ($exeHash.ToLowerInvariant() -eq $manifest.payload.'Simplicitor.exe') `
    'Installed executable matches built payload'

$oldPlatform = $env:QT_QPA_PLATFORM
$app = $null
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    $app = Start-Process -FilePath $installedExe -WorkingDirectory $env:RUNNER_TEMP `
        -WindowStyle Hidden -PassThru
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt 20) {
        $app.Refresh()
        if ($app.HasExited) { throw 'Installed app exited before the 20-second startup check.' }
        Start-Sleep -Seconds 1
    }
    $app.Refresh()
    Assert-Check (-not $app.HasExited) 'Installed app stays running offscreen for 20 seconds without Ollama'
} finally {
    if ($null -ne $app -and -not $app.HasExited) {
        Stop-Process -Id $app.Id -Force
        if (-not $app.WaitForExit(10000)) { throw 'Installed test app did not stop.' }
    }
    $env:QT_QPA_PLATFORM = $oldPlatform
}

$null = New-Item -ItemType Directory -Path (Split-Path -Parent $settingsPath) -Force
Set-Content -LiteralPath $settingsPath -Value '{"qualification_marker":"preserve-this-synthetic-setting"}' `
    -Encoding utf8
$settingsHash = (Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash
Invoke-Setup
Assert-Installation
Assert-Check ((Get-FileHash -LiteralPath $installedExe -Algorithm SHA256).Hash -eq $exeHash) `
    'Installed app survives reinstall over existing installation'
Assert-Check ((Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash -eq $settingsHash) `
    'Synthetic settings survive reinstall unchanged'

# Only this fixed, verified test installation is eligible for the built-in recursive uninstall.
Assert-Check ($installDir -eq [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs/Simplicitor'))) `
    'Uninstall target is the dedicated per-user test folder'
$process = Start-Process -FilePath $uninstaller -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
Assert-Check ($process.ExitCode -eq 0) 'Silent uninstaller exited successfully'
$deadline = [DateTime]::UtcNow.AddSeconds(30)
while ((Test-Path -LiteralPath $installDir) -and [DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 1
}
Assert-Check (-not (Test-Path -LiteralPath $installDir)) 'Install folder removed'
Assert-Check (-not (Test-Path -LiteralPath $uninstallKey)) 'HKCU uninstall entry removed'
Assert-Check (-not (Test-Path -LiteralPath $desktopShortcut)) 'Desktop shortcut removed'
Assert-Check (-not (Test-Path -LiteralPath $startShortcut)) 'Start Menu shortcut removed'
Assert-Check ((Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash -eq $settingsHash) `
    'Synthetic settings survive uninstall unchanged'

[ordered]@{
    status = 'passed'
    source_commit = $env:GITHUB_SHA
    run_id = $env:GITHUB_RUN_ID
    run_attempt = $env:GITHUB_RUN_ATTEMPT
    run_url = "https://github.com/$env:GITHUB_REPOSITORY/actions/runs/$env:GITHUB_RUN_ID"
    runner_os = [Environment]::OSVersion.Version.ToString()
    runner_image = $env:ImageVersion
    product_version = '2.0.0.0'
    app_running_seconds = 20
    checks = $checks.ToArray()
    artifacts = $artifactHashes
    limitations = @('Headless hosted-runner lifecycle check; not a native UI walkthrough, Task 6 accuracy gate, or downloaded-file SmartScreen qualification.')
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $dist 'installer-qualification.json') `
    -Encoding utf8
Write-Host 'Hosted Windows installer qualification passed.'

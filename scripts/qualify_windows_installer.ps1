# MSI qualification installs and removes software. Never run on a local PC.
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
$version = (& python -c "import build; print(build.PRODUCT_VERSION)").Trim()
$msi = Join-Path $dist "Simplicitor-$version.msi"
$payloadDir = Join-Path $dist 'standalone/main.dist'
$installDir = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs/Simplicitor'))
$installedExe = Join-Path $installDir 'Simplicitor.exe'
$settingsPath = Join-Path $env:APPDATA 'Simplicitor/settings.json'
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'Simplicitor.lnk'
$startShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Simplicitor.lnk'
$nsisKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Simplicitor'
$logDir = Join-Path $dist 'msi-logs'
$null = New-Item -ItemType Directory -Path $logDir -Force
$checks = [Collections.Generic.List[string]]::new()
$installer = New-Object -ComObject WindowsInstaller.Installer
$shell = New-Object -ComObject WScript.Shell
$manifest = $null

function Assert-Check([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $checks.Add($Name)
    Write-Host "PASS: $Name"
}

function Invoke-Msi([string]$Action, [string]$Package, [string]$Log, [string[]]$Extra = @()) {
    $arguments = @($Action, "`"$Package`"", '/qn', '/norestart', '/l*v', "`"$(Join-Path $logDir $Log)`"") + $Extra
    (Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden).ExitCode
}

# MSIINSTALLCONTEXT values from Msi.h: USERMANAGED = 1, USERUNMANAGED = 2, MACHINE = 4.
# A normal per-user MSI is USERUNMANAGED. Identify products by ProductCode.
$UserUnmanaged = 2
function Get-SimplicitorProducts {
    $found = @()
    foreach ($product in $installer.ProductsEx('', '', $UserUnmanaged)) {
        # Use COM dispatch directly; PowerShell's adapter does not expose these reliably.
        $productType = $product.GetType()
        $context = $productType.InvokeMember('Context', 'GetProperty', $null, $product, $null)
        if ($context -ne $UserUnmanaged) { throw 'Unexpected installation context.' }
        $name = $productType.InvokeMember('InstallProperty', 'GetProperty', $null, $product,
                                         @('ProductName'))
        if ($name -eq 'Simplicitor') {
            $found += [pscustomobject]@{
                ProductCode = $productType.InvokeMember('ProductCode', 'GetProperty',
                                                        $null, $product, $null)
                Version = $productType.InvokeMember('InstallProperty', 'GetProperty',
                                                    $null, $product, @('VersionString'))
                Location = $productType.InvokeMember('InstallProperty', 'GetProperty',
                                                     $null, $product, @('InstallLocation'))
            }
        }
    }
    , $found
}

function Assert-Installed([string]$ExpectedVersion, [string]$Label) {
    $products = Get-SimplicitorProducts
    Assert-Check ($products.Count -eq 1) "$Label exactly one Simplicitor product"
    Assert-Check ($products[0].Version -eq $ExpectedVersion) "$Label product version $ExpectedVersion"
    Assert-Check ([IO.Path]::GetFullPath($products[0].Location).TrimEnd('\') -eq $installDir) "$Label install location"
    Assert-Check (Test-Path -LiteralPath $installedExe -PathType Leaf) "$Label executable present"
    # The executable keeps the built version even when the probe MSI version changes.
    $script:observedExeVersion = (Get-Item -LiteralPath $installedExe).VersionInfo.ProductVersion
    Assert-Check ($script:observedExeVersion -eq "$version.0") "$Label executable version $version.0"
    Assert-Check ((Get-FileHash $installedExe -Algorithm SHA256).Hash.ToLowerInvariant() -eq
                  $manifest.payload.'Simplicitor.exe') "$Label executable matches built payload"
    foreach ($shortcut in @($desktopShortcut, $startShortcut)) {
        Assert-Check (Test-Path -LiteralPath $shortcut -PathType Leaf) "$Label shortcut exists"
        Assert-Check ($shell.CreateShortcut($shortcut).TargetPath -eq $installedExe) "$Label shortcut target"
    }
    $products[0].ProductCode
}

function Assert-Starts([string]$Label) {
    $app = $null
    $previous = $env:QT_QPA_PLATFORM
    try {
        $env:QT_QPA_PLATFORM = 'offscreen'
        $app = Start-Process -FilePath $installedExe -WorkingDirectory $env:RUNNER_TEMP -WindowStyle Hidden -PassThru
        $timer = [Diagnostics.Stopwatch]::StartNew()
        while ($timer.Elapsed.TotalSeconds -lt 20) {
            $app.Refresh()
            if ($app.HasExited) { throw "$Label app exited before the 20-second startup check." }
            Start-Sleep -Seconds 1
        }
        Assert-Check (-not $app.HasExited) "$Label app stays running for 20 seconds without Ollama"
    } finally {
        if ($null -ne $app -and -not $app.HasExited) {
            Stop-Process -Id $app.Id -Force
            if (-not $app.WaitForExit(10000)) { throw "$Label test app did not stop." }
        }
        $env:QT_QPA_PLATFORM = $previous
    }
}

# Fresh runner profile and the intended artifacts.
Assert-Check ((Get-SimplicitorProducts).Count -eq 0) 'No Simplicitor product before qualification'
foreach ($path in @($installDir, $settingsPath, $desktopShortcut, $startShortcut, $nsisKey)) {
    if (Test-Path -LiteralPath $path) { throw 'Qualification requires a fresh runner profile.' }
}
Assert-Check (Test-Path -LiteralPath $msi -PathType Leaf) "Intended MSI exists: Simplicitor-$version.msi"
$manifest = Get-Content -LiteralPath (Join-Path $dist 'SHA256SUMS.json') -Raw | ConvertFrom-Json
$artifactHashes = [ordered]@{}
foreach ($name in @("Simplicitor-$version.msi", 'Simplicitor-portable.zip')) {
    $hash = (Get-FileHash -LiteralPath (Join-Path $dist $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    Assert-Check ($hash -eq $manifest.artifacts.$name) "Artifact hash matches: $name"
    $artifactHashes[$name] = $hash
}

# Ollama must be absent; the app must survive that.
$client = [Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(2)
$ollamaResponds = $false
try {
    $response = $client.GetAsync('http://127.0.0.1:11434/api/version').GetAwaiter().GetResult()
    $ollamaResponds = $true
    $response.Dispose()
} catch [Net.Http.HttpRequestException] {
} catch [Threading.Tasks.TaskCanceledException] {
} finally {
    $client.Dispose()
}
Assert-Check (-not $ollamaResponds) 'Ollama endpoint is unavailable'

# A leftover 2.0.0 NSIS registration blocks installation without changing anything.
$null = New-Item -Path $nsisKey -Force
Set-ItemProperty -Path $nsisKey -Name UninstallString -Value 'C:\fake\uninstall.exe'
Assert-Check ((Invoke-Msi '/i' $msi 'nsis-conflict.log') -eq 1603) 'MSI refuses to install over Simplicitor 2.0.0'
Assert-Check (-not (Test-Path -LiteralPath $installDir)) 'Refused install left no files'
Assert-Check ((Get-SimplicitorProducts).Count -eq 0) 'Refused install registered nothing'
Remove-Item -Path $nsisKey -Recurse -Force

# Install.
Assert-Check ((Invoke-Msi '/i' $msi 'install.log') -eq 0) 'Silent MSI install succeeded'
$firstCode = Assert-Installed $version 'Install:'
Assert-Starts 'Install:'

# Settings must survive repair, upgrade, and uninstall.
$null = New-Item -ItemType Directory -Path (Split-Path -Parent $settingsPath) -Force
Set-Content -LiteralPath $settingsPath -Value '{"qualification_marker":"keep"}' -Encoding utf8
$settingsHash = (Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash

# Same-version repair restores a removed packaged file (runner test installation only).
$repairTarget = Join-Path $installDir 'LICENSE'
Assert-Check ($repairTarget.StartsWith($installDir + '\')) 'Repair target is inside the verified test installation'
$repairHash = (Get-FileHash -LiteralPath $repairTarget -Algorithm SHA256).Hash
Remove-Item -LiteralPath $repairTarget -Force
Assert-Check ((Invoke-Msi '/fa' $msi 'repair.log') -eq 0) 'Same-version repair succeeded'
Assert-Check ((Get-FileHash -LiteralPath $repairTarget -Algorithm SHA256).Hash -eq $repairHash) 'Repair restored the removed file'
$null = Assert-Installed $version 'Repair:'
Assert-Check ((Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash -eq $settingsHash) 'Settings survive repair'

# Major upgrade to a throwaway probe version built from the same payload; never published.
$probeVersion = '2.1.99'
$probe = Join-Path $env:RUNNER_TEMP "Simplicitor-$probeVersion-probe.msi"
& dotnet wix build (Join-Path $repoRoot 'packaging/simplicitor.wxs') (Join-Path $repoRoot '.nuitka/msi/payload.wxs') `
    -arch x64 -d "ProductVersion=$probeVersion" -bindpath "payload=$payloadDir" -o $probe
Assert-Check ($LASTEXITCODE -eq 0) 'Upgrade probe package built'
& dotnet wix msi validate $probe -sice ICE91
Assert-Check ($LASTEXITCODE -eq 0) 'Upgrade probe package validated'
Assert-Check ((Invoke-Msi '/i' $probe 'upgrade.log') -eq 0) "Major upgrade to $probeVersion succeeded"
$probeCode = Assert-Installed $probeVersion 'Upgrade:'
Assert-Check ($probeCode -ne $firstCode) 'Upgrade replaced the previous ProductCode'
Assert-Check (-not ((Get-SimplicitorProducts).ProductCode -contains $firstCode)) 'Previous product no longer registered'
Assert-Starts 'Upgrade:'
Assert-Check ((Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash -eq $settingsHash) 'Settings survive upgrade'

# Uninstall.
Assert-Check ((Invoke-Msi '/x' $probe 'uninstall.log') -eq 0) 'Silent uninstall succeeded'
Assert-Check ((Get-SimplicitorProducts).Count -eq 0) 'No Simplicitor product after uninstall'
Assert-Check (-not (Test-Path -LiteralPath $installDir)) 'Install folder removed, including subfolders'
Assert-Check (-not (Test-Path -LiteralPath $desktopShortcut)) 'Desktop shortcut removed'
Assert-Check (-not (Test-Path -LiteralPath $startShortcut)) 'Start Menu shortcut removed'
Assert-Check ((Get-FileHash -LiteralPath $settingsPath -Algorithm SHA256).Hash -eq $settingsHash) 'Settings survive uninstall'

[ordered]@{
    status = 'passed'
    source_commit = $env:GITHUB_SHA
    run_id = $env:GITHUB_RUN_ID
    run_url = "https://github.com/$env:GITHUB_REPOSITORY/actions/runs/$env:GITHUB_RUN_ID"
    runner_os = [Environment]::OSVersion.Version.ToString()
    runner_image = $env:ImageVersion
    msi_version = $version
    executable_version = $script:observedExeVersion
    upgrade_probe_msi_version = $probeVersion
    checks = $checks.ToArray()
    artifacts = $artifactHashes
    limitations = @('Hosted-runner lifecycle check; not a native UI walkthrough or downloaded-file SmartScreen qualification.')
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $dist 'installer-qualification.json') -Encoding utf8
Write-Host 'Hosted Windows MSI qualification passed.'

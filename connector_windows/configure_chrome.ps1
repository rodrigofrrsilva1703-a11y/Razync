param([Parameter(Mandatory=$true)][string]$Thumbprint)

$ErrorActionPreference = "Stop"

$normalized = ($Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
$cert = Get-ChildItem Cert:\CurrentUser\My, Cert:\LocalMachine\My -ErrorAction SilentlyContinue |
    Where-Object { $_.Thumbprint -eq $normalized -and $_.HasPrivateKey } |
    Select-Object -First 1
if (-not $cert) { throw "O certificado selecionado nao foi encontrado." }

function Get-Cn([string]$dn) {
    $match = [regex]::Match($dn, '(?:^|,\s*)CN=([^,]+)', 'IgnoreCase')
    if ($match.Success) { return $match.Groups[1].Value.Trim() }
    return ""
}

$subjectCn = Get-Cn ([string]$cert.Subject)
$issuerCn = Get-Cn ([string]$cert.Issuer)
if (-not $subjectCn -or -not $issuerCn) {
    throw "Nao foi possivel identificar o titular e o emissor do certificado."
}

$chromeCandidates = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)
$chrome = $chromeCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $chrome) { throw "Google Chrome nao encontrado." }

$policyApplied = $false
$policyScope = "none"
$filter = @{ ISSUER = @{ CN = $issuerCn }; SUBJECT = @{ CN = $subjectCn } }
$hosts = @(
    'https://cav.receita.fazenda.gov.br',
    'https://www.gov.br',
    'https://sso.acesso.gov.br',
    'https://certificado.sso.acesso.gov.br'
)
$rules = @()
foreach ($hostName in $hosts) {
    $rules += (@{ pattern = $hostName; filter = $filter } | ConvertTo-Json -Compress -Depth 6)
}
try {
    $policyPath = 'HKCU:\Software\Policies\Google\Chrome\AutoSelectCertificateForUrls'
    New-Item -Path $policyPath -Force -ErrorAction Stop | Out-Null
    for ($index = 0; $index -lt $rules.Count; $index++) {
        New-ItemProperty -Path $policyPath -Name ([string]($index + 1)) -Value $rules[$index] -PropertyType String -Force -ErrorAction Stop | Out-Null
    }
    $policyApplied = $true
    $policyScope = "user"
} catch [System.UnauthorizedAccessException] {
    # Se a politica do usuario estiver protegida, solicita elevacao somente
    # para gravar as mesmas regras na politica local da maquina.
    $machinePath = 'HKLM:\Software\Policies\Google\Chrome\AutoSelectCertificateForUrls'
    $machineRulesMatch = $true
    for ($index = 0; $index -lt $rules.Count; $index++) {
        $propertyName = [string]($index + 1)
        $installed = Get-ItemProperty -Path $machinePath -Name $propertyName -ErrorAction SilentlyContinue
        $installedRule = if ($installed) { $installed.PSObject.Properties[$propertyName].Value } else { $null }
        if ([string]$installedRule -ne [string]$rules[$index]) { $machineRulesMatch = $false; break }
    }
    if ($machineRulesMatch) {
        $policyApplied = $true
        $policyScope = "machine"
    }
    $adminHelper = Join-Path $PSScriptRoot 'configure_chrome_admin.ps1'
    if (-not $policyApplied -and (Test-Path $adminHelper)) {
        $rulesJson = ConvertTo-Json -Compress -InputObject @($rules)
        $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($rulesJson))
        try {
            $arguments = @(
                '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', ('"' + $adminHelper + '"'), '-RulesBase64', $payload
            )
            $elevated = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -Verb RunAs -Wait -PassThru -ErrorAction Stop
            if ($elevated.ExitCode -eq 0) {
                $policyApplied = $true
                $policyScope = "machine"
            }
        } catch {
            $policyApplied = $false
        }
    }
}

@{ chrome = [string]$chrome; subject_cn = $subjectCn; issuer_cn = $issuerCn; policy_applied = $policyApplied; policy_scope = $policyScope } |
    ConvertTo-Json -Compress

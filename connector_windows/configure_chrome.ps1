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

$policyPath = 'HKCU:\Software\Policies\Google\Chrome\AutoSelectCertificateForUrls'
New-Item -Path $policyPath -Force | Out-Null
$filter = @{ ISSUER = @{ CN = $issuerCn }; SUBJECT = @{ CN = $subjectCn } }
$hosts = @(
    'https://cav.receita.fazenda.gov.br',
    'https://www.gov.br',
    'https://sso.acesso.gov.br'
)
for ($index = 0; $index -lt $hosts.Count; $index++) {
    $rule = @{ pattern = $hosts[$index]; filter = $filter } | ConvertTo-Json -Compress -Depth 6
    New-ItemProperty -Path $policyPath -Name ([string]($index + 1)) -Value $rule -PropertyType String -Force | Out-Null
}

@{ chrome = [string]$chrome; subject_cn = $subjectCn; issuer_cn = $issuerCn } |
    ConvertTo-Json -Compress

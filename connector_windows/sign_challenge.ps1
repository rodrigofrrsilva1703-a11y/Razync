param(
    [Parameter(Mandatory = $true)][string]$Thumbprint,
    [Parameter(Mandatory = $true)][string]$ChallengeBase64
)

$ErrorActionPreference = "Stop"
$normalized = ($Thumbprint -replace "[^A-Fa-f0-9]", "").ToUpperInvariant()
if ($normalized.Length -lt 20) { throw "Identificador do certificado inválido." }

$cert = $null
foreach ($path in @("Cert:\CurrentUser\My\$normalized", "Cert:\LocalMachine\My\$normalized")) {
    if (Test-Path $path) {
        $cert = Get-Item $path
        break
    }
}
if ($null -eq $cert -or -not $cert.HasPrivateKey) {
    throw "Certificado com chave privada não encontrado."
}
if ($cert.NotAfter -lt (Get-Date)) {
    throw "O certificado selecionado está vencido."
}

$data = [Convert]::FromBase64String($ChallengeBase64)
$rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert)
if ($null -eq $rsa) { throw "Este certificado não possui uma chave RSA compatível." }

try {
    $signature = $rsa.SignData(
        $data,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
}
finally {
    $rsa.Dispose()
}

[ordered]@{
    thumbprint = $normalized
    algorithm = "RS256"
    signature = [Convert]::ToBase64String($signature)
    certificate = [Convert]::ToBase64String($cert.RawData)
} | ConvertTo-Json -Compress

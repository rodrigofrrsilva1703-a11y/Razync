$ErrorActionPreference = "Stop"

$items = @()
$stores = @(
    @{ Path = "Cert:\CurrentUser\My"; Scope = "CurrentUser" },
    @{ Path = "Cert:\LocalMachine\My"; Scope = "LocalMachine" }
)

foreach ($store in $stores) {
    if (-not (Test-Path $store.Path)) { continue }
    foreach ($cert in Get-ChildItem $store.Path) {
        if (-not $cert.HasPrivateKey) { continue }

        $subject = [string]$cert.Subject
        $cnpj = ""
        $matches = [regex]::Matches($subject, "(?<!\d)\d{14}(?!\d)")
        if ($matches.Count -gt 0) { $cnpj = $matches[0].Value }

        $items += [ordered]@{
            thumbprint = [string]$cert.Thumbprint
            subject = $subject
            issuer = [string]$cert.Issuer
            serial_number = [string]$cert.SerialNumber
            valid_from = $cert.NotBefore.ToUniversalTime().ToString("o")
            valid_to = $cert.NotAfter.ToUniversalTime().ToString("o")
            cnpj = $cnpj
            scope = $store.Scope
            has_private_key = $true
        }
    }
}

@($items) | ConvertTo-Json -Depth 4 -Compress

param([Parameter(Mandatory=$true)][string]$RulesBase64)

$ErrorActionPreference = "Stop"

try {
    $json = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($RulesBase64))
    $rules = @(ConvertFrom-Json -InputObject $json)
    $allowedHosts = @(
        'https://cav.receita.fazenda.gov.br',
        'https://www.gov.br',
        'https://sso.acesso.gov.br',
        'https://certificado.sso.acesso.gov.br'
    )
    if ($rules.Count -ne $allowedHosts.Count) { throw "Conjunto de regras invalido." }

    foreach ($ruleText in $rules) {
        if ([string]::IsNullOrWhiteSpace([string]$ruleText) -or ([string]$ruleText).Length -gt 4096) {
            throw "Regra de certificado invalida."
        }
        $rule = ConvertFrom-Json -InputObject ([string]$ruleText)
        if ($allowedHosts -notcontains [string]$rule.pattern) { throw "Endereco nao autorizado." }
        if (-not $rule.filter.ISSUER.CN -or -not $rule.filter.SUBJECT.CN) { throw "Filtro de certificado invalido." }
    }

    $policyPath = 'HKLM:\Software\Policies\Google\Chrome\AutoSelectCertificateForUrls'
    New-Item -Path $policyPath -Force | Out-Null
    $existing = Get-ItemProperty -Path $policyPath -ErrorAction SilentlyContinue
    if ($existing) {
        $existing.PSObject.Properties |
            Where-Object { $_.Name -match '^\d+$' } |
            ForEach-Object { Remove-ItemProperty -Path $policyPath -Name $_.Name -Force -ErrorAction SilentlyContinue }
    }
    for ($index = 0; $index -lt $rules.Count; $index++) {
        New-ItemProperty -Path $policyPath -Name ([string]($index + 1)) -Value ([string]$rules[$index]) -PropertyType String -Force | Out-Null
    }
    exit 0
} catch {
    exit 1
}

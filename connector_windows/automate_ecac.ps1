param(
    [Parameter(Mandatory=$true)][string]$Cnpj,
    [Parameter(Mandatory=$false)][string]$LogPath = "$env:LOCALAPPDATA\Razync\Connector\automation.log"
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddMinutes(10)
$messageId = 0
$lastStage = ""

function Write-AutomationLog([string]$Message) {
    try {
        $folder = Split-Path -Parent $LogPath
        if ($folder) { New-Item -ItemType Directory -Force -Path $folder | Out-Null }
        Add-Content -Path $LogPath -Encoding UTF8 -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $Message)
    } catch {}
}

function Invoke-CdpExpression([string]$WebSocketUrl, [string]$Expression) {
    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    try {
        $socket.Options.KeepAliveInterval = [TimeSpan]::FromSeconds(15)
        $socket.ConnectAsync([Uri]$WebSocketUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
        $script:messageId++
        $currentId = $script:messageId
        $payload = @{
            id = $currentId
            method = 'Runtime.evaluate'
            params = @{ expression = $Expression; returnByValue = $true; awaitPromise = $true; userGesture = $true }
        } | ConvertTo-Json -Compress -Depth 8
        $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
        $socket.SendAsync([ArraySegment[byte]]::new($bytes), [Net.WebSockets.WebSocketMessageType]::Text, $true,
            [Threading.CancellationToken]::None).GetAwaiter().GetResult()
        $buffer = New-Object byte[] 65536
        $expires = (Get-Date).AddSeconds(5)
        while ((Get-Date) -lt $expires) {
            $stream = [IO.MemoryStream]::new()
            do {
                $received = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer),
                    [Threading.CancellationToken]::None).GetAwaiter().GetResult()
                if ($received.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { return $null }
                $stream.Write($buffer, 0, $received.Count)
            } while (-not $received.EndOfMessage)
            $response = ([Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json)
            if ($response.id -eq $currentId) {
                if ($response.error) { throw [Exception]::new([string]$response.error.message) }
                return [string]$response.result.result.value
            }
        }
        throw "O Chrome não respondeu ao comando de automação."
    } finally {
        try { $socket.Dispose() } catch {}
    }
}

$safeCnpj = ($Cnpj -replace '\D', '')
if ($safeCnpj.Length -ne 14) { exit 2 }
$quotedCnpj = $safeCnpj | ConvertTo-Json -Compress

$expression = @"
(() => {
  const cnpj = $quotedCnpj;
  const clean = value => String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
  const visible = element => !!(element && element.getClientRects && element.getClientRects().length);
  const roots = [];
  const visit = root => {
    if (!root || roots.includes(root)) return;
    roots.push(root);
    for (const element of root.querySelectorAll('*')) {
      if (element.shadowRoot) visit(element.shadowRoot);
      if (element.tagName === 'IFRAME') {
        try { if (element.contentDocument) visit(element.contentDocument); } catch (_) {}
      }
    }
  };
  visit(document);
  const all = selector => roots.flatMap(root => [...root.querySelectorAll(selector)]);
  const controls = all('button,a,input[type=button],input[type=submit],[role=button]').filter(visible);
  const textOf = element => clean([
    element.innerText, element.textContent, element.value, element.title,
    element.getAttribute && element.getAttribute('aria-label'),
    element.getAttribute && element.getAttribute('href'),
    ...[...(element.querySelectorAll ? element.querySelectorAll('img') : [])].map(img => img.alt)
  ].filter(Boolean).join(' '));
  const activate = element => {
    try { element.scrollIntoView({block:'center'}); } catch (_) {}
    try { element.focus(); } catch (_) {}
    for (const name of ['pointerdown','mousedown','pointerup','mouseup','click']) {
      try { element.dispatchEvent(new MouseEvent(name,{bubbles:true,cancelable:true,view:window})); } catch (_) {}
    }
    try { element.click(); } catch (_) {}
  };
  const clickText = patterns => {
    const found = controls.find(element => patterns.some(pattern => textOf(element).includes(pattern)));
    if (!found) return false;
    activate(found);
    return true;
  };
  const inputs = all('input:not([type=hidden])').filter(visible);
  const cnpjInput = inputs.find(input => {
    const identity = clean([input.name,input.id,input.placeholder,input.getAttribute('aria-label')].join(' '));
    return identity.includes('cnpj') || identity.includes('cpf/cnpj') || identity.includes('ni');
  });
  if (cnpjInput) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    setter ? setter.call(cnpjInput, cnpj) : (cnpjInput.value = cnpj);
    cnpjInput.dispatchEvent(new Event('input',{bubbles:true}));
    cnpjInput.dispatchEvent(new Event('change',{bubbles:true}));
    for (const select of all('select').filter(visible)) {
      const option = [...select.options].find(item => clean(item.text).includes('procurador'));
      if (option) { select.value=option.value; select.dispatchEvent(new Event('change',{bubbles:true})); }
    }
    setTimeout(() => clickText(['alterar','confirmar','continuar','avancar']), 500);
    return 'cnpj_preenchido';
  }
  if (clickText(['entrar com gov.br','entrar com govbr','acesso gov.br','acesso govbr'])) return 'govbr_clicado';
  if (clickText(['certificado digital','seu certificado digital'])) return 'certificado_clicado';
  if (clickText(['alterar perfil de acesso','alterar perfil'])) return 'perfil_clicado';
  return 'aguardando:' + location.hostname;
})()
"@

try { Clear-Content -Path $LogPath -ErrorAction SilentlyContinue } catch {}
Write-AutomationLog "Automação iniciada."
Start-Sleep -Seconds 2
while ((Get-Date) -lt $deadline) {
    try {
        $targets = Invoke-RestMethod -Uri 'http://127.0.0.1:17892/json' -TimeoutSec 2
        $matched = $false
        foreach ($target in @($targets)) {
            if ($target.type -notin @('page','iframe') -or -not $target.webSocketDebuggerUrl) { continue }
            if ($target.url -notmatch 'gov\.br|receita\.fazenda\.gov\.br') { continue }
            $matched = $true
            $stage = Invoke-CdpExpression ([string]$target.webSocketDebuggerUrl) $expression
            if ($stage -and $stage -ne $lastStage) {
                $lastStage = $stage
                Write-AutomationLog ("Etapa: " + $stage)
            }
        }
        if (-not $matched -and $lastStage -ne 'chrome_sem_pagina') {
            $lastStage = 'chrome_sem_pagina'
            Write-AutomationLog "Chrome conectado, aguardando a página do e-CAC."
        }
    } catch {
        $safeError = ([string]$_.Exception.Message -replace '[\r\n]+',' ')
        if (("erro:" + $safeError) -ne $lastStage) {
            $lastStage = "erro:" + $safeError
            Write-AutomationLog ("Erro: " + $safeError)
        }
    }
    Start-Sleep -Milliseconds 900
}
Write-AutomationLog "Tempo da automação encerrado."

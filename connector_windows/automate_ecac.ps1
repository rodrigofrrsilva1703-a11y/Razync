param([Parameter(Mandatory=$true)][string]$Cnpj)

$ErrorActionPreference = "SilentlyContinue"
$deadline = (Get-Date).AddMinutes(10)
$messageId = 0

function Invoke-CdpExpression([string]$WebSocketUrl, [string]$Expression) {
    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $uri = [Uri]$WebSocketUrl
    $socket.ConnectAsync($uri, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $script:messageId++
    $payload = @{
        id = $script:messageId
        method = 'Runtime.evaluate'
        params = @{ expression = $Expression; returnByValue = $true; awaitPromise = $true }
    } | ConvertTo-Json -Compress -Depth 8
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    $segment = [ArraySegment[byte]]::new($bytes)
    $socket.SendAsync($segment, [Net.WebSockets.WebSocketMessageType]::Text, $true,
        [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $buffer = New-Object byte[] 65536
    $received = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer),
        [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $socket.CloseAsync([Net.WebSockets.WebSocketCloseStatus]::NormalClosure, 'done',
        [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    return [Text.Encoding]::UTF8.GetString($buffer, 0, $received.Count)
}

$safeCnpj = ($Cnpj -replace '\D', '')
if ($safeCnpj.Length -ne 14) { exit 2 }
$quotedCnpj = $safeCnpj | ConvertTo-Json -Compress

$expression = @"
(() => {
  const cnpj = $quotedCnpj;
  const clean = value => String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
  const visible = element => !!(element && element.getClientRects().length);
  const controls = [...document.querySelectorAll(
    'button,a,input[type=button],input[type=submit],[role=button]'
  )].filter(visible);
  const clickText = patterns => {
    const found = controls.find(element => {
      const text = clean(element.innerText || element.value || element.getAttribute('aria-label'));
      return patterns.some(pattern => text.includes(pattern));
    });
    if (!found) return false;
    found.click();
    return true;
  };
  const inputs = [...document.querySelectorAll('input:not([type=hidden])')].filter(visible);
  const cnpjInput = inputs.find(input => {
    const identity = clean([input.name,input.id,input.placeholder,input.getAttribute('aria-label')].join(' '));
    return identity.includes('cnpj') || identity.includes('cpf/cnpj') || identity.includes('ni');
  });
  if (cnpjInput) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    setter ? setter.call(cnpjInput, cnpj) : (cnpjInput.value = cnpj);
    cnpjInput.dispatchEvent(new Event('input',{bubbles:true}));
    cnpjInput.dispatchEvent(new Event('change',{bubbles:true}));
    for (const select of [...document.querySelectorAll('select')].filter(visible)) {
      const option = [...select.options].find(item => clean(item.text).includes('procurador'));
      if (option) { select.value=option.value; select.dispatchEvent(new Event('change',{bubbles:true})); }
    }
    setTimeout(() => clickText(['alterar','confirmar','continuar','avancar']), 500);
    return 'cnpj';
  }
  if (clickText(['entrar com gov.br'])) return 'govbr';
  if (clickText(['certificado digital','seu certificado digital'])) return 'certificate';
  if (clickText(['alterar perfil de acesso','alterar perfil'])) return 'profile';
  return 'waiting';
})()
"@

Start-Sleep -Seconds 2
while ((Get-Date) -lt $deadline) {
    try {
        $targets = Invoke-RestMethod -Uri 'http://127.0.0.1:17892/json' -TimeoutSec 2
        foreach ($target in @($targets)) {
            if ($target.type -ne 'page' -or -not $target.webSocketDebuggerUrl) { continue }
            if ($target.url -notmatch 'gov\.br|receita\.fazenda\.gov\.br') { continue }
            [void](Invoke-CdpExpression ([string]$target.webSocketDebuggerUrl) $expression)
        }
    } catch {}
    Start-Sleep -Milliseconds 900
}

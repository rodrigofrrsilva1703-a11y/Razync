(() => {
  "use strict";

  const clean = value => String(value || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();
  const visible = element => !!(element && element.getClientRects().length);
  const controls = () => [...document.querySelectorAll(
    'button, a, input[type="button"], input[type="submit"], [role="button"]'
  )].filter(visible);
  const clickText = patterns => {
    const item = controls().find(element => {
      const text = clean(element.innerText || element.value || element.getAttribute("aria-label"));
      return patterns.some(pattern => text.includes(pattern));
    });
    if (!item) return false;
    item.click();
    return true;
  };
  const emitValue = (input, value) => {
    const setter = Object.getOwnPropertyDescriptor(
      input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
      "value"
    )?.set;
    setter ? setter.call(input, value) : (input.value = value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const hash = new URLSearchParams(location.hash.replace(/^#/, ""));
  const incomingCnpj = (hash.get("razync_cnpj") || "").replace(/\D/g, "");
  if (incomingCnpj.length === 14) {
    chrome.storage.local.set({ razyncCnpj: incomingCnpj, razyncStartedAt: Date.now() });
    history.replaceState(null, "", location.pathname + location.search);
  }

  let busy = false;
  async function advance() {
    if (busy) return;
    busy = true;
    try {
      const { razyncCnpj, razyncStartedAt } = await chrome.storage.local.get([
        "razyncCnpj", "razyncStartedAt"
      ]);
      if (!razyncCnpj || Date.now() - Number(razyncStartedAt || 0) > 30 * 60 * 1000) return;

      const body = clean(document.body?.innerText);
      const host = location.hostname.toLowerCase();

      if (body.includes("entrar com gov.br") && clickText(["entrar com gov.br"])) return;
      if ((host === "www.gov.br" || host === "sso.acesso.gov.br") &&
          clickText(["certificado digital", "seu certificado digital"])) return;

      const candidateInputs = [...document.querySelectorAll('input:not([type="hidden"])')].filter(visible);
      const cnpjInput = candidateInputs.find(input => {
        const identity = clean([
          input.name, input.id, input.placeholder, input.getAttribute("aria-label")
        ].join(" "));
        return identity.includes("cnpj") || identity.includes("cpf/cnpj") || identity.includes("ni");
      });
      if (cnpjInput) {
        emitValue(cnpjInput, razyncCnpj);
        const selects = [...document.querySelectorAll("select")].filter(visible);
        for (const select of selects) {
          const option = [...select.options].find(item => clean(item.text).includes("procurador"));
          if (option) {
            select.value = option.value;
            select.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }
        setTimeout(() => clickText(["alterar", "confirmar", "continuar", "avancar"]), 500);
        return;
      }

      if (clickText(["alterar perfil de acesso", "alterar perfil"])) return;
    } finally {
      busy = false;
    }
  }

  const observer = new MutationObserver(() => setTimeout(advance, 250));
  observer.observe(document.documentElement, { childList: true, subtree: true });
  setInterval(advance, 1200);
  advance();
})();

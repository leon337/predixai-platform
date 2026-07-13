# PTP-GOV.4.6A — Contrato da janela autorizada e falha fechada

Status: `CONTRACT_CHARACTERIZED_NOT_FUNCTIONALLY_INTEGRATED`

Este contrato governa as futuras PTP-GOV.4.6B–4.6E. Ele não autoriza captura, OCR,
corretora, servidor, integração funcional ou uso de runtime real.

## Fonte autorizada

Uma fonte visual somente pode ser confirmada quando todos os campos abaixo estiverem
presentes e forem revalidados imediatamente antes de cada captura:

| Campo | Regra vinculante |
|---|---|
| `AUTHORIZED_WINDOW_ID` | ID explícito, não nulo e estável; nunca usar janela ativa genérica. |
| `AUTHORIZED_WINDOW_PID` | PID positivo e exatamente igual ao observado. |
| `AUTHORIZED_PROCESS_NAME` | Nome exato do processo autorizado; VS Code, Codex e terminais são proibidos. |
| `AUTHORIZED_TITLE_PATTERN` | Expressão regular integral, específica da fonte autorizada. |
| `AUTHORIZED_GEOMETRY` | `x`, `y`, `width` e `height` exatos; dimensões positivas. |
| `DISPLAY_SERVER` | `X11` ou `WAYLAND`, com backend explicitamente compatível. |
| `WINDOW_VISIBLE` | Deve ser `true`. |
| `WINDOW_MINIMIZED` | Deve ser `false`. |
| `WINDOW_FOREGROUND` | Deve ser `true` quando exigido pelo backend. |
| `GEOMETRY_STABLE` | Deve ser `true` após comparação pré-captura. |
| `SOURCE_CONFIRMED` | Deve ser `true`; confirmação nunca é inferida por fallback. |

Também são vinculantes:

```text
MONITOR_COUNT=1
CAPTURE_TARGET_MODE=EXPLICIT_WINDOW_ID
FULL_SCREEN_FALLBACK=PROHIBITED
ACTIVE_WINDOW_GENERIC_FALLBACK=PROHIBITED
DESKTOP_CAPTURE_FALLBACK=PROHIBITED
```

Um navegador pode hospedar a fonte visual somente quando ID, PID, processo, título e
geometria forem todos explicitamente autorizados. O simples fato de o navegador estar em
primeiro plano não confirma a fonte.

## Revalidação futura por captura

1. Ler novamente ID, PID, processo, título e geometria da janela autorizada.
2. Confirmar visibilidade e estado não minimizado.
3. Confirmar foreground quando o backend exigir.
4. Confirmar uma única tela e geometria estável.
5. Capturar diretamente pelo ID ou retângulo autorizado.
6. Revalidar identidade e geometria depois da captura para reduzir risco de TOCTOU.
7. Publicar somente se as duas validações e a leitura normalizada forem válidas.

Sobreposição não pode ser provada apenas com metadados X11/Wayland em todos os
compositores. Quando não houver prova suficiente, a decisão obrigatória é falhar fechada.

## Contrato de falha fechada

Qualquer campo ausente, divergente, instável ou não comprovável produz:

```text
CAPTURE_ALLOWED=NO
CAPTURE_EXECUTED=NO
OCR_EXECUTED=NO
INVALID_READING_PUBLISHED=NO
LAST_VALID_READING_PRESERVED=YES
SOURCE_STATE=WAITING_SOURCE_OR_SOURCE_NOT_CONFIRMED
FAIL_CLOSED=YES
```

Não é permitido substituir a fonte por tela inteira, desktop, janela ativa genérica,
VS Code, Codex, terminal ou navegador não autorizado.

## Caracterização do ambiente em 2026-07-13

```text
DISPLAY_SERVER=X11
XDG_SESSION_TYPE=x11
DESKTOP_SESSION=xfce
XDG_CURRENT_DESKTOP=XFCE
DISPLAY=:0.0
WINDOW_MANAGER=Xfwm4
ROOT_GEOMETRY=1366x768+0+0
WMCTRL_AVAILABLE=YES
XPROP_AVAILABLE=YES
XWININFO_AVAILABLE=YES
XWD_AVAILABLE=YES
DIRECT_WINDOW_CAPTURE_CAPABILITY=AVAILABLE_NOT_EXECUTED_XWD_EXPLICIT_WINDOW_ID
OVERLAP_DETECTION_CAPABILITY=NOT_PROVABLE_FROM_METADATA_FAIL_CLOSED
```

`wmctrl`, `xprop` e `xwininfo` conseguiram consultar apenas metadados do X11. `xwd`
declara suporte a `-id <wdid>`, mas nenhuma captura foi executada nesta etapa. Não foram
encontrados `import`, `scrot`, `gnome-screenshot`, `grim`, `slurp`, `spectacle`, `maim`
ou `xdotool`.

## Travas preservadas

```text
SIMULATION_ONLY=YES
REAL_MONEY_ENABLED=NO
REAL_ORDER_ENABLED=NO
AUTO_CLICK_ENABLED=NO
BROKER_LOGIN_AUTOMATION=NO
CREDENTIALS_ALLOWED=NO
BROKER_SCREEN_IS_VISUAL_SOURCE_ONLY=YES
REAL_RUNTIME_USED=NO
CAPTURE_EXECUTED=NO
OCR_EXECUTED=NO
SERVER_STARTED=NO
BROKER_OPENED=NO
```

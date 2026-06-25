# PredixAI BR — Notas do Arquiteto

Este arquivo registra ideias, riscos, melhorias e observações futuras.

Nenhuma nota vira decisão sem aprovação explícita do Leo e registro em `DECISIONS.md`.

## Ideias futuras

- Validar captura no Linux Mint depois da estabilidade no Windows 10.
- Evoluir a captura manual para captura controlada por intervalo somente quando o PTP correspondente autorizar.
- Preparar leitura visual futura com OpenCV e OCR sem misturar com a fundação atual.
- Criar Auditor com SQLite para registrar capturas, dados detectados e sinais sugeridos.
- Criar Dashboard em modo observando, sem botão de execução.
- Integrar Gemini apenas como analista, depois que Auditor e Strategy estiverem prontos.

## Backlog técnico

- Definir backend de captura compatível com Linux Mint.
- Documentar requisitos gráficos para X11 e Wayland.
- Adicionar testes automatizados para configuração, logger, Perception e Capture Engine.
- Definir política para capturas locais não serem versionadas por acidente.
- Preparar separação futura entre logs técnicos e registros do Auditor.
- Criar validação local de licença somente no PTP de Security autorizado.

## Riscos conhecidos

- Captura de tela depende de sessão gráfica com permissão suficiente.
- Ambientes sandboxados ou sem desktop real podem bloquear captura.
- Linux Mint pode exigir backend diferente do Windows.
- OCR e OpenCV ainda não foram integrados e podem exigir dependências nativas.
- Registros futuros do Auditor podem crescer rapidamente se a retenção não for definida.
- Arquivos sensíveis precisam continuar fora do Git.

## Melhorias propostas

- Criar um comando de diagnóstico que verifique ambiente sem executar captura.
- Criar um relatório local de pré-execução para suporte técnico.
- Padronizar mensagens de erro para captura indisponível.
- Criar testes de contrato para garantir que a V1 continue sem execução, cliques ou automação.
- Avaliar uma política de limpeza ou retenção para imagens em `captures`.

## Observações do arquiteto

- A prioridade atual é manter a sequência dos PTPs simples e auditável.
- A base Windows 10 deve continuar sendo o caminho principal até a validação Linux Mint.
- Toda expansão precisa preservar o Core como coordenador.
- Cada módulo deve continuar com responsabilidade clara e baixo acoplamento.
- A V1 deve permanecer transparente: observar, registrar, gerar sinal sugerido e explicar, sem executar operações.

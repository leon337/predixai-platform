# PredixAI BR — Política de Segurança v1.0

## 1. Princípio

Nunca confiar totalmente no computador do usuário.

## 2. V1

Na V1 haverá apenas segurança básica local.

Recursos:

- license.local.json local
- identificação simples da máquina
- logs de inicialização
- proteção para API Key
- .gitignore para arquivos sensíveis

## 3. V2 e futuras

- licença em nuvem
- validação por usuário e dispositivo
- expiração de licença
- revogação remota
- estratégias criptografadas
- marketplace protegido
- assinatura digital de estratégias
- verificação de integridade

## 4. API Keys

API Keys nunca devem ficar:

- no README
- no código-fonte
- em commits
- em prints públicos

Devem ficar em:

- .env
- license.local.json
- secrets.local.json
- futuro cofre de segredos

O nome license.json não deve ser usado como nome final para licença local da V1.

## 5. Pirataria

Medidas futuras:

- licença por dispositivo
- limite de máquinas
- validação online periódica
- estratégias criptografadas
- bloqueio de cópias não autorizadas

## 6. Logs de segurança

Registrar:

- início do sistema;
- validação de licença;
- erro de licença;
- troca de configuração sensível;
- falha de API;
- tentativa de uso sem autorização.

# Política de Preflight de Scripts — PredixAI BR

Data de criação: 2026-07-10
Origem: PTP-113C.8.4.2A.2.1

## Objetivo

Evitar que scripts PredixAI confundam arquivos criados pela própria execução com resíduos anteriores e impedir falhas em cascata.

## Regra central

Nenhum arquivo no working tree pode ser criado antes da fotografia inicial do Git.

## Ordem obrigatória

1. confirmar repositório, branch e remote;
2. capturar HEAD, staged, modificados e untracked;
3. capturar checksums e estado esperado;
4. criar workspace somente em `/tmp`;
5. executar testes sintéticos do executor;
6. construir candidatos fora do working tree;
7. validar candidatos;
8. gravar atomicamente;
9. validar allowlist;
10. fechar relatório;
11. commit;
12. push;
13. confirmar `origin/main`;
14. abrir o relatório sem modificá-lo.

## Estados de fase

- `PREFLIGHT_STATUS`
- `SYNTHETIC_TEST_STATUS`
- `BUILD_STATUS`
- `VALIDATION_STATUS`
- `ROLLBACK_STATUS`
- `DOCUMENTATION_STATUS`
- `PUBLICATION_STATUS`
- `DELIVERY_STATUS`

Se o build não ocorrer, validações pós-build devem ficar `SKIPPED`.

## Relatório e publicação

O relatório versionado é fechado antes do commit e deve registrar:

`PUBLICATION_STATUS=PENDING_BY_DESIGN`

Commit, push e hash remoto são confirmados apenas no recibo final do terminal.

## Git seguro

Proibido:

- `git add .`
- `git add -A`
- `git reset --hard`
- `git clean`
- `git pull` automático
- `git rebase` automático
- `git push --force`

O stage e a árvore do commit devem corresponder a uma allowlist explícita.

## Rollback

- antes do commit: restaurar arquivos a partir de backups;
- depois do commit: não executar rollback destrutivo;
- push falhou: classificar `LOCAL_COMMIT_ONLY` e criar recovery específica.

## Alcance

Esta política está documentada e o executor desta PTP foi corrigido.

`ENFORCEMENT_AUTOMÁTICO_GLOBAL=NO`

Uma biblioteca reutilizável para impor o padrão a todos os scripts exige mini-PTP própria.

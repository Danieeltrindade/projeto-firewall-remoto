# Testes negativos e de falha

Este documento reúne os casos de falha do projeto e como cada um é
verificado. O objetivo é mostrar que o sistema **rejeita entradas inválidas e
se recupera de falhas, sem travar e sem executar nada fora do permitido**.

## 1. Casos automatizados (`testes/teste_falhas.py`)

Executados da máquina A contra o servidor real da máquina B:

```bash
python -m testes.teste_falhas
```

| Caso | O que é enviado | Código esperado |
|---|---|---|
| Token inválido | token com 64 zeros | `TOKEN_INVALIDO` |
| Token ausente | requisição sem o campo `token` | `TOKEN_INVALIDO` |
| Ação inválida | `"acao": "formatar"` | `ACAO_INVALIDA` |
| Comando PowerShell como ação | `"acao": "Remove-NetFirewallRule -All"` | `ACAO_INVALIDA` |
| Porta não autorizada | `"porta": 22` | `PORTA_NAO_AUTORIZADA` |
| Porta com comando injetado | `"porta": "8080; Remove-NetFirewallRule -All"` | `CAMPO_INVALIDO` |
| Campo extra | `"comando": "whoami"` | `CAMPO_INVALIDO` |
| JSON malformado | `{"acao": "consultar"` (sem fechar) | `JSON_INVALIDO` |
| Mensagem grande demais | 4096 bytes sem `\n` | `MENSAGEM_MUITO_GRANDE` |
| Bloquear (1ª vez) | bloquear 8080 | `REGRA_CRIADA` (ou `REGRA_JA_EXISTE`) |
| Bloquear de novo | bloquear 8080 | `REGRA_JA_EXISTE` |
| Consultar | consultar | `CONSULTA_REALIZADA` com **1** regra (sem duplicata) |
| Desbloquear | desbloquear 8080 | `REGRA_REMOVIDA` |
| Desbloquear de novo | desbloquear 8080 | `REGRA_INEXISTENTE` |
| Servidor ainda responde | consultar | `CONSULTA_REALIZADA` |

O teste termina com a porta liberada e mostra `RESULTADO: APROVADO` quando os
15 casos batem. O token nunca aparece na saída.

### Servidor indisponível

Com o servidor de controle da máquina B **desligado**:

```bash
python -m testes.teste_falhas --indisponivel
```

O cliente precisa mostrar uma mensagem `[FALHA] ...` clara, sem travar.

## 2. Roteiros manuais

Estes casos dependem do estado das máquinas e foram verificados à mão:

| Caso | Como reproduzir | Resultado esperado | Evidência |
|---|---|---|---|
| Certificado falso | servidor com outro certificado | cliente recusa a conexão TLS | etapa 2.3 |
| Falta de privilégio | `servidor` e `firewall` em um terminal **sem** Administrador | aviso na inicialização e `SemPrivilegio` | etapa 4.3 |
| Recuperação de regra | regra ativa + servidor desligado → `python -m servidor.recuperacao` | regra removida, `LaboratorioBase` intacto, HTTP volta | etapa 4.4 |

## 3. Testes unitários

Os testes unitários (`testes/test_*.py`) cobrem a validação, o firewall (com
PowerShell simulado), a recuperação e a conectividade, sem precisar da rede:

```bash
python -m unittest discover -s testes -v
```
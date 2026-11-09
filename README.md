# Automação de Firewall do Windows via Comando Remoto

Projeto 4.3: uma máquina A envia comandos autenticados para uma máquina B, que cria, consulta e remove regras do Windows Firewall de forma controlada.

> **Status:** em desenvolvimento. Acompanhe o andamento pelas [Issues](../../issues), pelos [Milestones](../../milestones) e pelo quadro Kanban do projeto.

## Objetivo

Demonstrar, em ambiente de laboratório isolado, que um comando remoto autenticado consegue bloquear e restaurar o acesso a um serviço:

1. A máquina A acessa o serviço HTTP da máquina B (porta 8080).
2. A máquina A envia um comando autenticado de bloqueio.
3. A máquina B cria a regra no firewall, e o acesso falha.
4. A máquina A envia o comando de desbloqueio.
5. A máquina B remove a regra, e o acesso volta a funcionar.

## Arquitetura

```
 Máquina A (cliente)                         Máquina B (servidor, executado como Administrador)
┌──────────────┐   TCP 5000 + TLS + JSON   ┌──────────────────────────────────────────┐
│ cliente.py   │ ────────────────────────▶ │ servidor.py → autenticacao.py            │
│              │ ◀──────────────────────── │   → validacao.py → firewall.py           │
└──────────────┘     resposta JSON         │        │                                 │
                                           │        ▼ PowerShell (comandos fixos)     │
┌──────────────┐        TCP 8080           │   Windows Firewall ─ bloqueia ─▶ 8080    │
│ testes       │ ────────────────────────▶ │   servidor_http.py (serviço de teste)    │
└──────────────┘                           └──────────────────────────────────────────┘
```

## Estrutura do repositório

| Caminho | Responsabilidade |
|---|---|
| `cliente/` | Cliente da máquina A (menu interativo) |
| `servidor/` | Servidor de controle, autenticação, validação, firewall e recuperação |
| `comum/` | Funções de protocolo compartilhadas entre cliente e servidor |
| `testes/` | Servidor HTTP de teste e testes de conectividade e de falhas |
| `certificados/` | Script de geração dos certificados TLS (os certificados não são versionados) |
| `docs/` | Protocolo, ambiente, evidências e roteiro de apresentação |
| `config.exemplo.json` | Modelo de configuração. Copie para `config.json` e preencha |

## Tecnologias

- Python 3.12+ (somente a biblioteca padrão)
- Sockets TCP com TLS (`socket`, `ssl`)
- Mensagens JSON delimitadas por linha
- PowerShell: `New-NetFirewallRule`, `Get-NetFirewallRule`, `Remove-NetFirewallRule`
- VirtualBox com rede Host-Only

## Equipe (papéis)

| Integrante | Responsabilidade | Critério |
|---|---|---|
| 1 | Servidor TCP e ambiente | 1 |
| 2 | Cliente, protocolo e autenticação | 2 |
| 3 | Gerenciamento do firewall | 3 e 5 |
| 4 | Testes, integração e documentação | 4 |

## Segurança

- O servidor executa apenas ações pré-definidas, em portas autorizadas.
- Nenhum comando recebido pela rede é executado diretamente.
- Autenticação por token e canal protegido por TLS.
- Token, chaves e certificados nunca são versionados.
- Uso exclusivo em rede de laboratório isolada.
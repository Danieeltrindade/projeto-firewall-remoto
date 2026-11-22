# Projeto Firewall Remoto

Um cliente Python na **máquina A** envia comandos autenticados a um servidor
Python na **máquina B**, que cria, consulta e remove regras do **Windows
Firewall** via PowerShell. O serviço usado na demonstração é um servidor HTTP
na porta **TCP 8080** da máquina B.

| Critério do professor | Como o projeto atende |
|---|---|
| 1. Comunicação cliente-servidor | Socket TCP na porta 5000, protegido por TLS, com protocolo JSON ([docs/protocolo.md](docs/protocolo.md)) |
| 2. Autenticação e validação | Token de 64 caracteres comparado em tempo constante; só ações e portas da lista permitida |
| 3. Bloqueio da porta | `New-NetFirewallRule` cria a regra de bloqueio da porta 8080 |
| 4. Comprovação do descarte | `testes/teste_conectividade.py`: antes SUCESSO, durante TIMEOUT, depois SUCESSO |
| 5. Restauração e remoção | Desbloqueio remoto e recuperação local ([docs/recuperacao.md](docs/recuperacao.md)) |

## Arquitetura

```
 Máquina A (notebook)                        Máquina B (VM Windows Server)
 192.168.56.1                                192.168.56.10
┌──────────────────────┐   TLS · TCP 5000   ┌──────────────────────────────┐
│ cliente/cliente.py   │ ─────────────────▶ │ servidor/servidor.py         │
│  menu: bloquear,     │   JSON + token     │  autenticação → validação    │
│  desbloquear,        │ ◀───────────────── │  → firewall.py (PowerShell)  │
│  consultar           │   resposta JSON    │                              │
└──────────────────────┘                    │ Windows Firewall             │
           │                                │  regra ProjetoFirewallRemoto │
           │            HTTP · TCP 8080     │                              │
           └──────────────────────────────▶ │ testes/servidor_http.py      │
                (bloqueado ou liberado)     └──────────────────────────────┘
```

As duas máquinas ficam em uma rede **Host-Only isolada** (192.168.56.0/24).
A porta de controle nunca é exposta à internet.

## Estrutura

```
cliente/cliente.py           cliente de controle (máquina A)
comum/protocolo.py           envio e recebimento de mensagens JSON
servidor/servidor.py         servidor de controle com TLS (máquina B)
servidor/autenticacao.py     verificação do token
servidor/validacao.py        ações e portas permitidas
servidor/firewall.py         comandos fixos do Windows Firewall
servidor/recuperacao.py      remoção local das regras do projeto
certificados/                script do certificado TLS (o .crt e o .key não vão para o Git)
testes/servidor_http.py      serviço HTTP de teste na porta 8080
testes/test_*.py             testes unitários
testes/teste_conectividade.py  teste antes/durante/depois do bloqueio
testes/teste_falhas.py       testes negativos contra o servidor real
docs/                        ambiente, protocolo, recuperação e testes
config.exemplo.json          modelo de configuração
```

## 1. Requisitos

| | Máquina A (cliente) | Máquina B (servidor) |
|---|---|---|
| Sistema | Windows 10/11 | Windows Server 2025 (VirtualBox) |
| Python | 3.10 ou superior | 3.10 ou superior |
| Git | Git for Windows (inclui o Git Bash e o OpenSSL) | Git for Windows |
| Rede | Adaptador Host-Only 192.168.56.1 | Adaptador Host-Only 192.168.56.10/24, sem gateway |
| Privilégio | Usuário comum | **Administrador** (para alterar o firewall) |

Não há bibliotecas externas: o projeto usa só a biblioteca padrão do Python.

## 2. Preparação do ambiente

A criação da VM, da rede Host-Only, das regras de permissão e dos snapshots
está descrita em [docs/ambiente.md](docs/ambiente.md). Em resumo, na máquina B,
em um PowerShell como Administrador:

```powershell
New-NetFirewallRule -DisplayName "LAB - Permitir controle TCP 5000" -Group "LaboratorioBase" `
  -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -RemoteAddress 192.168.56.0/24 -Profile Any
New-NetFirewallRule -DisplayName "LAB - Permitir HTTP teste TCP 8080" -Group "LaboratorioBase" `
  -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -RemoteAddress 192.168.56.0/24 -Profile Any
```

Teste a rede a partir da máquina A (PowerShell):

```powershell
Test-NetConnection 192.168.56.10 -Port 5000
```

## 3. Instalação

Nas **duas máquinas**:

```bash
git clone https://github.com/Danieeltrindade/projeto-firewall-remoto.git
cd projeto-firewall-remoto
git switch develop        # ou main, para a última versão publicada
```

Na máquina B, use a pasta `C:\projetos\projeto-firewall-remoto`.

## 4. Configuração

### 4.1 Token

Gere o token **uma vez**, em qualquer máquina:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4.2 config.json

Nas **duas máquinas**, copie o modelo e edite:

```bash
cp config.exemplo.json config.json
```

Troque `SUBSTITUA_PELO_TOKEN_GERADO` pelo token gerado. O valor precisa ser
**idêntico** nas duas máquinas. O servidor se recusa a iniciar com o token de
exemplo ou com menos de 32 caracteres.

O `config.json` está no `.gitignore`: **nunca** faça commit dele nem mostre o
token em prints.

### 4.3 Certificado TLS

Na **máquina B**, no Git Bash, na pasta do projeto:

```bash
bash certificados/gerar_certificado.sh
```

São criados `certificados/servidor.crt` (público) e `certificados/servidor.key`
(privado). Copie **apenas o `servidor.crt`** para a pasta `certificados/` da
máquina A. A chave privada nunca sai da máquina B.

Confira se o certificado é o mesmo nas duas máquinas (as impressões digitais
precisam ser iguais):

```bash
openssl x509 -in certificados/servidor.crt -noout -fingerprint -sha256
```

## 5. Execução

Siga esta ordem.

| # | Máquina | Terminal | Comando |
|---|---|---|---|
| 1 | B | PowerShell **como Administrador** | `python -m testes.servidor_http` |
| 2 | B | outro PowerShell **como Administrador** | `python -m servidor.servidor` |
| 3 | A | Git Bash | `python -m cliente.cliente` |

Todos os comandos rodam **na raiz do projeto**. Sem Administrador, o servidor
inicia com um aviso e responde `SEM_PRIVILEGIO` a bloquear e desbloquear.

No cliente:

```
1 - Bloquear porta       (Enter usa a porta padrão 8080)
2 - Desbloquear porta
3 - Consultar regras
0 - Sair
```

Para conferir o efeito, na máquina A:

```bash
curl --max-time 5 http://192.168.56.10:8080
```

- Liberada: mostra `Servico de teste ativo`.
- Bloqueada: termina em timeout (o pacote é descartado).

Os eventos do servidor ficam no console e no arquivo `servidor.log`.
Para encerrar qualquer programa: **Ctrl+C**.

## 6. Testes

```bash
# Testes unitários (qualquer máquina, sem rede)
python -m unittest discover -s testes -v

# Integração: antes, durante e depois do bloqueio (máquina A, com B ligada)
python -m testes.teste_conectividade --sequencia --pausa

# Testes negativos contra o servidor real (máquina A, com B ligada)
python -m testes.teste_falhas

# Servidor indisponível (máquina A, com o servidor de controle de B desligado)
python -m testes.teste_falhas --indisponivel
```

Casos e roteiros manuais: [docs/testes-falhas.md](docs/testes-falhas.md).

## 7. Protocolo

Uma requisição JSON por conexão, uma linha terminada em `\n`, no máximo
4096 bytes. Exemplo:

```json
{"id": "a1b2c3", "token": "<token>", "acao": "bloquear", "porta": 8080}
```

Formato completo, os 15 códigos de resposta e exemplos:
[docs/protocolo.md](docs/protocolo.md).

## 8. Segurança

- **Nenhum comando vem da rede.** O cliente só escolhe a ação (`bloquear`,
  `desbloquear`, `consultar`) e a porta; os comandos PowerShell são fixos no
  servidor.
- **Lista de portas permitidas:** apenas a 8080. Qualquer outra porta recebe
  `PORTA_NAO_AUTORIZADA`.
- **Nome fixo de regra e grupo próprio** (`ProjetoFirewallRemoto`): o projeto só
  cria e remove as suas regras.
- **`subprocess` com argumentos separados e sem `shell=True`**, e a porta é
  conferida de novo antes de chegar ao PowerShell.
- **TLS 1.2 ou superior**, com o certificado do servidor fixado no cliente.
- **Token** gerado com `secrets` e comparado com `hmac.compare_digest`.
  Ele nunca aparece nos logs.
- **Limites:** 4096 bytes por mensagem, tempo limite em cada conexão e campos
  desconhecidos recusados.
- **Rede isolada:** a porta 5000 só aceita a rede 192.168.56.0/24.
- **Sem segredos no Git:** `config.json`, `*.key`, `*.crt`, `*.pem` e `*.log` estão
  no `.gitignore`.
- **Privilégio documentado:** só o servidor da máquina B precisa de Administrador.

## 9. Recuperação

Se a comunicação cair com a porta bloqueada, na **máquina B**, em um PowerShell
como Administrador:

```powershell
python -m servidor.recuperacao
```

O script remove só as regras do grupo `ProjetoFirewallRemoto`. O comando manual
equivalente e o snapshot `base-limpa` estão em
[docs/recuperacao.md](docs/recuperacao.md).

## 10. Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Arquivo config.json não encontrado` | config não criado | `cp config.exemplo.json config.json` e preencha o token |
| Servidor diz que o token é o de exemplo | token não trocado | gere um token (seção 4.1) |
| `TOKEN_INVALIDO` | tokens diferentes nas máquinas | copie o mesmo token para os dois `config.json` |
| `O certificado do servidor não confere` | `servidor.crt` diferente em A | copie o `.crt` de B de novo e compare a impressão digital |
| `Certificado não encontrado` | `.crt` ausente em A | copie `certificados/servidor.crt` da máquina B |
| Cliente: `não respondeu a tempo` | servidor desligado ou rede | confira o servidor em B e `Test-NetConnection 192.168.56.10 -Port 5000` |
| Servidor: `Não foi possível abrir 192.168.56.10:5000` | porta em uso ou IP errado | feche outro servidor aberto; confira o IP com `ipconfig` |
| `SEM_PRIVILEGIO` | servidor sem Administrador | abra o PowerShell como Administrador |
| `PORTA_NAO_AUTORIZADA` | outra porta digitada | aperte só Enter para usar a 8080 |
| curl em `localhost` falha na VM | `servidor_http` não está rodando | inicie `python -m testes.servidor_http` |
| Porta continua bloqueada | servidor caiu com a regra ativa | `python -m servidor.recuperacao` na máquina B |
| `Test-NetConnection` não existe | rodado no Git Bash | use o PowerShell |
| Texto com acentos estranhos no log | codificação | `Get-Content servidor.log -Encoding UTF8` |

## 11. Organização do trabalho

- **Equipe:** I1 servidor e ambiente · I2 cliente, protocolo e autenticação ·
  I3 firewall · I4 testes e documentação.
- **Issues** com labels por integrante e milestones M1 a M6, acompanhadas no
  quadro Kanban do GitHub Projects.
- **Branches:** `main` (versões publicadas), `develop` (integração) e
  `feature/*` (uma por issue), com Pull Request e revisão.
- **Commits** no padrão Conventional Commits (`feat`, `fix`, `test`, `docs`, `chore`).
- **Releases** com tags anotadas a cada milestone (`v0.1.0` a `v1.0.0`).

## Documentação

- [docs/ambiente.md](docs/ambiente.md): topologia, VM, rede e snapshots
- [docs/protocolo.md](docs/protocolo.md): formato das mensagens e códigos
- [docs/recuperacao.md](docs/recuperacao.md): recuperação e limpeza das regras
- [docs/testes-falhas.md](docs/testes-falhas.md): testes negativos e roteiros manuais

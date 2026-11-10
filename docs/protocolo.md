# Protocolo de comunicação

**Versão 1.0.** Contrato entre o cliente (`cliente/cliente.py`, máquina A) e o servidor de controle (`servidor/servidor.py`, máquina B).

## 1. Transporte

| Item                    | Definição                                                 |
| ----------------------- | --------------------------------------------------------- |
| Protocolo               | TCP com TLS 1.2 ou superior                               |
| Endereço do servidor    | `192.168.56.10`, porta `5000`                             |
| Codificação             | UTF-8                                                     |
| Formato                 | Um objeto JSON por linha, terminado em `\n` (LF)          |
| Tamanho máximo          | 4096 bytes por mensagem, incluindo o `\n`                 |
| Requisições por conexão | **Uma.** O servidor responde e encerra a conexão          |
| Tempo limite            | 10 segundos para o servidor receber a requisição completa |

O TCP entrega um fluxo contínuo de bytes, sem separação entre mensagens. O `\n` marca onde cada mensagem termina. Como o `json.dumps()` nunca gera quebras de linha dentro do JSON, o delimitador é inequívoco.

## 2. Requisição (cliente → servidor)

| Campo   | Tipo    | Obrigatório                   | Regras                                                                              |
| ------- | ------- | ----------------------------- | ----------------------------------------------------------------------------------- |
| `id`    | texto   | sempre                        | 1 a 64 caracteres. Gerado pelo cliente (UUID) e devolvido na resposta               |
| `token` | texto   | sempre                        | Segredo compartilhado entre cliente e servidor                                      |
| `acao`  | texto   | sempre                        | `bloquear`, `desbloquear` ou `consultar`                                            |
| `porta` | inteiro | em `bloquear` e `desbloquear` | Deve estar na lista de portas autorizadas (`8080`). **Não** é aceita em `consultar` |

Regras gerais:

- Campos não listados acima são rejeitados.
- `porta` deve ser um número inteiro: `"8080"` (texto), `8080.0` (decimal) e `true` (booleano) são inválidos.
- O cliente **não escolhe** o nome da regra nem o comando executado. Esses valores são fixos no servidor.

Formato transmitido (uma única linha):

```text
{"id": "3f2b9c1e", "token": "TOKEN_DE_EXEMPLO", "acao": "bloquear", "porta": 8080}\n
```

## 3. Resposta (servidor → cliente)

Toda resposta contém **sempre os mesmos cinco campos**:

| Campo      | Tipo            | Descrição                                                          |
| ---------- | --------------- | ------------------------------------------------------------------ |
| `id`       | texto ou `null` | O `id` da requisição. `null` quando a requisição não pôde ser lida |
| `status`   | texto           | `ok` (pedido atendido) ou `erro` (pedido recusado ou falhou)       |
| `codigo`   | texto           | Código fixo da seção 5. É ele que o programa interpreta            |
| `mensagem` | texto           | Explicação em português, para o usuário                            |
| `dados`    | objeto          | Informações adicionais. `{}` quando não houver                     |

## 4. Ordem de processamento no servidor

O servidor valida a requisição nesta ordem e **para na primeira falha**:

| Etapa | Verificação                                       | Código em caso de falha                                   |
| ----- | ------------------------------------------------- | --------------------------------------------------------- |
| 1     | Tamanho até 4096 bytes                            | `MENSAGEM_MUITO_GRANDE`                                   |
| 2     | JSON válido e do tipo objeto                      | `JSON_INVALIDO`                                           |
| 3     | Token presente e correto                          | `TOKEN_INVALIDO`                                          |
| 4     | Campos obrigatórios, campos desconhecidos e tipos | `CAMPO_AUSENTE` / `CAMPO_INVALIDO`                        |
| 5     | Ação permitida                                    | `ACAO_INVALIDA`                                           |
| 6     | Porta autorizada                                  | `PORTA_NAO_AUTORIZADA`                                    |
| 7     | Execução no Windows Firewall                      | Códigos de sucesso, ou `SEM_PRIVILEGIO` / `ERRO_FIREWALL` |

O token é verificado **antes** dos demais campos: quem não está autenticado não recebe nenhuma informação sobre o formato esperado.

## 5. Códigos de resposta

### Sucesso (`status: "ok"`)

| Código               | Quando ocorre                                              |
| -------------------- | ---------------------------------------------------------- |
| `REGRA_CRIADA`       | `bloquear`: a regra foi criada                             |
| `REGRA_JA_EXISTE`    | `bloquear`: a regra já existia e nada foi alterado         |
| `REGRA_REMOVIDA`     | `desbloquear`: a regra foi removida                        |
| `REGRA_INEXISTENTE`  | `desbloquear`: não havia regra e nada foi alterado         |
| `CONSULTA_REALIZADA` | `consultar`: lista das regras do projeto em `dados.regras` |

### Erro (`status: "erro"`)

| Código                  | Quando ocorre                                                                |
| ----------------------- | ---------------------------------------------------------------------------- |
| `MENSAGEM_MUITO_GRANDE` | A mensagem ultrapassou 4096 bytes                                            |
| `JSON_INVALIDO`         | O conteúdo não é um JSON válido ou não é um objeto                           |
| `TOKEN_INVALIDO`        | O token está ausente ou incorreto                                            |
| `CAMPO_AUSENTE`         | Falta um campo obrigatório                                                   |
| `CAMPO_INVALIDO`        | Campo com tipo errado, campo desconhecido, ou `porta` enviada em `consultar` |
| `ACAO_INVALIDA`         | A ação não é `bloquear`, `desbloquear` nem `consultar`                       |
| `PORTA_NAO_AUTORIZADA`  | A porta não está na lista de portas autorizadas                              |
| `SEM_PRIVILEGIO`        | O servidor não está sendo executado como Administrador                       |
| `ERRO_FIREWALL`         | O PowerShell falhou ao executar a operação                                   |
| `ERRO_INTERNO`          | Erro inesperado no servidor                                                  |

## 6. Idempotência

`bloquear` e `desbloquear` são idempotentes: repetir a mesma requisição leva ao mesmo estado final e responde `status: "ok"`.

Isso torna seguro repetir um pedido após uma falha de rede. Se o servidor criou a regra mas a resposta se perdeu, o cliente pode enviar `bloquear` novamente e receberá `REGRA_JA_EXISTE`, sem duplicar a regra.

## 7. Exemplos

As mensagens aparecem formatadas em várias linhas apenas para facilitar a leitura. Na rede, cada uma ocupa **uma única linha** terminada em `\n`.

### 7.1 Bloquear (regra criada)

Requisição:

```json
{ "id": "a1", "token": "TOKEN_DE_EXEMPLO", "acao": "bloquear", "porta": 8080 }
```

Resposta:

```json
{
  "id": "a1",
  "status": "ok",
  "codigo": "REGRA_CRIADA",
  "mensagem": "Regra de bloqueio criada para a porta TCP 8080.",
  "dados": { "porta": 8080, "regra": "ProjetoFirewallRemoto-Bloqueio-TCP-8080" }
}
```

### 7.2 Bloquear novamente (regra já existente)

```json
{
  "id": "a2",
  "status": "ok",
  "codigo": "REGRA_JA_EXISTE",
  "mensagem": "A porta TCP 8080 já estava bloqueada. Nenhuma alteração foi feita.",
  "dados": { "porta": 8080, "regra": "ProjetoFirewallRemoto-Bloqueio-TCP-8080" }
}
```

### 7.3 Desbloquear (regra removida)

Requisição:

```json
{
  "id": "a3",
  "token": "TOKEN_DE_EXEMPLO",
  "acao": "desbloquear",
  "porta": 8080
}
```

Resposta:

```json
{
  "id": "a3",
  "status": "ok",
  "codigo": "REGRA_REMOVIDA",
  "mensagem": "Regra de bloqueio da porta TCP 8080 removida.",
  "dados": { "porta": 8080 }
}
```

### 7.4 Desbloquear sem regra ativa

```json
{
  "id": "a4",
  "status": "ok",
  "codigo": "REGRA_INEXISTENTE",
  "mensagem": "Não havia regra de bloqueio para a porta TCP 8080. Nenhuma alteração foi feita.",
  "dados": { "porta": 8080 }
}
```

### 7.5 Consultar

Requisição:

```json
{ "id": "a5", "token": "TOKEN_DE_EXEMPLO", "acao": "consultar" }
```

Resposta:

```json
{
  "id": "a5",
  "status": "ok",
  "codigo": "CONSULTA_REALIZADA",
  "mensagem": "1 regra do projeto encontrada.",
  "dados": {
    "regras": [
      {
        "nome": "ProjetoFirewallRemoto-Bloqueio-TCP-8080",
        "porta": 8080,
        "direcao": "Inbound",
        "acao": "Block",
        "habilitada": true
      }
    ]
  }
}
```

### 7.6 Token inválido

```json
{
  "id": "b1",
  "status": "erro",
  "codigo": "TOKEN_INVALIDO",
  "mensagem": "Autenticação recusada.",
  "dados": {}
}
```

### 7.7 Ação inválida

Requisição:

```json
{ "id": "b2", "token": "TOKEN_DE_EXEMPLO", "acao": "formatar", "porta": 8080 }
```

Resposta:

```json
{
  "id": "b2",
  "status": "erro",
  "codigo": "ACAO_INVALIDA",
  "mensagem": "Ação 'formatar' não permitida. Use: bloquear, desbloquear ou consultar.",
  "dados": {}
}
```

### 7.8 Porta não autorizada

Requisição:

```json
{ "id": "b3", "token": "TOKEN_DE_EXEMPLO", "acao": "bloquear", "porta": 3389 }
```

Resposta:

```json
{
  "id": "b3",
  "status": "erro",
  "codigo": "PORTA_NAO_AUTORIZADA",
  "mensagem": "A porta 3389 não está na lista de portas autorizadas.",
  "dados": {}
}
```

### 7.9 Porta enviada como texto

Requisição:

```json
{ "id": "b4", "token": "TOKEN_DE_EXEMPLO", "acao": "bloquear", "porta": "8080" }
```

Resposta:

```json
{
  "id": "b4",
  "status": "erro",
  "codigo": "CAMPO_INVALIDO",
  "mensagem": "O campo 'porta' deve ser um número inteiro.",
  "dados": {}
}
```

### 7.10 Campo ausente

Requisição:

```json
{ "id": "b5", "token": "TOKEN_DE_EXEMPLO", "porta": 8080 }
```

Resposta:

```json
{
  "id": "b5",
  "status": "erro",
  "codigo": "CAMPO_AUSENTE",
  "mensagem": "Campo obrigatório ausente: 'acao'.",
  "dados": {}
}
```

### 7.11 JSON inválido

Requisição (falta fechar a chave):

```text
{"id": "b6", "acao": "bloquear"
```

Resposta (o `id` não pôde ser lido):

```json
{
  "id": null,
  "status": "erro",
  "codigo": "JSON_INVALIDO",
  "mensagem": "A requisição não é um JSON válido.",
  "dados": {}
}
```

### 7.12 Mensagem muito grande

Requisição com mais de 4096 bytes. O servidor para de ler, responde e encerra a conexão:

```json
{
  "id": null,
  "status": "erro",
  "codigo": "MENSAGEM_MUITO_GRANDE",
  "mensagem": "A requisição ultrapassa o limite de 4096 bytes.",
  "dados": {}
}
```

### 7.13 Servidor sem privilégio de Administrador

```json
{
  "id": "c1",
  "status": "erro",
  "codigo": "SEM_PRIVILEGIO",
  "mensagem": "O servidor precisa ser executado como Administrador para alterar o firewall.",
  "dados": {}
}
```

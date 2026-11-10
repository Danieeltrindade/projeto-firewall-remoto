# Protocolo de comunicação

**Versão 1.0.** Contrato entre o cliente (`cliente/cliente.py`, máquina A) e o servidor de controle (`servidor/servidor.py`, máquina B).

## 1. Transporte

| Item | Definição |
|---|---|
| Protocolo | TCP com TLS 1.2 ou superior |
| Endereço do servidor | `192.168.56.10`, porta `5000` |
| Codificação | UTF-8 |
| Formato | Um objeto JSON por linha, terminado em `\n` (LF) |
| Tamanho máximo | 4096 bytes por mensagem, incluindo o `\n` |
| Requisições por conexão | **Uma.** O servidor responde e encerra a conexão |
| Tempo limite | 10 segundos para o servidor receber a requisição completa |

O TCP entrega um fluxo contínuo de bytes, sem separação entre mensagens. O `\n` marca onde cada mensagem termina. Como o `json.dumps()` nunca gera quebras de linha dentro do JSON, o delimitador é inequívoco.

## 2. Requisição (cliente → servidor)

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | texto | sempre | 1 a 64 caracteres. Gerado pelo cliente (UUID) e devolvido na resposta |
| `token` | texto | sempre | Segredo compartilhado entre cliente e servidor |
| `acao` | texto | sempre | `bloquear`, `desbloquear` ou `consultar` |
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

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | texto ou `null` | O `id` da requisição. `null` quando a requisição não pôde ser lida |
| `status` | texto | `ok` (pedido atendido) ou `erro` (pedido recusado ou falhou) |
| `codigo` | texto | Código fixo da seção 5. É ele que o programa interpreta |
| `mensagem` | texto | Explicação em português, para o usuário |
| `dados` | objeto | Informações adicionais. `{}` quando não houver |

## 4. Ordem de processamento no servidor

O servidor valida a requisição nesta ordem e **para na primeira falha**:

| Etapa | Verificação | Código em caso de falha |
|---|---|---|
| 1 | Tamanho até 4096 bytes | `MENSAGEM_MUITO_GRANDE` |
| 2 | JSON válido e do tipo objeto | `JSON_INVALIDO` |
| 3 | Token presente e correto | `TOKEN_INVALIDO` |
| 4 | Campos obrigatórios, campos desconhecidos e tipos | `CAMPO_AUSENTE` / `CAMPO_INVALIDO` |
| 5 | Ação permitida | `ACAO_INVALIDA` |
| 6 | Porta autorizada | `PORTA_NAO_AUTORIZADA` |
| 7 | Execução no Windows Firewall | Códigos de sucesso, ou `SEM_PRIVILEGIO` / `ERRO_FIREWALL` |

O token é verificado **antes** dos demais campos: quem não está autenticado não recebe nenhuma informação sobre o formato esperado.
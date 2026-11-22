"""Testes negativos e de falha contra o servidor real (Integrante 4).

Envia à máquina B requisições inválidas ou maliciosas e confere se cada
uma recebe o código de erro esperado, sem executar nada no firewall.
Depois confere a idempotência (regra já existente) e se o servidor
continua funcionando no final.

O token nunca é exibido: só aparecem o nome do caso e os códigos.

Execução (na raiz do projeto, na máquina A, com o servidor de B ligado):
    python -m testes.teste_falhas
    python -m testes.teste_falhas --indisponivel   (com o servidor de B DESLIGADO)
"""

import argparse
import io
import json
import sys
import uuid
from contextlib import redirect_stdout

from cliente.cliente import abrir_conexao, criar_contexto_tls, executar_acao
from comum.protocolo import TAMANHO_MAXIMO, carregar_config, receber_mensagem

PORTA = 8080


def linha_json(objeto):
    """Converte um dicionário em uma linha do protocolo (bytes terminados em \\n)."""
    return json.dumps(objeto).encode("utf-8") + b"\n"


def requisicao(token, acao, **extras):
    return {"id": uuid.uuid4().hex, "token": token, "acao": acao, **extras}


def enviar_bruto(config, contexto_tls, dados):
    """Envia bytes exatamente como estão e devolve a resposta do servidor."""
    with abrir_conexao(config, contexto_tls) as conexao:
        conexao.sendall(dados)
        return receber_mensagem(conexao)


def casos_negativos(token):
    """(nome, bytes enviados, código esperado). Nenhum deles pode chegar ao firewall."""
    return [
        ("Token inválido", linha_json(requisicao("0" * 64, "consultar")), "TOKEN_INVALIDO"),
        ("Token ausente", linha_json({"id": uuid.uuid4().hex, "acao": "consultar"}), "TOKEN_INVALIDO"),
        ("Ação inválida", linha_json(requisicao(token, "formatar")), "ACAO_INVALIDA"),
        ("Comando PowerShell como ação",
         linha_json(requisicao(token, "Remove-NetFirewallRule -All")), "ACAO_INVALIDA"),
        ("Porta não autorizada (22)", linha_json(requisicao(token, "bloquear", porta=22)),
         "PORTA_NAO_AUTORIZADA"),
        ("Porta com comando injetado",
         linha_json(requisicao(token, "bloquear", porta="8080; Remove-NetFirewallRule -All")),
         "CAMPO_INVALIDO"),
        ("Campo extra 'comando'", linha_json(requisicao(token, "consultar", comando="whoami")),
         "CAMPO_INVALIDO"),
        ("JSON malformado", b'{"acao": "consultar"\n', "JSON_INVALIDO"),
        ("Mensagem grande demais", b"x" * TAMANHO_MAXIMO, "MENSAGEM_MUITO_GRANDE"),
    ]


def casos_idempotencia(token):
    """Sequência que precisa terminar com a porta liberada."""
    return [
        ("Bloquear (1ª vez)", linha_json(requisicao(token, "bloquear", porta=PORTA)),
         {"REGRA_CRIADA", "REGRA_JA_EXISTE"}),
        ("Bloquear de novo", linha_json(requisicao(token, "bloquear", porta=PORTA)), {"REGRA_JA_EXISTE"}),
        ("Consultar (sem duplicata)", linha_json(requisicao(token, "consultar")), {"CONSULTA_REALIZADA"}),
        ("Desbloquear", linha_json(requisicao(token, "desbloquear", porta=PORTA)), {"REGRA_REMOVIDA"}),
        ("Desbloquear de novo", linha_json(requisicao(token, "desbloquear", porta=PORTA)),
         {"REGRA_INEXISTENTE"}),
        ("Servidor ainda responde", linha_json(requisicao(token, "consultar")), {"CONSULTA_REALIZADA"}),
    ]


def executar_caso(config, contexto_tls, nome, dados, esperados):
    """Executa um caso e mostra uma linha de resultado. Devolve True se passou."""
    if isinstance(esperados, str):
        esperados = {esperados}
    try:
        resposta = enviar_bruto(config, contexto_tls, dados)
    except (OSError, ValueError) as erro:
        print(f"  FALHOU  {nome:32} erro de comunicação: {type(erro).__name__}")
        return False

    obtido = resposta.get("codigo")
    passou = obtido in esperados
    if passou and nome.startswith("Consultar"):
        quantidade = len(resposta.get("dados", {}).get("regras", []))
        passou = quantidade == 1
        obtido = f"{obtido} ({quantidade} regra)"
    situacao = "OK    " if passou else "FALHOU"
    print(f"  {situacao}  {nome:32} esperado {'/'.join(sorted(esperados)):30} obtido {obtido}")
    return passou


def testar_servidor_ligado(config):
    contexto_tls = criar_contexto_tls(config)
    resultados = []

    print("Casos negativos (nada pode ser executado no firewall):")
    for nome, dados, esperado in casos_negativos(config["token"]):
        resultados.append(executar_caso(config, contexto_tls, nome, dados, esperado))

    print("\nRegra já existente e recuperação do estado:")
    for nome, dados, esperados in casos_idempotencia(config["token"]):
        resultados.append(executar_caso(config, contexto_tls, nome, dados, esperados))

    aprovados = sum(resultados)
    print(f"\n{aprovados}/{len(resultados)} casos aprovados.")
    return aprovados == len(resultados)


def testar_servidor_desligado(config):
    """Com o servidor de B desligado, o cliente precisa mostrar uma falha clara."""
    print("Servidor indisponível (aguarde o tempo limite do cliente)...")
    saida = io.StringIO()
    with redirect_stdout(saida):
        executar_acao(config, criar_contexto_tls(config), "consultar")
    mensagem = saida.getvalue().strip()
    print(f"  Mensagem do cliente: {mensagem}")
    passou = mensagem.startswith("[FALHA]")
    print(f"  {'OK' if passou else 'FALHOU'}: o cliente {'informou' if passou else 'NÃO informou'} a falha sem travar.")
    return passou


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Testes negativos e de falha contra o servidor real.")
    parser.add_argument("--indisponivel", action="store_true", help="teste com o servidor desligado")
    opcoes = parser.parse_args(argumentos)

    config = carregar_config()
    if opcoes.indisponivel:
        aprovado = testar_servidor_desligado(config)
    else:
        aprovado = testar_servidor_ligado(config)
    print("\nRESULTADO: " + ("APROVADO" if aprovado else "REPROVADO"))
    return 0 if aprovado else 1


if __name__ == "__main__":
    sys.exit(main())
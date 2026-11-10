"""Funções do protocolo compartilhadas entre cliente e servidor.

Formato: um objeto JSON por linha, codificado em UTF-8 e terminado em "\n".
Especificação completa em docs/protocolo.md.
"""

import json
from pathlib import Path

TAMANHO_MAXIMO = 4096  # bytes por mensagem, incluindo o "\n"
DELIMITADOR = b"\n"
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_CONFIG = RAIZ_PROJETO / "config.json"


class MensagemMuitoGrande(Exception):
    """A mensagem ultrapassou TAMANHO_MAXIMO bytes."""


class ConexaoEncerrada(Exception):
    """O outro lado fechou a conexão antes de enviar uma mensagem completa."""


def carregar_config(caminho=CAMINHO_CONFIG):
    """Lê o config.json da raiz do projeto e devolve um dicionário."""
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def enviar_mensagem(conexao, dados):
    """Converte um dicionário em JSON e envia como uma linha terminada em "\n"."""
    texto = json.dumps(dados, ensure_ascii=False)
    conexao.sendall(texto.encode("utf-8") + DELIMITADOR)


def receber_linha(conexao):
    """Lê bytes até encontrar o "\n" e devolve a linha, sem o "\n"."""
    buffer = b""
    while DELIMITADOR not in buffer:
        if len(buffer) >= TAMANHO_MAXIMO:
            raise MensagemMuitoGrande()
        pedaco = conexao.recv(1024)
        if not pedaco:
            raise ConexaoEncerrada()
        buffer += pedaco

    linha, _, _ = buffer.partition(DELIMITADOR)
    if len(linha) + 1 > TAMANHO_MAXIMO:
        raise MensagemMuitoGrande()
    return linha


def receber_mensagem(conexao):
    """Recebe uma linha e a converte de JSON para dicionário."""
    linha = receber_linha(conexao)
    return json.loads(linha.decode("utf-8"))
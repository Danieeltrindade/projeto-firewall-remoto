"""Servidor de controle da máquina B (Integrante 1).

Recebe uma requisição JSON por conexão, protegida por TLS, e responde com JSON estruturado.
Nesta versão o servidor apenas confirma o recebimento: autenticação,
validação e firewall serão ligados nas Issues #7, #8 e #11.

Execução (na raiz do projeto):  python -m servidor.servidor
"""

import json
import socket
import ssl

from comum.protocolo import (
    ConexaoEncerrada,
    MensagemMuitoGrande,
    RAIZ_PROJETO,
    carregar_config,
    enviar_mensagem,
    receber_linha,
)

TEMPO_LIMITE = 10  # segundos para o cliente enviar a requisição completa


def montar_resposta(id_requisicao, status, codigo, mensagem, dados=None):
    """Cria uma resposta com os cinco campos definidos em docs/protocolo.md."""
    return {
        "id": id_requisicao,
        "status": status,
        "codigo": codigo,
        "mensagem": mensagem,
        "dados": dados if dados is not None else {},
    }


def processar_linha(linha):
    """Interpreta a linha recebida e devolve o dicionário de resposta."""
    try:
        requisicao = json.loads(linha.decode("utf-8"))
    except ValueError:
        return montar_resposta(
            None, "erro", "JSON_INVALIDO", "A requisição não é um JSON válido."
        )

    if not isinstance(requisicao, dict):
        return montar_resposta(
            None, "erro", "JSON_INVALIDO", "A requisição deve ser um objeto JSON."
        )

    id_requisicao = requisicao.get("id")
    if not isinstance(id_requisicao, str) or not 1 <= len(id_requisicao) <= 64:
        id_requisicao = None

    # PROVISÓRIO (Issue #4): apenas confirma o recebimento.
    # Será substituído por autenticação (#7), validação (#8) e firewall (#11).
    return montar_resposta(
        id_requisicao,
        "ok",
        "RECEBIDO",
        "Requisição recebida pelo servidor.",
        {"acao": requisicao.get("acao")},
    )


def criar_contexto_tls(config):
    """Prepara o TLS do servidor: certificado + chave privada, TLS 1.2 ou superior."""
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    contexto.load_cert_chain(
        certfile=RAIZ_PROJETO / config["certificado"],
        keyfile=RAIZ_PROJETO / config["chave_privada"],
    )
    return contexto


def atender_cliente(conexao, endereco):
    """Recebe uma requisição, responde e retorna (uma requisição por conexão)."""
    ip_cliente = endereco[0]

    try:
        linha = receber_linha(conexao)
        resposta = processar_linha(linha)
    except MensagemMuitoGrande:
        resposta = montar_resposta(
            None,
            "erro",
            "MENSAGEM_MUITO_GRANDE",
            "A requisição ultrapassa o limite de 4096 bytes.",
        )
    except ConexaoEncerrada:
        print(f"[{ip_cliente}] conexão encerrada sem enviar requisição")
        return
    except TimeoutError:
        print(f"[{ip_cliente}] tempo limite esgotado sem requisição completa")
        return
    except OSError as erro:
        print(f"[{ip_cliente}] erro de comunicação: {erro}")
        return

    try:
        enviar_mensagem(conexao, resposta)
    except OSError as erro:
        print(f"[{ip_cliente}] falha ao enviar resposta: {erro}")
        return

    print(f"[{ip_cliente}] respondido: {resposta['codigo']}")


def aceitar_tls(conexao, endereco, contexto_tls):
    """Faz o handshake TLS; devolve a conexão cifrada ou None se falhar."""
    conexao.settimeout(TEMPO_LIMITE)
    try:
        return contexto_tls.wrap_socket(conexao, server_side=True)
    except (ssl.SSLError, OSError) as erro:
        print(f"[{endereco[0]}] handshake TLS recusado: {erro}")
        return None


def iniciar_servidor():
    """Abre a porta de controle e atende conexões até Ctrl+C."""
    config = carregar_config()
    host = config["servidor_host"]
    porta = config["servidor_porta"]
    contexto_tls = criar_contexto_tls(config)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((host, porta))
        servidor.listen()
        servidor.settimeout(1.0)  # permite que o Ctrl+C seja percebido no Windows
        print(f"Servidor de controle escutando em {host}:{porta} (TLS). Ctrl+C para encerrar.")

        while True:
            try:
                conexao, endereco = servidor.accept()
            except TimeoutError:
                continue  # nenhuma conexão neste segundo; volta a aguardar

            with conexao:
                print(f"[{endereco[0]}] conexão recebida")
                conexao_tls = aceitar_tls(conexao, endereco, contexto_tls)
                if conexao_tls is not None:
                    with conexao_tls:
                        atender_cliente(conexao_tls, endereco)


if __name__ == "__main__":
    try:
        iniciar_servidor()
    except KeyboardInterrupt:
        print("\nServidor encerrado pelo operador.")
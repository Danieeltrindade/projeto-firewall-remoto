"""Servidor de controle da máquina B (Integrante 1).

Recebe uma requisição JSON por conexão, protegida por TLS, e responde com JSON estruturado.
Toda requisição precisa trazer o token correto (Issue #7) e respeitar o
contrato: ações e portas permitidas (Issue #8). O firewall entra na Issue #11.

Os eventos são registrados no console e no arquivo servidor.log (Issue #9).
O token nunca é registrado.

Execução (na raiz do projeto):  python -m servidor.servidor
"""

import json
import logging
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
from servidor.autenticacao import token_configurado_valido, token_valido
from servidor.validacao import PORTAS_AUTORIZADAS, RequisicaoInvalida, validar_requisicao

TEMPO_LIMITE = 10  # segundos para o cliente enviar a requisição completa
ARQUIVO_LOG = RAIZ_PROJETO / "servidor.log"

log = logging.getLogger("servidor")


def configurar_registro():
    """Envia os registros para o console e para o arquivo servidor.log."""
    formato = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    for destino in (logging.StreamHandler(), logging.FileHandler(ARQUIVO_LOG, encoding="utf-8")):
        destino.setFormatter(formato)
        log.addHandler(destino)
    log.setLevel(logging.INFO)


def montar_resposta(id_requisicao, status, codigo, mensagem, dados=None):
    """Cria uma resposta com os cinco campos definidos em docs/protocolo.md."""
    return {
        "id": id_requisicao,
        "status": status,
        "codigo": codigo,
        "mensagem": mensagem,
        "dados": dados if dados is not None else {},
    }


def processar_linha(linha, token_esperado):
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

    # Autenticação antes de qualquer outra verificação (docs/protocolo.md, seção 4)
    if not token_valido(requisicao.get("token"), token_esperado):
        return montar_resposta(
            id_requisicao, "erro", "TOKEN_INVALIDO", "Autenticação recusada."
        )

    # Campos, tipos, ação e porta (docs/protocolo.md, seção 4, etapas 4 a 6)
    try:
        acao, porta = validar_requisicao(requisicao)
    except RequisicaoInvalida as erro:
        return montar_resposta(id_requisicao, "erro", erro.codigo, erro.mensagem)

    # PROVISÓRIO: a requisição é válida. A execução no firewall entra na Issue #11.
    return montar_resposta(
        id_requisicao,
        "ok",
        "RECEBIDO",
        "Requisição válida recebida pelo servidor.",
        {"acao": acao, "porta": porta},
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


def atender_cliente(conexao, endereco, token_esperado):
    """Recebe uma requisição, responde e retorna (uma requisição por conexão)."""
    ip_cliente = endereco[0]

    try:
        linha = receber_linha(conexao)
        resposta = processar_linha(linha, token_esperado)
    except MensagemMuitoGrande:
        resposta = montar_resposta(
            None,
            "erro",
            "MENSAGEM_MUITO_GRANDE",
            "A requisição ultrapassa o limite de 4096 bytes.",
        )
    except ConexaoEncerrada:
        log.info("[%s] conexão encerrada sem enviar requisição", ip_cliente)
        return
    except TimeoutError:
        log.warning("[%s] tempo limite esgotado sem requisição completa", ip_cliente)
        return
    except OSError as erro:
        log.warning("[%s] erro de comunicação: %s", ip_cliente, erro)
        return

    try:
        enviar_mensagem(conexao, resposta)
    except OSError as erro:
        log.warning("[%s] falha ao enviar resposta: %s", ip_cliente, erro)
        return

    registrar_resposta(ip_cliente, resposta)


def registrar_resposta(ip_cliente, resposta):
    """Registra o resultado de uma requisição (nunca o token)."""
    nivel = logging.INFO if resposta["status"] == "ok" else logging.WARNING
    log.log(
        nivel,
        "[%s] id=%r -> %s: %s %s",
        ip_cliente,
        resposta["id"],
        resposta["codigo"],
        resposta["mensagem"],
        resposta["dados"] or "",
    )


def aceitar_tls(conexao, endereco, contexto_tls):
    """Faz o handshake TLS; devolve a conexão cifrada ou None se falhar."""
    conexao.settimeout(TEMPO_LIMITE)
    try:
        return contexto_tls.wrap_socket(conexao, server_side=True)
    except (ssl.SSLError, OSError) as erro:
        log.warning("[%s] handshake TLS recusado: %s", endereco[0], erro)
        return None


def iniciar_servidor():
    """Abre a porta de controle e atende conexões até Ctrl+C."""
    config = carregar_config()
    host = config["servidor_host"]
    porta = config["servidor_porta"]
    token_esperado = config["token"]

    if not token_configurado_valido(token_esperado):
        log.error("O token do config.json é o de exemplo ou tem menos de 32 caracteres.")
        log.error("Gere um token novo e coloque o mesmo valor no config.json das duas máquinas.")
        return

    contexto_tls = criar_contexto_tls(config)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        try:
            servidor.bind((host, porta))
        except OSError as erro:
            log.error("Não foi possível abrir %s:%s: %s", host, porta, erro)
            log.error("A porta já está em uso (outro servidor aberto?) ou o IP não pertence a esta máquina.")
            return
        servidor.listen()
        servidor.settimeout(1.0)  # permite que o Ctrl+C seja percebido no Windows
        log.info("Servidor de controle escutando em %s:%s (TLS). Ctrl+C para encerrar.", host, porta)
        log.info("Portas autorizadas: %s. Registro em %s", sorted(PORTAS_AUTORIZADAS), ARQUIVO_LOG.name)

        while True:
            try:
                conexao, endereco = servidor.accept()
            except TimeoutError:
                continue  # nenhuma conexão neste segundo; volta a aguardar

            with conexao:
                log.info("[%s] conexão recebida", endereco[0])
                conexao_tls = aceitar_tls(conexao, endereco, contexto_tls)
                if conexao_tls is not None:
                    with conexao_tls:
                        atender_cliente(conexao_tls, endereco, token_esperado)


if __name__ == "__main__":
    configurar_registro()
    try:
        iniciar_servidor()
    except KeyboardInterrupt:
        log.info("Servidor encerrado pelo operador.")
    except FileNotFoundError as erro:
        log.error("Arquivo não encontrado: %s", erro.filename)
        log.error("Confira o config.json e os certificados na pasta do projeto.")
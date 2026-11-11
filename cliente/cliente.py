"""Cliente de controle da máquina A (Integrante 2).

Menu interativo que envia requisições ao servidor da máquina B no formato
definido em docs/protocolo.md e exibe as respostas de forma compreensível.

A comunicação é protegida por TLS: o cliente só aceita o servidor que
apresentar o certificado de certificados/servidor.crt.

Execução (na raiz do projeto):  python -m cliente.cliente
"""

import socket
import ssl
import uuid

from comum.protocolo import (
    ConexaoEncerrada,
    RAIZ_PROJETO,
    carregar_config,
    enviar_mensagem,
    receber_mensagem,
)

PORTA_PADRAO = 8080

OPCOES = {
    "1": "bloquear",
    "2": "desbloquear",
    "3": "consultar",
}


def montar_requisicao(token, acao, porta=None):
    """Cria a requisição com os campos exigidos pelo contrato."""
    requisicao = {
        "id": uuid.uuid4().hex,
        "token": token,
        "acao": acao,
    }
    if porta is not None:
        requisicao["porta"] = porta
    return requisicao


def criar_contexto_tls(config):
    """Prepara o TLS do cliente: confia apenas no certificado do servidor."""
    contexto = ssl.create_default_context(cafile=RAIZ_PROJETO / config["certificado"])
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    return contexto


def abrir_conexao(config, contexto_tls):
    """Abre a conexão TCP e faz o handshake TLS com o servidor de controle."""
    conexao = socket.create_connection(
        (config["servidor_host"], config["servidor_porta"]),
        timeout=config["timeout_segundos"],
    )
    try:
        return contexto_tls.wrap_socket(conexao, server_hostname=config["servidor_host"])
    except BaseException:
        conexao.close()
        raise


def enviar_requisicao(config, contexto_tls, requisicao):
    """Envia uma requisição e devolve a resposta do servidor (dicionário)."""
    with abrir_conexao(config, contexto_tls) as conexao:
        enviar_mensagem(conexao, requisicao)
        return receber_mensagem(conexao)


def perguntar_porta():
    """Pede a porta ao usuário; Enter vazio usa a porta padrão."""
    while True:
        texto = input(f"Porta [{PORTA_PADRAO}]: ").strip()
        if texto == "":
            return PORTA_PADRAO
        if texto.isdigit() and 1 <= int(texto) <= 65535:
            return int(texto)
        print("Porta inválida. Digite um número entre 1 e 65535.")


def exibir_resposta(resposta):
    """Mostra a resposta do servidor de forma legível."""
    rotulo = "OK" if resposta.get("status") == "ok" else "RECUSADO"
    print(f"\n[{rotulo}] {resposta.get('codigo')}")
    print(f"  {resposta.get('mensagem')}")

    regras = resposta.get("dados", {}).get("regras")
    if regras is not None:
        if not regras:
            print("  Nenhuma regra do projeto ativa.")
        for regra in regras:
            print(f"  - {regra.get('nome')} | porta {regra.get('porta')} | {regra.get('acao')}")


def executar_acao(config, contexto_tls, acao):
    """Monta, envia e exibe uma requisição, tratando falhas de comunicação."""
    porta = perguntar_porta() if acao in ("bloquear", "desbloquear") else None
    requisicao = montar_requisicao(config["token"], acao, porta)

    try:
        resposta = enviar_requisicao(config, contexto_tls, requisicao)
    except ssl.SSLCertVerificationError:
        print("\n[FALHA] O certificado do servidor não confere. Conexão recusada por segurança.")
    except ssl.SSLError as erro:
        print(f"\n[FALHA] Erro na negociação TLS: {erro}")
    except ConnectionRefusedError:
        print("\n[FALHA] O servidor recusou a conexão. Ele está em execução na máquina B?")
    except TimeoutError:
        print("\n[FALHA] O servidor não respondeu a tempo. Verifique a rede e o servidor.")
    except ConexaoEncerrada:
        print("\n[FALHA] O servidor encerrou a conexão sem responder.")
    except ValueError:
        print("\n[FALHA] O servidor enviou uma resposta em formato inválido.")
    except OSError as erro:
        print(f"\n[FALHA] Erro de comunicação: {erro}")
    else:
        exibir_resposta(resposta)


def mostrar_menu(config):
    print("\n=== Controle remoto do firewall ===")
    print(f"Servidor: {config['servidor_host']}:{config['servidor_porta']}")
    print("1 - Bloquear porta")
    print("2 - Desbloquear porta")
    print("3 - Consultar regras")
    print("0 - Sair")


def main():
    try:
        config = carregar_config()
    except FileNotFoundError:
        print("Arquivo config.json não encontrado. Copie config.exemplo.json para config.json.")
        return

    try:
        contexto_tls = criar_contexto_tls(config)
    except FileNotFoundError:
        print(f"Certificado não encontrado: {config['certificado']}. Copie o servidor.crt da máquina B.")
        return

    while True:
        mostrar_menu(config)
        escolha = input("Opção: ").strip()

        if escolha == "0":
            print("Encerrando o cliente.")
            break
        if escolha in OPCOES:
            executar_acao(config, contexto_tls, OPCOES[escolha])
        else:
            print("Opção inválida. Escolha 0, 1, 2 ou 3.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCliente encerrado.")
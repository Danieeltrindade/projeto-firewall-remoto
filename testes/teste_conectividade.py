"""Teste de conectividade da porta 8080 (Integrante 4).

Comprova que o tráfego para o serviço HTTP da máquina B é descartado
durante o bloqueio e volta a funcionar depois da remoção da regra.

Cada verificação faz duas tentativas e mostra horário e tempo de resposta:
  - TCP: abre uma conexão com socket.create_connection;
  - HTTP: envia um GET e lê a primeira linha da página.

Execução (na raiz do projeto, na máquina A):
    python -m testes.teste_conectividade                  uma verificação
    python -m testes.teste_conectividade --sequencia      antes, bloquear, durante, desbloquear, depois
    python -m testes.teste_conectividade --sequencia --pausa   pausa durante o bloqueio
"""

import argparse
import http.client
import socket
import sys
import time
from datetime import datetime

from cliente.cliente import criar_contexto_tls, enviar_requisicao, montar_requisicao
from comum.protocolo import carregar_config

PORTA_HTTP = 8080
TEMPO_LIMITE = 3  # segundos


def agora():
    return datetime.now().strftime("%H:%M:%S")


def testar_porta(host, porta, timeout=TEMPO_LIMITE):
    """Tenta abrir uma conexão TCP. Devolve (resultado, milissegundos)."""
    inicio = time.perf_counter()
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            resultado = "sucesso"
    except TimeoutError:
        resultado = "timeout"
    except ConnectionRefusedError:
        resultado = "recusada"
    except OSError:
        resultado = "erro"
    return resultado, round((time.perf_counter() - inicio) * 1000)


def testar_http(host, porta, timeout=TEMPO_LIMITE):
    """Envia um GET. Devolve (resultado, milissegundos, primeira linha da página)."""
    inicio = time.perf_counter()
    conexao = http.client.HTTPConnection(host, porta, timeout=timeout)
    try:
        conexao.request("GET", "/")
        resposta = conexao.getresponse()
        linha = resposta.read().decode("utf-8", errors="replace").splitlines()[:1]
        resultado = "sucesso" if resposta.status == 200 else f"HTTP {resposta.status}"
        detalhe = linha[0] if linha else ""
    except TimeoutError:
        resultado, detalhe = "timeout", ""
    except ConnectionRefusedError:
        resultado, detalhe = "recusada", ""
    except OSError as erro:
        resultado, detalhe = "erro", str(erro)
    finally:
        conexao.close()
    return resultado, round((time.perf_counter() - inicio) * 1000), detalhe


def verificar(host, porta, etapa=""):
    """Executa os dois testes, mostra o resultado e devolve o resultado do TCP."""
    titulo = f"[{etapa}] " if etapa else ""
    tcp, ms_tcp = testar_porta(host, porta)
    print(f"{agora()} {titulo}TCP  {host}:{porta} -> {tcp.upper():8} ({ms_tcp} ms)")
    http_resultado, ms_http, detalhe = testar_http(host, porta)
    complemento = f" | {detalhe}" if detalhe else ""
    print(f"{agora()} {titulo}HTTP {host}:{porta} -> {http_resultado.upper():8} ({ms_http} ms){complemento}")
    return tcp


def pedir_ao_servidor(config, contexto_tls, acao, porta):
    """Envia bloquear/desbloquear ao servidor de controle e mostra o código."""
    resposta = enviar_requisicao(config, contexto_tls, montar_requisicao(config["token"], acao, porta))
    print(f"{agora()} [{acao}] servidor respondeu {resposta.get('codigo')}")
    return resposta.get("status") == "ok"


def executar_sequencia(config, porta, pausa):
    """antes -> bloquear -> durante -> desbloquear -> depois. Devolve True se tudo bateu."""
    host = config["servidor_host"]
    contexto_tls = criar_contexto_tls(config)
    resultados = {}

    resultados["antes"] = verificar(host, porta, "antes")
    if not pedir_ao_servidor(config, contexto_tls, "bloquear", porta):
        return False
    resultados["durante"] = verificar(host, porta, "durante")
    if pausa:
        input("\nBloqueio ativo. Teste o acesso local na máquina B e aperte Enter para desbloquear...")
    if not pedir_ao_servidor(config, contexto_tls, "desbloquear", porta):
        return False
    resultados["depois"] = verificar(host, porta, "depois")

    esperado = {"antes": "sucesso", "durante": "timeout", "depois": "sucesso"}
    print("\nResumo:")
    for etapa, resultado in resultados.items():
        situacao = "OK" if resultado == esperado[etapa] else "DIFERENTE DO ESPERADO"
        print(f"  {etapa:8} esperado {esperado[etapa]:8} obtido {resultado:8} {situacao}")
    return resultados == esperado


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Testa a conectividade da porta HTTP da máquina B.")
    parser.add_argument("--porta", type=int, default=PORTA_HTTP)
    parser.add_argument("--sequencia", action="store_true", help="executa antes/durante/depois")
    parser.add_argument("--pausa", action="store_true", help="pausa com o bloqueio ativo")
    opcoes = parser.parse_args(argumentos)

    config = carregar_config()
    if not opcoes.sequencia:
        verificar(config["servidor_host"], opcoes.porta)
        return 0

    try:
        aprovado = executar_sequencia(config, opcoes.porta, opcoes.pausa)
    except OSError as erro:
        print(f"[FALHA] Não foi possível falar com o servidor de controle: {erro}")
        return 1
    print("\nRESULTADO: " + ("APROVADO" if aprovado else "REPROVADO"))
    return 0 if aprovado else 1


if __name__ == "__main__":
    sys.exit(main())
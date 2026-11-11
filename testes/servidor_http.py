"""Servidor HTTP de teste da máquina B (Integrante 4).

É o serviço que será bloqueado e liberado pelo projeto. Responde a qualquer
GET com uma página simples e registra cada acesso com data, hora e IP.

Execução (na raiz do projeto, na máquina B):  python -m testes.servidor_http
"""

import socket
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

ENDERECO = "0.0.0.0"  # todas as interfaces: permite também o teste local (localhost)
PORTA = 8080


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PaginaDeTeste(BaseHTTPRequestHandler):
    """Responde a requisições GET com uma página de texto."""

    def do_GET(self):
        corpo = (
            "Servico de teste ativo\n"
            f"Maquina: {socket.gethostname()}\n"
            f"Horario: {agora()}\n"
            f"Cliente: {self.client_address[0]}\n"
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato, *args):
        """Substitui o registro padrão: data/hora, IP do cliente e requisição."""
        print(f"{agora()} [{self.client_address[0]}] {formato % args}")


def main():
    with HTTPServer((ENDERECO, PORTA), PaginaDeTeste) as servidor:
        print(f"{agora()} Servidor HTTP de teste em {ENDERECO}:{PORTA}. Ctrl+C para encerrar.")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print(f"\n{agora()} Servidor HTTP de teste encerrado.")


if __name__ == "__main__":
    main()
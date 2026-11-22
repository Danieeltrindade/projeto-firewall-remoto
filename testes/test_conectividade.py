"""Testes unitários das funções de conectividade (Issue #14).

Usam um servidor local de verdade (127.0.0.1) para o caso de sucesso e
simulam o timeout com mock, sem depender da máquina B.

Execução (na raiz do projeto):  python -m unittest testes.test_conectividade -v
"""

import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from testes import teste_conectividade as conectividade


class PaginaSimples(BaseHTTPRequestHandler):
    def do_GET(self):
        corpo = b"Servico de teste ativo\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass  # silencia o registro durante os testes


class TestConectividade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = HTTPServer(("127.0.0.1", 0), PaginaSimples)  # porta 0: o sistema escolhe uma livre
        cls.porta = cls.servidor.server_address[1]
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def test_tcp_sucesso(self):
        resultado, ms = conectividade.testar_porta("127.0.0.1", self.porta)
        self.assertEqual(resultado, "sucesso")
        self.assertGreaterEqual(ms, 0)

    def test_http_sucesso_le_a_pagina(self):
        resultado, _, detalhe = conectividade.testar_http("127.0.0.1", self.porta)
        self.assertEqual(resultado, "sucesso")
        self.assertEqual(detalhe, "Servico de teste ativo")

    def test_tcp_recusada_em_porta_fechada(self):
        with socket.socket() as livre:
            livre.bind(("127.0.0.1", 0))
            porta_fechada = livre.getsockname()[1]
        resultado, _ = conectividade.testar_porta("127.0.0.1", porta_fechada)
        self.assertEqual(resultado, "recusada")

    def test_tcp_timeout(self):
        with mock.patch("testes.teste_conectividade.socket.create_connection", side_effect=TimeoutError):
            resultado, _ = conectividade.testar_porta("192.168.56.10", 8080)
        self.assertEqual(resultado, "timeout")

    def test_http_timeout(self):
        with mock.patch("http.client.HTTPConnection.request", side_effect=TimeoutError):
            resultado, _, _ = conectividade.testar_http("192.168.56.10", 8080)
        self.assertEqual(resultado, "timeout")


if __name__ == "__main__":
    unittest.main()
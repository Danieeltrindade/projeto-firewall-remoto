"""Testes unitários da validação e da ordem de processamento (Issue #8).

Execução (na raiz do projeto):  python -m unittest testes.test_validacao -v
Não precisa de rede nem da máquina B.
"""

import json
import unittest
from unittest import mock

from servidor.servidor import processar_linha
from servidor.validacao import RequisicaoInvalida, validar_requisicao

TOKEN = "t" * 64


def requisicao(**campos):
    """Monta uma requisição válida de bloqueio e aplica as alterações pedidas."""
    base = {"id": "teste", "token": TOKEN, "acao": "bloquear", "porta": 8080}
    base.update(campos)
    return base


class TestValidacao(unittest.TestCase):
    def assertCodigo(self, dados, codigo_esperado):
        with self.assertRaises(RequisicaoInvalida) as contexto:
            validar_requisicao(dados)
        self.assertEqual(contexto.exception.codigo, codigo_esperado)

    # Requisições válidas
    def test_bloquear_8080_valido(self):
        self.assertEqual(validar_requisicao(requisicao()), ("bloquear", 8080))

    def test_desbloquear_8080_valido(self):
        self.assertEqual(validar_requisicao(requisicao(acao="desbloquear")), ("desbloquear", 8080))

    def test_consultar_sem_porta_valido(self):
        dados = requisicao(acao="consultar")
        del dados["porta"]
        self.assertEqual(validar_requisicao(dados), ("consultar", None))

    # Campos ausentes e desconhecidos
    def test_sem_acao(self):
        dados = requisicao()
        del dados["acao"]
        self.assertCodigo(dados, "CAMPO_AUSENTE")

    def test_sem_id(self):
        dados = requisicao()
        del dados["id"]
        self.assertCodigo(dados, "CAMPO_AUSENTE")

    def test_sem_porta_em_bloquear(self):
        dados = requisicao()
        del dados["porta"]
        self.assertCodigo(dados, "CAMPO_AUSENTE")

    def test_campo_desconhecido(self):
        self.assertCodigo(requisicao(regra="outra"), "CAMPO_INVALIDO")

    # Tipos
    def test_id_longo_demais(self):
        self.assertCodigo(requisicao(id="x" * 65), "CAMPO_INVALIDO")

    def test_acao_numerica(self):
        self.assertCodigo(requisicao(acao=1), "CAMPO_INVALIDO")

    def test_porta_texto(self):
        self.assertCodigo(requisicao(porta="8080"), "CAMPO_INVALIDO")

    def test_porta_decimal(self):
        self.assertCodigo(requisicao(porta=8080.0), "CAMPO_INVALIDO")

    def test_porta_booleana(self):
        self.assertCodigo(requisicao(porta=True), "CAMPO_INVALIDO")

    def test_porta_em_consultar(self):
        self.assertCodigo(requisicao(acao="consultar"), "CAMPO_INVALIDO")

    # Ação e porta
    def test_acao_nao_permitida(self):
        self.assertCodigo(requisicao(acao="formatar"), "ACAO_INVALIDA")

    def test_porta_nao_autorizada(self):
        self.assertCodigo(requisicao(porta=3389), "PORTA_NAO_AUTORIZADA")


class TestOrdemProcessamento(unittest.TestCase):
    """Confere a ordem do contrato: JSON, depois token, depois campos."""

    def processar(self, dados):
        linha = json.dumps(dados).encode("utf-8")
        return processar_linha(linha, TOKEN)

    def test_token_errado_antes_de_acao_invalida(self):
        resposta = self.processar(requisicao(token="errado", acao="formatar"))
        self.assertEqual(resposta["codigo"], "TOKEN_INVALIDO")

    def test_token_ausente_antes_de_porta_invalida(self):
        dados = requisicao(porta=3389)
        del dados["token"]
        self.assertEqual(self.processar(dados)["codigo"], "TOKEN_INVALIDO")

    def test_requisicao_valida_chega_ao_firewall(self):
        # mock: substitui o firewall real por um falso, para o teste nunca mexer no Windows
        with mock.patch("servidor.firewall.bloquear_porta", return_value="regra-falsa") as falso:
            resposta = self.processar(requisicao())
        falso.assert_called_once_with(8080)
        self.assertEqual(resposta["codigo"], "REGRA_CRIADA")

    def test_resposta_tem_cinco_campos(self):
        resposta = self.processar(requisicao(porta=3389))
        self.assertEqual(set(resposta), {"id", "status", "codigo", "mensagem", "dados"})
        self.assertEqual(resposta["id"], "teste")


if __name__ == "__main__":
    unittest.main()
"""Testes unitários da recuperação local (Issue #13).

O firewall nunca é alterado de verdade: as funções do módulo firewall são
substituídas por falsos (mock).

Execução (na raiz do projeto):  python -m unittest testes.test_recuperacao -v
"""

import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock

from servidor import firewall, recuperacao

REGRA = {"nome": "ProjetoFirewallRemoto-Bloqueio-TCP-8080", "porta": 8080, "acao": "Block"}


class TestRemoverRegrasDoProjeto(unittest.TestCase):
    def test_remove_somente_o_grupo_do_projeto(self):
        with mock.patch("servidor.firewall.executando_como_administrador", return_value=True), \
             mock.patch("servidor.firewall.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, b"1", b"")
            self.assertEqual(firewall.remover_regras_do_projeto(), 1)
        script = run.call_args[0][0][-1]
        self.assertIn("-Group 'ProjetoFirewallRemoto'", script)
        self.assertIn("Remove-NetFirewallRule", script)
        self.assertNotIn("LaboratorioBase", script)

    def test_sem_administrador_nem_chega_ao_powershell(self):
        with mock.patch("servidor.firewall.executando_como_administrador", return_value=False), \
             mock.patch("servidor.firewall.subprocess.run") as run:
            with self.assertRaises(firewall.SemPrivilegio):
                firewall.remover_regras_do_projeto()
        run.assert_not_called()


class TestRecuperacao(unittest.TestCase):
    def setUp(self):
        self.admin = self.substituir("executando_como_administrador", return_value=True)
        self.consultar = self.substituir("consultar_regras", side_effect=[[REGRA], []])
        self.remover = self.substituir("remover_regras_do_projeto", return_value=1)

    def substituir(self, nome, **opcoes):
        substituto = mock.patch(f"servidor.recuperacao.firewall.{nome}", **opcoes)
        falso = substituto.start()
        self.addCleanup(substituto.stop)
        return falso

    def executar(self, argumentos, resposta=None):
        saida = io.StringIO()
        with redirect_stdout(saida), mock.patch("builtins.input", return_value=resposta) as entrada:
            codigo = recuperacao.main(argumentos)
        return codigo, saida.getvalue(), entrada

    def test_confirmado_remove_as_regras(self):
        codigo, saida, _ = self.executar([], resposta="s")
        self.assertEqual(codigo, 0)
        self.remover.assert_called_once()
        self.assertIn("1 regra(s) removida(s)", saida)

    def test_cancelado_nao_remove(self):
        codigo, saida, _ = self.executar([], resposta="n")
        self.assertEqual(codigo, 0)
        self.remover.assert_not_called()
        self.assertIn("Cancelado", saida)

    def test_opcao_sim_nao_pergunta(self):
        codigo, _, entrada = self.executar(["--sim"])
        self.assertEqual(codigo, 0)
        entrada.assert_not_called()
        self.remover.assert_called_once()

    def test_sem_regras_nada_a_fazer(self):
        self.consultar.side_effect = None
        self.consultar.return_value = []
        codigo, saida, _ = self.executar(["--sim"])
        self.assertEqual(codigo, 0)
        self.remover.assert_not_called()
        self.assertIn("Nada a fazer", saida)

    def test_sem_administrador_recusa(self):
        self.admin.return_value = False
        codigo, saida, _ = self.executar(["--sim"])
        self.assertEqual(codigo, 1)
        self.consultar.assert_not_called()
        self.assertIn("Administrador", saida)

    def test_regra_que_sobrou_e_avisada(self):
        self.consultar.side_effect = [[REGRA], [REGRA]]
        codigo, saida, _ = self.executar(["--sim"])
        self.assertEqual(codigo, 1)
        self.assertIn("ATENÇÃO", saida)

    def test_erro_do_firewall_e_tratado(self):
        self.consultar.side_effect = firewall.ErroFirewall("falha simulada")
        codigo, saida, _ = self.executar(["--sim"])
        self.assertEqual(codigo, 1)
        self.assertIn("falha simulada", saida)


if __name__ == "__main__":
    unittest.main()
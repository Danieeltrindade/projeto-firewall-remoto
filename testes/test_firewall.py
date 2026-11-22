"""Testes unitários do módulo de firewall e das respostas do servidor (Issues #11 e #12).

O PowerShell nunca é executado de verdade: o subprocess.run é substituído
por um falso (mock). Assim os testes rodam em qualquer máquina, sem mexer
no firewall.

Execução (na raiz do projeto):  python -m unittest testes.test_firewall -v
"""

import json
import subprocess
import unittest
from unittest import mock

from servidor import firewall
from servidor.servidor import processar_linha

TOKEN = "t" * 64


def resultado_falso(saida="", erro="", codigo=0):
    """Imita o objeto que o subprocess.run devolve."""
    return subprocess.CompletedProcess(
        args=[], returncode=codigo, stdout=saida.encode("utf-8"), stderr=erro.encode("utf-8")
    )


class TestFirewall(unittest.TestCase):
    def setUp(self):
        substituto = mock.patch("servidor.firewall.subprocess.run", return_value=resultado_falso())
        self.run = substituto.start()
        self.addCleanup(substituto.stop)

        administrador = mock.patch("servidor.firewall.executando_como_administrador", return_value=True)
        self.administrador = administrador.start()
        self.addCleanup(administrador.stop)

    def ultimo_script(self):
        """Devolve o script PowerShell da última chamada ao subprocess.run."""
        return self.run.call_args[0][0][-1]

    def test_nome_fixo_da_regra(self):
        self.assertEqual(firewall.nome_da_regra(8080), "ProjetoFirewallRemoto-Bloqueio-TCP-8080")

    def test_bloquear_cria_regra_quando_nao_existe(self):
        self.run.side_effect = [resultado_falso("nao"), resultado_falso()]
        self.assertTrue(firewall.bloquear_porta(8080))
        comando, kwargs = self.run.call_args
        self.assertIsInstance(comando[0], list)
        self.assertNotIn("shell", kwargs)
        self.assertEqual(comando[0][0], "powershell.exe")
        script = self.ultimo_script()
        self.assertIn("New-NetFirewallRule", script)
        self.assertIn("-LocalPort 8080", script)
        self.assertIn("-Action Block", script)
        self.assertIn("-Group 'ProjetoFirewallRemoto'", script)

    def test_bloquear_nao_duplica_regra_existente(self):
        self.run.return_value = resultado_falso("sim")
        self.assertFalse(firewall.bloquear_porta(8080))
        self.assertEqual(self.run.call_count, 1)
        self.assertNotIn("New-NetFirewallRule", self.ultimo_script())

    def test_desbloquear_remove_quando_existe(self):
        self.run.side_effect = [resultado_falso("sim"), resultado_falso()]
        self.assertTrue(firewall.desbloquear_porta(8080))
        self.assertIn("Remove-NetFirewallRule -Name 'ProjetoFirewallRemoto-Bloqueio-TCP-8080'", self.ultimo_script())

    def test_desbloquear_sem_regra_nao_executa_remocao(self):
        self.run.return_value = resultado_falso("nao")
        self.assertFalse(firewall.desbloquear_porta(8080))
        self.assertEqual(self.run.call_count, 1)

    def test_porta_nao_autorizada_nem_chega_ao_powershell(self):
        for porta in (3389, 5000, "8080", True):
            with self.assertRaises(ValueError):
                firewall.bloquear_porta(porta)
        self.run.assert_not_called()

    def test_sem_administrador_nem_chega_ao_powershell(self):
        self.administrador.return_value = False
        with self.assertRaises(firewall.SemPrivilegio):
            firewall.bloquear_porta(8080)
        with self.assertRaises(firewall.SemPrivilegio):
            firewall.desbloquear_porta(8080)
        self.run.assert_not_called()

    def test_acesso_negado_vira_sem_privilegio(self):
        self.run.return_value = resultado_falso(erro="Access is denied.", codigo=1)
        with self.assertRaises(firewall.SemPrivilegio):
            firewall.consultar_regras()

    def test_outro_erro_vira_erro_firewall(self):
        self.run.return_value = resultado_falso(erro="Falha inesperada.", codigo=1)
        with self.assertRaises(firewall.ErroFirewall) as contexto:
            firewall.consultar_regras()
        self.assertNotIsInstance(contexto.exception, firewall.SemPrivilegio)

    def test_consultar_converte_json(self):
        self.run.return_value = resultado_falso(
            '[{"nome":"ProjetoFirewallRemoto-Bloqueio-TCP-8080","porta":"8080",'
            '"direcao":"Inbound","acao":"Block","habilitada":"True"}]'
        )
        regras = firewall.consultar_regras()
        self.assertEqual(regras[0]["porta"], 8080)
        self.assertIs(regras[0]["habilitada"], True)

    def test_consultar_sem_regras(self):
        self.run.return_value = resultado_falso("[]")
        self.assertEqual(firewall.consultar_regras(), [])

    def test_powershell_travado_vira_erro_firewall(self):
        self.run.side_effect = subprocess.TimeoutExpired(cmd="powershell.exe", timeout=30)
        with self.assertRaises(firewall.ErroFirewall):
            firewall.consultar_regras()


class TestRespostasDoServidor(unittest.TestCase):
    """Confere os códigos do contrato devolvidos pelo servidor em cada situação."""

    def processar(self, acao):
        linha = json.dumps({"id": "t", "token": TOKEN, "acao": acao, "porta": 8080}).encode("utf-8")
        return processar_linha(linha, TOKEN)["codigo"]

    def test_regra_criada(self):
        with mock.patch("servidor.firewall.bloquear_porta", return_value=True):
            self.assertEqual(self.processar("bloquear"), "REGRA_CRIADA")

    def test_regra_ja_existe(self):
        with mock.patch("servidor.firewall.bloquear_porta", return_value=False):
            self.assertEqual(self.processar("bloquear"), "REGRA_JA_EXISTE")

    def test_regra_removida(self):
        with mock.patch("servidor.firewall.desbloquear_porta", return_value=True):
            self.assertEqual(self.processar("desbloquear"), "REGRA_REMOVIDA")

    def test_regra_inexistente(self):
        with mock.patch("servidor.firewall.desbloquear_porta", return_value=False):
            self.assertEqual(self.processar("desbloquear"), "REGRA_INEXISTENTE")

    def test_sem_privilegio(self):
        erro = firewall.SemPrivilegio("sem privilégio")
        with mock.patch("servidor.firewall.bloquear_porta", side_effect=erro):
            self.assertEqual(self.processar("bloquear"), "SEM_PRIVILEGIO")

    def test_erro_firewall(self):
        erro = firewall.ErroFirewall("falhou")
        with mock.patch("servidor.firewall.desbloquear_porta", side_effect=erro):
            self.assertEqual(self.processar("desbloquear"), "ERRO_FIREWALL")


if __name__ == "__main__":
    unittest.main()
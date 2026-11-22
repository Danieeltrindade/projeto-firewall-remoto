"""Testes unitários do módulo de firewall (Issue #11).

O PowerShell nunca é executado de verdade: o subprocess.run é substituído
por um falso (mock). Assim os testes rodam em qualquer máquina, sem mexer
no firewall.

Execução (na raiz do projeto):  python -m unittest testes.test_firewall -v
"""

import subprocess
import unittest
from unittest import mock

from servidor import firewall


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

    def comando_executado(self):
        """Devolve a lista de argumentos passada ao subprocess.run."""
        args, kwargs = self.run.call_args
        return args[0], kwargs

    def test_nome_fixo_da_regra(self):
        self.assertEqual(firewall.nome_da_regra(8080), "ProjetoFirewallRemoto-Bloqueio-TCP-8080")

    def test_bloquear_monta_comando_fixo_sem_shell(self):
        firewall.bloquear_porta(8080)
        comando, kwargs = self.comando_executado()
        self.assertIsInstance(comando, list)
        self.assertNotIn("shell", kwargs)
        self.assertEqual(comando[0], "powershell.exe")
        script = comando[-1]
        self.assertIn("New-NetFirewallRule", script)
        self.assertIn("-LocalPort 8080", script)
        self.assertIn("-Action Block", script)
        self.assertIn("-Group 'ProjetoFirewallRemoto'", script)

    def test_desbloquear_remove_pelo_nome(self):
        firewall.desbloquear_porta(8080)
        comando, _ = self.comando_executado()
        self.assertIn("Remove-NetFirewallRule -Name 'ProjetoFirewallRemoto-Bloqueio-TCP-8080'", comando[-1])

    def test_porta_nao_autorizada_nem_chega_ao_powershell(self):
        for porta in (3389, 5000, "8080", True):
            with self.assertRaises(ValueError):
                firewall.bloquear_porta(porta)
        self.run.assert_not_called()

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

    def test_erro_do_powershell_vira_erro_firewall(self):
        self.run.return_value = resultado_falso(erro="Access is denied.", codigo=1)
        with self.assertRaises(firewall.ErroFirewall) as contexto:
            firewall.bloquear_porta(8080)
        self.assertIn("Access is denied", str(contexto.exception))

    def test_powershell_travado_vira_erro_firewall(self):
        self.run.side_effect = subprocess.TimeoutExpired(cmd="powershell.exe", timeout=30)
        with self.assertRaises(firewall.ErroFirewall):
            firewall.consultar_regras()


if __name__ == "__main__":
    unittest.main()
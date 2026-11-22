"""Recuperação local da máquina B (Integrante 3).

Remove todas as regras do grupo ProjetoFirewallRemoto, e somente elas.
As regras de permissão do grupo LaboratorioBase (portas 5000 e 8080) não
são tocadas.

Roda direto na máquina B e não usa a rede: funciona mesmo com o servidor
de controle desligado ou inacessível. Precisa de Administrador.

Execução (na raiz do projeto, PowerShell como Administrador):
    python -m servidor.recuperacao          lista as regras e pede confirmação
    python -m servidor.recuperacao --sim    remove sem perguntar
"""

import argparse
import sys

from servidor import firewall


def mostrar_regras(regras):
    print(f"{len(regras)} regra(s) do projeto encontrada(s):")
    for regra in regras:
        print(f"  - {regra['nome']} | porta {regra['porta']} | {regra['acao']}")


def confirmar():
    resposta = input("Remover todas essas regras? [s/N]: ").strip().lower()
    return resposta in ("s", "sim")


def main(argumentos=None):
    parser = argparse.ArgumentParser(
        description="Remove as regras de bloqueio criadas pelo projeto nesta máquina."
    )
    parser.add_argument("--sim", action="store_true", help="remove sem pedir confirmação")
    opcoes = parser.parse_args(argumentos)

    if not firewall.executando_como_administrador():
        print("ERRO: execute a recuperação em um PowerShell aberto como Administrador.")
        return 1

    try:
        regras = firewall.consultar_regras()
        if not regras:
            print("Nenhuma regra do projeto ativa. Nada a fazer.")
            return 0

        mostrar_regras(regras)
        if not opcoes.sim and not confirmar():
            print("Cancelado. Nenhuma regra foi removida.")
            return 0

        removidas = firewall.remover_regras_do_projeto()
        restantes = firewall.consultar_regras()
    except firewall.ErroFirewall as erro:
        print(f"ERRO ao acessar o firewall: {erro}")
        return 1

    if restantes:
        print(f"ATENÇÃO: {len(restantes)} regra(s) ainda ativa(s). Use o comando manual de docs/recuperacao.md.")
        return 1

    print(f"{removidas} regra(s) removida(s). O tráfego bloqueado pelo projeto foi restaurado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
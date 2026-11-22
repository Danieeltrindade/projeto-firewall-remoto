"""Gerenciamento do Windows Firewall (Integrante 3).

Cria, consulta e remove a regra de bloqueio do projeto usando PowerShell.
Só comandos fixos são executados: o único valor variável é a porta, que
precisa ser um inteiro da lista de portas autorizadas.
"""

import json
import subprocess

from servidor.validacao import PORTAS_AUTORIZADAS

GRUPO = "ProjetoFirewallRemoto"
PREFIXO_REGRA = "ProjetoFirewallRemoto-Bloqueio-TCP-"
TEMPO_LIMITE_POWERSHELL = 30  # segundos


class ErroFirewall(Exception):
    """Falha ao executar uma operação no Windows Firewall."""


def nome_da_regra(porta):
    """Nome fixo da regra do projeto para uma porta (ex.: ...-TCP-8080)."""
    return f"{PREFIXO_REGRA}{porta}"


def _conferir_porta(porta):
    """Segunda barreira: mesmo validada antes, a porta é conferida aqui."""
    if isinstance(porta, bool) or not isinstance(porta, int) or porta not in PORTAS_AUTORIZADAS:
        raise ValueError(f"Porta não autorizada para o firewall: {porta!r}")


def _executar_powershell(script):
    """Executa um script PowerShell fixo e devolve a saída (texto)."""
    comando = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$ErrorActionPreference = 'Stop'; "
        f"try {{ {script} }} "
        "catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }",
    ]
    try:
        resultado = subprocess.run(comando, capture_output=True, timeout=TEMPO_LIMITE_POWERSHELL)
    except FileNotFoundError as erro:
        raise ErroFirewall("PowerShell não encontrado nesta máquina.") from erro
    except subprocess.TimeoutExpired as erro:
        raise ErroFirewall(f"O PowerShell não respondeu em {TEMPO_LIMITE_POWERSHELL} s.") from erro

    saida = resultado.stdout.decode("utf-8", errors="replace").strip()
    if resultado.returncode != 0:
        mensagem = resultado.stderr.decode("utf-8", errors="replace").strip()
        raise ErroFirewall(mensagem or f"PowerShell terminou com código {resultado.returncode}.")
    return saida


def bloquear_porta(porta):
    """Cria a regra de entrada que bloqueia TCP na porta. Devolve o nome da regra."""
    _conferir_porta(porta)
    nome = nome_da_regra(porta)
    _executar_powershell(
        f"New-NetFirewallRule -Name '{nome}' -DisplayName '{nome}' -Group '{GRUPO}' "
        "-Description 'Criada remotamente pelo Projeto 4.3' "
        f"-Direction Inbound -Protocol TCP -LocalPort {porta} -Action Block -Profile Any "
        "| Out-Null"
    )
    return nome


def desbloquear_porta(porta):
    """Remove a regra de bloqueio da porta. Devolve o nome da regra."""
    _conferir_porta(porta)
    nome = nome_da_regra(porta)
    _executar_powershell(f"Remove-NetFirewallRule -Name '{nome}'")
    return nome


def consultar_regras():
    """Lista as regras do grupo do projeto (lista de dicionários)."""
    saida = _executar_powershell(
        f"$regras = @(Get-NetFirewallRule -Group '{GRUPO}' -ErrorAction SilentlyContinue | "
        "ForEach-Object { $filtro = $_ | Get-NetFirewallPortFilter; "
        "[pscustomobject]@{ nome = $_.Name; porta = [string]$filtro.LocalPort; "
        "direcao = [string]$_.Direction; acao = [string]$_.Action; "
        "habilitada = [string]$_.Enabled } }); "
        "ConvertTo-Json -InputObject $regras -Compress"
    )
    regras = json.loads(saida) if saida else []
    for regra in regras:
        if str(regra.get("porta", "")).isdigit():
            regra["porta"] = int(regra["porta"])
        regra["habilitada"] = regra.get("habilitada") == "True"
    return regras
"""Autenticação por token (Integrante 2).

O cliente envia o token em toda requisição. O servidor compara com o token
do seu config.json usando comparação em tempo constante.
"""

import hmac

TAMANHO_MINIMO_TOKEN = 32
TOKEN_DE_EXEMPLO = "SUBSTITUA_PELO_TOKEN_GERADO"


def token_configurado_valido(token_esperado):
    """Verifica se o token do config.json pode ser usado pelo servidor."""
    return (
        isinstance(token_esperado, str)
        and len(token_esperado) >= TAMANHO_MINIMO_TOKEN
        and token_esperado != TOKEN_DE_EXEMPLO
    )


def token_valido(token_recebido, token_esperado):
    """Compara o token recebido com o esperado, em tempo constante."""
    if not isinstance(token_recebido, str):
        return False
    return hmac.compare_digest(
        token_recebido.encode("utf-8"), token_esperado.encode("utf-8")
    )
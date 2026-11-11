"""Validação das requisições (Integrante 2).

Garante que o servidor só execute ações previamente programadas, em portas
explicitamente autorizadas. Regras definidas em docs/protocolo.md.
"""

ACOES_PERMITIDAS = {"bloquear", "desbloquear", "consultar"}
ACOES_COM_PORTA = {"bloquear", "desbloquear"}
PORTAS_AUTORIZADAS = {8080}
CAMPOS_CONHECIDOS = {"id", "token", "acao", "porta"}


class RequisicaoInvalida(Exception):
    """Requisição fora do contrato. Carrega o código e a mensagem da resposta."""

    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


def _eh_inteiro(valor):
    """True só para inteiros de verdade (em Python, True e False também são int)."""
    return isinstance(valor, int) and not isinstance(valor, bool)


def validar_requisicao(requisicao):
    """Confere campos, tipos, ação e porta.

    Devolve (acao, porta) se a requisição for válida; porta é None em "consultar".
    Lança RequisicaoInvalida na primeira regra violada.
    """
    for campo in ("id", "acao"):
        if campo not in requisicao:
            raise RequisicaoInvalida("CAMPO_AUSENTE", f"Campo obrigatório ausente: '{campo}'.")

    desconhecidos = sorted(set(requisicao) - CAMPOS_CONHECIDOS)
    if desconhecidos:
        raise RequisicaoInvalida("CAMPO_INVALIDO", f"Campo desconhecido: '{desconhecidos[0]}'.")

    id_requisicao = requisicao["id"]
    if not isinstance(id_requisicao, str) or not 1 <= len(id_requisicao) <= 64:
        raise RequisicaoInvalida("CAMPO_INVALIDO", "O campo 'id' deve ser um texto de 1 a 64 caracteres.")

    acao = requisicao["acao"]
    if not isinstance(acao, str):
        raise RequisicaoInvalida("CAMPO_INVALIDO", "O campo 'acao' deve ser um texto.")
    if acao not in ACOES_PERMITIDAS:
        raise RequisicaoInvalida(
            "ACAO_INVALIDA",
            f"Ação {acao!r} não permitida. Use: bloquear, desbloquear ou consultar.",
        )

    if acao not in ACOES_COM_PORTA:
        if "porta" in requisicao:
            raise RequisicaoInvalida("CAMPO_INVALIDO", f"A ação '{acao}' não aceita o campo 'porta'.")
        return acao, None

    if "porta" not in requisicao:
        raise RequisicaoInvalida("CAMPO_AUSENTE", "Campo obrigatório ausente: 'porta'.")

    porta = requisicao["porta"]
    if not _eh_inteiro(porta):
        raise RequisicaoInvalida("CAMPO_INVALIDO", "O campo 'porta' deve ser um número inteiro.")
    if porta not in PORTAS_AUTORIZADAS:
        raise RequisicaoInvalida(
            "PORTA_NAO_AUTORIZADA", f"A porta {porta} não está na lista de portas autorizadas."
        )

    return acao, porta
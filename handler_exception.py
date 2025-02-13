from pydantic import ValidationError
from src.config.logger_config import logger

logger.service = "HandlerException"

# Mapeamento estendido de erros do Pydantic para mensagens mais amigáveis
CUSTOM_MESSAGES = {
    "value_error.int_parsing": "Valor deve ser um número inteiro.",
    "value_error.datetime_parsing": "Valor inválido para data e hora.",
    "value_error.datetime_from_date_parsing": "Valor inválido para data e hora.",
    "value_error.date_parsing": "Valor inválido para data.",
    "value_error.string_too_long": "Valor deve ter no máximo {limit_value} caracteres.",
    "value_error.any_str.min_length": "Valor deve ter no mínimo {limit_value} caracteres.",
    "value_error.any_str.max_length": "Valor deve ter no máximo {limit_value} caracteres.",
    "value_error.number.not_ge": "Valor deve ser maior ou igual a {limit_value}.",
    "value_error.number.not_le": "Valor deve ser menor ou igual a {limit_value}.",
    "value_error.number.not_gt": "Valor deve ser maior que {limit_value}.",
    "value_error.number.not_lt": "Valor deve ser menor que {limit_value}.",
    "value_error.float_parsing": "Valor deve ser um número de ponto flutuante.",
    "value_error.uuid_parsing": "Valor inválido para o tipo UUID.",
    "value_error.email": "Valor inválido para e-mail.",
    "value_error.url": "Valor inválido para URL.",
    "value_error.missing": "Campo obrigatório.",
    "type_error.bool": "Valor deve ser um booleano.",
    "type_error.list": "Valor deve ser uma lista.",
    "type_error.dict": "Valor deve ser um dicionário.",
    "type_error.str": "Valor deve ser uma string.",
    "type_error.int": "Valor deve ser um número inteiro."
}

class HandlerException:
    """
    Fornece métodos estáticos para tratar exceções de maneira uniforme—
    especificamente ValidationErrors do Pydantic e exceções Python de modo geral.
    """

    @staticmethod
    def handle_exception(ex: Exception):
        """
        Ponto de entrada principal para tratar exceções.
        Se for um ValidationError do Pydantic, chama _handle_invalid;
        caso contrário, chama _general_handle.
        """
        if isinstance(ex, ValidationError):
            return HandlerException._handle_invalid(ex)
        else:
            return HandlerException._general_handle(ex)

    @staticmethod
    def _handle_invalid(ex: ValidationError):
        """
        Trata ValidationErrors do Pydantic. Reúne cada erro individual
        e tenta mapear para uma mensagem customizada em CUSTOM_MESSAGES.
        Se não encontrar uma mensagem customizada, cai de volta na mensagem
        original do Pydantic.
        """
        errors = ex.errors()  # Lista de dicionários de erro
        messages = []

        for err in errors:
            # Exemplo de err:
            # {
            #   'loc': ('nome_do_campo', ...),
            #   'msg': 'mensagem de erro do Pydantic',
            #   'type': 'value_error.xxx' ou 'type_error.xxx',
            #   'ctx': {...} // contexto adicional
            # }
            error_type = err.get("type", "")
            loc = err.get("loc", [])
            pydantic_msg = err.get("msg", "")
            ctx = err.get("ctx", {})  # Contexto extra do Pydantic

            # Tenta combinar com a mensagem customizada
            custom_message = CUSTOM_MESSAGES.get(error_type)

            if custom_message:
                # Se a mensagem possui placeholders (ex.: {limit_value}), tenta formatar
                try:
                    error_msg = custom_message.format(**ctx)
                except KeyError:
                    # Se algum placeholder não existir em ctx, usa a mensagem customizada ou a original
                    error_msg = custom_message
            else:
                # Se não houver mensagem customizada, utiliza a mensagem original do Pydantic
                error_msg = pydantic_msg

            field_path = ".".join(str(part) for part in loc)
            full_message = f"Erro no campo '{field_path}': {error_msg}"
            messages.append(full_message)

        logger.error(f"Erros de validação encontrados: {messages}")

        return {
            "statusCode": 400,
            "body": {
                "error": "Parâmetros inválidos",
                "messages": messages
            }
        }

    @staticmethod
    def _general_handle(ex: Exception):
        """
        Trata todas as exceções que não sejam ValidationError, de modo genérico:
        registra o erro em log e retorna um response HTTP 500.
        """
        logger.error(f"Erro no processamento da aplicação: {ex}")

        return {
            "statusCode": 500,
            "body": {
                "error": "Ocorreu um erro inesperado.",
                "messages": [str(ex)]
            }
        }

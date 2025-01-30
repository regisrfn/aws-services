from aws_lambda_powertools import Logger
from pydantic import ValidationError

logger = Logger(service="HandlerException")

# Map certain Pydantic “type” codes to friendlier error messages
CUSTOM_MESSAGES = {
    "int_parsing":               "Valor deve ser um número inteiro.",
    "datetime_parsing":          "Valor inválido para data e hora.",
    "datetime_from_date_parsing":"Valor inválido para data e hora.",
    "date_parsing":              "Valor inválido para data.",
    "string_too_long":           "Valor deve ter no máximo {limit_value} caracteres.",
    "uuid_parsing":              "Valor inválido para o tipo UUID.",
    "missing":                   "Campo obrigatório."
}

class HandlerException:
    """
    Provides static methods to handle exceptions in a uniform way—specifically
    Pydantic ValidationErrors and general (unexpected) Python exceptions.
    """

    @staticmethod
    def handle_exception(ex: Exception):
        """
        Main entry point to handle an exception. If it is a Pydantic ValidationError,
        we call _handle_invalid; otherwise we call _general_handle.
        """
        if isinstance(ex, ValidationError):
            return HandlerException._handle_invalid(ex)
        else:
            return HandlerException._general_handle(ex)

    @staticmethod
    def _handle_invalid(ex: ValidationError):
        """
        Handles ValidationErrors from Pydantic. It gathers each individual error
        and tries to map it to a custom message in CUSTOM_MESSAGES. If no custom
        message is found for a given error type, it falls back to Pydantic’s
        original error message.
        """
        errors = ex.errors()  # A list of error dictionaries
        messages = []

        for err in errors:
            # err is something like:
            #   {
            #       'loc': ('field_name', ...),
            #       'msg': 'some Pydantic error message',
            #       'type': 'type_error.xxx',
            #       'ctx': {...}  # maybe
            #   }
            error_type = err.get("type", "")
            loc = err.get("loc", [])
            pydantic_msg = err.get("msg", "")
            ctx = err.get("ctx", {})  # Extra context from Pydantic

            # Try to match a custom message (and possibly do string format with ctx)
            custom_message = CUSTOM_MESSAGES.get(error_type)

            if custom_message:
                # If the custom message has placeholders like {limit_value},
                # we can fill them in with the contents of ctx.
                try:
                    error_msg = custom_message.format(**ctx)
                except KeyError:
                    # If a placeholder in custom_message is missing in ctx,
                    # just use the unformatted custom message or the original Pydantic message
                    error_msg = custom_message
            else:
                # Fallback to Pydantic’s original error message
                error_msg = pydantic_msg

            # Format a human‐friendly message:
            #   “Erro no campo 'field.subfield': Valor deve ser um número inteiro.”
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
        Handles all non‐ValidationError exceptions in a generic way, logging
        the error and returning an HTTP 500 response.
        """
        logger.error(f"Erro no processamento da aplicação: {ex}")

        return {
            "statusCode": 500,
            "body": {
                "error": "Ocorreu um erro inesperado.",
                "details": str(ex)
            }
        }

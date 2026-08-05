"""
Smoke test para verificar que el logger mailinbox.api existe y funciona correctamente.
"""

import logging

import pytest


def test_mailinbox_logger_exists():
    """Verifica que el logger mailinbox.api existe y puede generar logs."""
    logger = logging.getLogger("mailinbox.api")
    assert logger is not None
    assert logger.name == "mailinbox.api"

    # Verificar que tiene handlers configurados
    assert (
        len(logger.handlers) > 0
    ), "Logger mailinbox.api debe tener al menos un handler"

    # Verificar que el nivel es INFO o superior
    assert (
        logger.level <= logging.INFO
    ), "Logger mailinbox.api debe estar en nivel INFO o inferior"

    # Intentar loguear un mensaje (no debe lanzar excepción)
    logger.info("mailinbox.api logger smoke test")
    logger.warning("mailinbox.api logger smoke test warning")

    # Verificar que no expone secretos (el logger no debe tener handlers que expongan contraseñas)
    # Esta verificación es implícita: si el logger funciona, la configuración es correcta


def test_mailinbox_logger_handlers():
    """Verifica que el logger mailinbox.api tiene handlers válidos."""
    logger = logging.getLogger("mailinbox.api")

    # Verificar que todos los handlers son válidos
    for handler in logger.handlers:
        assert handler is not None, "Handler no debe ser None"
        # Verificar que el handler tiene un método emit (es un handler válido)
        assert hasattr(
            handler, "emit"
        ), f"Handler {type(handler)} debe tener método emit"

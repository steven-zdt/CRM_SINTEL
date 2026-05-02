"""
Helper para verificar robots.txt antes de descargar URLs.

Referencia: https://docs.python.org/3/library/urllib.robotparser.html
"""

import urllib.robotparser as rp
from urllib.parse import urlparse


def check_robots(url: str, user_agent: str = "SINTEL-ImpuestosBot/1.0"):
    """
    Verifica robots.txt para una URL y user agent.

    Args:
        url: URL a verificar
        user_agent: User agent a usar

    Returns:
        tuple (allowed: bool, crawl_delay: int|None)
    """
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"

    parser = rp.RobotFileParser()
    parser.set_url(robots_url)

    try:
        parser.read()
    except Exception:
        # Si no hay robots.txt o hay error, proceder con cautela
        return True, None

    allowed = parser.can_fetch(user_agent, url)
    delay = parser.crawl_delay(user_agent)

    return allowed, int(delay) if delay else None

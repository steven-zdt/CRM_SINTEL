"""
Parser para documentos HTML usando lxml.html y BeautifulSoup (opcional).

Referencia: https://lxml.de/
"""

from lxml import html

# BeautifulSoup opcional para HTML malformado
try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def parse_html_to_chunks(html_bytes: bytes | str) -> dict:
    """
    Parsea HTML y extrae contenido estructurado.

    Args:
        html_bytes: Contenido HTML como bytes o string

    Returns:
        dict con:
        - 'titles': lista de títulos (h1, h2, h3)
        - 'paragraphs': lista de párrafos
        - 'sections': [{'titulo': '...', 'texto': '...'}]
    """
    # Convertir a bytes si es string
    if isinstance(html_bytes, str):
        html_bytes = html_bytes.encode("utf-8")

    try:
        # Intentar con lxml primero (más rápido)
        tree = html.fromstring(html_bytes)

        # Extraer títulos
        titles = tree.xpath("//h1|//h2|//h3")
        titles_text = ["".join(t.xpath(".//text()")).strip() for t in titles]

        # Extraer párrafos
        paragraphs = tree.xpath("//p")
        paragraphs_text = [
            "".join(p.xpath(".//text()")).strip()
            for p in paragraphs
            if "".join(p.xpath(".//text()")).strip()
        ]

        # Construir secciones agrupando títulos con su contenido
        sections = []
        current_section = None

        for element in tree.xpath("//h1|//h2|//h3|//p"):
            tag = element.tag.lower()
            text = "".join(element.xpath(".//text()")).strip()

            if tag in ("h1", "h2", "h3"):
                # Guardar sección anterior si existe
                if current_section:
                    sections.append(current_section)
                # Nueva sección
                current_section = {
                    "titulo": text,
                    "texto": "",
                }
            elif tag == "p" and text:
                if current_section:
                    current_section["texto"] += text + "\n"
                else:
                    # Párrafo sin título previo
                    current_section = {
                        "titulo": None,
                        "texto": text,
                    }

        # Agregar última sección
        if current_section:
            sections.append(current_section)

        # Si no hay secciones, crear una con todo el texto
        if not sections:
            all_text = " ".join(paragraphs_text)
            sections.append(
                {
                    "titulo": None,
                    "texto": all_text,
                }
            )

    except Exception:
        # Fallback a BeautifulSoup si lxml falla (HTML malformado)
        if HAS_BS4:
            soup = BeautifulSoup(html_bytes, "lxml")

            titles_text = [t.get_text(strip=True) for t in soup.select("h1, h2, h3")]
            paragraphs_text = [
                p.get_text(strip=True) for p in soup.select("p") if p.get_text(strip=True)
            ]

            # Construir secciones
            sections = []
            for heading in soup.find_all(["h1", "h2", "h3"]):
                section = {
                    "titulo": heading.get_text(strip=True),
                    "texto": "",
                }
                # Recopilar párrafos siguientes hasta el próximo heading
                for sibling in heading.next_siblings:
                    if sibling.name in ("h1", "h2", "h3"):
                        break
                    if sibling.name == "p":
                        section["texto"] += sibling.get_text(strip=True) + "\n"
                sections.append(section)

            if not sections:
                all_text = " ".join(paragraphs_text)
                sections.append(
                    {
                        "titulo": None,
                        "texto": all_text,
                    }
                )
        else:
            # Si no hay BeautifulSoup, devolver estructura mínima
            sections = [
                {
                    "titulo": None,
                    "texto": html_bytes.decode("utf-8", errors="ignore"),
                }
            ]
            titles_text = []
            paragraphs_text = []

    return {
        "titles": titles_text,
        "paragraphs": paragraphs_text,
        "sections": sections,
    }

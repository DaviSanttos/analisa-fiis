import io
import re
from typing import Optional, Dict, Any

import pdfplumber
import pymupdf


PADROES_INDICADORES_BR = {
    "vacancia_fisica": re.compile(
        r"Vac[âa]ncia\s*[Ff][íi]sica[:\s]*([\d.,]+)\s*%", re.UNICODE
    ),
    "vacancia_financeira": re.compile(
        r"Vac[âa]ncia\s*[Ff]inanceira[:\s]*([\d.,]+)\s*%", re.UNICODE
    ),
    "dividend_yield": re.compile(
        r"Dividend\s*[Yy]ield[:\s]*R?\$?([\d.,]+)\s*%?", re.UNICODE
    ),
    "patrimonio_liquido": re.compile(
        r"Patrim[ôo]nio\s*[Ll][íi]quido[:\s]*R?\$?([\d.,]+)", re.UNICODE
    ),
    "numero_imoveis": re.compile(
        r"N[úu]mero\s*de\s*[Ii]m[óo]veis[:\s]*(\d+)", re.UNICODE
    ),
    "inadimplencia": re.compile(
        r"Inadimpl[êe]ncia[:\s]*([\d.,]+)\s*%", re.UNICODE
    ),
    "alavancagem": re.compile(
        r"Alavancagem[:\s]*([\d.,]+)\s*%?", re.UNICODE
    ),
    "receita": re.compile(
        r"Receita[:\s]*R?\$?([\d.,]+)", re.UNICODE
    ),
    "caixa": re.compile(
        r"Caixa[:\s]*R?\$?([\d.,]+)", re.UNICODE
    ),
    "endividamento": re.compile(
        r"Endividamento[:\s]*([\d.,]+)\s*%?", re.UNICODE
    ),
    "numero_cotistas": re.compile(
        r"N[úu]mero\s*de\s*[Cc]otistas[:\s]*([\d.]+)", re.UNICODE
    ),
    "pl_cota": re.compile(
        r"Valor\s*[Pp]atrimonial\s*[Cc]ota[:\s]*R?\$?([\d.,]+)", re.UNICODE
    ),
}


class PDFExtractor:
    @staticmethod
    def extrair_texto(conteudo_pdf: bytes) -> Optional[str]:
        try:
            with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
                texto_pages = []
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_pages.append(texto)
                if texto_pages:
                    return "\n".join(texto_pages)
        except Exception:
            pass

        try:
            doc = pymupdf.open(stream=conteudo_pdf, filetype="pdf")
            texto = ""
            for page in doc:
                texto += page.get_text()
            doc.close()
            return texto if texto.strip() else None
        except Exception:
            return None

    @staticmethod
    def extrair_indicadores(texto: str) -> Dict[str, Any]:
        indicadores: Dict[str, Any] = {}

        for nome, padrao in PADROES_INDICADORES_BR.items():
            match = padrao.search(texto)
            if match:
                valor_raw = match.group(1).replace(".", "").replace(",", ".")
                try:
                    if "." in valor_raw:
                        indicadores[nome] = float(valor_raw)
                    else:
                        indicadores[nome] = int(valor_raw)
                except ValueError:
                    indicadores[nome] = valor_raw

        return indicadores

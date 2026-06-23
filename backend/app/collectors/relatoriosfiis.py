import hashlib
import re
from datetime import date, datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from backend.app.collectors.base import BaseCollector, RelatorioEncontrado


class RelatoriosFIICollector(BaseCollector):
    BASE_URL = "https://www.relatoriosfiis.com.br"

    def __init__(self):
        super().__init__()
        self.name = "relatoriosfiis"
        self.priority = 3

    def buscar_relatorios(
        self, ticker: str, cnpj: Optional[str] = None
    ) -> List[RelatorioEncontrado]:
        relatorios: List[RelatorioEncontrado] = []
        url_fii = f"{self.BASE_URL}/{ticker.upper()}"

        try:
            resp = requests.get(url_fii, timeout=30, headers=self._headers())
            if resp.status_code != 200:
                return relatorios

            soup = BeautifulSoup(resp.text, "html.parser")

            links_pdf = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))
            for link in links_pdf:
                href = link.get("href", "").strip()
                if not href:
                    continue

                if href.startswith("/"):
                    url_pdf = f"{self.BASE_URL}{href}"
                elif href.startswith("http"):
                    url_pdf = href
                else:
                    url_pdf = f"{self.BASE_URL}/{href}"

                texto_link = link.get_text(strip=True)

                data = self._extrair_data(texto_link)
                raw = f"{ticker}{url_pdf}".encode()
                hash_ = hashlib.sha256(raw).hexdigest()

                relatorios.append(
                    RelatorioEncontrado(
                        url=url_pdf,
                        data_publicacao=data,
                        tipo="RELATORIO_GERENCIAL",
                        ticker=ticker.upper(),
                        hash_sha256=hash_,
                        fonte="RelatoriosFIIs",
                    )
                )

            if not links_pdf:
                linhas = soup.find_all("tr")
                for linha in linhas:
                    cols = linha.find_all("td")
                    for col in cols:
                        a = col.find("a", href=re.compile(r"\.pdf$", re.I))
                        if a:
                            href = a.get("href", "").strip()
                            if href.startswith("/"):
                                url_pdf = f"{self.BASE_URL}{href}"
                            elif href.startswith("http"):
                                url_pdf = href
                            else:
                                url_pdf = href

                            texto = a.get_text(strip=True)
                            data = self._extrair_data(texto)
                            raw = f"{ticker}{url_pdf}".encode()
                            hash_ = hashlib.sha256(raw).hexdigest()

                            relatorios.append(
                                RelatorioEncontrado(
                                    url=url_pdf,
                                    data_publicacao=data,
                                    tipo="RELATORIO_GERENCIAL",
                                    ticker=ticker.upper(),
                                    hash_sha256=hash_,
                                    fonte="RelatoriosFIIs",
                                )
                            )

        except Exception:
            return relatorios

        return relatorios

    def _extrair_data(self, texto: str) -> date:
        padroes = [
            r"(\d{2})/(\d{4})",
            r"(\w{3,9})/(\d{4})",
            r"(\d{4})-(\d{2})-(\d{2})",
        ]
        meses = {
            "jan": 1, "fev": 2, "mar": 3, "abr": 4,
            "mai": 5, "jun": 6, "jul": 7, "ago": 8,
            "set": 9, "out": 10, "nov": 11, "dez": 12,
        }

        for padrao in padroes:
            match = re.search(padrao, texto, re.I)
            if match:
                try:
                    if "/" in padrao:
                        grupos = match.groups()
                        if len(grupos) == 2:
                            mes_texto = grupos[0].lower()[:3]
                            ano = int(grupos[1])
                            if mes_texto in meses:
                                return date(ano, meses[mes_texto], 1)
                            mes = int(grupos[0])
                            return date(ano, mes, 1)
                    else:
                        return date(
                            int(match.group(1)),
                            int(match.group(2)),
                            int(match.group(3)),
                        )
                except (ValueError, IndexError):
                    continue

        return date.today()

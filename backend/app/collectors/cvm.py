import csv
import hashlib
import io
import re
import zipfile
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import requests

from backend.app.collectors.base import BaseCollector, RelatorioEncontrado


class TickerMapper:
    CNPJ_CACHE: Dict[str, str] = {}

    @classmethod
    def buscar_cnpj(cls, ticker: str) -> Optional[str]:
        ticker = ticker.upper().strip()

        if ticker in cls.CNPJ_CACHE:
            return cls.CNPJ_CACHE[ticker]

        cnpj = cls._via_statusinvest(ticker)
        if cnpj:
            cls.CNPJ_CACHE[ticker] = cnpj
            return cnpj

        cnpj = cls._via_cvm_geral(ticker)
        if cnpj:
            cls.CNPJ_CACHE[ticker] = cnpj
            return cnpj

        return None

    @staticmethod
    def _via_statusinvest(ticker: str) -> Optional[str]:
        try:
            url = f"https://statusinvest.com.br/fundos-imobiliarios/{ticker.lower()}"
            resp = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    )
                },
            )
            if resp.status_code == 200:
                match = re.search(
                    r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", resp.text
                )
                if match:
                    return match.group(0)
        except Exception:
            pass
        return None

    @staticmethod
    def _via_cvm_geral(ticker: str) -> Optional[str]:
        try:
            url = (
                "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/"
                f"inf_mensal_fii_{datetime.now().year}.zip"
            )
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                return None

            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    if "geral" not in name.lower():
                        continue
                    with zf.open(name) as f:
                        content = f.read().decode("latin-1")
                        reader = csv.DictReader(
                            io.StringIO(content), delimiter=";"
                        )
                        for row in reader:
                            nome = (
                                row.get("Nome_Fundo_Classe", "").upper()
                            )
                            if ticker in nome:
                                return row.get(
                                    "CNPJ_Fundo_Classe", ""
                                ).strip()
        except Exception:
            pass
        return None


class CVMCollector(BaseCollector):
    BASE_URL = "https://dados.cvm.gov.br"
    INF_MENSAL_URL = urljoin(
        BASE_URL, "/dados/FII/DOC/INF_MENSAL/DADOS/"
    )

    def __init__(self):
        super().__init__()
        self.name = "cvm"
        self.priority = 1

    def buscar_cnpj(self, ticker: str) -> Optional[str]:
        return TickerMapper.buscar_cnpj(ticker)

    def buscar_relatorios(
        self, ticker: str, cnpj: Optional[str] = None
    ) -> List[RelatorioEncontrado]:
        relatorios: List[RelatorioEncontrado] = []

        if not cnpj:
            cnpj = self.buscar_cnpj(ticker)
        if not cnpj:
            return relatorios

        ano_atual = datetime.now().year
        for ano in range(ano_atual, ano_atual - 3, -1):
            url_zip = urljoin(
                self.INF_MENSAL_URL, f"inf_mensal_fii_{ano}.zip"
            )
            try:
                resp = requests.get(url_zip, timeout=120)
                if resp.status_code != 200:
                    continue

                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    for csv_name in zf.namelist():
                        if "complemento" not in csv_name.lower():
                            continue
                        with zf.open(csv_name) as f:
                            content = f.read().decode("latin-1")
                            reader = csv.DictReader(
                                io.StringIO(content), delimiter=";"
                            )
                            for row in reader:
                                cnpj_row = (
                                    row.get("CNPJ_Fundo_Classe", "").strip()
                                )
                                if cnpj_row != cnpj:
                                    continue

                                data_ref = row.get("Data_Referencia", "")
                                try:
                                    data = datetime.strptime(
                                        data_ref, "%Y-%m-%d"
                                    ).date()
                                except ValueError:
                                    data = date(ano, 1, 1)

                                pl = row.get("Patrimonio_Liquido", "")
                                dy = row.get(
                                    "Percentual_Dividend_Yield_Mes", ""
                                )
                                cotistas = row.get(
                                    "Total_Numero_Cotistas", ""
                                )
                                cota = row.get("Valor_Patrimonial_Cotas", "")

                                indicadores = (
                                    f"PL: R$ {pl} | DY: {dy}% | "
                                    f"Cotistas: {cotistas} | "
                                    f"VPC: R$ {cota}"
                                )

                                raw = f"{ticker}{data_ref}{cnpj_row}".encode()
                                hash_ = hashlib.sha256(raw).hexdigest()

                                relatorios.append(
                                    RelatorioEncontrado(
                                        url=f"cvm://{cnpj_row}/{data_ref}",
                                        data_publicacao=data,
                                        tipo="INFORME_MENSAL",
                                        ticker=ticker.upper(),
                                        hash_sha256=hash_,
                                        fonte="CVM",
                                    )
                                )

            except Exception:
                continue

        return relatorios

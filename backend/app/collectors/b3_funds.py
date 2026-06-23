import base64
import hashlib
import json
from datetime import date, datetime, timedelta
from typing import List, Optional

import requests

from backend.app.collectors.base import BaseCollector, RelatorioEncontrado


class B3FundosCollector(BaseCollector):
    B3_BASE_URL = "https://sistemaswebb3-listados.b3.com.br"
    DOCUMENTS_URL = "/fundsProxy/fundsCall/GetListedDocuments"

    CATEGORIAS_RELEVANTES = [
        "Relatório Gerencial",
        "Informe Mensal",
        "Informe Trimestral",
    ]

    def __init__(self):
        super().__init__()
        self.name = "b3_fundos"
        self.priority = 2

    def buscar_relatorios(
        self, ticker: str, cnpj: Optional[str] = None
    ) -> List[RelatorioEncontrado]:
        relatorios: List[RelatorioEncontrado] = []

        if not cnpj:
            return relatorios

        data_fim = date.today()
        data_ini = data_fim - timedelta(days=365 * 3)

        params = {
            "pageNumber": 1,
            "pageSize": 50,
            "cnpj": cnpj,
            "dateInitial": data_ini.strftime("%Y-%m-%d"),
            "dateFinal": data_fim.strftime("%Y-%m-%d"),
            "category": None,
        }

        try:
            json_str = json.dumps(params, separators=(",", ":"))
            param_b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
            url = f"{self.B3_BASE_URL}{self.DOCUMENTS_URL}/{param_b64}"

            resp = requests.get(url, timeout=30, headers=self._headers())
            if resp.status_code != 200:
                return relatorios

            data = resp.json()
            resultados = data.get("results", [])

            for doc in resultados:
                categoria = doc.get("category", {})
                nome_categoria = categoria.get("describle", "")

                if not any(
                    cat.lower() in nome_categoria.lower()
                    for cat in self.CATEGORIAS_RELEVANTES
                ):
                    continue

                url_fundosnet = doc.get("urlFundosNet", "")
                if not url_fundosnet:
                    continue

                try:
                    data_ref = datetime.strptime(
                        doc.get("referenceDate", ""), "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    try:
                        data_ref = datetime.strptime(
                            doc.get("deliveryDate", ""), "%Y-%m-%d"
                        ).date()
                    except (ValueError, TypeError):
                        data_ref = date.today()

                raw = f"{ticker}{url_fundosnet}".encode()
                hash_ = hashlib.sha256(raw).hexdigest()

                relatorios.append(
                    RelatorioEncontrado(
                        url=url_fundosnet,
                        data_publicacao=data_ref,
                        tipo="RELATORIO_GERENCIAL",
                        ticker=ticker.upper(),
                        hash_sha256=hash_,
                        fonte="B3/FundosNET",
                    )
                )

        except Exception:
            return relatorios

        return relatorios

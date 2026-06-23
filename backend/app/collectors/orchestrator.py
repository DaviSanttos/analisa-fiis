from typing import List, Optional

from backend.app.collectors.base import BaseCollector, RelatorioEncontrado
from backend.app.collectors.cvm import CVMCollector
from backend.app.collectors.b3_funds import B3FundosCollector
from backend.app.collectors.relatoriosfiis import RelatoriosFIICollector


class ColetorOrquestrador:
    def __init__(self):
        self.coletores: List[BaseCollector] = sorted(
            [
                CVMCollector(),
                B3FundosCollector(),
                RelatoriosFIICollector(),
            ],
            key=lambda c: c.priority,
        )

    def buscar_relatorios(
        self, ticker: str, cnpj: Optional[str] = None
    ) -> List[RelatorioEncontrado]:
        todos_relatorios: List[RelatorioEncontrado] = []
        urls_vistas: set = set()

        for coletor in self.coletores:
            try:
                relatorios = coletor.buscar_relatorios(ticker, cnpj)
                for r in relatorios:
                    if r.url and r.url not in urls_vistas:
                        urls_vistas.add(r.url)
                        todos_relatorios.append(r)
            except Exception:
                continue

        todos_relatorios.sort(
            key=lambda r: r.data_publicacao, reverse=True
        )

        return todos_relatorios

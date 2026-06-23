from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date


class RelatorioEncontrado:
    def __init__(
        self,
        url: str,
        data_publicacao: date,
        tipo: str,
        ticker: str,
        hash_sha256: Optional[str] = None,
        fonte: str = "",
    ):
        self.url = url
        self.data_publicacao = data_publicacao
        self.tipo = tipo
        self.ticker = ticker
        self.hash_sha256 = hash_sha256
        self.fonte = fonte

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "data_publicacao": self.data_publicacao.isoformat(),
            "tipo": self.tipo,
            "ticker": self.ticker,
            "fonte": self.fonte,
        }


class BaseCollector(ABC):
    def __init__(self):
        self.name = "base"
        self.priority = 99

    @abstractmethod
    def buscar_relatorios(
        self, ticker: str, cnpj: Optional[str] = None
    ) -> List[RelatorioEncontrado]:
        pass

    def baixar_pdf(self, url: str) -> Optional[bytes]:
        import requests

        try:
            resp = requests.get(url, timeout=30, headers=self._headers())
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

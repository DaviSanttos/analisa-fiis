import json
import os
import re
from typing import Optional, Dict, Any, List

import requests

from backend.app.extractors.pdf_extractor import PDFExtractor


class IAAnalyzer:
    OLLAMA_BASE_URL = os.getenv(
        "OLLAMA_BASE_URL", "http://localhost:11434"
    )
    MODELO = os.getenv("OLLAMA_MODEL", "qwen2.5")
    TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

    def __init__(self):
        self.extrator = PDFExtractor()

    def analisar_relatorio(
        self,
        texto_atual: str,
        texto_anterior: Optional[str] = None,
        politica_fundo: Optional[str] = None,
        indicadores_extraidos: Optional[Dict[str, Any]] = None,
        diario_bordo: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        prompt = self._montar_prompt(
            texto_atual, texto_anterior, politica_fundo, indicadores_extraidos, diario_bordo
        )

        try:
            resposta = self._chamar_ollama(prompt)
            return self._parsear_resposta(resposta)
        except Exception:
            return None

    def _montar_prompt(
        self,
        texto_atual: str,
        texto_anterior: Optional[str],
        politica_fundo: Optional[str],
        indicadores: Optional[Dict[str, Any]],
        diario_bordo: Optional[str] = None,
    ) -> str:
        prompt = """Você é um analista profissional especializado em fundos imobiliários brasileiros.

Faça uma análise DETALHADA (pente fino) do relatório gerencial abaixo seguindo um pipeline estruturado de critérios. Retorne APENAS um JSON válido (sem markdown, sem código, sem comentários) com a estrutura exata abaixo:

{
    "resumo_executivo": "texto curto",
    "o_que_mudou": "texto ou null",
    "tendencias_identificadas": "texto ou null",
    "indicadores_encontrados": "texto ou null",
    "eventos_relevantes": "texto ou null",
    "pontos_positivos": "texto",
    "pontos_negativos": "texto",
    "riscos": "texto",
    "oportunidades": "texto",
    "score_saude": "media ponderada dos criterios abaixo (0-100)",
    "nivel_atencao": "VERDE (score>=70) | AMARELO (40-69) | VERMELHO (<40)",
    "recomendacao_acompanhamento": "texto curto",
    "analise_comentada": "texto",
    "dimensoes": {
        "rentabilidade": 0-100,
        "vacancia": 0-100,
        "crescimento_patrimonial": 0-100,
        "liquidez": 0-100,
        "governanca": 0-100
    },
    "criterios_analise": {
        "geracao_renda": {"score": 0-100, "peso": 30, "detalhes": "texto", "sub_itens": {"dividend_yield": 0-100, "consistencia": 0-100, "cobertura": 0-100}},
        "qualidade_portfolio": {"score": 0-100, "peso": 25, "detalhes": "texto", "sub_itens": {"vacancia": 0-100, "inadimplencia": 0-100, "diversificacao": 0-100}},
        "saude_financeira": {"score": 0-100, "peso": 20, "detalhes": "texto", "sub_itens": {"crescimento_pl": 0-100, "p_vp": 0-100, "liquidez_mercado": 0-100}},
        "gestao_governanca": {"score": 0-100, "peso": 15, "detalhes": "texto", "sub_itens": {"transparencia": 0-100, "conformidade": 0-100, "track_record": 0-100}},
        "perspectivas": {"score": 0-100, "peso": 10, "detalhes": "texto", "sub_itens": {"tendencia_setor": 0-100, "crescimento_cotistas": 0-100, "eventos_futuros": 0-100}}
    },
    "conformidade_politica": {
        "status": "CONFORME|DESVIO_PARCIAL|DESVIO_GRAVE",
        "detalhes": "texto",
        "impacto": "texto"
    },
    "recomendacao_acao": {
        "decisao": "CONTINUE_COMPRANDO|MANTER_MONITORAR|PARE_REQUER_ANALISE",
        "justificativa": "texto"
    }
}

PIPELINE DE CRITERIOS (pesos): geracao_renda(30%), qualidade_portfolio(25%), saude_financeira(20%), gestao_governanca(15%), perspectivas(10%)

score_saude = geracao_renda.score*0.30 + qualidade_portfolio.score*0.25 + saude_financeira.score*0.20 + gestao_governanca.score*0.15 + perspectivas.score*0.10

REGRAS:
- Nao invente. Sem dados use 50.
- Nivel: VERDE(score>=70), AMARELO(40-69), VERMELHO(<40)
- Preencha TODOS os criterios com scores, pesos, sub_itens e detalhes
- Analise comentada: explique em portugues claro para leigo
"""
        if diario_bordo:
            prompt += f"\n--- DIÁRIO DE BORDO DO FII (histórico de análises anteriores) ---\n{diario_bordo[:2000]}\n"

        prompt += f"\n--- RELATÓRIO ATUAL ---\n{texto_atual[:2000]}\n"

        if texto_anterior:
            prompt += f"\n--- ÚLTIMO RELATÓRIO (para comparação) ---\n{texto_anterior[:1000]}\n"

        if politica_fundo:
            prompt += f"\n--- POLÍTICA DO FUNDO ---\n{politica_fundo[:1000]}\n"

        if indicadores:
            prompt += f"\n--- INDICADORES ---\n{json.dumps(indicadores, ensure_ascii=False, indent=2)}\n"

        return prompt

    def _chamar_ollama(self, prompt: str) -> str:
        url = f"{self.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": self.MODELO,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 8192,
            },
        }

        resp = requests.post(url, json=payload, timeout=self.TIMEOUT)
        resp.raise_for_status()

        dados = resp.json()
        return dados.get("response", "")

    def _parsear_resposta(self, resposta: str) -> Optional[Dict[str, Any]]:
        json_match = re.search(r"\{.*\}", resposta, re.DOTALL)
        if not json_match:
            return None
        try:
            dados = json.loads(json_match.group(0))
            return {
                "resumo_executivo": dados.get("resumo_executivo", ""),
                "o_que_mudou": dados.get("o_que_mudou"),
                "tendencias_identificadas": dados.get("tendencias_identificadas"),
                "indicadores_encontrados": dados.get("indicadores_encontrados"),
                "eventos_relevantes": dados.get("eventos_relevantes"),
                "pontos_positivos": dados.get("pontos_positivos", ""),
                "pontos_negativos": dados.get("pontos_negativos", ""),
                "riscos": dados.get("riscos", ""),
                "oportunidades": dados.get("oportunidades", ""),
                "score_saude": dados.get("score_saude", 50),
                "nivel_atencao": dados.get("nivel_atencao", "VERDE"),
                "recomendacao_acompanhamento": dados.get("recomendacao_acompanhamento"),
                "analise_comentada": dados.get("analise_comentada"),
                "conformidade_politica": dados.get("conformidade_politica", {}),
                "recomendacao_acao": dados.get("recomendacao_acao", {}),
                "dimensoes": dados.get("dimensoes"),
                "criterios_analise": dados.get("criterios_analise"),
            }
        except (json.JSONDecodeError, KeyError):
            return None

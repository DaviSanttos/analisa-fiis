import json
import os
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from backend.app import models, schemas, crud
from backend.app.collectors.orchestrator import ColetorOrquestrador
from backend.app.extractors.pdf_extractor import PDFExtractor
from backend.app.analyzers.ia_analyzer import IAAnalyzer


class PipelineProcessamento:
    def __init__(self, db: Session):
        self.db = db
        self.orquestrador = ColetorOrquestrador()
        self.extrator = PDFExtractor()
        self.analyser = IAAnalyzer()
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "pdfs",
        )
        os.makedirs(self.data_dir, exist_ok=True)

    def executar_para_fii(
        self, ticker: str, cnpj: Optional[str] = None, max_relatorios: int = 10
    ) -> Dict[str, Any]:
        resultado = {"ticker": ticker, "relatorios_analisados": 0, "total": 0, "ignorados": 0, "erro": None}

        fii = crud.get_fii_by_ticker(self.db, ticker)
        if not fii:
            resultado["erro"] = f"FII {ticker} não cadastrado"
            return resultado

        if not cnpj:
            cnpj = fii.cnpj
        if not cnpj:
            from backend.app.collectors.cvm import TickerMapper
            cnpj = TickerMapper.buscar_cnpj(ticker)
            if cnpj and not fii.cnpj:
                crud.update_fii(
                    self.db, ticker,
                    schemas.FIICreate(ticker=ticker, nome=fii.nome, cnpj=cnpj)
                )

        relatorios_encontrados = self.orquestrador.buscar_relatorios(ticker, cnpj)
        if not relatorios_encontrados:
            resultado["erro"] = "Nenhum relatório encontrado"
            return resultado

        relatorios_encontrados.sort(key=lambda r: r.data_publicacao)
        alvo = relatorios_encontrados[-max_relatorios:]

        resultado["total"] = len(alvo)

        # Carrega diário de bordo da análise mais recente (se existir)
        ultima_analise = crud.get_last_analise(self.db, ticker)
        diario_bordo = ultima_analise.diario_bordo if ultima_analise else None

        for relatorio in alvo:
            existente = crud.get_relatorio_by_hash(self.db, relatorio.hash_sha256)
            if existente:
                analises_existentes = crud.get_analises_by_relatorio(self.db, existente.id)
                if analises_existentes:
                    # Atualiza o diário se essa análise já tem um mais recente
                    for ae in analises_existentes:
                        if ae.diario_bordo and (not diario_bordo or ae.id > (ultima_analise.id if ultima_analise else 0)):
                            diario_bordo = ae.diario_bordo
                    resultado["ignorados"] += 1
                    continue
                relatorio_db = existente
                texto_extraido = existente.texto_extraido
            else:
                texto_extraido = None
                caminho_pdf = None

                if relatorio.url.startswith("cvm://"):
                    texto_extraido = (
                        f"Relatório CVM estruturado para {ticker} "
                        f"competência {relatorio.data_publicacao}"
                    )
                else:
                    conteudo_pdf = self._baixar_pdf(relatorio.url)
                    if not conteudo_pdf:
                        continue
                    caminho_pdf = self._salvar_pdf(ticker, relatorio, conteudo_pdf)
                    texto_extraido = self.extrator.extrair_texto(conteudo_pdf)

                if not texto_extraido:
                    continue

                relatorio_db = crud.create_relatorio(
                    self.db,
                    schemas.RelatorioCreate(
                        fii_ticker=ticker,
                        url=relatorio.url,
                        hash_sha256=relatorio.hash_sha256,
                        data_publicacao=relatorio.data_publicacao,
                        caminho_pdf=caminho_pdf,
                        texto_extraido=texto_extraido,
                    ),
                )

            # Analisar
            texto_limitado = texto_extraido[:2000]

            texto_anterior = None
            if ultima_analise and ultima_analise.relatorio:
                ta = ultima_analise.relatorio.texto_extraido
                if ta:
                    texto_anterior = ta[:1000]

            politica = fii.politica_fundo if hasattr(fii, "politica_fundo") else None
            indicadores = self.extrator.extrair_indicadores(texto_limitado)

            analise = self.analyser.analisar_relatorio(
                texto_atual=texto_limitado,
                texto_anterior=texto_anterior,
                politica_fundo=politica,
                indicadores_extraidos=indicadores,
                diario_bordo=diario_bordo,
            )

            if analise:
                dims = analise.get("dimensoes")
                criterios = analise.get("criterios_analise")
                ind_json = {}
                if dims and isinstance(dims, dict):
                    ind_json["dimensoes"] = dims
                if criterios and isinstance(criterios, dict):
                    ind_json["criterios"] = criterios
                if ind_json:
                    if analise.get("indicadores_encontrados"):
                        ind_json["detalhes"] = analise.get("indicadores_encontrados")
                    indicadores_str = json.dumps(ind_json, ensure_ascii=False)
                else:
                    indicadores_str = analise.get("indicadores_encontrados")

                # Constrói o novo diário de bordo
                data_ref = relatorio.data_publicacao.isoformat() if hasattr(relatorio.data_publicacao, 'isoformat') else str(relatorio.data_publicacao)
                score = analise.get("score_saude", "?")
                nivel = analise.get("nivel_atencao", "?")
                resumo = (analise.get("resumo_executivo") or "")[:150]
                comentada = analise.get("analise_comentada")

                pts_pos = (analise.get("pontos_positivos") or "")[:80]
                pts_neg = (analise.get("pontos_negativos") or "")[:80]
                nova_entrada = "[%s] Score: %s | %s" % (data_ref, score, nivel)
                nova_entrada += "\n  Resumo: " + resumo
                if pts_pos:
                    nova_entrada += "\n  Positivo: " + pts_pos
                if pts_neg:
                    nova_entrada += "\n  Negativo: " + pts_neg
                if comentada:
                    nova_entrada += "\n  -> " + comentada[:200]
                novo_diario = (diario_bordo + "\n\n" + nova_entrada) if diario_bordo else nova_entrada

                crud.create_analise(
                    self.db,
                    schemas.AnaliseCreate(
                        relatorio_id=relatorio_db.id,
                        fii_ticker=ticker,
                        resumo_executivo=analise.get("resumo_executivo", ""),
                        o_que_mudou=analise.get("o_que_mudou"),
                        tendencias_identificadas=analise.get("tendencias_identificadas"),
                        indicadores_encontrados=indicadores_str,
                        eventos_relevantes=analise.get("eventos_relevantes"),
                        pontos_positivos=analise.get("pontos_positivos", ""),
                        pontos_negativos=analise.get("pontos_negativos", ""),
                        riscos=analise.get("riscos", ""),
                        oportunidades=analise.get("oportunidades", ""),
                        score_saude=analise.get("score_saude", 50),
                        nivel_atencao=analise.get("nivel_atencao", "VERDE"),
                        recomendacao_acompanhamento=analise.get("recomendacao_acompanhamento"),
                        analise_comentada=comentada,
                        diario_bordo=novo_diario,
                    ),
                )
                diario_bordo = novo_diario
                resultado["relatorios_analisados"] += 1

        return resultado

    def _baixar_pdf(self, url: str) -> Optional[bytes]:
        import requests
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None

    def _salvar_pdf(self, ticker: str, relatorio, conteudo: bytes) -> str:
        nome = f"{ticker}_{relatorio.data_publicacao.isoformat()}_{relatorio.hash_sha256[:12]}.pdf"
        caminho = os.path.join(self.data_dir, nome)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        return caminho

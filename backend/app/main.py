from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from backend.app import models, schemas, crud
from backend.app.database import engine, get_db
from backend.app.pipeline import PipelineProcessamento

models.Base.metadata.create_all(bind=engine)

# Process tracking
processing_fiis = set()

app = FastAPI(
    title="Sistema de Monitoramento de FIIs com IA",
    description="API do backend para monitoramento inteligente e análise de Fundos Imobiliários.",
    version="1.0.0"
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
os.makedirs(STATIC_DIR, exist_ok=True)

# --- DASHBOARD AGGREGATED ENDPOINT ---

@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    fiis = crud.get_fiis(db)
    data = []
    for fii in fiis:
        relatorios = crud.get_relatorios_by_fii(db, fii.ticker)
        analises = crud.get_analises_by_fii(db, fii.ticker)
        ultima_analise = analises[0] if analises else None
        ultimo_relatorio = relatorios[0] if relatorios else None

        item = {
            "ticker": fii.ticker,
            "nome": fii.nome,
            "cnpj": fii.cnpj,
            "analisando": fii.ticker in processing_fiis,
            "total_relatorios": len(relatorios),
            "total_analises": len(analises),
            "ultimo_relatorio": {
                "data": ultimo_relatorio.data_publicacao.isoformat() if ultimo_relatorio else None,
                "url": ultimo_relatorio.url if ultimo_relatorio else None,
            } if ultimo_relatorio else None,
        }
        if ultima_analise:
            item["ultima_analise"] = {
                "score_saude": ultima_analise.score_saude,
                "nivel_atencao": ultima_analise.nivel_atencao,
                "resumo_executivo": ultima_analise.resumo_executivo[:200] if ultima_analise.resumo_executivo else None,
                "data": ultima_analise.created_at.isoformat() if ultima_analise.created_at else None,
                "recomendacao_acao": ultima_analise.recomendacao_acompanhamento,
            }
        data.append(item)
    return {"fiis": data}

# --- STATIC HTML DASHBOARD ---

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_dashboard_html():
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Analisa FIIs</h1><p>Frontend nao encontrado. Execute o setup.</p>")

# --- ENDPOINTS FII ---

@app.post("/fiis/", response_model=schemas.FIIOut, status_code=status.HTTP_201_CREATED)
def cadastrar_fii(fii: schemas.FIICreate, db: Session = Depends(get_db)):
    db_fii = crud.get_fii_by_ticker(db, ticker=fii.ticker)
    if db_fii:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FII com o ticker {fii.ticker} já está cadastrado."
        )
    if not fii.cnpj:
        from backend.app.collectors.cvm import TickerMapper
        cnpj = TickerMapper.buscar_cnpj(fii.ticker)
        if cnpj:
            fii.cnpj = cnpj
    return crud.create_fii(db=db, fii=fii)

@app.get("/fiis/", response_model=List[schemas.FIIOut])
def listar_fiis(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_fiis(db, skip=skip, limit=limit)

@app.get("/fiis/{ticker}", response_model=schemas.FIIOut)
def obter_fii(ticker: str, db: Session = Depends(get_db)):
    db_fii = crud.get_fii_by_ticker(db, ticker=ticker)
    if not db_fii:
        raise HTTPException(status_code=404, detail=f"FII {ticker.upper()} não encontrado.")
    return db_fii

@app.patch("/fiis/{ticker}", response_model=schemas.FIIOut)
def atualizar_fii(ticker: str, fii: schemas.FIICreate, db: Session = Depends(get_db)):
    db_fii = crud.get_fii_by_ticker(db, ticker=ticker)
    if not db_fii:
        raise HTTPException(status_code=404, detail="FII não encontrado")
    return crud.update_fii(db, ticker=ticker, fii=fii)

@app.delete("/fiis/{ticker}", status_code=status.HTTP_200_OK)
def remover_fii(ticker: str, db: Session = Depends(get_db)):
    removido = crud.delete_fii(db, ticker=ticker)
    if not removido:
        raise HTTPException(status_code=404, detail=f"FII {ticker.upper()} não encontrado.")
    return {"message": f"FII {ticker.upper()} removido com sucesso."}

# --- ENDPOINTS RELATÓRIOS ---

@app.get("/fiis/{ticker}/relatorios")
def listar_relatorios(ticker: str, db: Session = Depends(get_db)):
    rels = crud.get_relatorios_by_fii(db, ticker=ticker)
    return [
        {
            "id": r.id,
            "data_publicacao": r.data_publicacao.isoformat(),
            "tipo": "PDF" if r.caminho_pdf else "CVM",
            "url": r.url,
            "tem_analise": r.analise is not None,
        }
        for r in rels
    ]

# --- SCORE HISTORY ---

@app.get("/fiis/{ticker}/score-history")
def get_score_history(ticker: str, limit: int = 30, db: Session = Depends(get_db)):
    scores = crud.get_score_history(db, ticker, limit=limit)
    return {"ticker": ticker, "history": scores}

# --- ENDPOINTS ANÁLISES ---

@app.get("/fiis/{ticker}/analises")
def listar_analises(ticker: str, db: Session = Depends(get_db)):
    anals = crud.get_analises_by_fii(db, ticker=ticker)
    return [
        {
            "id": a.id,
            "score_saude": a.score_saude,
            "nivel_atencao": a.nivel_atencao,
            "resumo_executivo": a.resumo_executivo[:300] if a.resumo_executivo else None,
            "data": a.created_at.isoformat() if a.created_at else None,
        }
        for a in anals
    ]

@app.get("/fiis/{ticker}/analises/ultima")
def obter_ultima_analise(ticker: str, db: Session = Depends(get_db)):
    analise = crud.get_last_analise(db, ticker=ticker)
    if not analise:
        return {"ticker": ticker, "score_saude": None, "nivel_atencao": None, "resumo_executivo": None}
    return {
        "score_saude": analise.score_saude,
        "nivel_atencao": analise.nivel_atencao,
        "resumo_executivo": analise.resumo_executivo,
        "o_que_mudou": analise.o_que_mudou,
        "tendencias_identificadas": analise.tendencias_identificadas,
        "indicadores_encontrados": analise.indicadores_encontrados,
        "eventos_relevantes": analise.eventos_relevantes,
        "pontos_positivos": analise.pontos_positivos,
        "pontos_negativos": analise.pontos_negativos,
        "riscos": analise.riscos,
        "oportunidades": analise.oportunidades,
        "recomendacao_acompanhamento": analise.recomendacao_acompanhamento,
        "analise_comentada": analise.analise_comentada,
        "diario_bordo": analise.diario_bordo,
        "data": analise.created_at.isoformat() if analise.created_at else None,
    }

# --- PIPELINE ---

@app.post("/pipeline/{ticker}")
def executar_pipeline(ticker: str, max_relatorios: int = 2, reset: bool = False, db: Session = Depends(get_db)):
    ticker_up = ticker.upper()
    if reset:
        db.query(models.Analise).filter(models.Analise.fii_ticker == ticker_up).delete()
        db.query(models.Relatorio).filter(models.Relatorio.fii_ticker == ticker_up).delete()
        db.commit()
    processing_fiis.add(ticker_up)
    try:
        pipeline = PipelineProcessamento(db)
        return pipeline.executar_para_fii(ticker_up, max_relatorios=max_relatorios)
    finally:
        processing_fiis.discard(ticker_up)

@app.post("/pipeline/todos")
def executar_pipeline_todos(db: Session = Depends(get_db)):
    fiis = crud.get_fiis(db)
    pipeline = PipelineProcessamento(db)
    resultados = []
    for fii in fiis:
        processing_fiis.add(fii.ticker)
        try:
            resultado = pipeline.executar_para_fii(fii.ticker, fii.cnpj, max_relatorios=2)
            resultados.append(resultado)
        finally:
            processing_fiis.discard(fii.ticker)
    return {"resultados": resultados}

@app.post("/pipeline/reanalisar/{ticker}")
def reanalisar_ultimo_relatorio(ticker: str, db: Session = Depends(get_db)):
    relatorios = crud.get_relatorios_by_fii(db, ticker)
    if not relatorios:
        raise HTTPException(status_code=404, detail="Nenhum relatório encontrado")
    ultimo = relatorios[0]
    if not ultimo.texto_extraido:
        raise HTTPException(status_code=400, detail="Relatório sem texto extraído")

    from backend.app.analyzers.ia_analyzer import IAAnalyzer
    from backend.app.extractors.pdf_extractor import PDFExtractor

    extrator = PDFExtractor()
    indicadores = extrator.extrair_indicadores(ultimo.texto_extraido[:2000])

    ultima_analise = crud.get_last_analise(db, ticker)
    texto_anterior = None
    if ultima_analise and ultima_analise.relatorio and ultima_analise.relatorio.texto_extraido:
        texto_anterior = ultima_analise.relatorio.texto_extraido[:1000]

    fii = crud.get_fii_by_ticker(db, ticker)
    politica = fii.politica_fundo if fii else None

    analyzer = IAAnalyzer()
    analise = analyzer.analisar_relatorio(
        texto_atual=ultimo.texto_extraido[:2000],
        texto_anterior=texto_anterior,
        politica_fundo=politica,
        indicadores_extraidos=indicadores,
    )
    if not analise:
        raise HTTPException(status_code=500, detail="Falha na análise IA")

    # Inclui dimensoes no indicadores_encontrados para o radar chart
    dims = analise.get("dimensoes")
    if dims and isinstance(dims, dict):
        import json as _json
        ind_json = {"dimensoes": dims}
        if analise.get("indicadores_encontrados"):
            ind_json["detalhes"] = analise.get("indicadores_encontrados")
        indicadores_str = _json.dumps(ind_json, ensure_ascii=False)
    else:
        indicadores_str = analise.get("indicadores_encontrados")

    comentada = analise.get("analise_comentada")
    score = analise.get("score_saude", "?")
    nivel = analise.get("nivel_atencao", "?")
    resumo = (analise.get("resumo_executivo") or "")[:150]
    data_ref = ultimo.data_publicacao.isoformat() if hasattr(ultimo.data_publicacao, 'isoformat') else str(ultimo.data_publicacao)
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
    ultima_analise_existente = crud.get_last_analise(db, ticker)
    diario_bordo = ultima_analise_existente.diario_bordo if ultima_analise_existente else None
    novo_diario = (diario_bordo + "\n\n" + nova_entrada) if diario_bordo else nova_entrada

    crud.create_analise(
        db,
        schemas.AnaliseCreate(
            relatorio_id=ultimo.id,
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
    return {"ticker": ticker, "status": "analisado"}

# --- BUSCAR CNPJ ---

@app.get("/api/buscar-cnpj/{ticker}")
def buscar_cnpj(ticker: str):
    from backend.app.collectors.cvm import TickerMapper
    cnpj = TickerMapper.buscar_cnpj(ticker)
    if cnpj:
        return {"ticker": ticker.upper(), "cnpj": cnpj}
    raise HTTPException(status_code=404, detail="CNPJ não encontrado")

from sqlalchemy.orm import Session
from backend.app import models, schemas
from typing import List, Optional

# --- CRUD FIIs ---

def get_fii_by_ticker(db: Session, ticker: str) -> Optional[models.FII]:
    return db.query(models.FII).filter(models.FII.ticker == ticker.upper()).first()

def get_fiis(db: Session, skip: int = 0, limit: int = 100) -> List[models.FII]:
    return db.query(models.FII).offset(skip).limit(limit).all()

def create_fii(db: Session, fii: schemas.FIICreate) -> models.FII:
    db_fii = models.FII(
        ticker=fii.ticker.upper(),
        nome=fii.nome,
        cnpj=fii.cnpj,
        politica_fundo=fii.politica_fundo,
        regulamento_url=fii.regulamento_url,
    )
    db.add(db_fii)
    db.commit()
    db.refresh(db_fii)
    return db_fii

def update_fii(db: Session, ticker: str, fii: schemas.FIICreate) -> models.FII:
    db_fii = get_fii_by_ticker(db, ticker)
    if not db_fii:
        return None
    db_fii.nome = fii.nome
    db_fii.cnpj = fii.cnpj
    db_fii.politica_fundo = fii.politica_fundo
    db_fii.regulamento_url = fii.regulamento_url
    db.commit()
    db.refresh(db_fii)
    return db_fii

def delete_fii(db: Session, ticker: str) -> bool:
    db_fii = get_fii_by_ticker(db, ticker)
    if db_fii:
        db.delete(db_fii)
        db.commit()
        return True
    return False


# --- CRUD Relatórios ---

def get_relatorio_by_hash(db: Session, hash_sha256: str) -> Optional[models.Relatorio]:
    return db.query(models.Relatorio).filter(models.Relatorio.hash_sha256 == hash_sha256).first()

def get_relatorios_by_fii(db: Session, ticker: str) -> List[models.Relatorio]:
    return db.query(models.Relatorio).filter(models.Relatorio.fii_ticker == ticker.upper()).order_by(models.Relatorio.data_publicacao.desc()).all()

def create_relatorio(db: Session, relatorio: schemas.RelatorioCreate) -> models.Relatorio:
    db_relatorio = models.Relatorio(
        fii_ticker=relatorio.fii_ticker.upper(),
        url=relatorio.url,
        hash_sha256=relatorio.hash_sha256,
        data_publicacao=relatorio.data_publicacao,
        caminho_pdf=relatorio.caminho_pdf,
        texto_extraido=relatorio.texto_extraido
    )
    db.add(db_relatorio)
    db.commit()
    db.refresh(db_relatorio)
    return db_relatorio


# --- CRUD Análises ---

def get_analises_by_fii(db: Session, ticker: str) -> List[models.Analise]:
    return db.query(models.Analise).filter(models.Analise.fii_ticker == ticker.upper()).order_by(models.Analise.created_at.desc()).all()

def get_analises_by_relatorio(db: Session, relatorio_id: int) -> List[models.Analise]:
    return db.query(models.Analise).filter(models.Analise.relatorio_id == relatorio_id).all()

def get_score_history(db: Session, ticker: str, limit: int = 20):
    results = (
        db.query(models.Analise.score_saude, models.Analise.created_at, models.Relatorio.data_publicacao)
        .join(models.Relatorio, models.Relatorio.id == models.Analise.relatorio_id)
        .filter(models.Analise.fii_ticker == ticker.upper())
        .order_by(models.Relatorio.data_publicacao.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "score": row[0],
            "created_at": row[1].isoformat() if row[1] else None,
            "data_ref": row[2].isoformat() if row[2] else None,
        }
        for row in results
    ]

def get_last_analise(db: Session, ticker: str) -> Optional[models.Analise]:
    return db.query(models.Analise).filter(models.Analise.fii_ticker == ticker.upper()).order_by(models.Analise.created_at.desc()).first()

def create_analise(db: Session, analise: schemas.AnaliseCreate) -> models.Analise:
    db_analise = models.Analise(
        relatorio_id=analise.relatorio_id,
        fii_ticker=analise.fii_ticker.upper(),
        resumo_executivo=analise.resumo_executivo,
        o_que_mudou=analise.o_que_mudou,
        tendencias_identificadas=analise.tendencias_identificadas,
        indicadores_encontrados=analise.indicadores_encontrados,
        eventos_relevantes=analise.eventos_relevantes,
        pontos_positivos=analise.pontos_positivos,
        pontos_negativos=analise.pontos_negativos,
        riscos=analise.riscos,
        oportunidades=analise.oportunidades,
        score_saude=analise.score_saude,
        nivel_atencao=analise.nivel_atencao,
        recomendacao_acompanhamento=analise.recomendacao_acompanhamento,
        analise_comentada=analise.analise_comentada,
        diario_bordo=analise.diario_bordo,
    )
    db.add(db_analise)
    db.commit()
    db.refresh(db_analise)
    return db_analise


# --- CRUD Alertas ---

def get_alertas_nao_enviados(db: Session) -> List[models.Alerta]:
    return db.query(models.Alerta).filter(models.Alerta.enviado == False).all()

def create_alerta(db: Session, alerta: schemas.AlertaBase) -> models.Alerta:
    db_alerta = models.Alerta(
        fii_ticker=alerta.fii_ticker.upper(),
        tipo=alerta.tipo,
        mensagem=alerta.mensagem,
        enviado=alerta.enviado
    )
    db.add(db_alerta)
    db.commit()
    db.refresh(db_alerta)
    return db_alerta

def marcar_alerta_enviado(db: Session, alerta_id: int) -> bool:
    db_alerta = db.query(models.Alerta).filter(models.Alerta.id == alerta_id).first()
    if db_alerta:
        db_alerta.enviado = True
        db.commit()
        return True
    return False

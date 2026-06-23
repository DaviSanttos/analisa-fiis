import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app import crud
from backend.app.pipeline import PipelineProcessamento

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def executar_pipeline_todos():
    logger.info("Iniciando execução automática do pipeline para todos FIIs")
    db: Session = SessionLocal()
    try:
        fiis = crud.get_fiis(db)
        pipeline = PipelineProcessamento(db)
        for fii in fiis:
            try:
                resultado = pipeline.executar_para_fii(fii.ticker, fii.cnpj)
                if resultado.get("novos_relatorios", 0) > 0:
                    logger.info(
                        f"{fii.ticker}: {resultado['novos_relatorios']} novo(s) relatório(s)"
                    )
                elif resultado.get("erro"):
                    logger.warning(f"{fii.ticker}: {resultado['erro']}")
            except Exception as e:
                logger.error(f"Erro ao processar {fii.ticker}: {e}")
    finally:
        db.close()
    logger.info("Pipeline automático finalizado")


def start_scheduler():
    scheduler.add_job(
        executar_pipeline_todos,
        IntervalTrigger(hours=24),
        id="pipeline_diario",
        name="Executar pipeline para todos FIIs",
        next_run_time=datetime.now(),
    )
    scheduler.start()
    logger.info("Scheduler iniciado - execução diária automática")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler parado")

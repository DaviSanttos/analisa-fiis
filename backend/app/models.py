from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

class FII(Base):
    __tablename__ = "fiis"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True, nullable=False)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(18), nullable=True)
    politica_fundo = Column(Text, nullable=True)
    regulamento_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    relatorios = relationship("Relatorio", back_populates="fii", cascade="all, delete-orphan")
    analises = relationship("Analise", back_populates="fii", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="fii", cascade="all, delete-orphan")


class Relatorio(Base):
    __tablename__ = "relatorios"

    id = Column(Integer, primary_key=True, index=True)
    fii_ticker = Column(String(10), ForeignKey("fiis.ticker", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    hash_sha256 = Column(String(64), unique=True, index=True, nullable=False)
    data_publicacao = Column(Date, nullable=False)
    caminho_pdf = Column(String(500), nullable=True)
    texto_extraido = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    fii = relationship("FII", back_populates="relatorios")
    analise = relationship("Analise", back_populates="relatorio", uselist=False, cascade="all, delete-orphan")


class Analise(Base):
    __tablename__ = "analises"

    id = Column(Integer, primary_key=True, index=True)
    relatorio_id = Column(Integer, ForeignKey("relatorios.id", ondelete="CASCADE"), nullable=False)
    fii_ticker = Column(String(10), ForeignKey("fiis.ticker", ondelete="CASCADE"), nullable=False)
    
    # Seções exigidas no instructions.md
    resumo_executivo = Column(Text, nullable=False)
    o_que_mudou = Column(Text, nullable=True)
    tendencias_identificadas = Column(Text, nullable=True)
    indicadores_encontrados = Column(Text, nullable=True)  # Pode armazenar um JSON em formato string
    eventos_relevantes = Column(Text, nullable=True)
    pontos_positivos = Column(Text, nullable=True)
    pontos_negativos = Column(Text, nullable=True)
    riscos = Column(Text, nullable=True)
    oportunidades = Column(Text, nullable=True)
    score_saude = Column(Integer, nullable=False, default=50)  # 0 a 100
    nivel_atencao = Column(String(20), nullable=False, default="VERDE")  # VERDE, AMARELO, VERMELHO
    recomendacao_acompanhamento = Column(Text, nullable=True)
    analise_comentada = Column(Text, nullable=True)
    diario_bordo = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    fii = relationship("FII", back_populates="analises")
    relatorio = relationship("Relatorio", back_populates="analise")


class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    fii_ticker = Column(String(10), ForeignKey("fiis.ticker", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)  # ex: NOVO_RELATORIO, QUEDA_SCORE, STATUS_VERMELHO, TENDENCIA_NEGATIVA
    mensagem = Column(Text, nullable=False)
    enviado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    fii = relationship("FII", back_populates="alertas")

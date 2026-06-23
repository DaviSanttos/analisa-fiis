from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional, List, Dict, Any

# FII Schemas
class FIIBase(BaseModel):
    ticker: str = Field(..., max_length=10, description="Ticker do FII, ex: MXRF11")
    nome: str = Field(..., max_length=100, description="Nome do FII, ex: Maxi Renda")

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()

class FIICreate(FIIBase):
    cnpj: Optional[str] = Field(None, max_length=18, description="CNPJ do fundo, ex: 00.000.000/0000-00")
    politica_fundo: Optional[str] = Field(None, description="Texto da política de investimento extraída do prospecto")
    regulamento_url: Optional[str] = Field(None, max_length=500, description="URL do regulamento/prospecto")

class FIIOut(FIIBase):
    id: int
    cnpj: Optional[str] = None
    politica_fundo: Optional[str] = None
    regulamento_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Relatorio Schemas
class RelatorioBase(BaseModel):
    fii_ticker: str
    url: str
    hash_sha256: str
    data_publicacao: date
    caminho_pdf: Optional[str] = None
    texto_extraido: Optional[str] = None

class RelatorioCreate(RelatorioBase):
    pass

class RelatorioOut(RelatorioBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Analise Schemas
class AnaliseBase(BaseModel):
    relatorio_id: int
    fii_ticker: str
    resumo_executivo: str
    o_que_mudou: Optional[str] = None
    tendencias_identificadas: Optional[str] = None
    indicadores_encontrados: Optional[str] = None  # JSON string
    eventos_relevantes: Optional[str] = None
    pontos_positivos: Optional[str] = None
    pontos_negativos: Optional[str] = None
    riscos: Optional[str] = None
    oportunidades: Optional[str] = None
    score_saude: int = Field(50, ge=0, le=100)
    nivel_atencao: str = "VERDE"
    recomendacao_acompanhamento: Optional[str] = None
    analise_comentada: Optional[str] = None
    diario_bordo: Optional[str] = None

class AnaliseCreate(AnaliseBase):
    pass

class AnaliseOut(AnaliseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Alerta Schemas
class AlertaBase(BaseModel):
    fii_ticker: str
    tipo: str
    mensagem: str
    enviado: bool = False

class AlertaOut(AlertaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

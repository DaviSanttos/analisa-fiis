import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app import models, schemas, crud

# Configurar banco de dados SQLite em memória para testes isolados
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Cria as tabelas antes de cada teste
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Limpa as tabelas depois de cada teste
        Base.metadata.drop_all(bind=engine)

def test_criar_e_obter_fii(db_session):
    # Dado: Um novo FII para cadastrar
    fii_in = schemas.FIICreate(ticker="MXRF11", nome="Maxi Renda")
    
    # Quando: Criamos o FII no banco
    db_fii = crud.create_fii(db=db_session, fii=fii_in)
    
    # Então: Os dados devem coincidir e o ID deve estar presente
    assert db_fii.id is not None
    assert db_fii.ticker == "MXRF11"
    assert db_fii.nome == "Maxi Renda"
    
    # E: Devemos conseguir buscá-lo pelo ticker
    fii_buscado = crud.get_fii_by_ticker(db=db_session, ticker="MXRF11")
    assert fii_buscado is not None
    assert fii_buscado.nome == "Maxi Renda"

def test_listar_fiis(db_session):
    # Dado: Dois FIIs cadastrados
    fii_1 = schemas.FIICreate(ticker="MXRF11", nome="Maxi Renda")
    fii_2 = schemas.FIICreate(ticker="HGLG11", nome="Pátria Logística")
    crud.create_fii(db=db_session, fii=fii_1)
    crud.create_fii(db=db_session, fii=fii_2)
    
    # Quando: Buscamos a lista
    lista = crud.get_fiis(db=db_session)
    
    # Então: O tamanho deve ser 2 e conter os tickers corretos
    assert len(lista) == 2
    tickers = [f.ticker for f in lista]
    assert "MXRF11" in tickers
    assert "HGLG11" in tickers

def test_deletar_fii(db_session):
    # Dado: Um FII cadastrado
    fii_in = schemas.FIICreate(ticker="MXRF11", nome="Maxi Renda")
    crud.create_fii(db=db_session, fii=fii_in)
    
    # Quando: Deletamos o FII
    deletado = crud.delete_fii(db=db_session, ticker="MXRF11")
    
    # Então: O retorno deve ser True
    assert deletado is True
    
    # E: O FII não deve mais existir no banco
    fii_buscado = crud.get_fii_by_ticker(db=db_session, ticker="MXRF11")
    assert fii_buscado is None

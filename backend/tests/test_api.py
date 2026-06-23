import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, close_all_sessions

from backend.app.main import app
from backend.app.database import Base, get_db


@pytest.fixture(scope="function")
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    close_all_sessions()
    engine.dispose()

    try:
        os.unlink(db_path)
    except PermissionError:
        pass


def test_api_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Bem-vindo" in response.json()["message"]


def test_cadastrar_fii_api(client):
    response = client.post("/fiis/", json={"ticker": "MXRF11", "nome": "Maxi Renda"})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "MXRF11"
    assert data["nome"] == "Maxi Renda"
    assert "id" in data

    response_dup = client.post("/fiis/", json={"ticker": "mxrf11", "nome": "Outro Nome"})
    assert response_dup.status_code == 400
    assert "já está cadastrado" in response_dup.json()["detail"]


def test_listar_e_obter_fii_api(client):
    client.post("/fiis/", json={"ticker": "MXRF11", "nome": "Maxi Renda"})
    client.post("/fiis/", json={"ticker": "HGLG11", "nome": "Pátria Logística"})

    response_list = client.get("/fiis/")
    assert response_list.status_code == 200
    data_list = response_list.json()
    assert len(data_list) == 2
    tickers = [f["ticker"] for f in data_list]
    assert "MXRF11" in tickers
    assert "HGLG11" in tickers

    response_get = client.get("/fiis/MXRF11")
    assert response_get.status_code == 200
    assert response_get.json()["nome"] == "Maxi Renda"

    response_get_fake = client.get("/fiis/FAKE11")
    assert response_get_fake.status_code == 404


def test_remover_fii_api(client):
    client.post("/fiis/", json={"ticker": "MXRF11", "nome": "Maxi Renda"})

    response_del = client.delete("/fiis/MXRF11")
    assert response_del.status_code == 200
    assert "removido com sucesso" in response_del.json()["message"]

    response_get = client.get("/fiis/MXRF11")
    assert response_get.status_code == 404

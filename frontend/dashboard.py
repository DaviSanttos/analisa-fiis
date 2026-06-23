import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Analisa FIIs",
    page_icon="🏢",
    layout="wide",
)

st.title("📊 Analisa FIIs - Monitoramento Inteligente")
st.markdown("---")


def cor_status(nivel):
    return {"VERDE": "green", "AMARELO": "orange", "VERMELHO": "red"}.get(nivel, "gray")


def cor_recomendacao(dec):
    cores = {
        "CONTINUE_COMPRANDO": "green",
        "MANTER_MONITORAR": "orange",
        "PARE_REQUER_ANALISE": "red",
    }
    return cores.get(dec, "gray")


try:
    resp = requests.get(f"{API_BASE}/fiis/", timeout=10)
    fiis = resp.json() if resp.status_code == 200 else []
except Exception:
    fiis = []
    st.error("Não foi possível conectar à API. Verifique se o backend está rodando.")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Minha Carteira")
    if not fiis:
        st.info("Nenhum FII cadastrado. Adicione FIIs para começar.")
    else:
        for fii in fiis:
            with st.container(border=True):
                cols = st.columns([1, 2, 1, 1])
                with cols[0]:
                    st.markdown(f"### {fii['ticker']}")
                with cols[1]:
                    st.markdown(f"{fii['nome']}")
                with cols[2]:
                    try:
                        resp_a = requests.get(
                            f"{API_BASE}/fiis/{fii['ticker']}/analises/ultima",
                            timeout=5,
                        )
                        if resp_a.status_code == 200:
                            a = resp_a.json()
                            score = a.get("score_saude", 0)
                            nivel = a.get("nivel_atencao", "VERDE")
                            st.markdown(
                                f"Score: **{score}/100**  \n"
                                f":{cor_status(nivel)}[**{nivel}**]"
                            )
                        else:
                            st.markdown("*Sem análise*")
                    except Exception:
                        st.markdown("*Sem análise*")
                with cols[3]:
                    try:
                        resp_a = requests.get(
                            f"{API_BASE}/fiis/{fii['ticker']}/analises/ultima",
                            timeout=5,
                        )
                        if resp_a.status_code == 200:
                            a = resp_a.json()
                            rec_data = a.get("recomendacao_acao", {})
                            decisao = rec_data.get("decisao", "MANTER_MONITORAR")
                            st.markdown(
                                f":{cor_recomendacao(decisao)}[**{decisao.replace('_', ' ')}**]"
                            )
                        else:
                            st.markdown("*Aguardando*")
                    except Exception:
                        st.markdown("*Aguardando*")

with col2:
    st.subheader("⚙️ Ações")
    with st.container(border=True):
        ticker_input = st.text_input(
            "Adicionar FII", placeholder="MXRF11", max_chars=10
        ).strip().upper()
        nome_input = st.text_input("Nome do fundo", placeholder="Maxi Renda")
        cnpj_input = st.text_input(
            "CNPJ (opcional)", placeholder="00.000.000/0000-00"
        )
        if st.button("➕ Cadastrar", use_container_width=True):
            if ticker_input and nome_input:
                try:
                    resp = requests.post(
                        f"{API_BASE}/fiis/",
                        json={
                            "ticker": ticker_input,
                            "nome": nome_input,
                            "cnpj": cnpj_input or None,
                        },
                        timeout=10,
                    )
                    if resp.status_code == 201:
                        st.success(f"{ticker_input} cadastrado!")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Erro ao cadastrar"))
                except Exception as e:
                    st.error(f"Erro: {e}")

    with st.container(border=True):
        st.subheader("🔄 Pipeline")
        if st.button("▶️ Executar para todos", use_container_width=True):
            try:
                resp = requests.post(f"{API_BASE}/pipeline/todos", timeout=300)
                if resp.status_code == 200:
                    resultados = resp.json().get("resultados", [])
                    for r in resultados:
                        if r.get("novos_relatorios", 0) > 0:
                            st.success(
                                f"{r['ticker']}: {r['novos_relatorios']} relatório(s)"
                            )
                        elif r.get("erro"):
                            st.warning(f"{r['ticker']}: {r['erro']}")
                        else:
                            st.info(f"{r['ticker']}: sem novidades")
            except Exception as e:
                st.error(f"Erro no pipeline: {e}")

    with st.container(border=True):
        st.subheader("📄 Últimos Relatórios")
        if fiis:
            for fii in fiis[:5]:
                try:
                    resp_r = requests.get(
                        f"{API_BASE}/fiis/{fii['ticker']}/relatorios", timeout=5
                    )
                    if resp_r.status_code == 200:
                        rels = resp_r.json()
                        if rels:
                            ultimo = rels[0]
                            dt = ultimo.get("data_publicacao", "?")
                            st.markdown(f"**{fii['ticker']}** - {dt}")
                except Exception:
                    pass

st.markdown("---")
st.caption(f"Analisa FIIs v1.0.0 | Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

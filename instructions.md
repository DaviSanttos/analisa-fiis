# Analisa FIIs — Documentação do Projeto

Sistema local de monitoramento inteligente de Fundos Imobiliários (FIIs). Coleta relatórios gerenciais de fontes gratuitas, extrai indicadores, analisa com IA local (Ollama) e gera recomendações de investimento.

---

## Arquitetura

```
Frontend (HTML/JS via FastAPI) ←→ API REST (FastAPI) ←→ SQLite (SQLAlchemy)
                                      ↑
                              Pipeline de Processamento
                                      ↑
                              Coletor → Extrator → IA (Ollama/qwen2.5)
```

| Camada | Tecnologia |
|---|---|
| Frontend | HTML/CSS/JS puro + Chart.js (CDN) |
| Backend | FastAPI (Python 3.11) |
| ORM | SQLAlchemy |
| Banco | SQLite (`data/database.db`) |
| IA Local | Ollama + qwen2.5 |
| Coleta | CVM Dados Abertos (principal), B3/Fundos.NET, relatoriosfiis.com.br (fallback) |

---

## Status Atual (23/06/2026)

### ✅ Implementado

#### Coleta de Dados
- **Coletor CVM**: Baixa CSV estruturado da CVM com dados mensais de FIIs (receita, despesas, dividendos, vacância, cotistas, etc.)
- **TickerMapper**: Resolução automática de CNPJ via StatusInvest (ticker → CNPJ)
- **Coleta hierárquica**: CVM (primário) → B3 → relatoriosfiis.com.br (fallbacks)
- **Orquestrador**: Coordena as fontes com fallback automático
- **Cache de CNPJ**: Evita buscar repetidamente

#### Pipeline de Processamento
- **Pipeline**: Coleta → Extração → Análise → Persistência (sequencial)
- **Pipeline por FII**: Processa até 10 relatórios, do mais antigo ao mais novo
- **Deduplicação**: Verifica hash SHA256 para não reprocessar relatórios iguais
- **Detecção de novos**: Só analisa relatórios novos (não re-analisa existentes)
- **Estado "analisando"**: Rastreamento in-memory de FIIs em processamento
- **Timeout configurável**: `OLLAMA_TIMEOUT` (default 300s por chamada)

#### Extração de Indicadores
- `PDFExtractor.extrair_indicadores()`: Regex para indicadores brasileiros (vacância física/financeira, DY, P/VP, inadimplência, etc.)
- Extração de texto de PDFs via biblioteca Python

#### Análise com IA (Ollama)
- **Modelo**: `qwen2.5` (local, gratuito)
- **Prompt estruturado**: JSON com 15+ campos de análise
- **Pipeline de Critérios (Pente Fino)** — 5 categorias com pesos:
  | Critério | Peso | Sub-itens |
  |---|---|---|
  | Geração de Renda | 30% | DY, consistência, cobertura |
  | Qualidade do Portfólio | 25% | Vacância, inadimplência, diversificação |
  | Saúde Financeira | 20% | Crescimento PL, P/VP, liquidez |
  | Gestão e Governança | 15% | Transparência, conformidade, track record |
  | Perspectivas | 10% | Setor, cotistas, eventos |
- **Score final**: Média ponderada dos 5 critérios
- **Diário de Bordo**: Contexto cumulativo — cada análise recebe o resumo das anteriores
- **Análise Comentada**: Explicação em português claro para investidores
- **Dimensões para Radar**: Rentabilidade, Vacância, Crescimento, Liquidez, Governança
- **Conformidade com Política**: Verifica se o fundo segue sua política declarada
- **Recomendação de Ação**: `CONTINUE_COMPRANDO` / `MANTER_MONITORAR` / `PARE_REQUER_ANALISE`
- `temperature: 0.1` para respostas consistentes, `num_predict: 8192`

#### Banco de Dados (Modelos SQLAlchemy)
- **FII**: ticker, nome, CNPJ, política do fundo, regulamento_url
- **Relatorio**: FK → FII, url, hash_sha256 (unique), data_publicacao, texto_extraido, caminho_pdf
- **Analise**: FK → Relatorio + FII, resumo_executivo, o_que_mudou, score_saude, nivel_atencao, indicadores_encontrados (JSON), analise_comentada, diario_bordo, recomendacao_acompanhamento, pontos_positivos/negativos, riscos, oportunidades, conformidade_politica, etc.
- **Alerta**: FK → FII, tipo, mensagem, enviado

#### API REST (FastAPI)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Dashboard HTML |
| GET | `/api/dashboard` | Agregado: FIIs + última análise + status processamento |
| POST | `/fiis/` | Cadastrar FII (CNPJ auto) |
| GET | `/fiis/` | Listar FIIs |
| GET | `/fiis/{ticker}` | Detalhes do FII |
| PATCH | `/fiis/{ticker}` | Atualizar FII |
| DELETE | `/fiis/{ticker}` | Remover FII |
| GET | `/fiis/{ticker}/analises` | Listar análises |
| GET | `/fiis/{ticker}/analises/ultima` | Última análise completa |
| GET | `/fiis/{ticker}/score-history` | Histórico de scores para gráfico |
| GET | `/fiis/{ticker}/relatorios` | Listar relatórios |
| POST | `/pipeline/{ticker}` | Executar pipeline para 1 FII |
| POST | `/pipeline/todos` | Executar para todos FIIs |
| POST | `/pipeline/reanalisar/{ticker}` | Forçar re-análise do último relatório |
| GET | `/api/buscar-cnpj/{ticker}` | Buscar CNPJ via StatusInvest |

#### Frontend (HTML/Chart.js)
- **Abas**: Carteira, Em Andamento, Relatórios, Adicionar FII, Pipeline
- **Cards na Carteira**:
  - Score + nível (VERDE/AMARELO/VERMELHO)
  - Sparkline da evolução do score
  - Botões: "Ver Análise", "Analisar Agora", "Re-analisar", "Relatórios"
  - Status "Analisando..." com pulsação azul e botão desabilitado
- **Filtro**: Todos / Analisados / Pendentes / Em Análise
- **StatusBar**: Total FIIs, com análise, em atenção, em análise
- **Modal de Detalhes**:
  - Score grande + nível
  - Recomendação em destaque (verde/amarelo/vermelho)
  - Seção "Em Português Claro" (azul)
  - Tabela de Critérios (Pente Fino) com scores, pesos, contribuição
  - Radar Chart (5 dimensões)
  - Line Chart (evolução do score)
  - Resumo executivo, o que mudou, tendências, eventos
  - Pontos positivos/negativos, riscos, oportunidades
  - Diário de Bordo (timeline completa)
- **Indicador de processamento**: Spinner + desabilita botões durante análise
- **Auto-refresh**: A cada 5s se houver FIIs em análise
- **Layout responsivo**: Grid adaptável

#### Scheduler
- APScheduler configurado (desativado por enquanto)
- Job diário de pipeline para todos FIIs

---

### 🔄 Em Andamento / Precisa de Ajuste

| Item | Descrição | Prioridade |
|---|---|---|
| **Scheduler automático** | Job diário desativado; precisa ser habilitado e testado | Baixa |
| **Testes** | 7 testes unitários (`pytest backend/tests/`) — cobrem API e CRUD, mas pipeline e IA não têm teste | Média |
| **Logging** | Pipeline e IA com logging básico; pode melhorar para estruturação | Baixa |
| **PDFs** | Coleta de PDFs via B3/relatoriosfiis funciona, mas CVM é a fonte principal (estruturada) | Baixa |

---

### ❌ Não Implementado (Próximos Passos)

#### Para Comercialização (MVP)
| Item | Descrição | Esforço |
|---|---|---|
| **Autenticação de Usuários** | Modelo `User` + JWT + login/senha | 2-3 dias |
| **Carteira por Usuário** | Tabela `UserFIIs` (quais FIIs cada um segue) | 1 dia |
| **Trocar SQLite → PostgreSQL** | Apenas mudar a connection string no `.env` | 1 hora |
| **Planos / Limites** | Gratuito vs Premium (limite de FIIs por usuário) | 2 dias |

#### Funcionalidades
| Item | Descrição | Esforço |
|---|---|---|
| **Alertas (Telegram/Email)** | Notificar quando score cai, nível muda, novo relatório | 2 dias |
| **Comparação entre FIIs** | Ranking da carteira, melhor vs pior | 1 dia |
| **Checklist de Saúde** | "7 de 10 indicadores saudáveis" | 1 dia |
| **Exportar Análise (PDF)** | Gerar PDF com a análise completa | 2 dias |
| **Histórico de Decisões** | Log das recomendações com data; "comprei em X, o que mudou?" | 1 dia |
| **API Pública** | Endpoints acessíveis via chave de API para integrações | 2 dias |

#### Melhorias na IA
| Item | Descrição | Esforço |
|---|---|---|
| **Modelo maior** | Testar com `qwen2.5:14b` ou `llama3` para análises mais profundas | 1 dia |
| **Cache de respostas** | Se mesmo relatório for analisado de novo, usar cache | 1 dia |
| **Finetuning** | Treinar modelo pequeno com exemplos de análises de FIIs | 1 semana |

---

## Como Rodar

```bash
# 1. Ollama (janela separada)
ollama serve

# 2. API + Frontend
cd analisa-fiis
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 3. Abrir
http://localhost:8000
```

## Pipeline Completo (tempos estimados)

| Qtde Relatórios | Tempo total | Por relatório |
|---|---|---|
| 2 (dev, default) | ~2.5 min | ~75s |
| 10 (produção) | ~12 min | ~75s |

## Variáveis de Ambiente (`.env`)

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5
OLLAMA_TIMEOUT=300
DATABASE_URL=sqlite:///./data/database.db   # trocar para postgresql://... em produção
```

---

## Estrutura de Arquivos

```
analisa-fiis/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI app + endpoints
│       ├── models.py            # SQLAlchemy models
│       ├── schemas.py           # Pydantic schemas
│       ├── crud.py              # Database operations
│       ├── database.py          # Engine + session
│       ├── pipeline.py          # Pipeline orquestrador
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract collector
│       │   ├── cvm.py           # CVM collector + TickerMapper
│       │   ├── b3_funds.py      # B3/Fundos.NET collector
│       │   ├── relatoriosfiis.py # relatoriosfiis.com.br scraper
│       │   └── orchestrator.py  # Priority fallback logic
│       ├── extractors/
│       │   ├── __init__.py
│       │   └── pdf_extractor.py # PDF text + indicator extraction
│       ├── analyzers/
│       │   ├── __init__.py
│       │   └── ia_analyzer.py   # Ollama prompt + parser
│       ├── scheduler/
│       │   ├── __init__.py
│       │   └── cron.py          # APScheduler config
│       └── tests/
│           ├── __init__.py
│           ├── test_api.py
│           └── test_crud.py
├── frontend/
│   └── index.html               # SPA dashboard (Chart.js)
├── data/
│   ├── database.db              # SQLite
│   └── pdfs/                    # PDFs baixados
├── instructions.md              # Especificação original
├── README.md
├── .env.example
├── run.py
└── run_api.py
```

---

## Observações Técnicas

- **Windows**: PowerShell tem problemas com caracteres especiais em `python -c`. Prefira scripts `.py` ou use `cmd`.
- **Ollama**: `qwen2.5` ~4GB de RAM. Modelos maiores precisam de mais memória.
- **CVM**: Fonte principal gratuita sem rate limit. Dados desde ~2023.
- **Hash**: `hash_sha256` é calculado sobre o conteúdo + url do relatório para deduplicação.

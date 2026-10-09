# BeautyFlow

Plataforma de gestão para salões, clínicas de estética e profissionais autônomos. O projeto centraliza agenda, clientes, serviços, campanhas e apoio ao atendimento em uma única aplicação.

## Visão do produto

Negócios de beleza costumam distribuir informações entre agenda, mensagens, planilhas e anotações. O BeautyFlow reúne esses dados e transforma tarefas do dia a dia em fluxos organizados.

## Funcionalidades

- dashboard com clientes, agenda, receita e ticket médio;
- cadastro e manutenção de clientes e serviços;
- agenda com criação de horários e atualização de status;
- recomendação de serviços conforme o perfil da cliente;
- apoio à criação de mensagens e campanhas;
- simulação de atendimento e agendamento por WhatsApp;
- API documentada automaticamente;
- testes dos principais fluxos da aplicação.

## Arquitetura

```mermaid
flowchart LR
    UI[Interface Streamlit] --> API[API FastAPI]
    API --> DB[(SQLite)]
    API --> REC[Recomendação]
    API --> MSG[Atendimento e campanhas]
```

## Tecnologias

`Python` `FastAPI` `Streamlit` `SQLModel` `SQLite` `Pandas` `Pytest` `HTTPX`

## Executar localmente

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

No Linux ou macOS:

```bash
source .venv/bin/activate
```

Instale as dependências e prepare os dados:

```bash
pip install -r requirements.txt
python seed.py
```

Inicie a API:

```bash
python -m uvicorn app.main:app --reload
```

Em outro terminal, inicie a interface:

```bash
python -m streamlit run frontend/streamlit_app.py
```

- Aplicação: `http://localhost:8501`
- Documentação da API: `http://127.0.0.1:8000/docs`

## Estrutura

```text
app/             API, banco, serviços e recomendação
frontend/        interface e páginas da aplicação
data/            dados demonstrativos
knowledge_base/  conteúdo de apoio
docs/            documentação do produto
tests/           testes automatizados
```

## Testes

```bash
python -m compileall app frontend tests seed.py
pytest -q
```

Os testes usam um banco SQLite isolado e cobrem saúde da API, agendamentos,
disponibilidade, proteção de acesso, CRM, ferramentas de agente e chamadas LLM
simuladas em testes.

## Status real e como utilizar

A branch `main` contém o MVP local. Para iniciar:

1. Clone o repositório e siga as instruções de instalação acima.
2. Rode `python seed.py` apenas para carregar dados de demonstração.
3. Inicie o FastAPI e o Streamlit em terminais separados.
4. Acesse `http://localhost:8501`.

O login disponibilizado na interface é **somente demonstrativo**, com
credenciais públicas no código; não fornece autenticação segura.
Não use dados pessoais reais nem publique esta versão diretamente na Internet.

O assistente de texto usa um LLM real **somente** quando `OPENAI_API_KEY`
está configurada no backend. Sem chave, o endpoint retorna erro explicativo.
As ações determinísticas do agente são disponibilizadas pela API, com tokens
temporários de confirmação, mas ainda não são chamadas autonomamente pelo LLM.

O WhatsApp é uma **simulação local**: não envia mensagens reais.
PostgreSQL, autenticação multiusuário, migrações de esquema, HTTPS, hospedagem,
verificação de acesso e integração oficial com WhatsApp ainda precisam
ser concluídos antes de um lançamento público.

Consulte `docs/` para o contrato das ferramentas e a configuração da API.

## Roadmap

- autenticação multiusuário e RBAC com controle de acesso na API;
- migrações Alembic e PostgreSQL em ambiente implantado;
- orquestração de LLM com ferramentas de leitura e confirmação de ações;
- integração WhatsApp Cloud API com webhooks e opt-in;
- deploy seguro com observabilidade, backups e política de privacidade.

## Autoria

[Geovanna Eduarda da Silva](https://github.com/geovannasilva15)

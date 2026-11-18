# BeautyFlow AI

Painel para salões, clínicas de estética e profissionais autônomos. Reúne clientes, serviços, profissionais, agenda, indicadores e atendimento.

- A equipe entra com contas individuais de administrador ou profissional. Cada instalação usa um banco exclusivo para um negócio.
- A agenda consulta disponibilidade e permite criar, editar, cancelar e reagendar atendimentos. O dashboard usa os registros do banco.
- A Mentora de IA usa OpenAI quando configurada. Preços, clientes e horários são consultados em **Dados do sistema**. Ações assistidas exigem revisão e confirmação.
- O WhatsApp tem uma caixa de entrada para números de teste. A equipe responde pelo painel e trata pedidos de agendamento na Agenda. Campanhas e modelos de texto são recursos locais.

## Instalação local

Use Python 3.12. Na raiz do repositório, crie o ambiente virtual.

```bash
python -m venv .venv
```

No PowerShell, ative com `.\.venv\Scripts\Activate.ps1`. No Linux ou macOS, use `source .venv/bin/activate`. Copie `.env.example` para `.env` se precisar mudar as configurações locais.

Com uma base nova, instale e prepare o banco.

```bash
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.manage_accounts bootstrap
```

Digite o nome, e-mail e senha no terminal interativo. A senha precisa ter entre 16 e 128 caracteres. Se já houver uma base local, faça backup e consulte a seção de bases existentes no [guia de implantação](docs/DEPLOY_RENDER.md).

Em dois terminais com o ambiente virtual ativo, inicie a API e o painel.

```bash
python -m uvicorn app.main:app --reload
```

```bash
python -m streamlit run frontend/streamlit_app.py
```

Entre em `http://localhost:8501` com a conta criada. Use **Minha conta** para cadastrar a equipe. Cada integrante troca a senha inicial no primeiro acesso.

Para um ambiente local descartável, `python seed.py` carrega dados fictícios. Use um arquivo SQLite dedicado e aplique as migrações antes de executar o comando.

## Testes

```bash
python -m compileall -q app frontend migrations tests seed.py
python -m pytest -q
```

Para incluir os testes de migração com PostgreSQL real, defina `TEST_POSTGRES_URL` com a URL de um banco descartável no qual a conta possa criar schemas. O GitHub Actions inicia um PostgreSQL para esses testes. As chamadas à OpenAI e à Meta são simuladas pela suíte.

## Publicação e operação

O [guia do Render](docs/DEPLOY_RENDER.md) detalha os serviços, configuração, custos, criação da conta inicial, migração de bancos existentes, backup e teste de restauração. O Blueprint usa PostgreSQL. `/healthz` verifica a conexão e as tabelas da API.

- [Contas, sessões e permissões](docs/PLATFORM_SETUP.md)
- [Mentora OpenAI e tratamento de falhas](docs/LLM_ASSISTANT.md)
- [Ferramentas de consulta e confirmação](docs/AGENT_TOOLS.md)
- [WhatsApp Cloud API em ambiente de teste](docs/WHATSAPP_CLOUD.md)

O piloto usa dados fictícios. Antes de atender clientes reais, valide o ambiente hospedado, os backups, os controles de privacidade e as integrações com as contas oficiais. A recuperação de senha é feita pelo operador da instalação. O WhatsApp exige atendimento humano, número de teste e destinatários autorizados.

## Autoria

[Geovanna Eduarda da Silva](https://github.com/geovannasilva15)

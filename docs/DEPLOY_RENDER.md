# Publicação do aplicativo BeautyFlow no Render

Este blueprint prepara dois serviços web e PostgreSQL persistente:

- `beautyflow-web`: interface Streamlit;
- `beautyflow-api`: backend FastAPI;
- `beautyflow-db`: armazenamento PostgreSQL.

**Não é um deploy já realizado.** Conecte o repositório GitHub ao Render,
selecione Blueprint e escolha `render.yaml`. O Render criará recursos
que podem gerar cobranças. Confira os valores antes de aprovar.

## Configuração obrigatória

Defina `APP_LOGIN_EMAIL` e `APP_LOGIN_PASSWORD` (senha aleatória com
pelo menos 16 caracteres) no serviço web; não os coloque no GitHub.
O backend exige `API_ACCESS_TOKEN` em produção: o blueprint cria o segredo
e o encaminha ao servidor web.
A variável `OPENAI_API_KEY` é opcional; sem ela, a mentora LLM não responde.

**IMPORTANTE**: `API_URL` assume o endereço padrão
`https://beautyflow-api.onrender.com/api`. Confira o domínio real que o
Render atribuir. Se for diferente, corrija `API_URL` no serviço web.

## Segurança e limitações

O login em produção usa um único segredo configurado no ambiente e uma
sessão Streamlit; não é autenticação multiusuário ou RBAC.
Não cadastre informações reais ou sensíveis até existir autenticação robusta,
política de privacidade, backups, migrações e controles de autorização por usuário.
Não conecte WhatsApp real; o fluxo existente é simulado.

Ao implantar, confirme que `/api/health` retorna 200 autenticado e
teste manualmente cadastro, agenda e reagendamento antes de usar com clientes.

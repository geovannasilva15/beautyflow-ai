# Acesso de prévia privada

Em produção, o login de demonstração fica desabilitado. Para configurar um
administrador de prévia, execute `python generate_password_hash.py` em um
ambiente confiável. O programa solicita a senha sem mostrá-la e gera um hash.
Configure no serviço Streamlit `APP_ENV=production`, `APP_LOGIN_EMAIL` e
`APP_LOGIN_PASSWORD_HASH` com esse hash. Não salve a senha ou o hash no Git.
Configure também `API_ACCESS_TOKEN` no servidor da API e no Streamlit.

Esse acesso usa apenas um administrador compartilhado e a sessão Streamlit.
Ainda não oferece contas individuais, recuperação de senha, controle por
usuário na API, limitação de tentativas ou auditoria. Não é suficiente para
uso com dados reais ou lançamento público; essas etapas continuam pendentes.

# Preparação da prévia no Render

O Blueprint prepara API, painel e banco PostgreSQL. Isto não cria uma
implantação por si só. Os serviços e o banco podem gerar cobranças.
É necessário conectar o repositório ao Render e definir os segredos.

Gere o hash com `python generate_password_hash.py` e configure
`APP_LOGIN_EMAIL` e `APP_LOGIN_PASSWORD_HASH` no serviço web. Configure
`API_URL` para o endereço HTTPS real da API, seguido de `/api`, sem barra
final. O Blueprint compartilha `API_ACCESS_TOKEN` entre os serviços.
Configure `OPENAI_API_KEY` apenas se quiser ativar o assistente de texto.

A API executa `alembic upgrade head` na inicialização e só inicia caso a
migração seja concluída. A primeira migração foi feita para um banco vazio.
Não a execute em um banco já existente: faça backup e revise o esquema antes
de planejar a adoção de migrações. Não use `alembic stamp` sem conferir
que tabelas, colunas e índices correspondem ao esquema inicial.

Após implantar, confirme o endereço da API, o login e os fluxos com dados
fictícios. Esta é uma prévia privada, sem autenticação multiusuário,
autorização individual na API, limitação de tentativas e backups configurados.
Não é adequada para dados reais ou lançamento público. WhatsApp é simulado.

# Piloto no Render

O Blueprint usa dois serviços web e uma instância PostgreSQL. A API fica acessível por HTTPS para o painel e para o webhook da Meta. O banco aceita conexões pela rede interna do Render. O Blueprint mantém atualizações automáticas desligadas para que cada implantação seja deliberada.

Os preços de referência são US$ 7/mês para cada serviço web de 512 MB e US$ 6/mês para o plano PostgreSQL de 256 MB. Confirme o total, armazenamento, uso e encargos no painel antes de aplicar o Blueprint. OpenAI e Meta têm cobrança própria. [Preços do Render](https://render.com/pricing)

## Criar um ambiente novo

1. Entre no Render e conecte o repositório do GitHub. Escolha **New → Blueprint** e selecione a branch aprovada para o piloto. Confira os três recursos e os preços antes de aplicar.
2. Informe em `API_URL` o endereço HTTPS do serviço FastAPI seguido de `/api`. Se o endereço só aparecer depois da criação do serviço, atualize a variável em **Environment** do serviço web e faça o deploy dele.
3. Aguarde a migração e consulte `https://<endereço-da-api>/healthz`. O serviço usa o comando de pré-implantação para aplicar Alembic. A API retorna HTTP 503 se o banco ou as tabelas verificadas estiverem indisponíveis.
4. Na aba **Shell** do serviço da API, execute `python -m app.manage_accounts bootstrap`. Informe a primeira conta em terminal interativo. Use as variáveis gerenciadas do Render e mantenha a conexão PostgreSQL restrita à rede interna.
5. Abra a URL HTTPS do serviço web, entre com a conta inicial e crie um usuário profissional. Com dados fictícios, teste o cadastro e a edição de uma cliente, serviço e profissional, conflito de agenda, calendário, reagendamento, cancelamento, dashboard e saída. Repita o login e a navegação no celular. Como profissional, verifique o acesso à agenda e a restrição de criação de contas.
6. Se desejar validar a Mentora, inclua `OPENAI_API_KEY` somente no serviço da API e teste com contexto fictício. Para o WhatsApp, siga o [guia de testes da Meta](WHATSAPP_CLOUD.md).

Use **Manual Deploy** após revisar alterações e resultados da CI. Se configurar `BUSINESS_TIMEZONE`, use o mesmo valor na API e na interface. Os horários de abertura, fechamento e intervalo ficam no ambiente da API.

## Banco existente e migrações

1. Confirme qual banco e esquema a aplicação usa, suspenda as escritas e salve um backup verificável. Restaure em um banco novo para ensaiar o procedimento.
2. Verifique `python -m alembic current` na cópia. Se a base já tiver revisão, aplique `python -m alembic upgrade head` na cópia e compare contagens de registros, vínculos e amostras de agendamentos.
3. Para uma base antiga sem revisão, a primeira migração interrompe a execução ao encontrar tabelas existentes. Em um banco vazio de referência do mesmo tipo, rode `python -m alembic upgrade 91b31bc719f6`. Compare esquemas, incluindo tipos, chaves, índices, enums e timestamps. Confira também vínculos órfãos e sobreposições já cadastradas. Em PostgreSQL use `pg_dump --schema-only --no-owner --no-privileges` para facilitar a revisão.
4. Somente quando a estrutura e as convenções de dados coincidirem com a referência, registre `python -m alembic stamp 91b31bc719f6` na cópia. Aplique `python -m alembic upgrade head` e `python -m alembic check`. A migração guarda a duração vigente do serviço nas reservas antigas, conforme a regra anterior do sistema.
5. Use em produção apenas o procedimento ensaiado e autorizado. Uma base SQLite existente que precisa ser levada ao PostgreSQL exige uma transferência de dados revisada e ensaiada, além da migração de esquema. Estruturas divergentes exigem correção específica antes de registrar a revisão.

## Backup e teste de restauração

Ative e confira a janela de recuperação do PostgreSQL no Render. Gere também backups lógicos com uma rotina agendada, retenção documentada e armazenamento criptografado de acesso restrito. Teste a restauração periodicamente e antes de mudanças de esquema. [Backups e recuperação no Render](https://render.com/docs/postgresql-backups)

Exemplo em um host autorizado, com os parâmetros de conexão do PostgreSQL fornecidos pelo ambiente e a senha em um arquivo protegido indicado por `PGPASSFILE`. Para conexões de fora do Render, restrinja o acesso ao IP do operador e use TLS. Configure o destino em um ambiente isolado.

```bash
pg_dump --format=custom --file=beautyflow.backup
pg_restore --list beautyflow.backup
createdb beautyflow_restore
pg_restore --exit-on-error --no-owner --no-privileges --dbname=beautyflow_restore beautyflow.backup
```

Aponte `DATABASE_URL` para o banco restaurado. Confira `alembic current`, `alembic check`, contagens, clientes e agendamentos. Se uma cópia restaurada voltar a servir tráfego, revogue as sessões restauradas na tabela `loginsession` antes de liberar o acesso. Desative OpenAI e WhatsApp em cópias de recuperação. Registre a data e o resultado do teste.

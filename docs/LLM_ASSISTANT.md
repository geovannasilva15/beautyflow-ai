# Assistente LLM V1

Configure `OPENAI_API_KEY` **apenas no servidor** e, opcionalmente, `OPENAI_MODEL`.
O endpoint `POST /api/ai/chat` consulta o provedor real e retorna HTTP 503
quando a chave está ausente ou a chamada falha. Não há resposta falsa de IA.

Os testes usam provedor simulado e **não comprovam conectividade externa**.
Mensagens e contexto enviados à API são transmitidos ao provedor configurado:
evite dados pessoais sensíveis ou informações identificáveis de clientes.

Essa etapa é um assistente de texto, não um agente autônomo com tool-calling.
As ferramentas de agenda permanecem em `/api/agent/tools` e têm confirmação
em duas etapas. A orquestração segura entre LLM e ferramentas exige política de
autorização por usuário e implementação posterior.

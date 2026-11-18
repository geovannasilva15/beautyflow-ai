# Mentora OpenAI

Defina `OPENAI_API_KEY` somente na API. Use `OPENAI_MODEL` para escolher um modelo de chat disponível na sua conta. A aplicação envia o contexto e a pergunta que a pessoa digitou, com limite de tamanho e tempo de resposta, e retorna uma mensagem de indisponibilidade quando a configuração ou a chamada falha.

O chat oferece orientação geral de gestão. A equipe consulta preços, clientes e horários em **Dados do sistema**, com a sessão individual, e faz alterações de agenda por confirmações nessa mesma aba. O modelo recebe somente os campos informados no chat. Use exemplos fictícios. Os modelos de mensagem e campanha são textos baseados em regras.

O teste da API usa respostas simuladas. A validação externa exige uma chave ativa, acesso ao modelo e um teste com contexto fictício. [Referência da API OpenAI](https://platform.openai.com/docs/api-reference/chat)

# Consultas e operações assistidas

A aba **Dados do sistema** chama `POST /api/agent/tools` com a sessão da conta conectada. As ferramentas `list_services`, `find_client` e `availability` consultam registros do negócio.

Para `book`, `cancel` e `reschedule`, o primeiro pedido retorna um resumo e um `confirmation_token`. Confira cliente, serviço, profissional, valor e horário. O cliente envia os mesmos parâmetros, `confirm: true` e o token para executar.

O token é específico da conta, da ação e do resumo revisado. Ele dura dez minutos e só pode ser usado uma vez. A transação valida novamente o estado da agenda e grava a reserva e o consumo do token juntos. A Mentora OpenAI opera como chat de orientação sem chamadas a essas ferramentas.

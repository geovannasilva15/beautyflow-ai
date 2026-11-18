# WhatsApp Cloud API em teste

A caixa de entrada usa a API oficial da Meta. O piloto recebe mensagens de texto dos números autorizados e permite que um administrador responda manualmente. Pedidos de agendamento, cancelamento e reagendamento aparecem na caixa de entrada por categoria. A equipe combina os detalhes com a pessoa, confirma na Agenda e responde pelo painel.

## Configurar na API

1. Crie ou selecione um app Meta com WhatsApp, use o número de teste e registre os destinatários de teste. Consulte as permissões da lista e use apenas os números que autorizaram o teste.
2. Adicione as variáveis abaixo ao serviço da API. Guarde os tokens no gerenciador de segredos do serviço.

| Variável | O que informar |
| --- | --- |
| `WHATSAPP_TEST_MODE` | `true` |
| `WHATSAPP_APP_SECRET` | Segredo do app Meta para verificar a assinatura |
| `WHATSAPP_VERIFY_TOKEN` | Valor aleatório que você gera para verificar o callback |
| `WHATSAPP_ACCESS_TOKEN` | Token da conta de teste com permissão de envio |
| `WHATSAPP_PHONE_NUMBER_ID` | ID do número de teste |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | ID da conta WhatsApp Business de teste |
| `WHATSAPP_GRAPH_VERSION` | Versão da Graph API indicada no seu app Meta, no formato `vNN.N` |
| `WHATSAPP_TEST_RECIPIENTS` | Números de teste no formato internacional, só dígitos, separados por vírgulas |

3. No app Meta, configure o callback HTTPS `https://<endereço-da-api>/api/whatsapp/webhook`, informe o mesmo token de verificação e assine o campo `messages`. [Notificações de mensagens da Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages)
4. Envie uma mensagem fictícia do número autorizado. Em **Atendimento**, confirme que ela entrou uma vez. Use o formulário para revisar o destinatário, enviar a resposta e conferir a entrega no telefone de teste.

O webhook verifica a conta, o número, o remetente e a assinatura. Notificações repetidas reutilizam o registro anterior. O painel permite responder dentro da janela de atendimento, com margem de segurança. Aceitação pela Meta e entrega no telefone são etapas distintas. Se o resultado ficar incerto, confira o histórico no WhatsApp antes de outra tentativa. Testes automatizados substituem a Meta por respostas fictícias.

Para sair do piloto, será preciso aprovar e validar a conta oficial e revisar consentimento, gestão de dados, retenção e eventuais modelos de mensagem. O fluxo atual usa a lista de números de teste, texto recebido e resposta manual.

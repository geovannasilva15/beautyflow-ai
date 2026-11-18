# Contas e operação

Cada instalação atende a um negócio. Use banco, credenciais e serviços de hospedagem separados para cada negócio. Administrador e profissional da mesma equipe compartilham os dados operacionais dessa instalação.

| Operação | Administrador | Profissional |
| --- | --- | --- |
| Clientes, agenda, dashboard e ferramentas de consulta | Sim | Sim |
| Cadastro e atualização de clientes e agenda | Sim | Sim |
| Exclusão de cadastro de cliente sem histórico vinculado | Sim | |
| Cadastro, edição e desativação de serviços e profissionais da agenda | Sim | |
| Cadastro e desativação de contas e caixa de entrada do WhatsApp | Sim | |

O perfil de acesso profissional representa um membro da equipe. O cadastro de profissionais da agenda define quem oferece horários.

O primeiro administrador é criado no terminal da API com `python -m app.manage_accounts bootstrap`. Depois, a área **Minha conta** cria e desativa contas da equipe. Senhas temporárias devem ser comunicadas por um canal seguro. O sistema exige a troca no primeiro acesso.

A senha usa scrypt com salt individual. A API armazena somente o hash dos tokens aleatórios de sessão. Os tokens duram até oito horas, ficam no servidor Streamlit e são revogados ao sair, trocar senha ou desativar a conta. Todas as operações com dados verificam a sessão. O login tem limites persistentes por e-mail e para a instalação. A implantação usa HTTPS no navegador e entre o painel e a API.

Para recuperar o acesso, execute `python -m app.manage_accounts reset-password` em terminal interativo no host da API. Confirme a identidade da pessoa antes de definir uma senha temporária. Sessões antigas serão revogadas e a pessoa precisará trocar a senha ao entrar. Recuperação por e-mail exigiria um serviço de envio, validação de identidade e links de uso único. A CLI cobre o piloto.

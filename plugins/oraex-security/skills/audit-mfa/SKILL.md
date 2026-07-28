---
name: audit-mfa
description: Audita se o segundo fator (MFA/2FA/TOTP) é realmente exigido pelo servidor ou apenas sugerido pela interface. Procura a falha em que o controle de acesso pergunta "o usuário POSSUI um fator?" quando deveria perguntar "ESTA SESSÃO completou o fator?" — o que permite entrar só com a senha, ignorando a tela do código. Use quando o usuário pedir para auditar MFA/2FA/TOTP, verificar bypass de segundo fator, revisar AAL/step-up/re-autenticação, checar recovery codes, ou investigar lockout de quem perdeu o autenticador.
disallowed-tools: Edit, Write, NotebookEdit
---

# Auditoria: o segundo fator é realmente exigido?

Audite o repositório atual procurando **uma falha específica de MFA**, e só
ela. Não faça revisão geral de segurança — escopo estreito é o que torna esta
auditoria confiável.

Funciona em qualquer stack. As pistas de Supabase/Next abaixo são atalhos,
não pré-requisito.

## A falha

Sistemas com MFA costumam confundir duas perguntas diferentes:

- **A:** "este usuário *possui* um segundo fator cadastrado?"
- **B:** "*esta sessão* completou o segundo fator?"

A resposta de **A** vem de uma tabela de cadastro (o fator existe). A de **B**
vem do nível da sessão corrente (AAL2 / `amr` / claim equivalente).

Quando o controle de acesso pergunta **A** achando que está perguntando **B**,
o MFA vira decorativo: quem tem a senha entra sem nunca digitar o código. O
padrão que torna isso explorável é quase sempre o mesmo:

1. A etapa de senha **já grava a sessão** (cookie/JWT) antes da verificação
   do segundo fator;
2. A UI então mostra a tela do código, confiando que o usuário vai segui-la;
3. Nenhuma checagem no servidor recusa uma sessão que parou no passo 1.

Resultado: basta ignorar a tela do código e navegar direto para uma rota
protegida.

## Procedimento

Trabalhe por evidência: cite sempre `arquivo:linha` e **cole o trecho real**.
Se algo não existir, diga "não existe" — não presuma nem preencha lacunas.

### 1. Mapeie o caminho de login

Encontre onde a senha é verificada. Responda com precisão:

- **Em que momento exato a sessão passa a existir** (cookie setado, JWT
  emitido, registro de sessão criado)? É **antes** ou **depois** da
  verificação do segundo fator?
- Se for antes: essa sessão intermediária é **distinguível** de uma completa?
  (flag `mfa_pending`, cookie separado, escopo reduzido, TTL curto, claim de
  nível.) Ou é a mesma sessão de sempre?
- A decisão de exigir o segundo fator acontece **no servidor** ou é a UI que
  decide qual tela mostrar com base num valor de retorno?

### 2. Liste TODOS os pontos de controle de acesso

Middleware/proxy, guards de rota, layouts de área logada, decorators,
`before_action`, resolvers de API, server actions, route handlers, jobs
expostos por HTTP.

Para **cada um**, responda: ele checa **A** ou **B**?

Sinais de que está checando **A** (o problema):

- consulta a tabela de fatores/dispositivos cadastrados
  (ex.: `auth.mfa_factors`, `mfa_devices`, `user.totp_secret IS NOT NULL`)
- campo booleano do usuário: `hasMfa`, `mfa_enabled`, `two_factor_enabled`
- qualquer coisa derivada do **usuário**, não da **sessão**

Sinais de que está checando **B** (o correto):

- `getAuthenticatorAssuranceLevel()`, comparação `currentLevel`/`nextLevel`
- claim `aal`/`acr`/`amr` lido do token da sessão
- flag na própria sessão marcada só **após** a verificação do código

### 3. Procure o buraco entre autenticar e autorizar

- Existe rota protegida **fora** do alcance do middleware/guard? Confira o
  `matcher`/padrão de rotas: o que ele deixa de fora?
- Requests não-GET (Server Actions, POST de API) são dispensados do guard?
  Se sim, quem valida a sessão nesses caminhos?
- APIs/webhooks/rotas de arquivo aplicam a mesma regra das páginas?

### 4. Verifique os fluxos vizinhos (mesma classe de falha)

- **Troca de senha / e-mail**, exclusão de conta, gestão de chaves de API:
  exigem re-autenticação ou step-up? Ou bastam os cookies atuais?
- **Desativar o MFA**: quem consegue? Exige o segundo fator *antes* de
  desativar? Um atacante com sessão AAL1 consegue desligar o MFA?
- **Reset de senha por e-mail**: a sessão que nasce do link é AAL1? Ela
  contorna o MFA?
- **Recovery codes / códigos de backup**: existem? São de fato **consumidos**
  em algum caminho de código, ou só gerados e exibidos? Prove por grep se o
  campo de "usado" (`used_at` ou equivalente) é escrito em algum lugar.
- **Convites / OAuth / magic link**: entram por caminho que pula o MFA?

### 5. Perda de dispositivo

- Existe algum modo de um usuário que perdeu o autenticador voltar a entrar?
- Existe reset por administrador? Script de suporte? Runbook documentado?
- Se a resposta for "não" para todos: registre como **lockout**, e diga
  quais papéis ficam presos.

## Prove antes de afirmar

Se encontrar o bypass, tente confirmá-lo empiricamente. Suba o projeto local
com uma conta de teste com MFA ativo e:

1. Faça só a etapa de senha (via a action/endpoint de login, sem completar o
   código).
2. Capture os cookies/token que a resposta gravou.
3. Com esses cookies, requisite uma rota protegida.
4. `200` = bypass confirmado. Redirect para a tela de código = está correto.

Se não conseguir executar, **diga isso explicitamente** e classifique o
achado como leitura de código, não como exploração confirmada.

## Formato da resposta

Para cada achado:

- **Veredito:** `CONFIRMADO (executado)` · `PROVÁVEL (só leitura)` · `CORRETO`
- **Onde:** `arquivo:linha` + o trecho real
- **Cenário concreto:** quem faz o quê, e o que consegue indevidamente
- **Papéis/rotas afetados**
- **Correção mínima:** o menor diff que fecha o buraco

Encerre com um veredito de uma linha: **o segundo fator deste sistema é
obrigatório de fato, ou apenas sugerido pela interface?**

## Regras

- **Não altere nenhum arquivo.** Isto é auditoria; a correção vem depois, em
  decisão separada.
- Não relate achado sem `arquivo:linha`.
- Se a checagem estiver correta, **diga que está correta** — vale tanto
  quanto encontrar problema. Não invente achado para parecer produtivo.
- Distinga com clareza o que você **executou** do que você **leu**.

# Setup per-dev no AWS Secrets Manager (SSO)

Cada desenvolvedor faz isto **uma vez**. O `.mcp.json` do projeto é idêntico
para todos; o que individualiza é o `ORAEX_DEV_ID` e os segredos abaixo.

## 1. Criar os segredos do dev

Só precisam de segredo os MCPs que **exigem token** — Supabase usa OAuth (sem
segredo) e AWS usa a sessão SSO. Hoje isso é o **PAT do GitHub** (e qualquer MCP
stdio só-token que você adicione depois, no padrão `asm-exec`).

O **próprio dev** roda no terminal (o valor da chave é dele; não passe por mim).
No Claude Code, use o prefixo `!` para rodar na sessão.

```bash
# GitHub — PAT
aws secretsmanager create-secret \
  --name "oraex/dev/$ORAEX_DEV_ID/mcp/github" \
  --secret-string '{"token":"SEU_PAT_AQUI"}'
```

Para rotacionar: `put-secret-value` com o mesmo `--name`. O `.envrc` puxa esse
valor para `GITHUB_PAT` a cada shell (skill `env-conventions`).

> Nunca use `get-secret-value` para "conferir" — isso traz a chave para o
> contexto. Confira o funcionamento por `/mcp` (deve conectar).

## 2. IAM que se auto-escopa por dev (verificado contra a doc)

Com SSO (Identity Center / role assumida), `${aws:username}` **não** existe. O
escopo por dev usa a **session tag** `DevId` que o Identity Center passa, e que
a policy referencia como `${aws:PrincipalTag/DevId}`. Uma única policy serve
para todos. Duas formas válidas — escolha uma.

### Forma A — variável no ARN do Resource (recomendada aqui)

O `DevId` entra no próprio caminho do ARN; não precisa tagear o segredo:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadOwnMcpSecrets",
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:oraex/dev/${aws:PrincipalTag/DevId}/mcp/*"
  }]
}
```

- **Confirmado:** a linguagem de policy aceita variável no elemento `Resource`,
  inclusive `${aws:PrincipalTag/...}`. Se o dev não tiver a tag `DevId`, o ARN
  não casa com nada → **nega por padrão** (fail-closed).¹
- O `*` final cobre o hífen + 6 caracteres aleatórios que o Secrets Manager
  acrescenta ao ARN.² O **nome** do segredo é a fronteira — daí a disciplina de
  criar sempre em `oraex/dev/<id>/mcp/…`.

### Forma B — condição por tag (ABAC canônico do Secrets Manager)

Se preferir enforcement por **tag** e não por nome, o padrão oficial compara a
tag do recurso com a do principal:³

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadOwnMcpSecrets",
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:oraex/dev/*/mcp/*",
    "Condition": {
      "StringEquals": { "aws:ResourceTag/DevId": "${aws:PrincipalTag/DevId}" }
    }
  }]
}
```

Exige tagear cada segredo na criação (`--tags Key=DevId,Value=$ORAEX_DEV_ID`) e,
idealmente, um SCP que impeça alterar a tag `DevId` depois de posta.³

### Mapear `DevId` como session tag no Identity Center

Ambas as formas dependem de a tag chegar na sessão. No console do Identity
Center: **Settings → Attributes for access control → Add attribute**.⁴

- **Key**: `DevId` (o nome exato usado na policy)
- **Value**: o atributo da fonte de identidade que dá o id do dev
  (ex.: `${path:userName}` — confirme o atributo certo da sua fonte)

Atributo **single-value** — o Identity Center não suporta multi-value para
ABAC.⁴ O valor mapeado aqui é o mesmo que vai no `.envrc` como `ORAEX_DEV_ID`.

---

¹ [AWS Security Blog — PassRole com variável no Resource](https://aws.amazon.com/blogs/security/how-to-use-the-passrole-permission-with-iam-roles/) (variável no `Resource` + fail-closed)
² [Secrets Manager User Guide — Identity-based policies](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_iam-policies.html) (sufixo de 6 caracteres)
³ [Secrets Manager User Guide — ABAC](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access-abac.html) · [Scale ABAC with Identity Center](https://aws.amazon.com/blogs/security/scale-your-authorization-needs-for-secrets-manager-using-abac-with-iam-identity-center/) (guardrail de tag)
⁴ [IAM Identity Center — Attributes for access control](https://docs.aws.amazon.com/singlesignon/latest/userguide/attributesforaccesscontrol.html) · [Select your attributes](https://docs.aws.amazon.com/singlesignon/latest/userguide/configure-abac-attributes.html)

## 3. Sessão

`asm-exec` resolve o `{{resolve:...}}` assinando o endpoint MCP com as
credenciais da sessão SSO. Então, antes de abrir o Claude Code:

```bash
aws sso login --profile <SEU_PROFILE>
```

`AWS_PROFILE` e `AWS_REGION` vêm do `.envrc` (skill `env-conventions`).

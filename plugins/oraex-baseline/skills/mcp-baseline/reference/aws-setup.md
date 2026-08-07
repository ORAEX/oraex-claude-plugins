# Setup per-dev de segredos MCP — AWS SSM Parameter Store + ABAC (Identity Center)

Runbook **validado de ponta a ponta** para entregar segredos de MCP (ex.: PAT do
GitHub) por desenvolvedor, com isolamento real: cada dev lê só o próprio
parâmetro, provado por `AccessDenied` no alheio.

Modelo: o PAT é **env-sourced** (vai para `${GITHUB_PAT}` via `.envrc`), guardado
em **Parameter Store `SecureString`** (grátis no tier padrão), e o isolamento
per-dev sai de **ABAC tag-based** + um **permission set dedicado**. Secrets
Manager + `asm-exec` seguem válidos para o outro padrão (resolução em runtime,
segredo nunca no env) — ver o fim deste doc.

> **Por que Parameter Store e não Secrets Manager:** como o GitHub remoto pede o
> PAT como header (`${GITHUB_PAT}`), o segredo já vive no env de qualquer forma —
> então não precisamos da resolução em runtime do `asm-exec`. Parameter Store faz
> o mesmo mais barato. Ressalva: o hook do `aws-core` bloqueia `get-secret-value`,
> **não** `ssm get-parameter --with-decryption` — logo, não rode esse comando você
> mesmo; deixe o `.envrc` puxar direto para a variável.

## Valores da sua conta (preencha)

| Placeholder | O que é |
|---|---|
| `<INSTANCE_ARN>` | ARN da instância do Identity Center (`arn:aws:sso:::instance/ssoins-…`) |
| `<IDENTITY_STORE_ID>` | Identity Store (`d-…`) |
| `<REGION>` | região do Identity Center e dos parâmetros (ex.: `sa-east-1`) |
| `<DEV_ACCOUNT>` | conta AWS onde os parâmetros vivem e o permission set é atribuído |
| `<MGMT_PROFILE>` | profile SSO admin na conta de **gestão** (opera Identity Center/permission sets) |
| `<DEV_PROFILE>` | profile SSO do `AWSDeveloperAccess` na `<DEV_ACCOUNT>` (não-admin) |
| `<DEV_ID>` | `userName` do dev no Identity Center (na ORAEX, o **e-mail**) → vira a tag `DevId` |
| `<HANDLE>` | id curto **sem `@`** do dev (ex.: `athos.joao`) → compõe o **nome** do parâmetro |

> **Dois identificadores, de propósito:** o nome do parâmetro SSM **não aceita `@`**
> (`a-zA-Z0-9_.-/` apenas), então o **nome** usa `<HANDLE>`; já a **tag** `DevId` e
> a session tag usam o `<DEV_ID>` (e-mail), que é o que a ABAC emite de `userName`.
> A autorização é por **tag**, então o `@` no e-mail não é problema.

## ⚠️ Pegadinhas (cada uma nos custou um ciclo)

1. **`--region` explícito** em toda chamada `sso-admin`/`ssm`/`identitystore` — a
   resolução por profile falha com `NoRegion` de forma intermitente.
2. **Aspas simples** em volta de qualquer JSON com `${path:userName}` ou
   `${aws:PrincipalTag/…}` — senão o shell expande a variável para vazio.
3. **Verifique a ABAC** com `describe-…` depois de ligar. `AccessControlAttributes: []`
   significa que **não aplicou** — o valor não foi mapeado.
4. **Depois de mexer na ABAC ou provisionar, `logout` + `login`** — a session tag e
   as policies novas só entram numa sessão assumida **depois** da mudança.
5. **Base ampla (PowerUser) já libera `ssm:*`** → quem isola é o **`Deny`**, não o
   `Allow`. E toda alteração na inline exige **`provision-permission-set`**.
6. **O MCP `aws-core` fica preso ao profile do launch** (não troca por `--profile`
   em runtime). Para estas operações admin, use o **AWS CLI direto** com `--profile`.

## 1. Mapear `DevId` como session tag (ABAC) — na conta de gestão

```bash
aws sso-admin update-instance-access-control-attribute-configuration \
  --instance-arn <INSTANCE_ARN> \
  --instance-access-control-attribute-configuration \
  '{"AccessControlAttributes":[{"Key":"DevId","Value":{"Source":["${path:userName}"]}}]}' \
  --region <REGION> --profile <MGMT_PROFILE>

# VERIFIQUE (tem que listar DevId -> ${path:userName}, não [] ):
aws sso-admin describe-instance-access-control-attribute-configuration \
  --instance-arn <INSTANCE_ARN> --region <REGION> --profile <MGMT_PROFILE>
```

`update-…` se o ABAC já estiver `ENABLED` (o `create-…` falha nesse caso); o
`update` **substitui** o conjunto, então inclua atributos preexistentes.¹ É
**single-value** — sem multi-value para ABAC.²

## 2. Permission set dedicado `AWSDeveloperAccess` — na conta de gestão

```bash
PS_ARN=$(aws sso-admin create-permission-set --instance-arn <INSTANCE_ARN> \
  --name AWSDeveloperAccess --description "ORAEX developer access" \
  --session-duration PT8H --region <REGION> --profile <MGMT_PROFILE> \
  --query 'PermissionSet.PermissionSetArn' --output text)

aws sso-admin attach-managed-policy-to-permission-set --instance-arn <INSTANCE_ARN> \
  --permission-set-arn "$PS_ARN" \
  --managed-policy-arn arn:aws:iam::aws:policy/PowerUserAccess \
  --region <REGION> --profile <MGMT_PROFILE>

aws sso-admin put-inline-policy-to-permission-set --instance-arn <INSTANCE_ARN> \
  --permission-set-arn "$PS_ARN" --region <REGION> --profile <MGMT_PROFILE> \
  --inline-policy '{"Version":"2012-10-17","Statement":[{"Sid":"ReadOwnMcpParams","Effect":"Allow","Action":["ssm:GetParameter","ssm:GetParameters"],"Resource":"arn:aws:ssm:<REGION>:<DEV_ACCOUNT>:parameter/oraex/dev/*/mcp/*","Condition":{"StringEquals":{"aws:ResourceTag/DevId":"${aws:PrincipalTag/DevId}"}}},{"Sid":"DenyOtherDevsMcpParams","Effect":"Deny","Action":["ssm:GetParameter","ssm:GetParameters","ssm:GetParametersByPath"],"Resource":"arn:aws:ssm:<REGION>:<DEV_ACCOUNT>:parameter/oraex/dev/*/mcp/*","Condition":{"StringNotEquals":{"aws:ResourceTag/DevId":"${aws:PrincipalTag/DevId}"}}}]}'
```

- O **`Deny`** é o que isola: PowerUser já concede `ssm:*`, então sem ele um dev
  lê o parâmetro de qualquer outro. O `Deny` com `StringNotEquals` nega tudo em
  `/oraex/dev/*/mcp/*` cuja tag `DevId` ≠ a session tag do dev.³
- SSM suporta autorização por tag no recurso `Parameter` (`aws:ResourceTag/…`).⁴
- `SecureString` com a chave padrão `aws/ssm`: o PowerUser já cobre o `kms:Decrypt`;
  não precisa de statement de KMS.⁵

> **Alcance honesto:** o `Deny` isola os PATs entre devs, mas PowerUser é amplo —
> um dev determinado faz muita coisa na conta. Para isolamento forte, estreite a
> base (não use PowerUser). Aqui o objetivo é proteger o PAT de acesso cruzado
> casual e provar o padrão.

## 3. Grupo de devs + atribuição — na conta de gestão

```bash
GROUP_ID=$(aws identitystore create-group --identity-store-id <IDENTITY_STORE_ID> \
  --display-name "Developers" --region <REGION> --profile <MGMT_PROFILE> \
  --query 'GroupId' --output text)

# adicione cada dev (UserId do identity store):
aws identitystore create-group-membership --identity-store-id <IDENTITY_STORE_ID> \
  --group-id "$GROUP_ID" --member-id UserId=<USER_ID> \
  --region <REGION> --profile <MGMT_PROFILE>

# atribua o permission set ao grupo na conta de dev (provisiona sozinho):
aws sso-admin create-account-assignment --instance-arn <INSTANCE_ARN> \
  --permission-set-arn "$PS_ARN" --principal-type GROUP --principal-id "$GROUP_ID" \
  --target-type AWS_ACCOUNT --target-id <DEV_ACCOUNT> \
  --region <REGION> --profile <MGMT_PROFILE>
```

> Evite o prefixo `TEAM ` no nome do grupo — costuma pertencer à solução TEAM
> (Temporary Elevated Access Management) do Identity Center.
>
> **Ao alterar a inline policy depois de já atribuído**, re-provisione:
> `aws sso-admin provision-permission-set --instance-arn <INSTANCE_ARN>
> --permission-set-arn "$PS_ARN" --target-type AWS_ACCOUNT --target-id <DEV_ACCOUNT>
> --region <REGION> --profile <MGMT_PROFILE>`

## 4. Criar o parâmetro do dev (tagueado) e provar o isolamento

O dev cria o próprio (o valor do PAT é dele; não passe por mim):

```bash
aws ssm put-parameter --name "/oraex/dev/<HANDLE>/mcp/github" \
  --type SecureString --value "SEU_PAT" \
  --tags 'Key=DevId,Value=<DEV_ID>' \
  --region <REGION> --profile <DEV_PROFILE>
```

Prova (com o `<DEV_PROFILE>`, não-admin — faça `logout`/`login` antes para pegar a
session tag):

```bash
# o SEU deve retornar o nome (--query evita imprimir o PAT):
aws ssm get-parameter --name "/oraex/dev/<HANDLE>/mcp/github" --with-decryption \
  --region <REGION> --profile <DEV_PROFILE> --query 'Parameter.Name' --output text
# o de OUTRO dev deve dar AccessDeniedException (explicit deny).
```

`--tags` só funciona na **criação** do parâmetro (não junto de `--overwrite`).
Idealmente escope o `ssm:PutParameter` do dev para ele só taguear o próprio
`DevId` (guardrail contra plantar parâmetro no nome de outro).

## 5. Profile do dev + `.envrc`

`~/.aws/config` (session-based reaproveita a `[sso-session …]` existente):

```ini
[profile <DEV_PROFILE>]
sso_session = <SESSION_NAME>
sso_account_id = <DEV_ACCOUNT>
sso_role_name = AWSDeveloperAccess
region = <REGION>
output = json
```

O `.envrc` puxa o PAT para o env (ver skill [[env-conventions]]):

```bash
export GITHUB_PAT="$(aws ssm get-parameter --name "/oraex/dev/$ORAEX_DEV_ID/mcp/github" \
  --with-decryption --query 'Parameter.Value' --output text \
  --region "$AWS_REGION" --profile "$AWS_PROFILE")"
```

## Alternativa: Secrets Manager + asm-exec (resolução em runtime)

Para MCP **stdio só-token** onde você quer o segredo **nunca no env** (resolvido
em runtime, no processo filho), use Secrets Manager e o `asm-exec` do `aws-core`,
com `{{resolve:secretsmanager:oraex/dev/<id>/mcp/<servidor>:SecretString:token}}`.
O `asm-exec` resolve **só** Secrets Manager (não SSM). A ABAC/enforcement é a
mesma ideia; a policy usa `secretsmanager:GetSecretValue` (variável no ARN ou
condição por tag). O hook do `aws-core` bloqueia `get-secret-value` — barreira
estrutural que o SSM não tem.

> **`asm-exec` no PATH (setup por-máquina):** o `aws-core` entrega o `asm-exec`
> em `references/` do plugin, **fora do PATH** — um `.envrc`/shell comum não o
> acha (`asm-exec: command not found`). Este caminho alternativo só funciona com
> um wrapper por-máquina que localiza o binário no cache do plugin (resiliente a
> upgrade de versão):
>
> ```bash
> cat > ~/.local/bin/asm-exec <<'SH'
> #!/usr/bin/env bash
> exec python3 "$(ls -d "$HOME"/.claude/plugins/cache/claude-plugins-official/aws-core/*/skills/aws-secrets-manager/references/asm-exec | sort -V | tail -1)" "$@"
> SH
> chmod +x ~/.local/bin/asm-exec
> ```
>
> O caminho **padrão** (Parameter Store + `aws ssm get-parameter`) **não** precisa
> disso — só o `aws` CLI. Se o seu `.envrc` chama `asm-exec`, provavelmente foi
> gerado de um baseline antigo: rode `claude plugin marketplace update` e
> regenere pelo `env-conventions`.

---

¹ [CreateInstanceAccessControlAttributeConfiguration](https://docs.aws.amazon.com/singlesignon/latest/APIReference/API_CreateInstanceAccessControlAttributeConfiguration.html)
² [IAM Identity Center — Attributes for access control](https://docs.aws.amazon.com/singlesignon/latest/userguide/attributesforaccesscontrol.html)
³ [IAM — políticas com variável e tag](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_tags.html) · [PassRole com variável no Resource](https://aws.amazon.com/blogs/security/how-to-use-the-passrole-permission-with-iam-roles/)
⁴ [How AWS Systems Manager works with IAM — authorization based on tags](https://docs.aws.amazon.com/systems-manager/latest/userguide/security_iam_service-with-iam.html)
⁵ [SSM SecureString + KMS](https://docs.aws.amazon.com/systems-manager/latest/userguide/secure-string-parameter-kms-encryption.html)

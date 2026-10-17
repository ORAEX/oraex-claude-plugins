# Portal do cliente — abertura de chamados multi-tenant

> **Exemplo fictício** da skill `plano-fases`. O cliente "Acme Logística", o repositório e os
> commits citados são ilustrativos.

Status, critérios de aceite, decisões e bloqueios: [`PORTAL_CLIENTE.plan.json`](PORTAL_CLIENTE.plan.json)
(fonte da verdade). Quadro publicado: ver `artifact.url` no plano.

## Objetivo

Dar ao cliente final um portal próprio para abrir e acompanhar chamados, isolado por organização,
sem passar pelo e-mail do service desk. O agente do ITSM continua sendo quem atende; o portal é
só uma porta de entrada nova.

## Decisões (com o dono)

- **D1 — autenticação do portal:** magic link por e-mail, sem senha. Decidida em 2026-10-01.
- **D2 — anexos:** em aberto, ver o plano. Afeta a F3b.

## Fatias

As fatias, o que cada uma entrega e o critério de aceite vivem no plano. Este doc guarda o desenho e
os registros de fechamento.

## Registro — F1 (2026-10-02)

- **Entregue:** tabelas `portal_users` e `portal_invites` com `organization_id`, RLS e trilha de
  auditoria por trigger. Migration `20261002_portal_users.sql`.
- **Aceite:** `test_rls.py` cruzando duas orgs: usuário do portal da org A não lê convite da org B;
  service-role só no job de expiração de convite.
- Typecheck, lint e build ok.

## Registro — F2a (2026-10-06, local + staging)

- **Entregue:** login por magic link (`/portal/login`), sessão separada da sessão do agente
  (cookie com escopo `/portal`), expiração de 15 minutos.
- **Aceite:** link usado duas vezes é recusado; link de org A não abre sessão na org B; teste
  manual em staging com a org "Acme Logística".

## Registro — F2b (2026-10-10, staging)

- **Entregue:** formulário de abertura de chamado com categoria e prioridade herdadas do contrato
  da org; o chamado nasce no ITSM com `source = 'portal'`.
- **Aceite:** chamado aberto pelo portal aparece na fila do agente com SLA do contrato; cliente sem
  contrato ativo vê a mensagem "Fale com seu gestor de contas".
- Revisão de segurança (`revisao-seguranca`) sem achado bloqueante.

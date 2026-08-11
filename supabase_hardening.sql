-- Reforço de segurança da tabela usada pelo Hub Contábil
-- Execute no SQL Editor do Supabase somente após confirmar que o Streamlit
-- está usando uma chave secreta de servidor (sb_secret_...) ou service_role.
-- Este script não apaga nem altera os lançamentos já armazenados.

begin;

-- A tabela permanece acessível pela API, mas toda linha fica protegida por RLS.
alter table public.classificacoes_bancarias enable row level security;
alter table public.classificacoes_bancarias force row level security;

-- Impede leitura e alteração por visitantes anônimos, usuários comuns
-- e privilégios eventualmente herdados do papel PUBLIC.
revoke all privileges
on table public.classificacoes_bancarias
from public, anon, authenticated;

-- O aplicativo executado no servidor precisa apenas destas operações.
grant select, insert, update, delete
on table public.classificacoes_bancarias
to service_role;

commit;

-- Conferência: anon/authenticated não devem aparecer com privilégios.
select
    grantee,
    privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name = 'classificacoes_bancarias'
order by grantee, privilege_type;

-- Conferência: RLS e FORCE RLS devem retornar true.
select
    relrowsecurity as rls_ativo,
    relforcerowsecurity as rls_forcado
from pg_class
where oid = 'public.classificacoes_bancarias'::regclass;

-- Conferência de políticas existentes. Para esta arquitetura, nenhuma política
-- para anon/authenticated é necessária, pois somente o servidor acessa a tabela.
select
    policyname,
    roles,
    cmd
from pg_policies
where schemaname = 'public'
  and tablename = 'classificacoes_bancarias';

create table if not exists public.tarefas_empresas (
  codigo_empresa text not null,
  competencia date not null,
  concluida boolean not null default false,
  concluida_em timestamptz,
  atualizado_em timestamptz not null default now(),
  primary key (codigo_empresa, competencia),
  constraint tarefas_empresas_competencia_primeiro_dia
    check (extract(day from competencia) = 1)
);

alter table public.tarefas_empresas enable row level security;
revoke all on table public.tarefas_empresas from anon, authenticated;
grant select, insert, update, delete on table public.tarefas_empresas to service_role;

comment on table public.tarefas_empresas is
  'Controle mensal interno das empresas processadas no Razync.';

-- Self-registration support: ID number on users (SIH 26018 auth flow).
-- Nullable on purpose: pre-existing rows (e.g. seeded operator) are left
-- untouched with NULL; the /auth/register endpoint requires a non-empty
-- value for every newly created account. No uniqueness rule: the project
-- design does not require ID-number uniqueness, so none is invented here.
alter table public.users
  add column if not exists id_number text;

comment on column public.users.id_number is
  'Operator-supplied identity number collected at self-registration (required by the register endpoint, nullable only for pre-existing rows).';

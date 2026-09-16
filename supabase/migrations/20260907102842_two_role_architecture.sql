-- Two-role architecture: `user` (read-only) + `operator` (full document and
-- review/approval workflow). Retires `verifier` by mapping its capabilities
-- onto `operator`; keeps `admin` as an INTERNAL escalation rank only (never
-- user-facing, never creatable through self-registration).
--
-- Pre-flight facts verified against live data before writing this file:
--   * public.users            : 2 rows, both role='operator', 0 rows violate
--                               the new CHECK -> NO user row is modified.
--   * public.roles            : 3 rows (operator, verifier, admin).
--   * users.role              : TEXT CHECK only, NO foreign key to roles.name,
--                               so roles-table edits cannot cascade to users.
--   * role strings in history : 0 occurrences across audit_logs.metadata,
--                               audit_logs.old/new_value, review_tasks.reason,
--                               field_corrections.reason and
--                               validation_results.message -> audit history is
--                               role-agnostic and is preserved untouched.
--
-- ROLLBACK (paste-ready, restores the exact pre-migration state):
--   ALTER TABLE public.roles DROP CONSTRAINT roles_name_check;
--   ALTER TABLE public.roles ADD  CONSTRAINT roles_name_check
--     CHECK (name IN ('operator', 'verifier', 'admin'));
--   ALTER TABLE public.users DROP CONSTRAINT users_role_check;
--   ALTER TABLE public.users ADD  CONSTRAINT users_role_check
--     CHECK (role IN ('operator', 'verifier', 'admin'));
--   DELETE FROM public.roles WHERE name = 'user';
--   UPDATE public.roles SET permissions = '{"actions": ["documents:upload",
--     "documents:process", "documents:view", "reviews:create"]}'::jsonb
--     WHERE name = 'operator';
--   INSERT INTO public.roles (name, permissions) VALUES ('verifier',
--     '{"actions": ["documents:upload", "documents:process", "documents:view",
--     "reviews:create", "reviews:review", "reviews:edit", "records:approve",
--     "records:reject"]}'::jsonb);

BEGIN;

-- 1. Retire the verifier row BEFORE narrowing the CHECK (the old row would
--    otherwise violate the new constraint).
DELETE FROM public.roles WHERE name = 'verifier';

-- 2. Canonical role vocabulary. `verifier` is removed so a stale value can
--    never be stored again; `admin` is retained for internal administration.
ALTER TABLE public.roles DROP CONSTRAINT roles_name_check;
ALTER TABLE public.roles ADD  CONSTRAINT roles_name_check
  CHECK (name IN ('user', 'operator', 'admin'));

ALTER TABLE public.users DROP CONSTRAINT users_role_check;
ALTER TABLE public.users ADD  CONSTRAINT users_role_check
  CHECK (role IN ('user', 'operator', 'admin'));

-- 3. operator absorbs every capability formerly gated as verifier.
UPDATE public.roles
SET permissions = '{"actions": ["documents:upload", "documents:process",
  "documents:view", "documents:search", "reviews:create", "reviews:review",
  "reviews:edit", "reviews:complete", "records:approve", "records:reject",
  "records:export", "audit:view"]}'::jsonb
WHERE name = 'operator';

-- 4. The read-only role: search/view/export only, no mutation of any kind.
INSERT INTO public.roles (name, permissions) VALUES
  ('user', '{"actions": ["documents:view", "documents:search",
    "records:export"]}'::jsonb)
ON CONFLICT (name) DO UPDATE SET permissions = EXCLUDED.permissions;

COMMIT;

COMMENT ON TABLE public.roles IS
  'RBAC role definitions. users.role maps to roles.name. User-facing roles are '
  'user (read-only) and operator (full workflow); admin is internal-only. '
  'Reference data for humans and tooling — authorization itself is enforced '
  'server-side in the FastAPI layer (11_SECURITY_DESIGN section 3).';

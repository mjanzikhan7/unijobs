import { useState } from "react";

import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { Chip } from "@/components/Chip/Chip";
import { Input } from "@/components/Field/Input";
import { Select } from "@/components/Field/Select";
import { ErrorMessage } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import type { Role } from "@/viewmodels/auth";
import { useAuth } from "@/viewmodels/auth";
import { useInstitutions } from "@/viewmodels/useInstitutions";
import type { AssignedInstitution } from "@/viewmodels/useUsers";
import {
  useCreateUser,
  useSetInstitutions,
  useSetRole,
  useSetUserActive,
  useUsers,
} from "@/viewmodels/useUsers";

const ROLES: readonly Role[] = ["ADMIN", "MANAGER", "RECRUITER", "CANDIDATE"];

interface UserRow {
  id: number;
  username: string;
  email: string;
  email_verified: boolean;
  role: Role;
  is_active: boolean;
  assigned_institutions: AssignedInstitution[];
}

const fieldLabel = "block text-body-sm font-medium text-text-primary";

export function UserAdmin() {
  const { user: me, role: myRole } = useAuth();
  const users = useUsers();
  const institutions = useInstitutions();
  const create = useCreateUser();
  const setRole = useSetRole();
  const setActive = useSetUserActive();
  const setInstitutions = useSetInstitutions();

  const canEdit = myRole === "ADMIN";
  const [draft, setDraft] = useState({
    username: "",
    email: "",
    password: "",
    role: "CANDIDATE" as Role,
  });

  if (users.isError)
    return <ErrorMessage error={users.error} onRetry={() => void users.refetch()} />;

  const rows = (users.data?.results ?? []) as UserRow[];

  const isSelf = (row: UserRow) => row.username === me?.username;

  const columns: DataTableColumn<UserRow>[] = [
    { key: "username", header: "Username", isRowHeader: true, cell: (row) => row.username },
    {
      key: "email",
      header: "Email",
      cell: (row) => (
        <span className="flex flex-wrap items-center gap-2">
          {row.email}
          {!row.email_verified ? <Chip tone="caution">unverified</Chip> : null}
        </span>
      ),
    },
    {
      key: "role",
      header: "Role",
      cell: (row) =>
        canEdit && !isSelf(row) ? (
          <>
            <label className="sr-only" htmlFor={`role-${row.id}`}>
              Role for {row.username}
            </label>
            <Select
              id={`role-${row.id}`}
              value={row.role}
              onChange={(event) => setRole.mutate({ id: row.id, role: event.target.value as Role })}
              className="h-9 w-auto text-body-sm"
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </Select>
          </>
        ) : (
          <span>{row.role}</span>
        ),
    },
    {
      key: "institutions",
      header: "Institutions",
      cell: (row) => {
        if (row.role !== "RECRUITER") return <span className="text-text-muted">—</span>;
        if (!canEdit) {
          return (
            <span>{row.assigned_institutions.map((institution) => institution.name).join(", ") || "—"}</span>
          );
        }
        const options = institutions.data?.results ?? [];
        return (
          <>
            <label className="sr-only" htmlFor={`institutions-${row.id}`}>
              Institutions assigned to {row.username}
            </label>
            <select
              id={`institutions-${row.id}`}
              multiple
              size={3}
              value={row.assigned_institutions.map((institution) => institution.slug)}
              onChange={(event) => {
                const slugs = Array.from(event.target.selectedOptions, (option) => option.value);
                setInstitutions.mutate({ id: row.id, institutions: slugs });
              }}
              className="w-48 rounded-sm border border-border-strong bg-surface p-1 text-body-sm"
            >
              {options.map((institution) => (
                <option key={institution.slug} value={institution.slug}>
                  {institution.name}
                </option>
              ))}
            </select>
          </>
        );
      },
    },
    {
      key: "status",
      header: "Status",
      cell: (row) =>
        row.is_active ? (
          <Badge tone="positive">active</Badge>
        ) : (
          <Badge tone="negative">suspended</Badge>
        ),
    },
    {
      key: "actions",
      header: "Actions",
      cell: (row) =>
        canEdit && !isSelf(row) ? (
          <Button
            variant="quiet"
            size="sm"
            onClick={() => setActive.mutate({ id: row.id, active: !row.is_active })}
          >
            {row.is_active ? "Suspend" : "Restore"}
          </Button>
        ) : (
          <span className="text-text-muted">you</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <h1 className="font-display text-heading-xl font-bold">Users</h1>

      {!canEdit ? (
        <Notice tone="info">
          You can see the accounts in the system. Changing them is an administrator&rsquo;s job.
        </Notice>
      ) : null}

      {canEdit ? (
        <Card as="section" className="space-y-3">
          <div>
            <h2 className="font-display text-heading-sm font-semibold">Add an account</h2>
            <p className="mt-1 text-caption text-text-muted">
              Created ready to use — no confirmation email, since you have the address already.
            </p>
          </div>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              create.mutate(draft, {
                onSuccess: () =>
                  setDraft({ username: "", email: "", password: "", role: "CANDIDATE" }),
              });
            }}
          >
            <div className="min-w-40 flex-1">
              <label htmlFor="new-username" className={fieldLabel}>
                Username
              </label>
              <Input
                id="new-username"
                value={draft.username}
                onChange={(event) => setDraft({ ...draft, username: event.target.value })}
                className="mt-1"
                required
              />
            </div>

            <div className="min-w-40 flex-1">
              <label htmlFor="new-email" className={fieldLabel}>
                Email
              </label>
              <Input
                id="new-email"
                type="email"
                value={draft.email}
                onChange={(event) => setDraft({ ...draft, email: event.target.value })}
                className="mt-1"
                required
              />
            </div>

            <div className="min-w-40 flex-1">
              <label htmlFor="new-password" className={fieldLabel}>
                Password
              </label>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={draft.password}
                onChange={(event) => setDraft({ ...draft, password: event.target.value })}
                className="mt-1"
                required
              />
            </div>

            <div>
              <label htmlFor="new-role" className={fieldLabel}>
                Role
              </label>
              <Select
                id="new-role"
                value={draft.role}
                onChange={(event) => setDraft({ ...draft, role: event.target.value as Role })}
                className="mt-1 w-auto"
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </Select>
            </div>

            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create account"}
            </Button>
          </form>
          {create.isError ? <ErrorMessage error={create.error} /> : null}
        </Card>
      ) : null}

      {setRole.isError ? <ErrorMessage error={setRole.error} /> : null}
      {setActive.isError ? <ErrorMessage error={setActive.error} /> : null}
      {setInstitutions.isError ? <ErrorMessage error={setInstitutions.error} /> : null}

      <DataTable<UserRow>
        caption="Accounts"
        columns={columns}
        rows={rows}
        rowKey={(row) => row.id}
        loading={users.isLoading}
        emptyTitle="No accounts"
        emptyBody="Nothing to show — which should not happen, since you are signed in."
      />
    </div>
  );
}

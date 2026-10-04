import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { Chip } from "@/components/Chip/Chip";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Input } from "@/components/Field/Input";
import { Notice } from "@/components/Notice/Notice";
import { SegmentedControl } from "@/components/SegmentedControl/SegmentedControl";
import { useAuth } from "@/viewmodels/auth";
import {
  useAccount,
  useChangePassword,
  useDeleteAccount,
  useDownloadMyData,
  useSetDigest,
  useUpdateAccount,
} from "@/viewmodels/useAccount";

type EditingRow = "email" | "password" | "name" | null;

const sectionHeading = "font-display text-heading-md font-semibold border-b-2 border-border-subtle pb-2";
const row =
  "flex flex-col gap-2 border-b border-border-subtle py-4 sm:grid sm:grid-cols-[12rem_1fr_auto] sm:items-center sm:gap-4";
const rowLabel = "text-body text-text-primary";
const rowValue = "flex items-center gap-2 text-body text-text-secondary";
const fieldLabel = "block text-body-sm font-medium text-text-primary";
const hint = "text-caption text-text-muted";

export function AccountSettings() {
  const { signOut } = useAuth();
  const navigate = useNavigate();

  const account = useAccount();
  const update = useUpdateAccount();
  const changePassword = useChangePassword();
  const setDigest = useSetDigest();
  const closeAccount = useDeleteAccount();
  const downloadMyData = useDownloadMyData();

  const [editing, setEditing] = useState<EditingRow>(null);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");

  if (account.isLoading) return <Spinner label="Loading your account" />;
  if (account.isError) {
    return <ErrorMessage error={account.error} onRetry={() => void account.refetch()} />;
  }

  const me = account.data;
  if (!me) return null;

  const fullName = [me.first_name, me.last_name].filter(Boolean).join(" ");

  const open = (which: EditingRow) => {
    setEmail(me.email);
    setFirstName(me.first_name);
    setLastName(me.last_name);
    setCurrentPassword("");
    setNewPassword("");
    setEditing(which);
  };

  const editActions = (pending: boolean) => (
    <div className="flex gap-2">
      <Button type="submit" variant="primary" disabled={pending}>
        Save
      </Button>
      <Button variant="quiet" onClick={() => setEditing(null)}>
        Cancel
      </Button>
    </div>
  );

  return (
    <div className="mx-auto max-w-prose space-y-8">
      <h1 className="border-b-2 border-border-subtle pb-4 font-display text-heading-xl font-bold">
        Account settings
      </h1>

      <section>
        <h2 className={sectionHeading}>Personal details</h2>

        <div className={row}>
          <span className={rowLabel}>Email</span>
          <span className={rowValue}>
            {me.email || "—"}
            {!me.email_verified ? <Chip tone="caution">Unconfirmed</Chip> : null}
          </span>
          <Button variant="primary" className="w-full sm:w-auto" onClick={() => open("email")}>
            Edit
          </Button>
        </div>
        {editing === "email" ? (
          <form
            className="space-y-2 border-b border-border-subtle py-4"
            onSubmit={(event) => {
              event.preventDefault();
              update.mutate({ email }, { onSuccess: () => setEditing(null) });
            }}
          >
            <label htmlFor="account-email" className={fieldLabel}>
              New email
            </label>
            <Input
              id="account-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              error={update.isError}
              required
            />
            <p className={hint}>
              We will send a confirmation to the new address. Your account keeps its current one
              until you follow that link.
            </p>
            {update.isError ? <ErrorMessage error={update.error} /> : null}
            {editActions(update.isPending)}
          </form>
        ) : null}

        {me.pending_email ? (
          <div className="py-4">
            <Notice tone="info">
              Waiting for <strong>{me.pending_email}</strong> to be confirmed. Until then this
              account still uses {me.email || "its current address"}.
            </Notice>
          </div>
        ) : null}

        <div className={row}>
          <span className={rowLabel}>Password</span>
          <span className={rowValue}>••••••••••••••</span>
          <Button variant="primary" className="w-full sm:w-auto" onClick={() => open("password")}>
            Edit
          </Button>
        </div>
        {editing === "password" ? (
          <form
            className="space-y-2 border-b border-border-subtle py-4"
            onSubmit={(event) => {
              event.preventDefault();
              changePassword.mutate(
                { current_password: currentPassword, new_password: newPassword },
                { onSuccess: () => setEditing(null) },
              );
            }}
          >
            <label htmlFor="account-current" className={fieldLabel}>
              Current password
            </label>
            <Input
              id="account-current"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
            />
            <label htmlFor="account-new" className={fieldLabel}>
              New password
            </label>
            <Input
              id="account-new"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              required
            />
            <p className={hint}>Other devices are signed out. This one stays signed in.</p>
            {changePassword.isError ? <ErrorMessage error={changePassword.error} /> : null}
            {editActions(changePassword.isPending)}
          </form>
        ) : null}

        <div className={row}>
          <span className={rowLabel}>Name</span>
          <span className={rowValue}>{fullName || "—"}</span>
          <Button variant="primary" className="w-full sm:w-auto" onClick={() => open("name")}>
            Edit
          </Button>
        </div>
        {editing === "name" ? (
          <form
            className="space-y-2 border-b border-border-subtle py-4"
            onSubmit={(event) => {
              event.preventDefault();
              update.mutate(
                { first_name: firstName, last_name: lastName },
                { onSuccess: () => setEditing(null) },
              );
            }}
          >
            <label htmlFor="account-first" className={fieldLabel}>
              First name
            </label>
            <Input
              id="account-first"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
            />
            <label htmlFor="account-last" className={fieldLabel}>
              Last name
            </label>
            <Input
              id="account-last"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
            />
            {update.isError ? <ErrorMessage error={update.error} /> : null}
            {editActions(update.isPending)}
          </form>
        ) : null}

        <div className={row}>
          <span className={rowLabel}>Role</span>
          <span className={rowValue}>{me.role}</span>
          <span />
        </div>
      </section>

      <section>
        <h2 className={sectionHeading}>Communications preferences</h2>

        <div className={row}>
          <span className={`${rowLabel} sm:col-span-2`}>
            I would like to receive the overnight digest of new matches and closing deadlines
          </span>
          <SegmentedControl
            label="Overnight digest"
            value={me.digest_enabled ? "yes" : "no"}
            onChange={(value) => setDigest.mutate(value === "yes")}
            options={[
              { value: "yes", label: "Yes" },
              { value: "no", label: "No" },
            ]}
          />
        </div>

        <p className={`${hint} pt-3`}>
          The digest only goes out when there is something to say — never an email telling you
          nothing happened. You can change this at any time.
        </p>
        {setDigest.isError ? <ErrorMessage error={setDigest.error} /> : null}
      </section>

      <section>
        <h2 className={sectionHeading}>Your data</h2>

        <div className={row}>
          <span className={`${rowLabel} sm:col-span-2`}>
            Download a copy of everything we hold about you, as a JSON file
          </span>
          <Button
            variant="secondary"
            className="w-full sm:w-auto"
            disabled={downloadMyData.isPending}
            onClick={() => downloadMyData.mutate()}
          >
            {downloadMyData.isPending ? "Preparing…" : "Download your data"}
          </Button>
        </div>

        <p className={`${hint} pt-3`}>
          The{" "}
          <Link to="/privacy" className="text-brand underline underline-offset-2 hover:decoration-2">
            privacy notice
          </Link>{" "}
          explains what we store, why, and for how long.
        </p>
        {downloadMyData.isError ? <ErrorMessage error={downloadMyData.error} /> : null}
      </section>

      <section>
        <h2 className={sectionHeading}>Delete account</h2>

        <div className={row}>
          <span className={rowLabel}>Delete account</span>
          <span />
          <Button
            variant="primary"
            className="w-full sm:w-auto"
            onClick={() => setConfirmingDelete(true)}
          >
            Delete account
          </Button>
        </div>

        {confirmingDelete ? (
          <form
            className="space-y-3 py-4"
            onSubmit={(event) => {
              event.preventDefault();
              closeAccount.mutate(deletePassword, {
                onSuccess: () => {
                  void signOut();
                  void navigate("/login", { replace: true });
                },
              });
            }}
          >
            <Notice tone="danger">
              This cannot be undone. Your saved jobs, applications, profile and uploaded CVs are
              deleted with the account.
            </Notice>
            <label htmlFor="account-delete-password" className={fieldLabel}>
              Confirm your password
            </label>
            <Input
              id="account-delete-password"
              type="password"
              autoComplete="current-password"
              value={deletePassword}
              onChange={(event) => setDeletePassword(event.target.value)}
              required
            />
            {closeAccount.isError ? <ErrorMessage error={closeAccount.error} /> : null}
            <div className="flex gap-2">
              <Button type="submit" variant="danger" disabled={closeAccount.isPending}>
                {closeAccount.isPending ? "Deleting…" : "Delete my account"}
              </Button>
              <Button variant="quiet" onClick={() => setConfirmingDelete(false)}>
                Cancel
              </Button>
            </div>
          </form>
        ) : null}
      </section>

      <Button variant="primary" className="w-full" onClick={() => void signOut()}>
        Sign out
      </Button>
    </div>
  );
}

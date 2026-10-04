import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { ErrorMessage } from "@/components/Feedback";
import { confirmPasswordReset } from "@/viewmodels/accountAccess";

import { AuthCard } from "./AuthCard";
import { AuthField } from "./AuthField";

export function ResetPassword() {
  const { uid = "", token = "" } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await confirmPasswordReset({ uid, token, password });
      void navigate("/login", { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard
      title="Choose a new password"
      onSubmit={(event) => void submit(event)}
      footer={
        <p>
          <Link to="/login" className="text-brand underline underline-offset-2 hover:decoration-2">
            Back to sign in
          </Link>
        </p>
      }
    >
      <AuthField
        id="reset-password"
        label="New password"
        type="password"
        autoComplete="new-password"
        hint="Every device signed in to this account is signed out, including this one."
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      {error ? <ErrorMessage error={error} /> : null}

      <Button type="submit" variant="primary" className="w-full" disabled={busy}>
        {busy ? "Saving…" : "Set password"}
      </Button>
    </AuthCard>
  );
}

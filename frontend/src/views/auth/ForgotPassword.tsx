import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { ErrorMessage } from "@/components/Feedback";
import { requestPasswordReset } from "@/viewmodels/accountAccess";

import { AuthCard } from "./AuthCard";
import { AuthField } from "./AuthField";

const backToSignIn = (
  <p>
    <Link to="/login" className="text-brand underline underline-offset-2 hover:decoration-2">
      Back to sign in
    </Link>
  </p>
);

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <AuthCard title="Check your inbox" footer={backToSignIn}>
        <p className="text-body text-text-secondary">
          If that address has an account, a reset link is on its way.
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Reset your password"
      onSubmit={(event) => void submit(event)}
      footer={backToSignIn}
    >
      <AuthField
        id="forgot-email"
        label="Email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      {error ? <ErrorMessage error={error} /> : null}

      <Button type="submit" variant="primary" className="w-full" disabled={busy}>
        {busy ? "Sending…" : "Send reset link"}
      </Button>
    </AuthCard>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { ErrorMessage } from "@/components/Feedback";
import { registerAccount } from "@/viewmodels/accountAccess";

import { AuthCard } from "./AuthCard";
import { AuthField } from "./AuthField";

const backToSignIn = (
  <p>
    <Link to="/login" className="text-brand underline underline-offset-2 hover:decoration-2">
      Back to sign in
    </Link>
  </p>
);

export function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await registerAccount({ username, email, password });
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
          If that address can be registered, a confirmation link is on its way. The account cannot
          be used until the address is confirmed.
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Create an account"
      onSubmit={(event) => void submit(event)}
      footer={
        <p>
          <Link to="/login" className="text-brand underline underline-offset-2 hover:decoration-2">
            Already have an account?
          </Link>
        </p>
      }
    >
      <AuthField
        id="register-username"
        label="Username"
        autoComplete="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
        required
      />

      <AuthField
        id="register-email"
        label="Email"
        type="email"
        autoComplete="email"
        hint="We send a confirmation link here. The account cannot be used until you follow it."
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      <AuthField
        id="register-password"
        label="Password"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      {error ? <ErrorMessage error={error} /> : null}

      <Button type="submit" variant="primary" className="w-full" disabled={busy}>
        {busy ? "Creating…" : "Create account"}
      </Button>
    </AuthCard>
  );
}

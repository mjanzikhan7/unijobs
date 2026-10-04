import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { ErrorMessage } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import { signInWithPassword } from "@/viewmodels/accountAccess";
import { useAuth } from "@/viewmodels/auth";

import { AuthCard } from "./AuthCard";
import { AuthField } from "./AuthField";

export function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signInWithPassword(username, password);
      signIn();
      void navigate(params.get("next") ?? "/", { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard
      title="Sign in"
      onSubmit={(event) => void submit(event)}
      footer={
        <p className="flex flex-wrap gap-x-2">
          <Link to="/register" className="text-brand underline underline-offset-2 hover:decoration-2">
            Create an account
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/forgot-password" className="text-brand underline underline-offset-2 hover:decoration-2">
            Forgotten your password?
          </Link>
        </p>
      }
    >
      {params.get("verified") === "1" ? (
        <Notice tone="info">Address confirmed. Sign in to continue.</Notice>
      ) : null}

      <AuthField
        id="login-username"
        label="Username"
        autoComplete="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
        required
      />

      <AuthField
        id="login-password"
        label="Password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      {error ? <ErrorMessage error={error} /> : null}

      <Button type="submit" variant="primary" className="w-full" disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </Button>
    </AuthCard>
  );
}

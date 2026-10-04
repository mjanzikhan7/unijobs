import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Spinner } from "@/components/Feedback";
import { verifyEmail } from "@/viewmodels/accountAccess";

import { AuthCard } from "./AuthCard";

export function VerifyEmail() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState<"working" | "failed">("working");
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    verifyEmail(token)
      .then(() => void navigate("/login?verified=1", { replace: true }))
      .catch(() => setState("failed"));
  }, [token, navigate]);

  if (state === "working") return <Spinner label="Confirming your address" />;

  return (
    <AuthCard
      title="That link did not work"
      footer={
        <p className="flex flex-wrap gap-x-2">
          <Link to="/register" className="text-brand underline underline-offset-2 hover:decoration-2">
            Register again
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/login" className="text-brand underline underline-offset-2 hover:decoration-2">
            Sign in
          </Link>
        </p>
      }
    >
      <p className="text-body text-text-secondary">
        It may have expired, or already been used. Links are valid for 48 hours.
      </p>
    </AuthCard>
  );
}

import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Spinner } from "@/components/Feedback";
import { confirmEmailChange } from "@/viewmodels/accountAccess";

import { AuthCard } from "./AuthCard";

export function VerifyEmailChange() {
  const { token = "" } = useParams();
  const [state, setState] = useState<"working" | "done" | "failed">("working");
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    confirmEmailChange(token)
      .then(() => setState("done"))
      .catch(() => setState("failed"));
  }, [token]);

  if (state === "working") return <Spinner label="Confirming your new address" />;

  return (
    <AuthCard
      title={state === "done" ? "Address updated" : "That link did not work"}
      footer={
        <p>
          <Link to="/profile" className="text-brand underline underline-offset-2 hover:decoration-2">
            Back to your account
          </Link>
        </p>
      }
    >
      <p className="text-body text-text-secondary">
        {state === "done"
          ? "Your account now uses this address."
          : "It may have expired, already been used, or been replaced by a newer request. Your account still uses its previous address."}
      </p>
    </AuthCard>
  );
}

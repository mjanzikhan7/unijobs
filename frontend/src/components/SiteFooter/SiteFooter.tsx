import { Link } from "react-router-dom";

const SECURITY_POLICY_URL = "/.well-known/security.txt";

export function SiteFooterLinks({ className = "" }: { className?: string }) {
  return (
    <nav aria-label="Legal and support" className={className}>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        <li>
          <Link to="/accessibility" className="underline underline-offset-2 hover:decoration-2">
            Accessibility statement
          </Link>
        </li>
        <li>
          <Link to="/privacy" className="underline underline-offset-2 hover:decoration-2">
            Privacy notice
          </Link>
        </li>
        <li>
          <a href={SECURITY_POLICY_URL} className="underline underline-offset-2 hover:decoration-2" rel="noreferrer">
            Report a security problem
          </a>
        </li>
      </ul>
    </nav>
  );
}

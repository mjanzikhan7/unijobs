import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { InstitutionBranding } from "@/views/admin/InstitutionBranding";
import { useAuth } from "@/viewmodels/auth";
import { useInstitutions } from "@/viewmodels/useInstitutions";

export function MyInstitution() {
  const { assignedInstitutions } = useAuth();
  const institutions = useInstitutions();

  if (institutions.isLoading) return <Spinner label="Loading your institution" />;
  if (institutions.isError) {
    return <ErrorMessage error={institutions.error} onRetry={() => void institutions.refetch()} />;
  }

  const mine = (institutions.data?.results ?? []).filter((institution) =>
    assignedInstitutions.includes(institution.slug),
  );

  return (
    <div className="mx-auto max-w-content space-y-4">
      <h1 className="font-display text-heading-xl font-bold">My institution</h1>
      <p className="text-body-sm text-text-secondary">
        The logo, banner, About text and contact details shown on each institution&rsquo;s own
        page. Which institutions you see here is set by an administrator.
      </p>

      {mine.length === 0 ? (
        <EmptyPanel
          title="Nothing assigned yet"
          body="An administrator has not assigned you to an institution. Ask one to set it up from Users."
        />
      ) : (
        <div className="space-y-4">
          {mine.map((institution) => (
            <InstitutionBranding key={institution.id} institution={institution} />
          ))}
        </div>
      )}
    </div>
  );
}

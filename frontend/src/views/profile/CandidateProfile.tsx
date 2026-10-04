import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { CVDropzone } from "@/components/CVDropzone/CVDropzone";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { Fact } from "@/components/Fact/Fact";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Input } from "@/components/Field/Input";
import { Notice } from "@/components/Notice/Notice";
import { TermChipGroup } from "@/components/TermChipGroup/TermChipGroup";
import { describe as describeError } from "@/components/Feedback";
import { useProfiles } from "@/viewmodels/useProfiles";
import { useApplyCV, useCVs, useUploadCV, type CVSuggestions } from "@/viewmodels/useCVs";

const TERM_FIELDS = ["skills", "domains", "seniority", "projects", "education"] as const;
type TermField = (typeof TERM_FIELDS)[number];

const FIELD_LABELS: Record<TermField, string> = {
  skills: "Skills",
  domains: "Domains",
  seniority: "Seniority",
  projects: "Projects",
  education: "Education",
};

export function CandidateProfile() {
  const profiles = useProfiles();
  const cvs = useCVs();
  const upload = useUploadCV();
  const apply = useApplyCV();

  const latest = cvs.data?.results[0] ?? null;
  const [draft, setDraft] = useState<CVSuggestions | null>(null);
  const [draftFrom, setDraftFrom] = useState<typeof latest>(null);

  if (latest !== draftFrom) {
    setDraftFrom(latest);
    if (latest?.suggestions && !latest.applied_at) setDraft(latest.suggestions);
  }

  const active = profiles.data?.results.find((row) => row.is_active) ?? null;

  const toggle = (field: TermField, term: string) => {
    setDraft((current) => {
      if (!current) return current;
      const present = current[field].includes(term);
      return {
        ...current,
        [field]: present
          ? current[field].filter((item) => item !== term)
          : [...current[field], term],
      };
    });
  };

  if (profiles.isLoading) return <Spinner label="Loading profile" />;

  return (
    <div className="mx-auto max-w-prose space-y-8">
      <header>
        <h1 className="font-display text-heading-xl font-bold">CV &amp; job matching</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          This is what job fitness is scored against. Fitness ranks what is already takeable — it
          never changes whether an employer can sponsor you.
        </p>
      </header>

      <section>
        <h2 className="font-display text-heading-md font-semibold">In force</h2>
        {active ? (
          <dl className="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2">
            {TERM_FIELDS.map((field) => (
              <Fact key={field} label={FIELD_LABELS[field]} value={active[field].join(", ")} />
            ))}
            <Fact label="Years of experience" value={active.years_experience} />
          </dl>
        ) : (
          <div className="mt-3">
            <EmptyPanel
              title="No profile yet"
              body="Upload a CV below to build one — every job scores 0 until you do."
            />
          </div>
        )}
      </section>

      <section>
        <h2 className="font-display text-heading-md font-semibold">Upload a CV</h2>
        <div className="mt-3">
          <CVDropzone
            onFile={(file) => upload.mutate(file)}
            uploading={upload.isPending}
            error={upload.isError ? describeError(upload.error) : null}
            fileName={latest?.original_filename ?? null}
          />
        </div>
      </section>

      {draft ? (
        <section className="space-y-4">
          <div>
            <h2 className="font-display text-heading-md font-semibold">What we found</h2>
            <p className="mt-1 text-body-sm text-text-secondary">
              Reading a CV is approximate, so nothing is saved until you confirm. Untick anything
              that is not right.
            </p>
          </div>

          {TERM_FIELDS.map((field) => (
            <TermChipGroup
              key={field}
              field={field}
              label={FIELD_LABELS[field]}
              terms={latest?.suggestions?.[field] ?? draft[field]}
              selected={draft[field]}
              onToggle={(term) => toggle(field, term)}
            />
          ))}

          <div>
            <label htmlFor="cv-years" className="block text-body-sm font-medium">
              Years of experience
            </label>
            <Input
              id="cv-years"
              type="number"
              min={0}
              max={70}
              value={draft.years_experience}
              onChange={(event) =>
                setDraft({ ...draft, years_experience: Number(event.target.value) })
              }
              className="mt-1 max-w-24"
            />
          </div>

          {apply.isError ? <ErrorMessage error={apply.error} /> : null}

          <Button
            variant="primary"
            disabled={apply.isPending || !latest}
            onClick={() => {
              if (latest) apply.mutate({ id: latest.id, body: draft });
            }}
          >
            {apply.isPending ? "Saving…" : "Add these to my profile"}
          </Button>

          <Notice tone="info">
            Added to what is already there — nothing is removed. Jobs re-score in the background.
          </Notice>
        </section>
      ) : null}
    </div>
  );
}

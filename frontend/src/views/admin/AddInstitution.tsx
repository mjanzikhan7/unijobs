import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { FileInput } from "@/components/Field/FileInput";
import { Input } from "@/components/Field/Input";
import { Select } from "@/components/Field/Select";
import { Textarea } from "@/components/Field/Textarea";
import { ErrorMessage } from "@/components/Feedback";
import { MonogramTile } from "@/components/MonogramTile/MonogramTile";
import { Notice } from "@/components/Notice/Notice";
import type { Institution, InstitutionType, Nation } from "@/models/api/types";
import { useAuth } from "@/viewmodels/auth";
import { useCreateInstitution, useUploadInstitutionMedia } from "@/viewmodels/useInstitutions";

interface NewInstitutionValues {
  name: string;
  careers_url: string;
  website: string;
  nation: Nation;
  institution_type: InstitutionType;
  city: string;
  ranking: string;
  crawl_enabled: boolean;
  notes: string;
  description: string;
  contact_email: string;
  contact_phone: string;
  address: string;
}

const EMPTY_VALUES: NewInstitutionValues = {
  name: "",
  careers_url: "",
  website: "",
  nation: "ENGLAND",
  institution_type: "UNIVERSITY",
  city: "",
  ranking: "",
  crawl_enabled: true,
  notes: "",
  description: "",
  contact_email: "",
  contact_phone: "",
  address: "",
};

const NATIONS: { value: Nation; label: string }[] = [
  { value: "ENGLAND", label: "England" },
  { value: "SCOTLAND", label: "Scotland" },
  { value: "WALES", label: "Wales" },
  { value: "NORTHERN_IRELAND", label: "Northern Ireland" },
];

const INSTITUTION_TYPES: { value: InstitutionType; label: string }[] = [
  { value: "UNIVERSITY", label: "University" },
  { value: "COLLEGE", label: "College" },
  { value: "CONSERVATOIRE", label: "Conservatoire" },
  { value: "RESEARCH_INSTITUTE", label: "Research institute" },
  { value: "BUSINESS_SCHOOL", label: "Business school" },
  { value: "OTHER", label: "Other" },
];

const fieldLabel = "block text-body-sm font-medium text-text-primary";
const slotLabel = "text-overline font-semibold tracking-wide text-text-muted uppercase";

function Field({
  id,
  label,
  full = false,
  required = false,
  children,
}: {
  id: string;
  label: string;
  full?: boolean;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={full ? "sm:col-span-2" : undefined}>
      <div className="flex items-baseline gap-1">
        <label htmlFor={id} className={fieldLabel}>
          {label}
        </label>
        {required ? (
          <span aria-hidden="true" className="text-danger">
            *
          </span>
        ) : null}
      </div>
      <div className="mt-1">{children}</div>
    </div>
  );
}

export function AddInstitution() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const create = useCreateInstitution();
  const upload = useUploadInstitutionMedia();

  const [values, setValues] = useState<NewInstitutionValues>(EMPTY_VALUES);
  const [logo, setLogo] = useState<File | null>(null);
  const [banner, setBanner] = useState<File | null>(null);

  const logoPreviewUrl = useMemo(() => (logo ? URL.createObjectURL(logo) : null), [logo]);
  const bannerPreviewUrl = useMemo(() => (banner ? URL.createObjectURL(banner) : null), [banner]);
  useEffect(() => () => (logoPreviewUrl ? URL.revokeObjectURL(logoPreviewUrl) : undefined), [logoPreviewUrl]);
  useEffect(
    () => () => (bannerPreviewUrl ? URL.revokeObjectURL(bannerPreviewUrl) : undefined),
    [bannerPreviewUrl],
  );

  if (role !== "ADMIN") {
    return (
      <div className="mx-auto max-w-content space-y-4">
        <Button variant="quiet" size="sm" onClick={() => void navigate("/admin/institutions")} type="button">
          ← Manage institutions
        </Button>
        <Notice tone="warning">Only an administrator can add an institution.</Notice>
      </div>
    );
  }

  const set = <K extends keyof NewInstitutionValues>(key: K, value: NewInstitutionValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));

  const pending = create.isPending || upload.isPending;

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();

    const payload: Partial<Institution> = {
      name: values.name.trim(),
      careers_url: values.careers_url.trim(),
      website: values.website.trim(),
      nation: values.nation,
      institution_type: values.institution_type,
      city: values.city.trim(),
      ranking: values.ranking.trim() ? Number(values.ranking) : null,
      crawl_enabled: values.crawl_enabled,
      notes: values.notes.trim(),
      description: values.description.trim(),
      contact_email: values.contact_email.trim(),
      contact_phone: values.contact_phone.trim(),
      address: values.address.trim(),
    };

    create.mutate(payload, {
      onSuccess: (institution) => {
        if (!logo && !banner) {
          void navigate("/admin/institutions");
          return;
        }
        upload.mutate(
          { id: institution.id, logo: logo ?? undefined, banner: banner ?? undefined },
          { onSuccess: () => void navigate("/admin/institutions") },
        );
      },
    });
  };

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-content space-y-6 pb-24">
      <div>
        <Button variant="quiet" size="sm" onClick={() => void navigate("/admin/institutions")} type="button">
          ← Manage institutions
        </Button>
        <h1 className="mt-2 font-display text-heading-xl font-bold">Add an institution</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          <span aria-hidden="true" className="text-danger">
            *
          </span>{" "}
          Required. Everything else can be filled in now, or left for a recruiter to add once
          they are assigned.
        </p>
      </div>

      <Card as="section" className="space-y-4">
        <h2 className="font-display text-heading-sm font-semibold">Basics</h2>
        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
          <Field id="institution-name" label="Name" required>
            <Input
              id="institution-name"
              value={values.name}
              onChange={(event) => set("name", event.target.value)}
              disabled={pending}
              required
            />
          </Field>

          <Field id="institution-careers-url" label="Careers URL">
            <Input
              id="institution-careers-url"
              type="url"
              value={values.careers_url}
              onChange={(event) => set("careers_url", event.target.value)}
              placeholder="https://www.example.ac.uk/jobs"
              disabled={pending}
            />
          </Field>

          <Field id="institution-website" label="Website">
            <Input
              id="institution-website"
              type="url"
              value={values.website}
              onChange={(event) => set("website", event.target.value)}
              placeholder="https://www.example.ac.uk"
              disabled={pending}
            />
          </Field>
        </div>
      </Card>

      <Card as="section" className="space-y-4">
        <h2 className="font-display text-heading-sm font-semibold">Classification</h2>
        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
          <Field id="institution-nation" label="Nation">
            <Select
              id="institution-nation"
              value={values.nation}
              onChange={(event) => set("nation", event.target.value as Nation)}
              disabled={pending}
            >
              {NATIONS.map((nation) => (
                <option key={nation.value} value={nation.value}>
                  {nation.label}
                </option>
              ))}
            </Select>
          </Field>

          <Field id="institution-type" label="Institution type">
            <Select
              id="institution-type"
              value={values.institution_type}
              onChange={(event) => set("institution_type", event.target.value as InstitutionType)}
              disabled={pending}
            >
              {INSTITUTION_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
          </Field>

          <Field id="institution-city" label="City">
            <Input
              id="institution-city"
              value={values.city}
              onChange={(event) => set("city", event.target.value)}
              disabled={pending}
            />
          </Field>

          <Field id="institution-ranking" label="Ranking">
            <Input
              id="institution-ranking"
              type="number"
              min={1}
              value={values.ranking}
              onChange={(event) => set("ranking", event.target.value)}
              placeholder="Complete University Guide position"
              disabled={pending}
            />
          </Field>
        </div>
      </Card>

      <Card as="section" className="space-y-4">
        <h2 className="font-display text-heading-sm font-semibold">Crawl settings</h2>
        <label
          className="flex h-11 items-center gap-2 text-body-sm text-text-primary"
          htmlFor="institution-crawl-enabled"
        >
          <input
            id="institution-crawl-enabled"
            type="checkbox"
            checked={values.crawl_enabled}
            onChange={(event) => set("crawl_enabled", event.target.checked)}
            disabled={pending}
            className="h-5 w-5 accent-[var(--color-brand)]"
          />
          Crawl this institution
        </label>
        <Field id="institution-notes" label="Notes" full>
          <Textarea
            id="institution-notes"
            rows={3}
            value={values.notes}
            onChange={(event) => set("notes", event.target.value)}
            placeholder="Anything an operator should know about this institution's portal."
            disabled={pending}
          />
        </Field>
      </Card>

      <Card as="section" className="space-y-4">
        <h2 className="font-display text-heading-sm font-semibold">Public profile</h2>
        <Field id="institution-description" label="About this institution" full>
          <Textarea
            id="institution-description"
            rows={6}
            value={values.description}
            onChange={(event) => set("description", event.target.value)}
            placeholder="Shown on the institution's page. Plain text — line breaks are kept."
            disabled={pending}
          />
        </Field>

        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
          <Field id="institution-contact-email" label="Contact email">
            <Input
              id="institution-contact-email"
              type="email"
              value={values.contact_email}
              onChange={(event) => set("contact_email", event.target.value)}
              placeholder="careers@example.ac.uk"
              disabled={pending}
            />
          </Field>

          <Field id="institution-contact-phone" label="Contact phone">
            <Input
              id="institution-contact-phone"
              type="tel"
              value={values.contact_phone}
              onChange={(event) => set("contact_phone", event.target.value)}
              placeholder="01223 000000"
              disabled={pending}
            />
          </Field>
        </div>

        <Field id="institution-address" label="Postal address" full>
          <Textarea
            id="institution-address"
            rows={3}
            value={values.address}
            onChange={(event) => set("address", event.target.value)}
            placeholder="Shown to a candidate as the institution's address."
            disabled={pending}
          />
        </Field>
      </Card>

      <Card as="section" className="space-y-4">
        <h2 className="font-display text-heading-sm font-semibold">Branding</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <span className={slotLabel}>Logo</span>
            {logoPreviewUrl ? (
              <img src={logoPreviewUrl} alt="" className="h-16 w-16 rounded-md object-contain" />
            ) : (
              <span className="flex items-center gap-2 text-body-sm text-text-muted">
                <MonogramTile name={values.name || "?"} />
                None yet — the monogram is used instead
              </span>
            )}
            <FileInput
              id="institution-logo"
              label="Upload a logo"
              buttonLabel={logo ? "Change logo" : "Choose logo"}
              accept="image/*"
              disabled={pending}
              fileName={logo?.name}
              onFileChange={setLogo}
            />
          </div>

          <div className="space-y-2">
            <span className={slotLabel}>Banner</span>
            {bannerPreviewUrl ? (
              <img src={bannerPreviewUrl} alt="" className="h-20 w-full rounded-md object-cover" />
            ) : (
              <p className="text-body-sm text-text-muted">None yet</p>
            )}
            <FileInput
              id="institution-banner"
              label="Upload a banner"
              buttonLabel={banner ? "Change banner" : "Choose banner"}
              accept="image/*"
              disabled={pending}
              fileName={banner?.name}
              onFileChange={setBanner}
            />
          </div>
        </div>
      </Card>

      {create.isError ? <ErrorMessage error={create.error} /> : null}
      {upload.isError ? <ErrorMessage error={upload.error} /> : null}

      <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t border-border-subtle bg-surface px-4 py-3">
        <Button variant="quiet" type="button" onClick={() => void navigate("/admin/institutions")}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={pending}>
          {pending ? "Saving…" : "Add institution"}
        </Button>
      </div>
    </form>
  );
}

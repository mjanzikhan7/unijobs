import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { FileInput } from "@/components/Field/FileInput";
import { Input } from "@/components/Field/Input";
import { Textarea } from "@/components/Field/Textarea";
import { ErrorMessage } from "@/components/Feedback";
import { MonogramTile } from "@/components/MonogramTile/MonogramTile";
import type { Institution } from "@/models/api/types";
import { useUpdateInstitution, useUploadInstitutionMedia } from "@/viewmodels/useInstitutions";

const slotLabel = "text-overline font-semibold tracking-wide text-text-muted uppercase";
const fieldLabel = "block text-body-sm font-medium text-text-primary";

export function InstitutionBranding({ institution }: { institution: Institution }) {
  const update = useUpdateInstitution();
  const upload = useUploadInstitutionMedia();
  const [description, setDescription] = useState(institution.description ?? "");
  const [contactEmail, setContactEmail] = useState(institution.contact_email ?? "");
  const [contactPhone, setContactPhone] = useState(institution.contact_phone ?? "");
  const [address, setAddress] = useState(institution.address ?? "");

  const pick = (field: "logo" | "banner") => (file: File | null) => {
    if (file) upload.mutate({ id: institution.id, [field]: file });
  };

  return (
    <Card className="space-y-4">
      <h3 className="font-display text-heading-sm font-semibold">{institution.name}</h3>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <span className={slotLabel}>Logo</span>
          {institution.logo_url ? (
            <img
              src={institution.logo_url}
              alt=""
              className="h-16 w-16 rounded-md object-contain"
            />
          ) : (
            <span className="flex items-center gap-2 text-body-sm text-text-muted">
              <MonogramTile name={institution.name} />
              None yet — the monogram is used instead
            </span>
          )}
          <FileInput
            id={`logo-${institution.id}`}
            label={`Upload a logo for ${institution.name}`}
            buttonLabel="Choose logo"
            accept="image/*"
            disabled={upload.isPending}
            onFileChange={pick("logo")}
          />
        </div>

        <div className="space-y-2">
          <span className={slotLabel}>Banner</span>
          {institution.banner_url ? (
            <img
              src={institution.banner_url}
              alt=""
              className="h-20 w-full rounded-md object-cover"
            />
          ) : (
            <p className="text-body-sm text-text-muted">None yet</p>
          )}
          <FileInput
            id={`banner-${institution.id}`}
            label={`Upload a banner for ${institution.name}`}
            buttonLabel="Choose banner"
            accept="image/*"
            disabled={upload.isPending}
            onFileChange={pick("banner")}
          />
        </div>
      </div>

      {upload.isPending ? <p className="text-body-sm text-text-muted">Uploading…</p> : null}
      {upload.isError ? <ErrorMessage error={upload.error} /> : null}

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          update.mutate({
            id: institution.id,
            changes: {
              description,
              contact_email: contactEmail,
              contact_phone: contactPhone,
              address,
            },
          });
        }}
      >
        <div className="space-y-2">
          <label htmlFor={`description-${institution.id}`} className={fieldLabel}>
            About this institution
          </label>
          <Textarea
            id={`description-${institution.id}`}
            rows={6}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Shown on the institution's page. Plain text — line breaks are kept."
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor={`contact-email-${institution.id}`} className={fieldLabel}>
              Contact email
            </label>
            <Input
              id={`contact-email-${institution.id}`}
              type="email"
              value={contactEmail}
              onChange={(event) => setContactEmail(event.target.value)}
              placeholder="careers@example.ac.uk"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor={`contact-phone-${institution.id}`} className={fieldLabel}>
              Contact phone
            </label>
            <Input
              id={`contact-phone-${institution.id}`}
              type="tel"
              value={contactPhone}
              onChange={(event) => setContactPhone(event.target.value)}
              placeholder="01223 000000"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor={`address-${institution.id}`} className={fieldLabel}>
            Postal address
          </label>
          <Textarea
            id={`address-${institution.id}`}
            rows={3}
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="Shown to a candidate as the institution's address."
          />
        </div>

        {update.isError ? <ErrorMessage error={update.error} /> : null}
        <Button type="submit" variant="primary" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save about & contact details"}
        </Button>
      </form>
    </Card>
  );
}

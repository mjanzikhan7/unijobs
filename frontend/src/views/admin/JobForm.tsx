import type { ReactNode } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Input } from "@/components/Field/Input";
import { Select } from "@/components/Field/Select";
import { Textarea } from "@/components/Field/Textarea";
import type { Institution } from "@/models/api/types";
import type { JobFormFields } from "@/viewmodels/useJobs";
import {
  ACADEMIC_DISCIPLINES,
  DISCIPLINE_LABELS,
  PROFESSIONAL_DISCIPLINES,
  humanise,
} from "@/utilities/format";

export interface JobFormValues extends JobFormFields {
  institution: string;
  source_url: string;
}

interface JobFormProps {
  values: JobFormValues;
  onChange: (values: JobFormValues) => void;
  institutionOptions: Institution[];
  lockedInstitution?: { slug: string; name: string };
  disabled?: boolean;
}

const CONTRACT_TYPES = ["PERMANENT", "FIXED_TERM", "CASUAL", "SECONDMENT"] as const;
const HOURS = ["FULL_TIME", "PART_TIME"] as const;
const WORKPLACES = ["ON_SITE", "HYBRID", "REMOTE"] as const;

const fieldLabel = "block text-body-sm font-medium text-text-primary";

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

export function JobForm({
  values,
  onChange,
  institutionOptions,
  lockedInstitution,
  disabled = false,
}: JobFormProps) {
  const set = <K extends keyof JobFormValues>(key: K, value: JobFormValues[K]) =>
    onChange({ ...values, [key]: value });

  return (
    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
      <Field id="job-institution" label="Institution" required>
        {lockedInstitution ? (
          <p className="flex h-11 items-center gap-2 rounded-sm border border-border-subtle bg-surface-sunken px-3 text-body text-text-secondary">
            <Icon name="institutions" className="h-4 w-4 shrink-0 text-text-muted" />
            {lockedInstitution.name}
          </p>
        ) : (
          <Select
            id="job-institution"
            value={values.institution}
            onChange={(event) => set("institution", event.target.value)}
            disabled={disabled}
            required
          >
            <option value="">Choose an institution…</option>
            {institutionOptions.map((institution) => (
              <option key={institution.slug} value={institution.slug}>
                {institution.name}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field id="job-title" label="Title" required>
        <Input
          id="job-title"
          value={values.title}
          onChange={(event) => set("title", event.target.value)}
          disabled={disabled}
          required
        />
      </Field>

      <Field id="job-source-url" label="Source URL" required>
        {lockedInstitution ? (
          <p className="flex h-11 items-center gap-2 rounded-sm border border-border-subtle bg-surface-sunken px-3 text-body text-text-secondary">
            <Icon name="external-link" className="h-4 w-4 shrink-0 text-text-muted" />
            <span className="min-w-0 truncate">{values.source_url}</span>
          </p>
        ) : (
          <Input
            id="job-source-url"
            type="url"
            value={values.source_url}
            onChange={(event) => set("source_url", event.target.value)}
            disabled={disabled}
            required
          />
        )}
      </Field>

      <Field id="job-reference" label="Reference">
        <Input
          id="job-reference"
          value={values.reference}
          onChange={(event) => set("reference", event.target.value)}
          disabled={disabled}
        />
      </Field>

      <Field id="job-department" label="Department">
        <Input
          id="job-department"
          value={values.department}
          onChange={(event) => set("department", event.target.value)}
          disabled={disabled}
        />
      </Field>

      <Field id="job-category" label="Category">
        <Input
          id="job-category"
          value={values.category}
          onChange={(event) => set("category", event.target.value)}
          disabled={disabled}
        />
      </Field>

      <Field id="job-discipline" label="Discipline">
        <Select
          id="job-discipline"
          value={values.discipline}
          onChange={(event) => set("discipline", event.target.value)}
          disabled={disabled}
        >
          <option value="">Let the classifier decide</option>
          <optgroup label="Academic discipline / field of expertise">
            {ACADEMIC_DISCIPLINES.map((discipline) => (
              <option key={discipline} value={discipline}>
                {DISCIPLINE_LABELS[discipline]}
              </option>
            ))}
          </optgroup>
          <optgroup label="Professional, managerial & support services">
            {PROFESSIONAL_DISCIPLINES.map((discipline) => (
              <option key={discipline} value={discipline}>
                {DISCIPLINE_LABELS[discipline]}
              </option>
            ))}
          </optgroup>
        </Select>
      </Field>

      <Field id="job-salary" label="Salary as advertised">
        <Input
          id="job-salary"
          value={values.salary_raw}
          onChange={(event) => set("salary_raw", event.target.value)}
          disabled={disabled}
          placeholder="e.g. £44,120 to £51,300 per annum"
        />
      </Field>

      <Field id="job-grade" label="Grade">
        <Input
          id="job-grade"
          value={values.grade_raw}
          onChange={(event) => set("grade_raw", event.target.value)}
          disabled={disabled}
        />
      </Field>

      <Field id="job-contract" label="Contract">
        <Select
          id="job-contract"
          value={values.contract_type}
          onChange={(event) => set("contract_type", event.target.value)}
          disabled={disabled}
        >
          <option value="">Let the classifier decide</option>
          {CONTRACT_TYPES.map((type) => (
            <option key={type} value={type}>
              {humanise(type)}
            </option>
          ))}
        </Select>
      </Field>

      <Field id="job-hours" label="Hours">
        <Select
          id="job-hours"
          value={values.hours}
          onChange={(event) => set("hours", event.target.value)}
          disabled={disabled}
        >
          <option value="">Let the classifier decide</option>
          {HOURS.map((hours) => (
            <option key={hours} value={hours}>
              {humanise(hours)}
            </option>
          ))}
        </Select>
      </Field>

      <Field id="job-workplace" label="Workplace">
        <Select
          id="job-workplace"
          value={values.workplace}
          onChange={(event) => set("workplace", event.target.value)}
          disabled={disabled}
        >
          <option value="">Let the classifier decide</option>
          {WORKPLACES.map((workplace) => (
            <option key={workplace} value={workplace}>
              {humanise(workplace)}
            </option>
          ))}
        </Select>
      </Field>

      <Field id="job-posted-date" label="Posted date">
        <Input
          id="job-posted-date"
          type="date"
          value={values.posted_date ?? ""}
          onChange={(event) => set("posted_date", event.target.value || null)}
          disabled={disabled}
        />
      </Field>

      <Field id="job-closing-date" label="Closing date">
        <Input
          id="job-closing-date"
          type="date"
          value={values.closing_date ?? ""}
          onChange={(event) => set("closing_date", event.target.value || null)}
          disabled={disabled}
        />
      </Field>

      <Field id="job-description" label="Description" full>
        <Textarea
          id="job-description"
          rows={10}
          value={values.description_html}
          onChange={(event) => set("description_html", event.target.value)}
          disabled={disabled}
        />
      </Field>
    </div>
  );
}

export const EMPTY_JOB_FORM: JobFormValues = {
  institution: "",
  source_url: "",
  title: "",
  department: "",
  category: "",
  reference: "",
  location_raw: "",
  city: "",
  salary_raw: "",
  grade_raw: "",
  contract_raw: "",
  hours_raw: "",
  contract_type: "",
  hours: "",
  workplace: "",
  discipline: "",
  description_html: "",
  closing_date: null,
  posted_date: null,
};

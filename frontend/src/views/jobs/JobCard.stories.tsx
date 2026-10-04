import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router-dom";

import type { Job, Screening } from "@/models/api/types";

import { JobCard } from "./JobCard";

const screening: Screening = {
  sponsor_verdict: "CONFIRMED",
  sponsor_matched_name: "Northgate University",
  threshold_verdict: "TARGET_BAND",
  threshold_explanation: "£47,940 clears the general threshold and the going rate for SOC 2133.",
  salary_min: "47940",
  salary_max: "57120",
  ruleset_version: 4,
};

const job: Job = {
  id: 1,
  title: "Senior Research Software Engineer",
  institution_name: "Northgate University",
  institution_slug: "northgate-university",
  nation: "ENGLAND",
  department: "Research Computing",
  city: "Leeds",
  location_raw: "Leeds, West Yorkshire",
  salary_raw: "Grade 8: £47,940 - £57,120 per annum",
  grade_raw: "Grade 8",
  contract_type: "PERMANENT",
  hours: "FULL_TIME",
  workplace: "HYBRID",
  posted_date: "2026-08-28",
  closing_date: "2026-09-15",
  status: "OPEN",
  source: "PORTAL",
  source_url: "https://jobs.northgate.ac.uk/vacancy/1",
  first_seen_at: "2026-08-28T09:00:00Z",
  last_seen_at: "2026-09-06T06:00:00Z",
  screening,
  is_saved: false,
  fitness_score: 82,
  fitness_reasons: [],
};

const meta: Meta<typeof JobCard> = {
  title: "Jobs/JobCard",
  component: JobCard,
  args: { job },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <div className="max-w-[720px]">
          <Story />
        </div>
      </MemoryRouter>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof JobCard>;

export const Default: Story = {};

export const Saved: Story = {
  args: { job: { ...job, is_saved: true }, onSave: () => {} },
};

export const BRatedAndLateral: Story = {
  args: {
    job: {
      ...job,
      id: 2,
      title: "Lecturer in Cyber Security",
      institution_name: "Brackenfield Institute of Technology",
      city: "Dundee",
      salary_raw: "£40,521 - £49,794 per annum",
      fitness_score: 61,
      screening: {
        ...screening,
        sponsor_verdict: "B_RATED",
        threshold_verdict: "LATERAL_CONTINGENT",
        salary_min: "40521",
        salary_max: "49794",
      },
    },
  },
};

export const AdvertExcludesSponsorship: Story = {
  args: {
    job: {
      ...job,
      id: 3,
      title: "Head of Digital Infrastructure",
      institution_name: "Wearmouth Metropolitan University",
      city: "Sunderland",
      fitness_score: 73,
      screening: { ...screening, advert_excludes_sponsorship: true },
    },
  },
};

export const SalaryUnclear: Story = {
  args: {
    job: {
      ...job,
      id: 4,
      salary_raw: "Competitive salary, dependent on experience",
      screening: {
        ...screening,
        threshold_verdict: "SALARY_UNCLEAR",
        salary_min: null,
        salary_max: null,
      },
    },
  },
};

export const NotScreened: Story = {
  args: { job: { ...job, screening: undefined as unknown as Screening, fitness_score: 0 } },
};

export const NoLongerListed: Story = {
  args: { job: { ...job, status: "DISAPPEARED" } },
};

export const KeyboardFocused: Story = { args: { isFocused: true } };

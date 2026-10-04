import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { TermChipGroup } from "./TermChipGroup";

const terms = ["Python", "Kubernetes", "CI/CD", "Terraform", "Fortran", "MATLAB"];

const meta: Meta<typeof TermChipGroup> = {
  title: "Primitives/TermChipGroup",
  component: TermChipGroup,
};

export default meta;
type Story = StoryObj<typeof TermChipGroup>;

export const AllSuggested: Story = {
  render: function AllSuggestedStory() {
    const [selected, setSelected] = useState(terms);
    return (
      <TermChipGroup
        field="skills"
        label="Skills"
        terms={terms}
        selected={selected}
        onToggle={(term) =>
          setSelected((current) =>
            current.includes(term) ? current.filter((item) => item !== term) : [...current, term],
          )
        }
      />
    );
  },
};

export const SomeRejected: Story = {
  args: {
    field: "skills",
    label: "Skills",
    terms,
    selected: terms.slice(0, 4),
    onToggle: () => {},
  },
};

export const NothingFound: Story = {
  args: { field: "education", label: "Education", terms: [], selected: [], onToggle: () => {} },
};

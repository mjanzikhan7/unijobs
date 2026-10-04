import type { Meta, StoryObj } from "@storybook/react-vite";

import { CVDropzone } from "./CVDropzone";

const meta: Meta<typeof CVDropzone> = {
  title: "Primitives/CVDropzone",
  component: CVDropzone,
  args: { onFile: () => {} },
  decorators: [
    (Story) => (
      <div className="max-w-prose">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof CVDropzone>;

export const Idle: Story = {};
export const Uploading: Story = { args: { uploading: true } };
export const Parsed: Story = { args: { fileName: "a-morgan-cv.pdf" } };
export const Rejected: Story = {
  args: { error: "That file is larger than 5MB. Try exporting it again at a lower quality." },
};

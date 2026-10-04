import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useProfiles } from "./useProfiles";
import { paginate, storeWrapper, stubFetch } from "@/test-utils";
import type { CandidateProfile } from "@/models/api/types";

describe("useProfiles", () => {
  it("fetches the profiles list", async () => {
    const profile = { id: 1, headline: "Research software engineer" } as unknown as CandidateProfile;
    stubFetch({ "/profiles/": paginate([profile]) });

    const { result } = renderHook(() => useProfiles(), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.data?.results).toHaveLength(1));
    expect(result.current.data?.results[0]).toEqual(profile);
  });
});

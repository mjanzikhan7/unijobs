import { Button } from "@/components/Button/Button";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { filterLabel } from "@/utilities/format";

interface JobListEmptyProps {
  restrictiveFilter: string | null;
  filterValue?: string;
  onClearFilter: (key: string) => void;
  onClearAll: () => void;
  activeFilters: number;
}

export function JobListEmpty({
  restrictiveFilter,
  filterValue,
  onClearFilter,
  onClearAll,
  activeFilters,
}: JobListEmptyProps) {
  if (activeFilters === 0) {
    return (
      <EmptyPanel
        title="No vacancies yet"
        body="Nothing has been crawled into this view. Start a crawl from the crawl console to populate it."
      />
    );
  }

  return (
    <EmptyPanel
      title="No jobs match these filters"
      body={
        restrictiveFilter ? (
          <>
            <strong>{filterLabel(restrictiveFilter)}</strong>
            {filterValue ? ` (${filterValue})` : ""} is the most restrictive filter you have on.
          </>
        ) : (
          "Try removing a filter."
        )
      }
      action={
        <>
          {restrictiveFilter ? (
            <Button onClick={() => onClearFilter(restrictiveFilter)}>
              Clear {filterLabel(restrictiveFilter).toLowerCase()}
            </Button>
          ) : null}
          <Button variant="quiet" onClick={onClearAll}>
            Clear all {activeFilters} filters
          </Button>
        </>
      }
    />
  );
}

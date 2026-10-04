import { Icon } from "@/components/Icon/Icon";
import { useActiveRun } from "@/viewmodels/useActiveRun";
import { useReviewQueue } from "@/viewmodels/useInstitutions";

export function CrawlRunningPip() {
  const activeRun = useActiveRun();
  if (!activeRun.data?.run) return null;

  return (
    <span
      title="A crawl is running"
      aria-label="A crawl is running"
      role="img"
      className="ml-auto flex shrink-0 items-center text-success"
    >
      <Icon
        name="crawl"
        className="h-4 w-4 motion-safe:animate-spin motion-safe:[animation-duration:2.5s]"
      />
    </span>
  );
}

export function ReviewQueueBadge() {
  const reviewQueue = useReviewQueue();
  const count = reviewQueue.data?.length ?? 0;
  if (count === 0) return null;

  return (
    <span
      aria-label={`${count} awaiting review`}
      className="ml-auto inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-brand px-1.5 text-micro font-semibold tabular-nums text-text-inverse"
    >
      {count}
    </span>
  );
}

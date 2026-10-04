import { Card } from "@/components/Card/Card";
import { Skeleton } from "@/components/Skeleton/Skeleton";

export function JobCardSkeleton() {
  return (
    <Card aria-hidden="true">
      <Skeleton className="h-5 w-3/5" />
      <Skeleton className="mt-3 h-4 w-2/5" />
      <Skeleton className="mt-3 h-5 w-[85%]" />
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-6 w-28 rounded-full" />
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
    </Card>
  );
}

export function JobListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <ol aria-hidden="true" className="flex flex-col gap-3">
      {Array.from({ length: rows }, (_, index) => (
        <li key={index}>
          <JobCardSkeleton />
        </li>
      ))}
    </ol>
  );
}

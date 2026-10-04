import styles from "./Skeleton.module.css";

export interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "h-4 w-full" }: SkeletonProps) {
  return <span aria-hidden="true" className={`block rounded-sm ${styles.shimmer} ${className}`} />;
}

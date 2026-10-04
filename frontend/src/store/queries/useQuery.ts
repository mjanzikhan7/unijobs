import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { hashKey } from "./queryKey";
import type { QueryKey } from "./queryKey";
import { queryRefetchRequested, querySubscribed, queryUnsubscribed } from "./slice";
import type { QueriesRootState, QueryObserver, RetryPolicy } from "./slice";

export interface UseQueryOptions<TData> {
  queryKey: QueryKey;
  queryFn: (context: { previous: TData | undefined }) => Promise<TData>;
  enabled?: boolean;
  staleTime?: number;
  retry?: RetryPolicy;
  refetchInterval?: number | ((data: TData | undefined) => number | false);
  placeholderData?: (previous: TData | undefined) => TData | undefined;
}

export interface UseQueryResult<TData> {
  data: TData | undefined;
  error: Error | null;
  status: "pending" | "success" | "error";
  fetchStatus: "idle" | "fetching";
  isPending: boolean;
  isLoading: boolean;
  isFetching: boolean;
  isSuccess: boolean;
  isError: boolean;
  isPlaceholderData: boolean;
  failureCount: number;
  refetch: () => Promise<void>;
}

function toObserver<TData>(options: UseQueryOptions<TData>): QueryObserver {
  return {
    enabled: options.enabled ?? true,
    queryFn: ({ previous }) => options.queryFn({ previous: previous as TData | undefined }),
    staleTime: options.staleTime,
    retry: options.retry,
    refetchInterval: options.refetchInterval as QueryObserver["refetchInterval"],
  };
}

export function useQuery<TData>(options: UseQueryOptions<TData>): UseQueryResult<TData> {
  const dispatch = useDispatch();
  const observerId = useId();
  const hash = hashKey(options.queryKey);
  const enabled = options.enabled ?? true;
  const entry = useSelector((state: QueriesRootState) => state.queries[hash]);

  const latest = useRef(options);
  useEffect(() => {
    latest.current = options;
  });

  useEffect(() => {
    const key = latest.current.queryKey;
    dispatch(querySubscribed({ key, observerId }, () => toObserver(latest.current)));
    return () => {
      dispatch(queryUnsubscribed({ key, observerId }));
    };
  }, [dispatch, hash, enabled, observerId]);

  const data = entry?.data as TData | undefined;
  const [previous, setPrevious] = useState<TData | undefined>(undefined);
  if (data !== undefined && data !== previous) setPrevious(data);

  const placeholder =
    data === undefined && options.placeholderData ? options.placeholderData(previous) : undefined;
  const isPlaceholderData = placeholder !== undefined;

  const status = isPlaceholderData ? "success" : (entry?.status ?? "pending");
  const isFetching = entry ? entry.fetchStatus === "fetching" : enabled;

  const refetch = useCallback(
    () =>
      new Promise<void>((resolve) => {
        dispatch(queryRefetchRequested({ key: JSON.parse(hash) as QueryKey }, resolve));
      }),
    [dispatch, hash],
  );

  return {
    data: data !== undefined ? data : placeholder,
    error: entry?.error ?? null,
    status,
    fetchStatus: isFetching ? "fetching" : "idle",
    isPending: status === "pending",
    isLoading: status === "pending" && isFetching,
    isFetching,
    isSuccess: status === "success",
    isError: status === "error",
    isPlaceholderData,
    failureCount: entry?.failureCount ?? 0,
    refetch,
  };
}

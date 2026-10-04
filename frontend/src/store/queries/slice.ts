import { createAction, createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";

import { hashKey, keyStartsWith } from "./queryKey";
import type { QueryKey } from "./queryKey";

export interface QueryEntry {
  key: QueryKey;
  data: unknown;
  error: Error | null;
  status: "pending" | "success" | "error";
  fetchStatus: "idle" | "fetching";
  dataUpdatedAt: number;
  isInvalidated: boolean;
  failureCount: number;
}

export type QueriesState = Record<string, QueryEntry>;

export interface QueriesRootState {
  queries: QueriesState;
}

export type RetryPolicy = boolean | ((failureCount: number, error: unknown) => boolean);

export interface QueryObserver {
  enabled: boolean;
  queryFn: (context: { previous: unknown }) => Promise<unknown>;
  staleTime?: number;
  retry?: RetryPolicy;
  refetchInterval?: number | ((data: unknown) => number | false);
}

function entryFor(state: QueriesState, key: QueryKey): QueryEntry {
  const hash = hashKey(key);
  return (state[hash] ??= {
    key,
    data: undefined,
    error: null,
    status: "pending",
    fetchStatus: "idle",
    dataUpdatedAt: 0,
    isInvalidated: false,
    failureCount: 0,
  });
}

const initialState: QueriesState = {};

const slice = createSlice({
  name: "queries",
  initialState,
  reducers: {
    fetchStarted(state, action: PayloadAction<{ key: QueryKey }>) {
      const entry = entryFor(state, action.payload.key);
      entry.fetchStatus = "fetching";
      entry.failureCount = 0;
    },
    fetchRetried(state, action: PayloadAction<{ key: QueryKey; failureCount: number }>) {
      entryFor(state, action.payload.key).failureCount = action.payload.failureCount;
    },
    fetchSucceeded: {
      reducer(state, action: PayloadAction<{ key: QueryKey; data: unknown; at: number }>) {
        const entry = entryFor(state, action.payload.key);
        entry.data = action.payload.data;
        entry.error = null;
        entry.status = "success";
        entry.fetchStatus = "idle";
        entry.dataUpdatedAt = action.payload.at;
        entry.isInvalidated = false;
        entry.failureCount = 0;
      },
      prepare: (payload: { key: QueryKey; data: unknown }) => ({
        payload: { ...payload, at: Date.now() },
      }),
    },
    fetchFailed(
      state,
      action: PayloadAction<{ key: QueryKey; error: Error; failureCount: number }>,
    ) {
      const entry = entryFor(state, action.payload.key);
      entry.error = action.payload.error;
      entry.status = "error";
      entry.fetchStatus = "idle";
      entry.failureCount = action.payload.failureCount;
    },
    fetchCancelled(state, action: PayloadAction<{ key: QueryKey }>) {
      const entry = state[hashKey(action.payload.key)];
      if (entry) entry.fetchStatus = "idle";
    },
    queryDataSet: {
      reducer(state, action: PayloadAction<{ key: QueryKey; data: unknown; at: number }>) {
        const entry = entryFor(state, action.payload.key);
        entry.data = action.payload.data;
        entry.error = null;
        entry.status = "success";
        entry.dataUpdatedAt = action.payload.at;
      },
      prepare: (payload: { key: QueryKey; data: unknown }) => ({
        payload: { ...payload, at: Date.now() },
      }),
    },
    queriesInvalidated(state, action: PayloadAction<{ key: QueryKey }>) {
      for (const entry of Object.values(state)) {
        if (keyStartsWith(entry.key, action.payload.key)) entry.isInvalidated = true;
      }
    },
    queriesCleared(state, action: PayloadAction<{ except?: QueryKey }>) {
      const { except } = action.payload;
      for (const [hash, entry] of Object.entries(state)) {
        if (!except || !keyStartsWith(entry.key, except)) delete state[hash];
      }
    },
    queryRemoved(state, action: PayloadAction<{ key: QueryKey }>) {
      delete state[hashKey(action.payload.key)];
    },
  },
});

export const queriesReducer = slice.reducer;
export const {
  fetchStarted,
  fetchRetried,
  fetchSucceeded,
  fetchFailed,
  fetchCancelled,
  queryDataSet,
  queriesInvalidated,
  queriesCleared,
  queryRemoved,
} = slice.actions;

export const querySubscribed = createAction(
  "queries/subscribed",
  (payload: { key: QueryKey; observerId: string }, getOptions: () => QueryObserver) => ({
    payload,
    meta: { getOptions },
  }),
);

export const queryUnsubscribed = createAction<{ key: QueryKey; observerId: string }>(
  "queries/unsubscribed",
);

export const queryRefetchRequested = createAction(
  "queries/refetchRequested",
  (payload: { key: QueryKey }, done: () => void) => ({ payload, meta: { done } }),
);

export const queriesCancelRequested = createAction<{ key: QueryKey }>("queries/cancelRequested");

export function selectQueries(state: QueriesRootState): QueriesState {
  return state.queries;
}

export function selectQuery(state: QueriesRootState, key: QueryKey): QueryEntry | undefined {
  return state.queries[hashKey(key)];
}

export function selectQueryData(state: QueriesRootState, key: QueryKey): unknown {
  return state.queries[hashKey(key)]?.data;
}

export function selectQueriesData(
  state: QueriesRootState,
  prefix: QueryKey,
): [QueryKey, unknown][] {
  return Object.values(state.queries)
    .filter((entry) => keyStartsWith(entry.key, prefix) && entry.data !== undefined)
    .map((entry) => [entry.key, entry.data]);
}

import type { Task } from "redux-saga";
import { all, call, cancel, delay, put, race, select, spawn, take, takeEvery } from "redux-saga/effects";
import type { Action } from "@reduxjs/toolkit";

import { toError } from "../saga";
import type { Saga } from "../saga";
import { hashKey, keyStartsWith } from "./queryKey";
import type { QueryKey } from "./queryKey";
import {
  fetchCancelled,
  fetchFailed,
  fetchRetried,
  fetchStarted,
  fetchSucceeded,
  queriesCancelRequested,
  queriesCleared,
  queriesInvalidated,
  queryDataSet,
  queryRefetchRequested,
  queryRemoved,
  querySubscribed,
  queryUnsubscribed,
  selectQueries,
  selectQuery,
  selectQueryData,
} from "./slice";
import type { QueriesState, QueryEntry, QueryObserver, RetryPolicy } from "./slice";

export interface QueryDefaults {
  staleTime: number;
  gcTime: number;
  retry: RetryPolicy;
}

const MAX_RETRY_DELAY = 30_000;

function shouldRetry(policy: RetryPolicy, failureCount: number, error: unknown): boolean {
  if (typeof policy === "function") return policy(failureCount, error);
  return policy && failureCount < 3;
}

function needsFetch(entry: QueryEntry | undefined, staleTime: number): boolean {
  if (!entry || entry.status !== "success" || entry.isInvalidated) return true;
  return Date.now() - entry.dataUpdatedAt >= staleTime;
}

export function createQueriesSaga(defaults: QueryDefaults): () => Saga {
  const observers = new Map<string, Map<string, () => QueryObserver>>();
  const fetches = new Map<string, { key: QueryKey; task: Task }>();
  const polls = new Map<string, Task>();
  const collectors = new Map<string, Task>();

  function observersOf(hash: string): QueryObserver[] {
    return [...(observers.get(hash)?.values() ?? [])].map((getOptions) => getOptions());
  }

  function isOnScreen(hash: string): boolean {
    return observersOf(hash).some((observer) => observer.enabled);
  }

  function settles(hash: string) {
    return (action: Action): boolean =>
      (fetchSucceeded.match(action) ||
        fetchFailed.match(action) ||
        fetchCancelled.match(action) ||
        queryDataSet.match(action)) &&
      hashKey(action.payload.key) === hash;
  }

  function* runFetch(key: QueryKey): Saga {
    const hash = hashKey(key);
    const mounted = observersOf(hash);
    const observer = mounted.filter((candidate) => candidate.enabled).at(-1) ?? mounted.at(-1);
    if (!observer) return;

    const retry = observer.retry ?? defaults.retry;
    let failureCount = 0;
    try {
      yield put(fetchStarted({ key }));
      while (true) {
        try {
          const previous = yield select(selectQueryData, key);
          const data = yield call(observer.queryFn, { previous });
          yield put(fetchSucceeded({ key, data }));
          return;
        } catch (thrown) {
          failureCount += 1;
          if (!shouldRetry(retry, failureCount - 1, thrown)) {
            yield put(fetchFailed({ key, error: toError(thrown), failureCount }));
            return;
          }
          yield put(fetchRetried({ key, failureCount }));
          yield delay(Math.min(1000 * 2 ** (failureCount - 1), MAX_RETRY_DELAY));
        }
      }
    } finally {
      fetches.delete(hash);
    }
  }

  function* startFetch(key: QueryKey): Saga {
    const hash = hashKey(key);
    if (fetches.has(hash)) return;
    const task = (yield spawn(runFetch, key)) as Task;
    if (task.isRunning()) fetches.set(hash, { key, task });
  }

  function* stopFetch(hash: string): Saga {
    const running = fetches.get(hash);
    if (running) yield cancel(running.task);
  }

  function* poll(key: QueryKey, getOptions: () => QueryObserver): Saga {
    const hash = hashKey(key);
    while (true) {
      const data = yield select(selectQueryData, key);
      const { refetchInterval } = getOptions();
      const interval =
        typeof refetchInterval === "function" ? refetchInterval(data) : (refetchInterval ?? false);
      if (interval === false) {
        yield take(settles(hash));
        continue;
      }
      const winner = (yield race({ elapsed: delay(interval), changed: take(settles(hash)) })) as {
        elapsed?: true;
      };
      if (winner.elapsed) yield call(startFetch, key);
    }
  }

  function* collect(key: QueryKey): Saga {
    const hash = hashKey(key);
    yield delay(defaults.gcTime);
    collectors.delete(hash);
    yield call(stopFetch, hash);
    yield put(queryRemoved({ key }));
  }

  function* onSubscribed(action: ReturnType<typeof querySubscribed>): Saga {
    const { key, observerId } = action.payload;
    const { getOptions } = action.meta;
    const hash = hashKey(key);

    const collector = collectors.get(hash);
    if (collector) {
      collectors.delete(hash);
      yield cancel(collector);
    }

    let group = observers.get(hash);
    if (!group) {
      group = new Map();
      observers.set(hash, group);
    }
    group.set(observerId, getOptions);

    const observer = getOptions();
    if (!observer.enabled) return;

    const entry = (yield select(selectQuery, key)) as QueryEntry | undefined;
    if (needsFetch(entry, observer.staleTime ?? defaults.staleTime)) yield call(startFetch, key);

    if (observer.refetchInterval !== undefined) {
      polls.set(`${hash}|${observerId}`, (yield spawn(poll, key, getOptions)) as Task);
    }
  }

  function* onUnsubscribed(action: ReturnType<typeof queryUnsubscribed>): Saga {
    const { key, observerId } = action.payload;
    const hash = hashKey(key);

    const pollId = `${hash}|${observerId}`;
    const polling = polls.get(pollId);
    if (polling) {
      polls.delete(pollId);
      yield cancel(polling);
    }

    const group = observers.get(hash);
    group?.delete(observerId);
    if (group && group.size > 0) return;

    observers.delete(hash);
    if (Number.isFinite(defaults.gcTime)) {
      collectors.set(hash, (yield spawn(collect, key)) as Task);
    }
  }

  function* onInvalidated(action: ReturnType<typeof queriesInvalidated>): Saga {
    const entries = (yield select(selectQueries)) as QueriesState;
    for (const entry of Object.values(entries)) {
      const hash = hashKey(entry.key);
      if (!keyStartsWith(entry.key, action.payload.key) || !isOnScreen(hash)) continue;
      yield call(stopFetch, hash);
      yield call(startFetch, entry.key);
    }
  }

  function* onRefetchRequested(action: ReturnType<typeof queryRefetchRequested>): Saga {
    const { key } = action.payload;
    const hash = hashKey(key);
    yield call(startFetch, key);
    if (fetches.has(hash)) yield take(settles(hash));
    action.meta.done();
  }

  function* onCancelRequested(action: ReturnType<typeof queriesCancelRequested>): Saga {
    for (const [hash, running] of [...fetches]) {
      if (!keyStartsWith(running.key, action.payload.key)) continue;
      yield call(stopFetch, hash);
      yield put(fetchCancelled({ key: running.key }));
    }
  }

  function* onCleared(action: ReturnType<typeof queriesCleared>): Saga {
    const { except } = action.payload;
    for (const [hash, running] of [...fetches]) {
      if (!except || !keyStartsWith(running.key, except)) yield call(stopFetch, hash);
    }
  }

  return function* queriesSaga(): Saga {
    yield all([
      takeEvery(querySubscribed.match, onSubscribed),
      takeEvery(queryUnsubscribed.match, onUnsubscribed),
      takeEvery(queriesInvalidated.match, onInvalidated),
      takeEvery(queryRefetchRequested.match, onRefetchRequested),
      takeEvery(queriesCancelRequested.match, onCancelRequested),
      takeEvery(queriesCleared.match, onCleared),
    ]);
  };
}

import { put } from "redux-saga/effects";
import type { PutEffect } from "redux-saga/effects";

import type { QueryKey } from "./queryKey";
import { queriesCancelRequested, queriesCleared, queriesInvalidated, queryDataSet } from "./slice";

export function invalidateQueries(key: QueryKey): PutEffect {
  return put(queriesInvalidated({ key }));
}

export function cancelQueries(key: QueryKey): PutEffect {
  return put(queriesCancelRequested({ key }));
}

export function setQueryData(key: QueryKey, data: unknown): PutEffect {
  return put(queryDataSet({ key, data }));
}

export function clearQueries(except?: QueryKey): PutEffect {
  return put(queriesCleared({ except }));
}

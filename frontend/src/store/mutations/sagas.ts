import { call, put, takeEvery } from "redux-saga/effects";

import { invalidateQueries } from "../queries/effects";
import { toError } from "../saga";
import type { Saga } from "../saga";
import { mutationFailed, mutationRequested, mutationSucceeded } from "./slice";

function* runMutation(action: ReturnType<typeof mutationRequested>): Saga {
  const { id, run } = action.payload;
  const { definition, variables, resolve, reject } = action.meta;
  const { invalidates } = definition;

  let context: unknown;
  let data: unknown;
  let failure: Error | null = null;

  try {
    if (definition.onMutate) context = yield call(definition.onMutate, variables);
    data = yield call(definition.mutationFn, variables);
    const stale = typeof invalidates === "function" ? invalidates(data, variables) : invalidates;
    for (const key of stale ?? []) yield invalidateQueries(key);
  } catch (thrown) {
    failure = toError(thrown);
  }

  try {
    if (failure && definition.onError) yield call(definition.onError, failure, variables, context);
    if (definition.onSettled) yield call(definition.onSettled, variables);
  } catch (thrown) {
    failure = toError(thrown);
  }

  if (failure) {
    yield put(mutationFailed({ id, run, error: failure }));
    reject(failure);
  } else {
    yield put(mutationSucceeded({ id, run, data }));
    resolve(data);
  }
}

export function* mutationsSaga(): Saga {
  yield takeEvery(mutationRequested.match, runMutation);
}

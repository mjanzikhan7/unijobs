import { createAction } from "@reduxjs/toolkit";
import { all, call, takeEvery } from "redux-saga/effects";

import { request } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";

import { clearQueries, invalidateQueries, setQueryData } from "../queries/effects";
import type { Saga } from "../saga";

export const signedIn = createAction("session/signedIn");

export const signOutRequested = createAction("session/signOutRequested", (done: () => void) => ({
  payload: undefined,
  meta: { done },
}));

function* onSignedIn(): Saga {
  yield clearQueries(queryKeys.me());
  yield invalidateQueries(queryKeys.me());
}

function* onSignOutRequested(action: ReturnType<typeof signOutRequested>): Saga {
  try {
    yield call(request, "/auth/logout/", { method: "POST" });
  } catch {
    // A failed logout request must still sign the person out locally.
  }
  yield clearQueries(queryKeys.me());
  yield setQueryData(queryKeys.me(), null);
  action.meta.done();
}

export function* sessionSaga(): Saga {
  yield all([
    takeEvery(signedIn.match, onSignedIn),
    takeEvery(signOutRequested.match, onSignOutRequested),
  ]);
}

import { combineReducers, configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import { all, call } from "redux-saga/effects";

import { ApiError } from "@/models/api/client";

import { mutationsSaga } from "./mutations/sagas";
import { mutationsReducer } from "./mutations/slice";
import { createQueriesSaga } from "./queries/sagas";
import type { QueryDefaults } from "./queries/sagas";
import { queriesReducer } from "./queries/slice";
import type { Saga } from "./saga";
import { sessionSaga } from "./session/sagas";

const rootReducer = combineReducers({
  queries: queriesReducer,
  mutations: mutationsReducer,
});

export type RootState = ReturnType<typeof rootReducer>;

const defaultQueryOptions: QueryDefaults = {
  staleTime: 30_000,
  gcTime: 5 * 60_000,
  retry: (failureCount, error) => {
    if (error instanceof ApiError && error.status < 500) return false;
    return failureCount < 2;
  },
};

export function createAppStore(queryOptions: Partial<QueryDefaults> = {}) {
  const sagaMiddleware = createSagaMiddleware();
  const queriesSaga = createQueriesSaga({ ...defaultQueryOptions, ...queryOptions });

  const store = configureStore({
    reducer: rootReducer,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: {
          ignoredActionPaths: ["meta", "payload.error"],
          ignoredPaths: [/^(queries|mutations)\..*\.error$/],
        },
      }).concat(sagaMiddleware),
  });

  sagaMiddleware.run(function* rootSaga(): Saga {
    yield all([call(queriesSaga), call(mutationsSaga), call(sessionSaga)]);
  });

  return store;
}

export type AppStore = ReturnType<typeof createAppStore>;

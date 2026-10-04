import { createAction, createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";

import type { QueryKey } from "../queries/queryKey";
import type { Saga } from "../saga";

export interface MutationEntry {
  run: number;
  status: "idle" | "pending" | "success" | "error";
  data: unknown;
  error: Error | null;
}

export type MutationsState = Record<string, MutationEntry>;

export interface MutationsRootState {
  mutations: MutationsState;
}

export interface MutationDefinition<TData, TVariables, TContext = undefined> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  invalidates?: readonly QueryKey[] | ((data: TData, variables: TVariables) => readonly QueryKey[]);
  onMutate?: (variables: TVariables) => Saga<TContext>;
  onError?: (error: Error, variables: TVariables, context: TContext | undefined) => Saga;
  onSettled?: (variables: TVariables) => Saga;
}

export type AnyMutationDefinition = MutationDefinition<unknown, unknown, unknown>;

export interface MutationRequestMeta {
  definition: AnyMutationDefinition;
  variables: unknown;
  resolve: (data: unknown) => void;
  reject: (error: Error) => void;
}

export const mutationRequested = createAction(
  "mutations/requested",
  (payload: { id: string; run: number }, meta: MutationRequestMeta) => ({ payload, meta }),
);

const initialState: MutationsState = {};

const slice = createSlice({
  name: "mutations",
  initialState,
  reducers: {
    mutationSucceeded(state, action: PayloadAction<{ id: string; run: number; data: unknown }>) {
      const entry = state[action.payload.id];
      if (entry?.run !== action.payload.run) return;
      entry.status = "success";
      entry.data = action.payload.data;
    },
    mutationFailed(state, action: PayloadAction<{ id: string; run: number; error: Error }>) {
      const entry = state[action.payload.id];
      if (entry?.run !== action.payload.run) return;
      entry.status = "error";
      entry.error = action.payload.error;
    },
    mutationCleared(state, action: PayloadAction<{ id: string }>) {
      delete state[action.payload.id];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(mutationRequested, (state, action) => {
      state[action.payload.id] = {
        run: action.payload.run,
        status: "pending",
        data: undefined,
        error: null,
      };
    });
  },
});

export const mutationsReducer = slice.reducer;
export const { mutationSucceeded, mutationFailed, mutationCleared } = slice.actions;

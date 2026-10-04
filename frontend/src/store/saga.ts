import type { Effect } from "redux-saga/effects";

export type Saga<Result = void> = Generator<Effect, Result, unknown>;

export function toError(thrown: unknown): Error {
  return thrown instanceof Error ? thrown : new Error(String(thrown));
}

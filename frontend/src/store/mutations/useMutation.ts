import { useCallback, useEffect, useId, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";

import { mutationCleared, mutationRequested } from "./slice";
import type { AnyMutationDefinition, MutationDefinition, MutationsRootState } from "./slice";

export interface MutateCallbacks<TData, TError, TVariables> {
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: TError, variables: TVariables) => void;
  onSettled?: (data: TData | undefined, error: TError | null, variables: TVariables) => void;
}

export interface UseMutationResult<TData = unknown, TError = Error, TVariables = void> {
  data: TData | undefined;
  error: TError | null;
  status: "idle" | "pending" | "success" | "error";
  isIdle: boolean;
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
  mutate: (variables: TVariables, callbacks?: MutateCallbacks<TData, TError, TVariables>) => void;
  mutateAsync: (variables: TVariables) => Promise<TData>;
  reset: () => void;
}

export function useMutation<TData, TVariables = void, TContext = undefined>(
  definition: MutationDefinition<TData, TVariables, TContext>,
): UseMutationResult<TData, Error, TVariables> {
  const dispatch = useDispatch();
  const id = useId();
  const entry = useSelector((state: MutationsRootState) => state.mutations[id]);

  const latest = useRef(definition);
  useEffect(() => {
    latest.current = definition;
  });

  const runs = useRef(0);

  useEffect(
    () => () => {
      dispatch(mutationCleared({ id }));
    },
    [dispatch, id],
  );

  const mutateAsync = useCallback(
    (variables: TVariables) =>
      new Promise<TData>((resolve, reject) => {
        runs.current += 1;
        dispatch(
          mutationRequested(
            { id, run: runs.current },
            {
              definition: latest.current as unknown as AnyMutationDefinition,
              variables,
              resolve: resolve as (data: unknown) => void,
              reject,
            },
          ),
        );
      }),
    [dispatch, id],
  );

  const mutate = useCallback(
    (variables: TVariables, callbacks?: MutateCallbacks<TData, Error, TVariables>) => {
      mutateAsync(variables).then(
        (data) => {
          callbacks?.onSuccess?.(data, variables);
          callbacks?.onSettled?.(data, null, variables);
        },
        (error: Error) => {
          callbacks?.onError?.(error, variables);
          callbacks?.onSettled?.(undefined, error, variables);
        },
      );
    },
    [mutateAsync],
  );

  const reset = useCallback(() => {
    dispatch(mutationCleared({ id }));
  }, [dispatch, id]);

  const status = entry?.status ?? "idle";
  return {
    data: entry?.data as TData | undefined,
    error: entry?.error ?? null,
    status,
    isIdle: status === "idle",
    isPending: status === "pending",
    isSuccess: status === "success",
    isError: status === "error",
    mutate,
    mutateAsync,
    reset,
  };
}

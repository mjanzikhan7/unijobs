export type QueryKey = readonly unknown[];

export function hashKey(key: QueryKey): string {
  return JSON.stringify(key);
}

export function keyStartsWith(key: QueryKey, prefix: QueryKey): boolean {
  return (
    prefix.length <= key.length &&
    prefix.every((part, index) => JSON.stringify(part) === JSON.stringify(key[index]))
  );
}

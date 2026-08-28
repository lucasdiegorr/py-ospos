export interface OutboxEntry {
  id: string;
  operation: string;
  payload: unknown;
}

const OUTBOX_KEY = "pyospos:outbox";

function read(): OutboxEntry[] {
  try {
    return JSON.parse(
      localStorage.getItem(OUTBOX_KEY) ?? "[]",
    ) as OutboxEntry[];
  } catch {
    return [];
  }
}

function write(entries: OutboxEntry[]): void {
  if (entries.length === 0) {
    localStorage.removeItem(OUTBOX_KEY);
  } else {
    localStorage.setItem(OUTBOX_KEY, JSON.stringify(entries));
  }
}

function newId(): string {
  return (
    globalThis.crypto?.randomUUID?.() ??
    `${Date.now()}-${Math.random().toString(36).slice(2)}`
  );
}

export function enqueue(operation: string, payload: unknown): OutboxEntry {
  const entry: OutboxEntry = { id: newId(), operation, payload };
  write([...read(), entry]);
  return entry;
}

export function pendingEntries(): OutboxEntry[] {
  return read();
}

export function pendingCount(): number {
  return read().length;
}

export function clearOutbox(): void {
  write([]);
}

/** Push queued writes to the server in order; stop at the first failure. */
export async function flushOutbox(
  send: (entry: OutboxEntry) => Promise<void>,
): Promise<number> {
  let flushed = 0;
  for (;;) {
    const entries = read();
    if (entries.length === 0) return flushed;
    try {
      await send(entries[0]);
      write(entries.slice(1));
      flushed += 1;
    } catch {
      return flushed;
    }
  }
}

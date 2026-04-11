import initSqlJs, { type Database, type SqlJsStatic } from 'sql.js';

const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');
const DB_PATH = `${BASE}/yengo-puzzle-collections/yengo-search.db`;
const DB_VERSION_PATH = `${BASE}/yengo-puzzle-collections/db-version.json`;
const WASM_PATH = `${BASE}/sql-wasm.wasm`;
const DB_VERSION_KEY = 'yen-go-db-version';

let db: Database | null = null;
let sqlPromise: Promise<SqlJsStatic> | null = null;
let initPromise: Promise<void> | null = null;

/** Initialize sql.js and load the search database. */
export async function init(): Promise<void> {
  if (db) return;
  if (initPromise) return initPromise;

  initPromise = (async () => {
    if (!sqlPromise) {
      sqlPromise = initSqlJs({
        locateFile: () => WASM_PATH,
      });
    }
    const SQL = await sqlPromise;

    const response = await fetch(DB_PATH);
    if (!response.ok) {
      throw new Error(`Failed to fetch search database: ${response.status}`);
    }
    const buffer = await response.arrayBuffer();

    db = new SQL.Database(new Uint8Array(buffer));

    // Store current DB version for future update checks (non-blocking)
    void fetch(DB_VERSION_PATH)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.db_version) {
          localStorage.setItem(DB_VERSION_KEY, data.db_version);
        }
      })
      .catch(() => {/* best-effort */});
  })();

  void initPromise.catch(() => {
    initPromise = null;
  });

  return initPromise;
}

/** Execute a SQL query and return typed results. */
export function query<T = Record<string, unknown>>(
  sql: string,
  params?: (string | number | null)[],
): T[] {
  if (!db) throw new Error('Database not initialized. Call init() first.');

  const stmt = db.prepare(sql);
  if (params) stmt.bind(params);

  const results: T[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as T;
    results.push(row);
  }
  stmt.free();
  return results;
}

/** Check if the database is ready. */
export function isReady(): boolean {
  return db !== null;
}

/** Get the raw database instance (for advanced queries). */
export function getDb(): Database | null {
  return db;
}

export interface UpdateCheckResult {
  updateAvailable: boolean;
  currentVersion: string | null;
  newVersion: string | null;
}

/**
 * Check whether a newer version of the search database is available.
 *
 * Fetches ``db-version.json`` and compares its ``db_version`` against the
 * version stored in ``localStorage`` at init time.  Non-blocking — never
 * throws; returns ``updateAvailable: false`` on any network or parse error.
 */
export async function checkForUpdates(): Promise<UpdateCheckResult> {
  const stored = localStorage.getItem(DB_VERSION_KEY);
  try {
    const res = await fetch(DB_VERSION_PATH);
    if (!res.ok) return { updateAvailable: false, currentVersion: stored, newVersion: null };
    const data = (await res.json()) as { db_version?: string };
    const remote = data.db_version ?? null;
    if (remote && remote !== stored) {
      return { updateAvailable: true, currentVersion: stored, newVersion: remote };
    }
    return { updateAvailable: false, currentVersion: stored, newVersion: remote };
  } catch {
    return { updateAvailable: false, currentVersion: stored, newVersion: null };
  }
}

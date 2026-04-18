/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly BASE_URL: string;
  /** External data base URL for puzzle assets (DB, SGF, JSON). When set, frontend fetches data from this origin instead of same-origin Pages path. */
  readonly VITE_DATA_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

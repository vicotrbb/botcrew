export interface SecretSummary {
  id: string;
  key: string;
  value: string; // masked "********" in list, real value in single-get
  description: string | null;
  created_at: string;
  updated_at: string;
}

// Single-get returns real value
export type SecretDetail = SecretSummary;

export interface CreateSecretInput {
  key: string;
  value: string;
  description?: string;
}

export interface UpdateSecretInput {
  key?: string;
  value?: string;
  description?: string;
}

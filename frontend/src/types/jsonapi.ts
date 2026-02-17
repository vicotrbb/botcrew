export interface JSONAPIResource<T = Record<string, unknown>> {
  type: string;
  id: string;
  attributes: T;
  relationships?: Record<string, unknown>;
}

export interface JSONAPISingleResponse<T> {
  data: JSONAPIResource<T>;
}

export interface JSONAPIListResponse<T> {
  data: JSONAPIResource<T>[];
  meta?: {
    total_count?: number;
    has_next?: boolean;
    unread_count?: number;
    [key: string]: unknown;
  };
  links?: {
    first?: string;
    next?: string;
  };
}

export interface JSONAPIErrorDetail {
  status: string;
  title: string;
  detail?: string;
}

export interface JSONAPIErrorResponse {
  errors: JSONAPIErrorDetail[];
}

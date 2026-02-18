import type {
  JSONAPISingleResponse,
  JSONAPIListResponse,
  JSONAPIErrorResponse,
} from '@/types/jsonapi';

export const API_BASE =
  import.meta.env.VITE_API_URL || '/api/v1';

export class ApiError extends Error {
  status: number;
  errors: { status: string; title: string; detail?: string }[];

  constructor(
    status: number,
    message: string,
    errors: { status: string; title: string; detail?: string }[] = [],
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.errors = errors;
  }
}

async function handleResponse(res: Response): Promise<unknown> {
  if (!res.ok) {
    let errors: { status: string; title: string; detail?: string }[] = [];
    let message = `API error ${res.status}`;
    try {
      const body = (await res.json()) as JSONAPIErrorResponse;
      if (body.errors?.length) {
        errors = body.errors;
        message = body.errors.map((e) => e.detail || e.title).join('; ');
      }
    } catch {
      // response body was not JSON
    }
    throw new ApiError(res.status, message, errors);
  }
  // 204 No Content
  if (res.status === 204) return undefined;
  return res.json();
}

/**
 * Fetch a single JSON:API resource, unwrap to `{ id, ...attributes }`.
 */
export async function fetchOne<T>(path: string): Promise<T & { id: string }> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  const json = (await handleResponse(res)) as JSONAPISingleResponse<T>;
  return { id: json.data.id, ...json.data.attributes };
}

/**
 * Fetch a JSON:API list, unwrap each resource to `{ id, ...attributes }`.
 */
export async function fetchList<T>(path: string): Promise<(T & { id: string })[]> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  const json = (await handleResponse(res)) as JSONAPIListResponse<T>;
  return json.data.map((r) => ({ id: r.id, ...r.attributes }));
}

/**
 * Fetch a JSON:API list with meta and links (for pagination).
 */
export async function fetchListWithMeta<T>(
  path: string,
): Promise<{
  items: (T & { id: string })[];
  meta?: JSONAPIListResponse<T>['meta'];
  links?: JSONAPIListResponse<T>['links'];
}> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  const json = (await handleResponse(res)) as JSONAPIListResponse<T>;
  return {
    items: json.data.map((r) => ({ id: r.id, ...r.attributes })),
    meta: json.meta,
    links: json.links,
  };
}

/**
 * POST JSON body wrapped in JSON:API envelope, return unwrapped single resource.
 * Pass `type` to wrap as `{ data: { type, attributes: body } }`.
 * If `type` is omitted the body is sent as-is (for body-less POSTs like duplicate).
 */
export async function postJSON<T>(
  path: string,
  body: unknown,
  type?: string,
): Promise<T & { id: string }> {
  const payload = type ? { data: { type, attributes: body } } : body;
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const json = (await handleResponse(res)) as JSONAPISingleResponse<T>;
  return { id: json.data.id, ...json.data.attributes };
}

/**
 * PATCH JSON body wrapped in JSON:API envelope, return unwrapped single resource.
 */
export async function patchJSON<T>(
  path: string,
  body: unknown,
  type: string,
): Promise<T & { id: string }> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: { type, attributes: body } }),
  });
  const json = (await handleResponse(res)) as JSONAPISingleResponse<T>;
  return { id: json.data.id, ...json.data.attributes };
}

/**
 * DELETE resource (no body). Returns void.
 */
export async function deleteJSON(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });
  await handleResponse(res);
}

/**
 * DELETE with JSON body wrapped in JSON:API envelope. Returns void.
 */
export async function deleteJSONWithBody(
  path: string,
  body: unknown,
  type: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: { type, attributes: body } }),
  });
  await handleResponse(res);
}

/**
 * PUT JSON body wrapped in JSON:API envelope, return unwrapped single resource.
 */
export async function putJSON<T>(
  path: string,
  body: unknown,
  type: string,
): Promise<T & { id: string }> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: { type, attributes: body } }),
  });
  const json = (await handleResponse(res)) as JSONAPISingleResponse<T>;
  return { id: json.data.id, ...json.data.attributes };
}

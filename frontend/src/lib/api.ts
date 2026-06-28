const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function refreshToken(): Promise<string | null> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) return null;

  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!res.ok) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    return null;
  }

  const data = await res.json();
  localStorage.setItem("access_token", data.access_token);
  if (data.refresh_token) {
    localStorage.setItem("refresh_token", data.refresh_token);
  }
  return data.access_token;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && token) {
    const newToken = await refreshToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getCurrentUser: () =>
    request<{ id: string; username: string; is_admin: boolean }>("/employees/me"),

  login: (username: string, password: string) =>
    request<{
      access_token: string;
      refresh_token: string;
      employee: { id: string; username: string; is_admin: boolean };
    }>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username, password }),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),

  loginJson: (username: string, password: string) =>
    request<{
      access_token: string;
      refresh_token: string;
      employee: { id: string; username: string; is_admin: boolean };
    }>("/auth/login/json", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  list: <T>(entity: string, params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params) : "";
    return request<T[]>(`/${entity}${qs}`);
  },

  get: <T>(entity: string, id: string) =>
    request<T>(`/${entity}/${id}`),

  create: <T>(entity: string, data: unknown) =>
    request<T>(`/${entity}/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: <T>(entity: string, id: string, data: unknown) =>
    request<T>(`/${entity}/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (entity: string, id: string) =>
    request<void>(`/${entity}/${id}`, { method: "DELETE" }),

  // --- POS / Cart methods ---
  getCart: () =>
    request<SaleDetail | null>("/sales/cart"),

  createCart: (data?: { customer_id?: string; comment?: string }) =>
    request<SaleDetail>("/sales/cart", {
      method: "POST",
      body: JSON.stringify(data ?? {}),
    }),

  addToCart: (data: {
    item_id?: string;
    item_name?: string;
    quantity?: number;
    unit_price?: number;
    discount_percent?: number;
  }) =>
    request<SaleDetail>("/sales/cart/items", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateCartItem: (data: {
    line_id: string;
    quantity?: number;
    discount_percent?: number;
    discount_amount?: number;
  }) =>
    request<SaleDetail>("/sales/cart/items", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  removeFromCart: (lineId: string) =>
    request<void>(`/sales/cart/items/${lineId}`, { method: "DELETE" }),

  completeSale: (data: {
    payments: { payment_type: string; amount: number }[];
    customer_id?: string;
    comment?: string;
  }) =>
    request<SaleDetail>("/sales/cart/complete", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  suspendSale: () =>
    request<SaleResponse>("/sales/cart/suspend", { method: "POST" }),

  getSuspendedSales: () =>
    request<SaleDetail[]>("/sales/suspended"),

  recallSale: (saleId: string) =>
    request<SaleDetail>(`/sales/suspended/${saleId}/recall`, { method: "POST" }),

  lookupBarcode: (barcode: string) =>
    request<ItemResponse>(`/items/barcode/${encodeURIComponent(barcode)}`),
};

// --- POS types ---

export interface SaleResponse {
  id: string;
  customer_id?: string;
  status: string;
  employee_id: string;
  comment?: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  created_at: string;
  completed_at?: string;
  suspended_at?: string;
}

export interface SaleLine {
  id: string;
  sale_id: string;
  item_id?: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  cost_price: number;
  discount_percent: number;
  discount_amount: number;
  line_total: number;
}

export interface Payment {
  id: string;
  sale_id: string;
  payment_type: string;
  amount: number;
  reference_number?: string;
}

export interface SaleDetail extends SaleResponse {
  lines: SaleLine[];
  payments: Payment[];
}

export interface ItemResponse {
  id: string;
  name: string;
  description?: string;
  sku?: string;
  item_number?: string;
  category_id?: string;
  quantity: number;
  reorder_level: number;
  cost_price: number;
  unit_price: number;
  is_service: boolean;
  is_serialized: boolean;
  is_active: boolean;
  is_below_reorder_level?: boolean;
}

// Legacy entity types
export interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
}

export interface Item {
  id: string;
  name: string;
  description?: string;
  cost_price: number;
  unit_price: number;
  stock_quantity: number;
  category?: { id: string; name: string };
}

export interface Employee {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  is_admin: boolean;
  is_active: boolean;
}

export interface Expense {
  id: string;
  description: string;
  amount: number;
  date: string;
  category?: { id: string; name: string };
}

export interface Invoice {
  id: string;
  invoice_number: string;
  customer_name?: string;
  total: number;
  status: string;
  created_at: string;
}

export interface Quotation {
  id: string;
  quotation_number: string;
  customer_name?: string;
  total: number;
  status: string;
  created_at: string;
}

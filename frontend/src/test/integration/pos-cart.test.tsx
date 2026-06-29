import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/pos",
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { id: "1", username: "cashier", permissions: ["sales.create", "items.read", "customers.read"] },
    loading: false,
    logout: vi.fn(),
    can: (perm: string) => perm === "sales.create" || perm === "items.read" || perm === "customers.read",
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockFetch = vi.fn();
const storage: Record<string, string> = {};
beforeEach(() => {
  mockFetch.mockReset();
  global.fetch = mockFetch;
  Object.keys(storage).forEach((k) => delete storage[k]);
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => { storage[key] = value; },
    removeItem: (key: string) => { delete storage[key]; },
    clear: () => { Object.keys(storage).forEach((k) => delete storage[k]); },
    get length() { return Object.keys(storage).length; },
    key: (i: number) => Object.keys(storage)[i] ?? null,
  });
});

const emptyCart = {
  id: "cart-1",
  status: "open",
  employee_id: "1",
  subtotal: 0,
  tax_amount: 0,
  discount_amount: 0,
  total: 0,
  lines: [],
  payments: [],
  created_at: new Date().toISOString(),
};

const itemResponse = {
  id: "item-1",
  name: "Test Item",
  unit_price: 10.99,
  cost_price: 5.0,
  quantity: 100,
  is_active: true,
  is_service: false,
  is_serialized: false,
  is_below_reorder_level: false,
};

async function setupPosPage() {
  const { default: PosPage } = await import("@/app/pos/page");
  return render(<PosPage />);
}

describe("POS cart integration", () => {
  it("loads empty cart and shows empty state", async () => {
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(emptyCart), { status: 200 }));

    await setupPosPage();

    await waitFor(() => {
      expect(screen.getByText("Cart is empty")).toBeInTheDocument();
    });
  });

  it("creates a new cart when none exists", async () => {
    mockFetch
      .mockResolvedValueOnce(new Response(JSON.stringify(null), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(emptyCart), { status: 201 }));

    await setupPosPage();

    await waitFor(() => {
      const createCalls = mockFetch.mock.calls.filter(
        (c) =>
          typeof c[0] === "string" &&
          c[0].includes("/sales/cart") &&
          (c[1] as RequestInit)?.method === "POST"
      );
      expect(createCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("searches items and displays results", async () => {
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(emptyCart), { status: 200 }));

    await setupPosPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search items/)).toBeInTheDocument();
    });

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([itemResponse]), { status: 200 })
    );

    const searchInput = screen.getByPlaceholderText(/Search items/);
    await userEvent.type(searchInput, "Test");

    await waitFor(() => {
      expect(screen.getByText("Test Item")).toBeInTheDocument();
    });

    expect(screen.getByText("$10.99")).toBeInTheDocument();
  });

  it("adds item to cart", async () => {
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(emptyCart), { status: 200 }));

    await setupPosPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search items/)).toBeInTheDocument();
    });

    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify([itemResponse]), { status: 200 }));

    const searchInput = screen.getByPlaceholderText(/Search items/);
    await userEvent.type(searchInput, "Test");

    await waitFor(() => expect(screen.getByText("Test Item")).toBeInTheDocument());

    const cartWithItem = {
      ...emptyCart,
      subtotal: 10.99,
      total: 10.99,
      lines: [{
        id: "line-1",
        sale_id: "cart-1",
        item_id: "item-1",
        item_name: "Test Item",
        quantity: 1,
        unit_price: 10.99,
        cost_price: 5.0,
        discount_percent: 0,
        discount_amount: 0,
        line_total: 10.99,
      }],
    };

    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(cartWithItem), { status: 201 }));

    await userEvent.click(screen.getByText("Test Item"));

    await waitFor(() => {
      expect(screen.getByText("Test Item")).toBeInTheDocument();
      expect(screen.getAllByText("$10.99").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("opens checkout modal and shows total", async () => {
    const cartWithItem = {
      ...emptyCart,
      subtotal: 10.99,
      total: 10.99,
      lines: [{
        id: "line-1",
        sale_id: "cart-1",
        item_id: "item-1",
        item_name: "Test Item",
        quantity: 1,
        unit_price: 10.99,
        cost_price: 5.0,
        discount_percent: 0,
        discount_amount: 0,
        line_total: 10.99,
      }],
    };

    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(cartWithItem), { status: 200 }));

    await setupPosPage();

    await waitFor(() => {
      expect(screen.getByText("Checkout")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Checkout"));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Complete Sale/ })).toBeInTheDocument();
      expect(screen.getByText(/Total:/)).toBeInTheDocument();
    });
  });

  it("completes sale and shows receipt", async () => {
    const cartWithItem = {
      ...emptyCart,
      subtotal: 10.99,
      total: 11.99,
      lines: [{
        id: "line-1",
        sale_id: "cart-1",
        item_id: "item-1",
        item_name: "Test Item",
        quantity: 1,
        unit_price: 10.99,
        cost_price: 5.0,
        discount_percent: 0,
        discount_amount: 0,
        line_total: 10.99,
      }],
    };

    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(cartWithItem), { status: 200 }));

    await setupPosPage();

    await waitFor(() => expect(screen.getByText("Checkout")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Checkout"));

    await waitFor(() => expect(screen.getByRole("heading", { name: /Complete Sale/ })).toBeInTheDocument());

    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(cartWithItem), { status: 200 }));
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify(emptyCart), { status: 201 }));

    const amountInput = screen.getByDisplayValue("11.99");

    await userEvent.click(screen.getByRole("button", { name: /Complete Sale/ }));

    await waitFor(() => {
      expect(screen.getByText("Sale Complete")).toBeInTheDocument();
      expect(screen.getByText("New Sale")).toBeInTheDocument();
    });
  });
});

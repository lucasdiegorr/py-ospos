import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/customers",
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { id: "1", username: "admin", isAdmin: true },
    loading: false,
    logout: vi.fn(),
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

async function setupCustomersPage() {
  const { default: CustomersPage } = await import("@/app/(dashboard)/customers/page");
  return render(<CustomersPage />);
}

describe("Customers CRUD integration", () => {
  it("loads and displays customer list", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          { id: "1", first_name: "John", last_name: "Doe", email: "john@test.com", phone: "123", company_name: "ACME", is_active: true },
          { id: "2", first_name: "Jane", last_name: "Smith", email: null, phone: null, company_name: null, is_active: true },
        ]),
        { status: 200 }
      )
    );

    await setupCustomersPage();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
      expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    });

    expect(screen.getByText("john@test.com")).toBeInTheDocument();
  });

  it("opens create modal and submits new customer", async () => {
    mockFetch.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

    await setupCustomersPage();

    await waitFor(() => expect(screen.getByText("Customers")).toBeInTheDocument());

    await userEvent.click(screen.getByText(/Add Customer/));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Add Customer" })).toBeInTheDocument();
    });

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "3", first_name: "New", last_name: "Customer" }), { status: 201 })
    );

    const modal = screen.getByRole("heading", { name: "Add Customer" }).closest("[class*='rounded-xl']") as HTMLElement;
    const modalInputs = within(modal).getAllByDisplayValue("");
    await userEvent.type(modalInputs[0], "New");
    await userEvent.type(modalInputs[1], "Customer");
    await userEvent.type(modalInputs[2], "new@test.com");

    await userEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      const createCall = mockFetch.mock.calls.find(
        (c) => (c[1] as RequestInit)?.method === "POST"
      );
      expect(createCall).toBeTruthy();
      if (createCall) {
        const body = JSON.parse(createCall[1].body as string);
        expect(body.first_name).toBe("New");
        expect(body.last_name).toBe("Customer");
      }
    });
  });

  it("shows empty state when no customers", async () => {
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));

    await setupCustomersPage();

    await waitFor(() => {
      expect(screen.getByText("No results found")).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/lib/auth-context";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
}));

function TestConsumer() {
  const { user, can, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="username">{user?.username ?? "none"}</span>
      <span data-testid="can-customers">{can("customers.read") ? "yes" : "no"}</span>
      <span data-testid="can-admin">{can("admin.roles") ? "yes" : "no"}</span>
    </div>
  );
}

const mockFetch = vi.fn();
let store: Record<string, string> = {};

beforeEach(() => {
  mockFetch.mockReset();
  store = {};
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  });
  global.fetch = mockFetch;
});

describe("can() helper", () => {
  it("returns false when no user is logged in", async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("can-customers").textContent).toBe("no");
      expect(screen.getByTestId("can-admin").textContent).toBe("no");
    });
  });

  it("returns true for permissions the user has", async () => {
    store["access_token"] = "valid-token";
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "1",
          username: "admin",
          permissions: ["customers.read", "items.read", "employees.read"],
        }),
        { status: 200 }
      )
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("username").textContent).toBe("admin");
      expect(screen.getByTestId("can-customers").textContent).toBe("yes");
      expect(screen.getByTestId("can-admin").textContent).toBe("no");
    });
  });
});

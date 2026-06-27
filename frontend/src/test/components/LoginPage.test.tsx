import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  usePathname: () => "/login",
}));

const mockFetch = vi.fn();
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
})();

Object.defineProperty(global, "localStorage", { value: localStorageMock });
Object.defineProperty(global, "fetch", { value: mockFetch });
Object.defineProperty(global, "navigator", {
  value: { clipboard: { writeText: vi.fn() } },
  writable: true,
  configurable: true,
});

beforeEach(() => {
  mockFetch.mockReset();
  localStorageMock.clear();
  mockPush.mockReset();
});

async function setupLoginPage() {
  const { default: LoginPage } = await import("@/app/(auth)/login/page");
  return render(<LoginPage />);
}

describe("LoginPage", () => {
  it("renders form elements", async () => {
    await setupLoginPage();
    expect(screen.getByPlaceholderText("Enter your username")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter your password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows validation error on empty submit", async () => {
    await setupLoginPage();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByText("Username and password are required")).toBeInTheDocument();
  });

  it("shows error on invalid credentials", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid username or password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    await setupLoginPage();
    await userEvent.type(screen.getByPlaceholderText("Enter your username"), "admin");
    await userEvent.type(screen.getByPlaceholderText("Enter your password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByText(/Invalid/)).toBeInTheDocument();
    });
  });

  it("stores token and redirects on successful login", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "test-token",
          refresh_token: "test-refresh",
          employee: { id: "1", username: "admin", is_admin: true },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );

    await setupLoginPage();
    await userEvent.type(screen.getByPlaceholderText("Enter your username"), "admin");
    await userEvent.type(screen.getByPlaceholderText("Enter your password"), "correct");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(localStorageMock.getItem("access_token")).toBe("test-token");
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });

  it("disables button while loading", async () => {
    mockFetch.mockImplementationOnce(() => new Promise(() => {}));

    await setupLoginPage();
    await userEvent.type(screen.getByPlaceholderText("Enter your username"), "admin");
    await userEvent.type(screen.getByPlaceholderText("Enter your password"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("button", { name: /Signing in/ })).toBeDisabled();
  });
});

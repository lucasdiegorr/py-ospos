import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "@/lib/api";

const mockFetch = vi.fn();
let store: Record<string, string> = {};

beforeEach(() => {
  mockFetch.mockReset();
  store = {};
  global.fetch = mockFetch;

  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  });
});

describe("API client", () => {
  describe("request", () => {
    it("injects Authorization header when token exists", async () => {
      localStorage.setItem("access_token", "test-token");
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "1" }), { status: 200 })
      );

      await api.getCurrentUser();

      expect(mockFetch.mock.calls[0][1].headers.Authorization).toBe("Bearer test-token");
    });

    it("does not inject Authorization header without token", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      );

      await api.list("items");

      expect(mockFetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Not found" }), { status: 404 })
      );

      await expect(api.get("items", "123")).rejects.toThrow("Not found");
    });

    it("refreshes token on 401 and retries", async () => {
      localStorage.setItem("access_token", "expired");
      localStorage.setItem("refresh_token", "refresh");

      mockFetch
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 })
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({ access_token: "new-token", refresh_token: "new-refresh" }),
            { status: 200 }
          )
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ id: "1" }), { status: 200 })
        );

      const result = await api.getCurrentUser();

      expect(localStorage.getItem("access_token")).toBe("new-token");
      expect(localStorage.getItem("refresh_token")).toBe("new-refresh");
      expect(result).toEqual({ id: "1" });
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it("clears tokens on refresh failure", async () => {
      localStorage.setItem("access_token", "expired");
      localStorage.setItem("refresh_token", "bad");

      mockFetch
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 })
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ detail: "Invalid" }), { status: 401 })
        );

      await expect(api.getCurrentUser()).rejects.toThrow();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });
  });

  describe("URL building", () => {
    it("list builds query string from params", async () => {
      mockFetch.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

      await api.list("customers", { skip: "0", limit: "10", search: "john" });

      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain("skip=0");
      expect(url).toContain("limit=10");
      expect(url).toContain("search=john");
    });

    it("create sends POST with JSON body", async () => {
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 201 }));

      await api.create("customers", { first_name: "John" });

      expect(mockFetch.mock.calls[0][1].method).toBe("POST");
      expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ first_name: "John" });
    });

    it("update sends PATCH", async () => {
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 200 }));

      await api.update("items", "1", { name: "New Name" });

      expect(mockFetch.mock.calls[0][1].method).toBe("PATCH");
    });

    it("delete sends DELETE", async () => {
      mockFetch.mockResolvedValue(new Response(null, { status: 204 }));

      await api.delete("customers", "1");

      expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
    });
  });

  describe("permissions", () => {
    it("getCurrentUser returns permissions array", async () => {
      localStorage.setItem("access_token", "token");
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: "1", username: "admin", permissions: ["customers.read", "items.read"] }),
          { status: 200 }
        )
      );

      const user = await api.getCurrentUser();
      expect(user.permissions).toEqual(["customers.read", "items.read"]);
    });
  });

  describe("POS methods", () => {
    it("getCart returns null when no active cart", async () => {
      mockFetch.mockResolvedValue(new Response(JSON.stringify(null), { status: 200 }));

      expect(await api.getCart()).toBeNull();
    });

    it("completeSale sends payments", async () => {
      mockFetch.mockResolvedValue(
        new Response(JSON.stringify({ id: "1", lines: [], payments: [] }), { status: 200 })
      );

      await api.completeSale({ payments: [{ payment_type: "cash", amount: 100 }] });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.payments).toEqual([{ payment_type: "cash", amount: 100 }]);
    });
  });
});

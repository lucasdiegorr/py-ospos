import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, getToken, setToken } from "./api";

export type Role = "attendant" | "manager" | "admin";

export interface User {
  id: number;
  username: string;
  name: string;
  role: Role;
}

const USER_KEY = "pyospos:user";

interface AuthContextValue {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readUser(): User | null {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) ?? "null") as User | null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readUser());

  useEffect(() => {
    const token = getToken();
    if (!token) setUser(null);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api<{
      access_token: string;
      user: User;
    }>("/auth/login", { body: { username, password } });
    setToken(data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // local logout still proceeds when the server is unreachable
    }
    setToken(null);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within an AuthProvider");
  return value;
}

export function roleAtLeast(user: User | null, role: Role): boolean {
  if (!user) return false;
  const rank: Record<Role, number> = { attendant: 0, manager: 1, admin: 2 };
  return rank[user.role] >= rank[role];
}

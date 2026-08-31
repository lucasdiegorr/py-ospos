import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Menu } from "lucide-react";
import { api } from "./api";
import { AuthProvider, roleAtLeast, useAuth } from "./auth";
import { flushOutbox, pendingCount } from "./outbox";
import { ThemeProvider } from "./theme";
import { ThemeToggle } from "./components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Sidebar, AppLayout } from "./components/Sidebar";
import Customers from "./pages/Customers";
import Login from "./pages/Login";
import Pos from "./pages/Pos";
import Products from "./pages/Products";
import Reports from "./pages/Reports";
import Shift from "./pages/Shift";

function Topbar({ onMenu }: { onMenu: () => void }) {
  const { user, logout } = useAuth();
  const [localPending, setLocalPending] = useState(pendingCount());

  const refreshPending = useCallback(() => setLocalPending(pendingCount()), []);

  useEffect(() => {
    const flush = () => {
      void syncNow();
    };
    window.addEventListener("online", flush);
    window.addEventListener("outbox-changed", refreshPending);
    return () => {
      window.removeEventListener("online", flush);
      window.removeEventListener("outbox-changed", refreshPending);
    };
  }, [refreshPending]);

  async function syncNow() {
    await flushOutbox(async (entry) => {
      await api("/sync/ingest", {
        body: {
          idempotency_key: entry.id,
          operation: entry.operation,
          payload: entry.payload,
        },
      });
    });
    refreshPending();
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-card px-4">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMenu}
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <span className="text-base font-semibold">py-ospos</span>
      </div>
      <div className="flex items-center gap-2">
        {localPending > 0 && (
          <Button variant="outline" size="sm" onClick={() => void syncNow()}>
            Sincronizar ({localPending})
          </Button>
        )}
        {user && (
          <span className="hidden sm:inline text-sm text-muted-foreground">
            {user.name} ({user.role})
          </span>
        )}
        <ThemeToggle />
        {user && (
          <Button variant="ghost" size="sm" onClick={() => void logout()}>
            Sair
          </Button>
        )}
      </div>
    </header>
  );
}

function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user } = useAuth();
  const isManager = roleAtLeast(user, "manager");

  if (!user) {
    return <Login />;
  }

  return (
    <ThemeProvider>
      <AppLayout>
        <Topbar onMenu={() => setSidebarOpen(true)} />
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 p-4 md:p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/pos" replace />} />
            <Route path="/pos" element={<Pos />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/products" element={<Products />} />
            <Route path="/shift" element={<Shift />} />
            <Route
              path="/reports"
              element={isManager ? <Reports /> : <Navigate to="/pos" replace />}
            />
          </Routes>
        </main>
      </AppLayout>
    </ThemeProvider>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

import { useCallback, useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import { api } from "./api";
import { AuthProvider, roleAtLeast, useAuth } from "./auth";
import { flushOutbox, pendingCount } from "./outbox";
import Customers from "./pages/Customers";
import Login from "./pages/Login";
import Pos from "./pages/Pos";
import Products from "./pages/Products";
import Reports from "./pages/Reports";
import Shift from "./pages/Shift";

function AppShell() {
  const { user, logout } = useAuth();
  const [localPending, setLocalPending] = useState(pendingCount());
  const isManager = roleAtLeast(user, "manager");

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

  if (!user) {
    return <Login />;
  }

  return (
    <div className="app">
      <header>
        <NavLink to="/pos" className="brand">
          py-ospos
        </NavLink>
        {localPending > 0 && (
          <button className="badge" onClick={() => void syncNow()}>
            Sincronizar ({localPending})
          </button>
        )}
        <span className="muted">
          {user.name} ({user.role}){" "}
          <button className="link" onClick={() => void logout()}>
            sair
          </button>
        </span>
      </header>
      <nav className="tabs">
        <NavLink to="/pos">PDV</NavLink>
        <NavLink to="/customers">Clientes</NavLink>
        <NavLink to="/products">Produtos</NavLink>
        <NavLink to="/shift">Caixa</NavLink>
        {isManager && <NavLink to="/reports">Relatórios</NavLink>}
      </nav>
      <main>
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
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

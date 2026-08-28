import { useEffect, useState } from "react";
import { api } from "../api";

const MONEY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const money = (cents: number) => MONEY.format(cents / 100);

type Tab = "sales" | "sellers" | "stock" | "fiados" | "cashflow" | "margin";

interface Row {
  [key: string]: unknown;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "sales", label: "Vendas" },
  { id: "sellers", label: "Mais vendidos" },
  { id: "stock", label: "Estoque" },
  { id: "fiados", label: "Fiados" },
  { id: "cashflow", label: "Fluxo" },
  { id: "margin", label: "Margem" },
];

export default function Reports() {
  const [tab, setTab] = useState<Tab>("sales");
  const [rows, setRows] = useState<Row[]>([]);
  const [stock, setStock] = useState<{
    low_stock: Row[];
    expiring: Row[];
  } | null>(null);
  const [pending, setPending] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void api<{ pending_sync_count: number }>("/reports/pending-sync")
      .then((d) => setPending(d.pending_sync_count))
      .catch(() => setPending(0));
  }, []);

  useEffect(() => {
    setLoading(true);
    const path: Record<Tab, string> = {
      sales: "/reports/sales-by-period?period=day",
      sellers: "/reports/best-sellers",
      stock: "/reports/critical-stock",
      fiados: "/reports/open-fiados",
      cashflow: "/reports/cash-flow",
      margin: "/reports/margin",
    };
    if (tab === "stock") {
      api<{ low_stock: Row[]; expiring: Row[] }>(path.stock)
        .then(setStock)
        .catch(() => setStock({ low_stock: [], expiring: [] }))
        .finally(() => setLoading(false));
      return;
    }
    api<Row[]>(path[tab])
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [tab]);

  return (
    <div className="reports">
      {pending > 0 && (
        <div className="notice">
          <strong>Atenção:</strong> há {pending} operação(ões) pendente(s) de
          sincronização — os dados podem estar incompletos.
        </div>
      )}
      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={t.id === tab ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {loading ? (
        <p>Carregando…</p>
      ) : tab === "stock" ? (
        <StockTables stock={stock} />
      ) : rows.length === 0 ? (
        <p className="muted">Sem dados.</p>
      ) : (
        <DataTable rows={rows} />
      )}
    </div>
  );
}

function DataTable({ rows }: { rows: Row[] }) {
  const keys = Object.keys(rows[0] ?? {});
  return (
    <table>
      <thead>
        <tr>
          {keys.map((key) => (
            <th key={key}>{key}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {keys.map((key) => (
              <td key={key}>{renderValue(key, row[key])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StockTables({
  stock,
}: {
  stock: { low_stock: Row[]; expiring: Row[] } | null;
}) {
  if (!stock) return <p className="muted">Sem dados.</p>;
  return (
    <div>
      <h3>Estoque baixo</h3>
      <DataTable rows={stock.low_stock} />
      <h3>Próximos à validade / vencidos</h3>
      <DataTable rows={stock.expiring} />
    </div>
  );
}

function renderValue(key: string, value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "number")
    return key.endsWith("_cents") ? money(value) : String(value);
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    return new Date(value).toLocaleString();
  }
  return String(value);
}

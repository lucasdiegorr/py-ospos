import { useEffect, useState } from "react";
import { ApiError, api } from "../api";

const MONEY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const money = (cents: number) => MONEY.format(cents / 100);

interface Customer {
  id: number;
  name: string;
  phone: string | null;
  credit_limit_cents: number | null;
  outstanding_balance_cents: number;
}

interface History {
  outstanding_balance_cents: number;
  recent_sales: { id: number; total_cents: number; created_at: string }[];
}

export default function Customers() {
  const [query, setQuery] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [creditLimit, setCreditLimit] = useState("");
  const [selected, setSelected] = useState<Customer | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const term = query.trim();
    api<Customer[]>(`/customers${term ? `?q=${encodeURIComponent(term)}` : ""}`)
      .then(setCustomers)
      .catch(() => setCustomers([]));
  }, [query]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await api<Customer>("/customers", {
        body: {
          name,
          phone: phone || null,
          fiado:
            creditLimit.trim() !== ""
              ? { credit_limit_cents: Number(creditLimit) }
              : null,
        },
      });
      setName("");
      setPhone("");
      setCreditLimit("");
      setCustomers((list) => [created, ...list]);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao cadastrar cliente",
      );
    }
  }

  async function open(customer: Customer) {
    setSelected(customer);
    setHistory(null);
    try {
      const data = await api<History>(`/customers/${customer.id}/history`);
      setHistory(data);
    } catch {
      setHistory(null);
    }
  }

  return (
    <div className="customers">
      <section>
        <h2>Clientes</h2>
        <input
          placeholder="Buscar por nome, CPF ou telefone"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <ul className="plain-list">
          {customers.map((c) => (
            <li key={c.id}>
              <button className="row" onClick={() => open(c)}>
                <span>
                  <strong>{c.name}</strong>
                  {c.phone && <span className="muted"> {c.phone}</span>}
                </span>
                <span className="muted">
                  saldo {money(c.outstanding_balance_cents)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Cadastrar cliente</h3>
        <form className="stack" onSubmit={create}>
          <input
            placeholder="Nome *"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            placeholder="Telefone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <input
            placeholder="Limite fiado (centavos, ex 10000 = R$ 100)"
            value={creditLimit}
            onChange={(e) => setCreditLimit(e.target.value)}
            inputMode="numeric"
          />
          {error && <p className="error">{error}</p>}
          <button disabled={!name.trim()}>Cadastrar</button>
        </form>
      </section>

      {selected && history && (
        <section>
          <h3>{selected.name}</h3>
          <p className="muted">
            Saldo devedor: {money(history.outstanding_balance_cents)}
          </p>
          <ul className="plain-list">
            {history.recent_sales.map((s) => (
              <li key={s.id} className="row">
                <span>Venda #{s.id}</span>
                <span>{money(s.total_cents)}</span>
                <span className="muted">
                  {new Date(s.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

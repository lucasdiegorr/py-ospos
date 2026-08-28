import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api } from "../api";
import { enqueue, pendingCount } from "../outbox";

interface Product {
  id: number;
  sku: string;
  name: string;
  unit_price_cents: number;
  pack_quantity: number | null;
  pack_price_cents: number | null;
  available_quantity: number;
}

interface Method {
  id: string;
  name: string;
}

interface Customer {
  id: number;
  name: string;
  outstanding_balance_cents: number;
}

interface CartLine {
  product_id: number;
  name: string;
  qty: number;
  pack: boolean;
  unit_price: number;
}

interface PaymentLine {
  method: string;
  amount_cents: number;
  card_installments?: number;
}

interface Receipt {
  sale_id: number;
  total_cents: number;
  lines: string[];
}

const MONEY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function money(cents: number): string {
  return MONEY.format(cents / 100);
}

export default function Pos() {
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [methods, setMethods] = useState<Method[]>([]);
  const [method, setMethod] = useState("cash");
  const [payments, setPayments] = useState<PaymentLine[]>([]);
  const [customerQuery, setCustomerQuery] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Method[]>("/payment-methods?enabled=true")
      .then(setMethods)
      .catch(() => setMethods([]));
  }, []);

  useEffect(() => {
    api<Product[]>("/products")
      .then(setProducts)
      .catch(() => setProducts([]));
  }, []);

  useEffect(() => {
    if (!customerQuery.trim()) {
      setCustomers([]);
      return;
    }
    api<Customer[]>(`/customers?q=${encodeURIComponent(customerQuery)}`)
      .then(setCustomers)
      .catch(() => setCustomers([]));
  }, [customerQuery]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return products;
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(term) ||
        p.sku.toLowerCase().includes(term),
    );
  }, [products, query]);

  const total = cart.reduce((sum, line) => sum + line.unit_price * line.qty, 0);
  const paid = payments.reduce((sum, p) => sum + p.amount_cents, 0);
  const remaining = total - paid;

  function addLine(product: Product, pack: boolean) {
    setCart((lines) => {
      const existing = lines.find(
        (l) => l.product_id === product.id && l.pack === pack,
      );
      if (existing) {
        return lines.map((l) =>
          l === existing ? { ...l, qty: l.qty + 1 } : l,
        );
      }
      return [
        ...lines,
        {
          product_id: product.id,
          name: product.name,
          qty: 1,
          pack,
          unit_price: pack
            ? product.pack_price_cents ?? 0
            : product.unit_price_cents,
        },
      ];
    });
  }

  function bump(line: CartLine, delta: number) {
    setCart((lines) =>
      lines
        .map((l) => (l === line ? { ...l, qty: l.qty + delta } : l))
        .filter((l) => l.qty > 0),
    );
  }

  function addPayment() {
    if (remaining <= 0) return;
    if (method === "fiado" && !customer) {
      setError("Selecione um cliente para vender fiado.");
      return;
    }
    setError(null);
    setPayments((list) => [
      ...list,
      {
        method,
        amount_cents: remaining,
        card_installments: method === "card" ? 1 : undefined,
      },
    ]);
  }

  async function complete() {
    if (paid !== total || total <= 0) return;
    setBusy(true);
    setError(null);
    const payload = {
      items: cart.map((line) => ({
        product_id: line.product_id,
        quantity: line.qty,
        pack: line.pack,
      })),
      payments: payments.map((p) => ({
        method: p.method,
        amount_cents: p.amount_cents,
        ...(p.card_installments ? { installments: p.card_installments } : {}),
      })),
      customer_id: customer?.id,
    };
    const localReceipt = buildLocalReceipt();
    try {
      if (navigator.onLine === false) {
        enqueue("sale.completed", payload);
        window.dispatchEvent(new CustomEvent("outbox-changed"));
        setReceipt({ sale_id: 0, total_cents: total, lines: localReceipt });
      } else {
        const sale = await api<{ id: number }>("/sales", { body: payload });
        setReceipt({
          sale_id: sale.id,
          total_cents: total,
          lines: localReceipt,
        });
      }
      setCart([]);
      setPayments([]);
      setCustomer(null);
      setQuery("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao finalizar a venda",
      );
    } finally {
      setBusy(false);
    }
  }

  function buildLocalReceipt(): string[] {
    const lines = ["--- RECIBO ---"];
    for (const line of cart) {
      lines.push(
        `${line.pack ? "[PACK] " : ""}${line.name} x${line.qty} = ${money(
          line.unit_price * line.qty,
        )}`,
      );
    }
    lines.push(`TOTAL: ${money(total)}`);
    for (const p of payments)
      lines.push(`${p.method}: ${money(p.amount_cents)}`);
    return lines;
  }

  if (receipt) {
    return (
      <div className="receipt">
        <h2>Venda finalizada</h2>
        <p>
          {receipt.sale_id
            ? `Venda #${receipt.sale_id}`
            : `Venda local #${
                receipt.sale_id
              } — será sincronizada (${pendingCount()} pendente(s))`}
        </p>
        <pre>{receipt.lines.join("\n")}</pre>
        <button onClick={() => setReceipt(null)}>Nova venda</button>
      </div>
    );
  }

  return (
    <div className="pos">
      <section className="pos-catalog">
        <h2>Produtos</h2>
        <input
          placeholder="Buscar produto ou SKU"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <ul className="product-list">
          {filtered.map((p) => (
            <li key={p.id} className="product-row">
              <div>
                <strong>{p.name}</strong>
                <span className="muted">
                  {money(p.unit_price_cents)} · estoque {p.available_quantity}
                </span>
              </div>
              <div className="row-actions">
                <button onClick={() => addLine(p, false)}>+ un</button>
                {p.pack_price_cents != null && (
                  <button onClick={() => addLine(p, true)}>
                    + pack ({money(p.pack_price_cents)})
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="pos-cart">
        <h2>Carrinho</h2>
        <ul className="cart-lines">
          {cart.map((line, i) => (
            <li key={i}>
              <span>
                {line.pack ? "[PACK] " : ""}
                {line.name} x{line.qty}
              </span>
              <span>{money(line.unit_price * line.qty)}</span>
              <span className="row-actions">
                <button onClick={() => bump(line, -1)}>−</button>
                <button onClick={() => bump(line, 1)}>+</button>
              </span>
            </li>
          ))}
        </ul>
        <p className="total">
          Total: <strong>{money(total)}</strong>
        </p>

        <h3>Pagamento</h3>
        <select value={method} onChange={(e) => setMethod(e.target.value)}>
          {methods.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
        <p className="muted">
          {remaining > 0
            ? `Restam ${money(remaining)}`
            : "Valor já coberto pelo pagamento."}
        </p>
        <button onClick={addPayment} disabled={remaining <= 0 || busy}>
          Adicionar {method} {money(Math.max(remaining, 0))}
        </button>

        {method === "fiado" && (
          <div className="customer-picker">
            <input
              placeholder="Buscar cliente (fiado)"
              value={customerQuery}
              onChange={(e) => setCustomerQuery(e.target.value)}
            />
            <ul>
              {customers.map((c) => (
                <li key={c.id}>
                  <button onClick={() => setCustomer(c)}>
                    {c.name} — saldo {money(c.outstanding_balance_cents)}
                  </button>
                </li>
              ))}
            </ul>
            {customer && (
              <p>
                Cliente fiado: <strong>{customer.name}</strong>{" "}
                <button onClick={() => setCustomer(null)}>trocar</button>
              </p>
            )}
          </div>
        )}

        <ul className="payments">
          {payments.map((p, i) => (
            <li key={i}>
              {p.method}: {money(p.amount_cents)}
            </li>
          ))}
        </ul>

        {error && <p className="error">{error}</p>}
        <button
          className="primary"
          onClick={complete}
          disabled={paid !== total || total <= 0 || busy}
        >
          Finalizar venda
        </button>
        <p className="muted">
          <Link to="/shift">Precisa abrir o caixa? Ir para Caixa</Link>
        </p>
      </section>
    </div>
  );
}

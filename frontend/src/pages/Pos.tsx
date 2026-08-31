import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Minus, Trash2 } from "lucide-react";
import { ApiError, api } from "../api";
import { enqueue, pendingCount } from "../outbox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";

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
      <Card className="mx-auto max-w-lg">
        <CardHeader>
          <CardTitle>Venda finalizada</CardTitle>
          <CardDescription>
            {receipt.sale_id
              ? `Venda #${receipt.sale_id}`
              : `Venda local — será sincronizada (${pendingCount()} pendente(s))`}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <pre className="whitespace-pre-wrap rounded-md bg-muted p-4 font-mono text-sm text-foreground">
            {receipt.lines.join("\n")}
          </pre>
          <Button onClick={() => setReceipt(null)} className="w-full">
            Nova venda
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>Produtos</CardTitle>
            <Input
              placeholder="Buscar produto ou SKU"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {filtered.map((p) => (
                <Card key={p.id} className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium leading-tight">{p.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {money(p.unit_price_cents)} · estoque{" "}
                        {p.available_quantity}
                      </p>
                    </div>
                    {p.pack_price_cents != null && (
                      <Badge variant="outline">c/ pack</Badge>
                    )}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => addLine(p, false)}>
                      <Plus className="mr-1 h-4 w-4" /> un
                    </Button>
                    {p.pack_price_cents != null && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => addLine(p, true)}
                      >
                        pack ({money(p.pack_price_cents)})
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <Card className="lg:sticky lg:top-20">
          <CardHeader>
            <CardTitle>Carrinho</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {cart.map((line, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between gap-2 rounded-md border border-border p-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {line.pack ? "[PACK] " : ""}
                      {line.name} x{line.qty}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {money(line.unit_price * line.qty)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => bump(line, -1)}
                      aria-label="Diminuir quantidade"
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => bump(line, 1)}
                      aria-label="Aumentar quantidade"
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </li>
              ))}
              {cart.length === 0 && (
                <li className="py-6 text-center text-sm text-muted-foreground">
                  Carrinho vazio
                </li>
              )}
            </ul>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Total</span>
              <span className="text-2xl font-semibold">{money(total)}</span>
            </div>

            <Separator />

            <div className="space-y-2">
              <p className="font-medium">Pagamento</p>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                {methods.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                {remaining > 0
                  ? `Restam ${money(remaining)}`
                  : "Valor já coberto pelo pagamento."}
              </p>
              <Button
                className="w-full"
                variant="outline"
                onClick={addPayment}
                disabled={remaining <= 0 || busy}
              >
                Adicionar {method} {money(Math.max(remaining, 0))}
              </Button>
            </div>

            {method === "fiado" && (
              <div className="space-y-2">
                <Input
                  placeholder="Buscar cliente (fiado)"
                  value={customerQuery}
                  onChange={(e) => setCustomerQuery(e.target.value)}
                />
                <ul className="space-y-1">
                  {customers.map((c) => (
                    <li key={c.id}>
                      <Button
                        className="w-full justify-start"
                        variant="ghost"
                        size="sm"
                        onClick={() => setCustomer(c)}
                      >
                        {c.name} — saldo {money(c.outstanding_balance_cents)}
                      </Button>
                    </li>
                  ))}
                </ul>
                {customer && (
                  <p className="text-sm">
                    Cliente fiado: <strong>{customer.name}</strong>{" "}
                    <button
                      className="text-muted-foreground underline"
                      onClick={() => setCustomer(null)}
                    >
                      trocar
                    </button>
                  </p>
                )}
              </div>
            )}

            <div className="space-y-1">
              {payments.map((p, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-sm"
                >
                  <span>
                    {p.method}: {money(p.amount_cents)}
                  </span>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() =>
                      setPayments((list) => list.filter((_, idx) => idx !== i))
                    }
                    aria-label="Remover pagamento"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button
              className="w-full"
              onClick={complete}
              disabled={paid !== total || total <= 0 || busy}
            >
              {busy ? "Finalizando..." : "Finalizar venda"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              <Link to="/shift">Precisa abrir o caixa? Ir para Caixa</Link>
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

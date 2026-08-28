import { useEffect, useState } from "react";
import { ApiError, api } from "../api";
import { roleAtLeast, useAuth } from "../auth";

const MONEY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const money = (cents: number) => MONEY.format(cents / 100);

interface Category {
  id: number;
  name: string;
}

interface Product {
  id: number;
  name: string;
  sku: string;
  category_name: string | null;
  unit_price_cents: number;
  cost_price_cents: number | null;
  pack_quantity: number | null;
  pack_price_cents: number | null;
  available_quantity: number;
  low_stock_threshold: number;
}

export default function Products() {
  const { user } = useAuth();
  const canManage = roleAtLeast(user, "manager");
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    sku: "",
    category_id: "",
    unit_price_cents: "",
    cost_price_cents: "",
    pack_quantity: "",
    pack_price_cents: "",
    low_stock_threshold: "0",
  });

  useEffect(() => {
    api<Category[]>("/categories")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    const term = query.trim();
    api<Product[]>(
      `/products${term ? `?search=${encodeURIComponent(term)}` : ""}`,
    )
      .then(setProducts)
      .catch(() => setProducts([]));
  }, [query]);

  function setField(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const body: Record<string, unknown> = {
        name: form.name,
        sku: form.sku,
        category_id: Number(form.category_id),
        unit_price_cents: Number(form.unit_price_cents),
        low_stock_threshold: Number(form.low_stock_threshold || 0),
      };
      if (form.cost_price_cents.trim() !== "")
        body.cost_price_cents = Number(form.cost_price_cents);
      if (
        form.pack_quantity.trim() !== "" &&
        form.pack_price_cents.trim() !== ""
      ) {
        body.pack_quantity = Number(form.pack_quantity);
        body.pack_price_cents = Number(form.pack_price_cents);
      }
      await api<Product>("/products", { body });
      setForm({
        name: "",
        sku: "",
        category_id: "",
        unit_price_cents: "",
        cost_price_cents: "",
        pack_quantity: "",
        pack_price_cents: "",
        low_stock_threshold: "0",
      });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao criar produto",
      );
    }
  }

  return (
    <div className="products">
      <section>
        <h2>Produtos</h2>
        <input
          placeholder="Buscar por nome ou SKU"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <table>
          <thead>
            <tr>
              <th>Produto</th>
              <th>Preço</th>
              <th>Pack</th>
              <th>Estoque</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td>
                  {p.name}
                  <br />
                  <span className="muted">{p.sku}</span>
                </td>
                <td>{money(p.unit_price_cents)}</td>
                <td>
                  {p.pack_quantity
                    ? `${p.pack_quantity}un ${money(p.pack_price_cents ?? 0)}`
                    : "—"}
                </td>
                <td>{p.available_quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {canManage && (
        <section>
          <h3>Cadastrar produto</h3>
          <form className="stack" onSubmit={create}>
            <input
              placeholder="Nome *"
              value={form.name}
              onChange={(e) => setField("name", e.target.value)}
              required
            />
            <input
              placeholder="SKU *"
              value={form.sku}
              onChange={(e) => setField("sku", e.target.value)}
              required
            />
            <select
              value={form.category_id}
              onChange={(e) => setField("category_id", e.target.value)}
              required
            >
              <option value="">Categoria *</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <input
              placeholder="Preço un. (centavos) *"
              inputMode="numeric"
              value={form.unit_price_cents}
              onChange={(e) => setField("unit_price_cents", e.target.value)}
              required
            />
            <input
              placeholder="Custo (centavos, opcional)"
              inputMode="numeric"
              value={form.cost_price_cents}
              onChange={(e) => setField("cost_price_cents", e.target.value)}
            />
            <input
              placeholder="Qtd por pack (opcional)"
              inputMode="numeric"
              value={form.pack_quantity}
              onChange={(e) => setField("pack_quantity", e.target.value)}
            />
            <input
              placeholder="Preço do pack (opcional)"
              inputMode="numeric"
              value={form.pack_price_cents}
              onChange={(e) => setField("pack_price_cents", e.target.value)}
            />
            <input
              placeholder="Estoque mínimo"
              inputMode="numeric"
              value={form.low_stock_threshold}
              onChange={(e) => setField("low_stock_threshold", e.target.value)}
            />
            {error && <p className="error">{error}</p>}
            <button>Cadastrar</button>
          </form>
        </section>
      )}
    </div>
  );
}

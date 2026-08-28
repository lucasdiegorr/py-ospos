import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api";

const MONEY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const money = (cents: number | null | undefined) =>
  cents == null ? "—" : MONEY.format(cents / 100);

interface ShiftSummary {
  id: number;
  status: string;
  float_cents: number;
  payment_totals: Record<string, number>;
  supplies_cents: number;
  bleeds_cents: number;
  expected_cents: number;
  counted_cents: number | null;
  difference_cents: number | null;
}

export default function Shift() {
  const [summary, setSummary] = useState<ShiftSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [floatCents, setFloatCents] = useState("");
  const [movementType, setMovementType] = useState<"supply" | "bleed">(
    "supply",
  );
  const [movementAmount, setMovementAmount] = useState("");
  const [movementReason, setMovementReason] = useState("");
  const [countedCents, setCountedCents] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const current = await api<{ id: number }>("/shifts/current");
      setSummary(await api<ShiftSummary>(`/shifts/${current.id}`));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setSummary(null);
      } else {
        setError(
          err instanceof Error ? err.message : "Falha ao carregar o caixa",
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openShift(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api("/shifts", { body: { float_cents: Number(floatCents) } });
      setFloatCents("");
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao abrir o caixa",
      );
    }
  }

  async function addMovement(event: React.FormEvent) {
    event.preventDefault();
    if (!summary) return;
    setError(null);
    try {
      await api(`/shifts/${summary.id}/movements`, {
        body: {
          type: movementType,
          amount_cents: Number(movementAmount),
          reason: movementReason,
        },
      });
      setMovementAmount("");
      setMovementReason("");
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao registrar movimento",
      );
    }
  }

  async function closeShift(event: React.FormEvent) {
    event.preventDefault();
    if (!summary) return;
    setError(null);
    try {
      await api(`/shifts/${summary.id}/close`, {
        body: { counted_cents: Number(countedCents) },
      });
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao fechar o caixa",
      );
    }
  }

  if (loading) return <p>Carregando…</p>;

  if (!summary) {
    return (
      <section>
        <h2>Abrir caixa</h2>
        <form className="stack" onSubmit={openShift}>
          <input
            placeholder="Fundo de troco (centavos, ex 10000 = R$ 100)"
            inputMode="numeric"
            value={floatCents}
            onChange={(e) => setFloatCents(e.target.value)}
            required
          />
          {error && <p className="error">{error}</p>}
          <button>Abrir caixa</button>
        </form>
      </section>
    );
  }

  if (summary.status === "closed") {
    return (
      <section>
        <h2>Caixa #{summary.id} — Fechado</h2>
        <SummaryTable summary={summary} />
        <button onClick={() => void load()}>Atualizar</button>
      </section>
    );
  }

  return (
    <div className="shift">
      <section>
        <h2>Caixa #{summary.id} (aberto)</h2>
        <SummaryTable summary={summary} />
      </section>

      <section>
        <h3>Suprimento / Sangria</h3>
        <form className="stack" onSubmit={addMovement}>
          <select
            value={movementType}
            onChange={(e) =>
              setMovementType(e.target.value as "supply" | "bleed")
            }
          >
            <option value="supply">Suprimento</option>
            <option value="bleed">Sangria</option>
          </select>
          <input
            placeholder="Valor (centavos)"
            inputMode="numeric"
            value={movementAmount}
            onChange={(e) => setMovementAmount(e.target.value)}
            required
          />
          <input
            placeholder="Motivo"
            value={movementReason}
            onChange={(e) => setMovementReason(e.target.value)}
            required
          />
          <button>Registrar</button>
        </form>
      </section>

      <section>
        <h3>Fechar caixa</h3>
        <form className="stack" onSubmit={closeShift}>
          <input
            placeholder="Dinheiro contado (centavos)"
            inputMode="numeric"
            value={countedCents}
            onChange={(e) => setCountedCents(e.target.value)}
            required
          />
          {error && <p className="error">{error}</p>}
          <button>Fechar caixa</button>
        </form>
      </section>
    </div>
  );
}

function SummaryTable({ summary }: { summary: ShiftSummary }) {
  return (
    <table>
      <tbody>
        <tr>
          <td>Fundo</td>
          <td>{money(summary.float_cents)}</td>
        </tr>
        {Object.entries(summary.payment_totals).map(([method, total]) => (
          <tr key={method}>
            <td>Vendas ({method})</td>
            <td>{money(total)}</td>
          </tr>
        ))}
        <tr>
          <td>Suprimentos</td>
          <td>{money(summary.supplies_cents)}</td>
        </tr>
        <tr>
          <td>Sangrias</td>
          <td>{money(summary.bleeds_cents)}</td>
        </tr>
        <tr>
          <td>Esperado</td>
          <td>{money(summary.expected_cents)}</td>
        </tr>
        <tr>
          <td>Contado</td>
          <td>{money(summary.counted_cents)}</td>
        </tr>
        <tr>
          <td>Diferença</td>
          <td>{money(summary.difference_cents)}</td>
        </tr>
      </tbody>
    </table>
  );
}

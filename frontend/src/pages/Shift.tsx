import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

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

  if (loading) return <p className="text-muted-foreground">Carregando…</p>;

  if (!summary) {
    return (
      <Card className="mx-auto max-w-md">
        <CardHeader>
          <CardTitle>Abrir caixa</CardTitle>
          <CardDescription>
            Registre o fundo de troco para iniciar o turno.
          </CardDescription>
        </CardHeader>
        <form onSubmit={openShift}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="float">Fundo de troco (centavos)</Label>
              <Input
                id="float"
                placeholder="Ex.: 10000 = R$ 100"
                inputMode="numeric"
                value={floatCents}
                onChange={(e) => setFloatCents(e.target.value)}
                required
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" className="w-full">
              Abrir caixa
            </Button>
          </CardContent>
        </form>
      </Card>
    );
  }

  if (summary.status === "closed") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Caixa #{summary.id} — Fechado</CardTitle>
          <CardDescription>Resumo de fechamento</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SummaryTable summary={summary} />
          <Button variant="outline" onClick={() => void load()}>
            Atualizar
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Caixa #{summary.id}</CardTitle>
              <CardDescription>Resumo do turno ativo</CardDescription>
            </div>
            <Badge>Aberto</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <SummaryTable summary={summary} />
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Suprimento / Sangria</CardTitle>
          </CardHeader>
          <form onSubmit={addMovement}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="movement-type">Tipo</Label>
                <select
                  id="movement-type"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={movementType}
                  onChange={(e) =>
                    setMovementType(e.target.value as "supply" | "bleed")
                  }
                >
                  <option value="supply">Suprimento</option>
                  <option value="bleed">Sangria</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="movement-amount">Valor (centavos)</Label>
                <Input
                  id="movement-amount"
                  inputMode="numeric"
                  value={movementAmount}
                  onChange={(e) => setMovementAmount(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="movement-reason">Motivo</Label>
                <Input
                  id="movement-reason"
                  value={movementReason}
                  onChange={(e) => setMovementReason(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full">
                Registrar
              </Button>
            </CardContent>
          </form>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fechar caixa</CardTitle>
            <CardDescription>
              Informe o valor contado para fechar o turno.
            </CardDescription>
          </CardHeader>
          <form onSubmit={closeShift}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="counted">Dinheiro contado (centavos)</Label>
                <Input
                  id="counted"
                  inputMode="numeric"
                  value={countedCents}
                  onChange={(e) => setCountedCents(e.target.value)}
                  required
                />
              </div>
              {summary.difference_cents != null && (
                <div
                  className={
                    summary.difference_cents < 0
                      ? "text-destructive"
                      : "text-foreground"
                  }
                >
                  Diferença atual: {money(summary.difference_cents)}
                </div>
              )}
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <Button type="submit" className="w-full">
                Fechar caixa
              </Button>
            </CardContent>
          </form>
        </Card>
      </div>
    </div>
  );
}

function SummaryTable({ summary }: { summary: ShiftSummary }) {
  const differenceClass =
    summary.difference_cents == null
      ? "text-muted-foreground"
      : summary.difference_cents < 0
        ? "text-destructive"
        : "text-foreground";

  return (
    <table className="w-full text-sm">
      <tbody>
        <tr className="border-b border-border">
          <td className="py-2 text-muted-foreground">Fundo</td>
          <td className="py-2 text-right font-medium">
            {money(summary.float_cents)}
          </td>
        </tr>
        {Object.entries(summary.payment_totals).map(([method, total]) => (
          <tr key={method} className="border-b border-border">
            <td className="py-2 text-muted-foreground">Vendas ({method})</td>
            <td className="py-2 text-right font-medium">{money(total)}</td>
          </tr>
        ))}
        <tr className="border-b border-border">
          <td className="py-2 text-muted-foreground">Suprimentos</td>
          <td className="py-2 text-right font-medium">
            {money(summary.supplies_cents)}
          </td>
        </tr>
        <tr className="border-b border-border">
          <td className="py-2 text-muted-foreground">Sangrias</td>
          <td className="py-2 text-right font-medium">
            {money(summary.bleeds_cents)}
          </td>
        </tr>
        <tr className="border-b border-border">
          <td className="py-2 text-muted-foreground">Esperado</td>
          <td className="py-2 text-right font-medium">
            {money(summary.expected_cents)}
          </td>
        </tr>
        <tr className="border-b border-border">
          <td className="py-2 text-muted-foreground">Contado</td>
          <td className="py-2 text-right font-medium">
            {money(summary.counted_cents)}
          </td>
        </tr>
        <tr>
          <td className="py-2 text-muted-foreground">Diferença</td>
          <td className={`py-2 text-right font-medium ${differenceClass}`}>
            {money(summary.difference_cents)}
          </td>
        </tr>
      </tbody>
    </table>
  );
}

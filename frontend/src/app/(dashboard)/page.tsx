"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ShoppingCart,
  Package,
  Users,
  UserCircle,
  Wallet,
  FileText,
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const modules = [
  {
    href: "/pos",
    label: "Point of Sale",
    icon: ShoppingCart,
    desc: "Create and manage sales",
    admin: false,
  },
  {
    href: "/customers",
    label: "Customers",
    icon: Users,
    desc: "Manage customer records",
    admin: true,
  },
  {
    href: "/items",
    label: "Items",
    icon: Package,
    desc: "Manage inventory items",
    admin: true,
  },
  {
    href: "/employees",
    label: "Employees",
    icon: UserCircle,
    desc: "Manage staff accounts",
    admin: true,
  },
  {
    href: "/expenses",
    label: "Expenses",
    icon: Wallet,
    desc: "Track business expenses",
    admin: true,
  },
  {
    href: "/invoices",
    label: "Invoices",
    icon: FileText,
    desc: "View and manage invoices",
    admin: true,
  },
  {
    href: "/quotations",
    label: "Quotations",
    icon: FileText,
    desc: "Create and manage quotes",
    admin: true,
  },
];

export default function HomePage() {
  const { user } = useAuth();
  const visibleModules = modules.filter((m) => !m.admin || user?.isAdmin);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">
          Welcome, {user?.username}
        </h1>
        <p className="text-muted text-sm mt-1">
          Select a module to get started
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visibleModules.map((mod) => {
          const Icon = mod.icon;
          return (
            <Link key={mod.href} href={mod.href}>
              <Card className="hover:bg-surface-hover transition-colors cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-accent/10 text-accent">
                      <Icon size={24} />
                    </div>
                    <div>
                      <CardTitle className="text-base">{mod.label}</CardTitle>
                      <p className="text-sm text-muted">{mod.desc}</p>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

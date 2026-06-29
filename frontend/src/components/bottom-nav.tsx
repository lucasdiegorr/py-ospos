"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShoppingCart, LayoutDashboard, Package, Users, Wallet } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { href: "/", label: "Home", icon: LayoutDashboard, perm: null },
  { href: "/pos", label: "POS", icon: ShoppingCart, perm: null },
  { href: "/customers", label: "Customers", icon: Users, perm: "customers.read" },
  { href: "/items", label: "Items", icon: Package, perm: "items.read" },
  { href: "/expenses", label: "Expenses", icon: Wallet, perm: "expenses.read" },
];

export function BottomNav() {
  const { can } = useAuth();
  const pathname = usePathname();
  const visibleItems = navItems.filter((item) => !item.perm || can(item.perm));
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-surface">
      <div className="flex items-center justify-around h-16 px-2">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                active ? "text-accent" : "text-muted hover:text-foreground"
              }`}
            >
              <Icon size={20} />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

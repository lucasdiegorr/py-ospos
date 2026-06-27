"use client";

import { EntityPage, type FormFieldProps } from "@/components/entity-page";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  company_name?: string;
  is_active: boolean;
}

export default function CustomersPage() {
  return (
    <EntityPage<Customer>
      title="Customers"
      apiPath="customers"
      idField="id"
      columns={[
        { header: "Name", accessor: (c) => `${c.first_name} ${c.last_name}` },
        { header: "Email", accessor: (c) => c.email ?? "—" },
        { header: "Phone", accessor: (c) => c.phone ?? "—" },
        { header: "Company", accessor: (c) => c.company_name ?? "—" },
        {
          header: "Status",
          accessor: (c) =>
            c.is_active ? (
              <span className="text-success">Active</span>
            ) : (
              <span className="text-muted">Inactive</span>
            ),
        },
      ]}
      formFields={FormFields}
      defaultFormData={{
        first_name: "",
        last_name: "",
        email: "",
        phone: "",
        company_name: "",
      }}
      serializeForm={(data) => ({
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email || null,
        phone: data.phone || null,
        company_name: data.company_name || null,
      })}
    />
  );
}

function FormFields({ data, onChange, errors }: FormFieldProps<Customer>) {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <InputField
          label="First Name *"
          value={data.first_name ?? ""}
          onChange={(v) => onChange({ ...data, first_name: v })}
          error={errors.first_name}
        />
        <InputField
          label="Last Name *"
          value={data.last_name ?? ""}
          onChange={(v) => onChange({ ...data, last_name: v })}
          error={errors.last_name}
        />
      </div>
      <InputField
        label="Email"
        value={data.email ?? ""}
        onChange={(v) => onChange({ ...data, email: v })}
        error={errors.email}
      />
      <InputField
        label="Phone"
        value={data.phone ?? ""}
        onChange={(v) => onChange({ ...data, phone: v })}
        error={errors.phone}
      />
      <InputField
        label="Company"
        value={data.company_name ?? ""}
        onChange={(v) => onChange({ ...data, company_name: v })}
        error={errors.company_name}
      />
    </>
  );
}

function InputField({
  label,
  value,
  onChange,
  error,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
      />
      {error && <p className="text-xs text-danger mt-1">{error}</p>}
    </div>
  );
}

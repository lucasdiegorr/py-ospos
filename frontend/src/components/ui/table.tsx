"use client";

import { Button } from "./button";

export interface Column<T> {
  header: string;
  accessor: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageCount: number;
  pageIndex: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
}

export function DataTable<T>({
  columns,
  data,
  pageCount,
  pageIndex,
  onPageChange,
  loading,
}: DataTableProps<T>) {
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-surface">
            <tr>
              {columns.map((col, i) => (
                <th
                  key={i}
                  className={`px-4 py-3 text-left font-medium text-muted ${col.className ?? ""}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-muted"
                >
                  Loading...
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-muted"
                >
                  No results found
                </td>
              </tr>
            ) : (
              data.map((item, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="border-t border-border hover:bg-surface/50 transition-colors"
                >
                  {columns.map((col, colIdx) => (
                    <td
                      key={colIdx}
                      className={`px-4 py-3 ${col.className ?? ""}`}
                    >
                      {col.accessor(item)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted">
            Page {pageIndex + 1} of {pageCount}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={pageIndex === 0}
              onClick={() => onPageChange(pageIndex - 1)}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={pageIndex >= pageCount - 1}
              onClick={() => onPageChange(pageIndex + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

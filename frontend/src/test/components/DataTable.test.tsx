import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable, type Column } from "@/components/ui/table";

interface TestItem {
  id: string;
  name: string;
}

const columns: Column<TestItem>[] = [
  { header: "ID", accessor: (item) => item.id },
  { header: "Name", accessor: (item) => item.name },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        pageCount={1}
        pageIndex={0}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("renders data rows", () => {
    render(
      <DataTable
        columns={columns}
        data={[
          { id: "1", name: "Item A" },
          { id: "2", name: "Item B" },
        ]}
        pageCount={1}
        pageIndex={0}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByText("Item A")).toBeInTheDocument();
    expect(screen.getByText("Item B")).toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        pageCount={1}
        pageIndex={0}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByText("No results found")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        pageCount={1}
        pageIndex={0}
        onPageChange={() => {}}
        loading={true}
      />
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows pagination controls when multiple pages", () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: "1", name: "Item" }]}
        pageCount={3}
        pageIndex={1}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
    expect(screen.getByText("Previous")).toBeInTheDocument();
    expect(screen.getByText("Next")).toBeInTheDocument();
  });

  it("does not show pagination for single page", () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: "1", name: "Item" }]}
        pageCount={1}
        pageIndex={0}
        onPageChange={() => {}}
      />
    );

    expect(screen.queryByText("Previous")).not.toBeInTheDocument();
    expect(screen.queryByText("Next")).not.toBeInTheDocument();
  });

  it("calls onPageChange with next page", async () => {
    const onPageChange = vi.fn();
    render(
      <DataTable
        columns={columns}
        data={[{ id: "1", name: "Item" }]}
        pageCount={3}
        pageIndex={0}
        onPageChange={onPageChange}
      />
    );

    await userEvent.click(screen.getByText("Next"));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("calls onPageChange with previous page", async () => {
    const onPageChange = vi.fn();
    render(
      <DataTable
        columns={columns}
        data={[{ id: "1", name: "Item" }]}
        pageCount={3}
        pageIndex={1}
        onPageChange={onPageChange}
      />
    );

    await userEvent.click(screen.getByText("Previous"));
    expect(onPageChange).toHaveBeenCalledWith(0);
  });

  it("disables Previous on first page", () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: "1", name: "Item" }]}
        pageCount={3}
        pageIndex={0}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByText("Previous")).toBeDisabled();
  });

  it("disables Next on last page", () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: "1", name: "Item" }]}
        pageCount={3}
        pageIndex={2}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByText("Next")).toBeDisabled();
  });
});

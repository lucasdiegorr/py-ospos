import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "@/components/ui/modal";

describe("Modal", () => {
  it("does not render when open is false", () => {
    render(
      <Modal open={false} onClose={() => {}} title="Test">
        Content
      </Modal>
    );
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });

  it("renders title and content when open is true", () => {
    render(
      <Modal open={true} onClose={() => {}} title="My Modal">
        Modal content
      </Modal>
    );
    expect(screen.getByText("My Modal")).toBeInTheDocument();
    expect(screen.getByText("Modal content")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    render(
      <Modal open={true} onClose={onClose} title="Test">
        Content
      </Modal>
    );

    const closeButton = screen.getByRole("button", { name: /close/i });
    await userEvent.click(closeButton);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when backdrop is clicked", async () => {
    const onClose = vi.fn();
    render(
      <Modal open={true} onClose={onClose} title="Test">
        Content
      </Modal>
    );

    // The backdrop overlay
    const backdrop = screen.getByTestId("modal-backdrop");
    await userEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledOnce();
  });
});

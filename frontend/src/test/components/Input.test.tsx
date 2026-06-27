import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "@/components/ui/input";

describe("Input", () => {
  it("renders label and input", () => {
    render(<Input label="Username" value="" onChange={() => {}} />);
    expect(screen.getByText("Username")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("calls onChange when typing", async () => {
    const onChange = vi.fn();
    render(<Input label="Name" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "a");
    expect(onChange).toHaveBeenCalled();
  });

  it("displays error message", () => {
    render(<Input label="Email" value="" onChange={() => {}} error="Required" />);
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("shows password input with type password", () => {
    render(<Input label="Password" type="password" value="" onChange={() => {}} />);
    const input = screen.getByDisplayValue("");
    expect(input).toHaveAttribute("type", "password");
  });

  it("displays the provided value", () => {
    render(<Input label="City" value="New York" onChange={() => {}} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("New York");
  });
});

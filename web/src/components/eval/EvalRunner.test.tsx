import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import EvalRunner from "./EvalRunner";

describe("EvalRunner", () => {
  const defaultProps = {
    onRun: vi.fn(),
    isPending: false,
  };

  it("renders the component with model chips", () => {
    render(<EvalRunner {...defaultProps} />);
    expect(screen.getByText("Run Evaluation")).toBeDefined();
    expect(screen.getByText("gemini-2.0-flash")).toBeDefined();
    expect(screen.getByText("gpt-4o")).toBeDefined();
  });

  it("shows selected model count in run button", () => {
    render(<EvalRunner {...defaultProps} />);
    expect(screen.getByText("Run on 2 models")).toBeDefined();
  });

  it("toggles model selection on chip click", () => {
    render(<EvalRunner {...defaultProps} />);
    const gptChip = screen.getByText("gpt-4o");
    fireEvent.click(gptChip);
    // After deselecting gpt-4o, only 1 model remains
    expect(screen.getByText("Run on 1 model")).toBeDefined();
  });

  it("disables run button when no models selected", () => {
    render(<EvalRunner {...defaultProps} />);
    // Deselect both default models
    fireEvent.click(screen.getByText("gemini-2.0-flash"));
    fireEvent.click(screen.getByText("gpt-4o"));
    const btn = screen.getByText("Run on 0 models");
    expect(btn.closest("button")!.hasAttribute("disabled")).toBe(true);
  });

  it("shows loading state when isPending", () => {
    render(<EvalRunner {...defaultProps} isPending={true} />);
    expect(screen.getByText("Running evaluation...")).toBeDefined();
  });

  it("calls onRun with selected models", () => {
    const onRun = vi.fn();
    render(<EvalRunner {...defaultProps} onRun={onRun} />);
    const runBtn = screen.getByText("Run on 2 models");
    fireEvent.click(runBtn);
    expect(onRun).toHaveBeenCalledOnce();
    expect(onRun.mock.calls[0][0]).toEqual(["gemini-2.0-flash", "gpt-4o"]);
  });

  it("adds custom model via input", () => {
    render(<EvalRunner {...defaultProps} />);
    const input = screen.getByPlaceholderText("Add custom model...");
    fireEvent.change(input, { target: { value: "my-custom-model" } });
    const addBtn = screen.getByText("Add");
    fireEvent.click(addBtn);
    expect(screen.getByText("Run on 3 models")).toBeDefined();
  });

  it("shows auto-generate tests button when callback provided", () => {
    const onGenerate = vi.fn();
    render(<EvalRunner {...defaultProps} onGenerateTests={onGenerate} />);
    expect(screen.getByText("Auto-Generate Tests")).toBeDefined();
  });

  it("hides auto-generate tests button when no callback", () => {
    render(<EvalRunner {...defaultProps} />);
    expect(screen.queryByText("Auto-Generate Tests")).toBeNull();
  });

  it("shows variables toggle", () => {
    render(<EvalRunner {...defaultProps} />);
    expect(screen.getByText("Add variables (JSON)")).toBeDefined();
  });

  it("toggles variables textarea", () => {
    render(<EvalRunner {...defaultProps} />);
    fireEvent.click(screen.getByText("Add variables (JSON)"));
    expect(screen.getByText("Hide variables")).toBeDefined();
  });
});

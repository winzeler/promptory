import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PromptBadges from "./PromptBadges";

describe("PromptBadges", () => {
  it("renders type and environment badges", () => {
    render(<PromptBadges type="chat" environment="production" />);
    expect(screen.getByText("chat")).toBeDefined();
    expect(screen.getByText("production")).toBeDefined();
  });

  it("applies correct color classes for production", () => {
    const { container } = render(<PromptBadges type="chat" environment="production" />);
    const badges = container.querySelectorAll("span");
    expect(badges[0].className).toContain("bg-blue-100");
    expect(badges[1].className).toContain("bg-green-100");
  });

  it("applies correct color classes for staging", () => {
    const { container } = render(<PromptBadges type="tts" environment="staging" />);
    const badges = container.querySelectorAll("span");
    expect(badges[0].className).toContain("bg-purple-100");
    expect(badges[1].className).toContain("bg-yellow-100");
  });

  it("applies correct color classes for development", () => {
    const { container } = render(<PromptBadges type="completion" environment="development" />);
    const badges = container.querySelectorAll("span");
    expect(badges[0].className).toContain("bg-indigo-100");
    expect(badges[1].className).toContain("bg-gray-100");
  });

  it("falls back to gray for unknown types", () => {
    const { container } = render(<PromptBadges type="unknown" environment="unknown" />);
    const badges = container.querySelectorAll("span");
    expect(badges[0].className).toContain("bg-gray-100");
    expect(badges[1].className).toContain("bg-gray-100");
  });

  it("renders all supported prompt types", () => {
    const types = ["chat", "tts", "completion", "transcription", "image"];
    for (const t of types) {
      const { unmount } = render(<PromptBadges type={t} environment="production" />);
      expect(screen.getByText(t)).toBeDefined();
      unmount();
    }
  });
});

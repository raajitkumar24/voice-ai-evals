import React from "react";
import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";
import OverviewPage from "./page";

describe("OverviewPage", () => {
  it("shows the safety promise and evidence-backed metrics", () => {
    render(<OverviewPage />);
    expect(screen.getByText(/No production writeback/i)).toBeInTheDocument();
    expect(screen.getByText(/Failure ownership/i)).toBeInTheDocument();
    expect(screen.getByText(/Human controlled/i)).toBeInTheDocument();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import App from "../src/App";
import type { Dashboard } from "../src/types";
import fixture from "./fixtures/dashboard.json";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      const body = path.startsWith("/api/metadata")
        ? fixture.metadata
        : path.startsWith("/api/replay")
          ? fixture.replay
          : path.startsWith("/api/accuracy")
            ? fixture.accuracy
            : fixture;
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});

test("shows measured forecast accuracy and actuals immediately without an unlocking action", async () => {
  render(<App />);
  expect(await screen.findByText("783")).toBeVisible();
  expect(
    screen.getByRole("img", { name: /with actual generation/i }),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: /reveal actuals/i }),
  ).not.toBeInTheDocument();
});

test("refreshes from Elexon once and updates daily, monthly and provenance from the same response", async () => {
  const next = structuredClone(fixture);
  next.replay.metrics.latest.mae = 1200;
  next.accuracy.aggregate.mae = 1100;
  next.data_status.retrieved_at = "2026-10-25T09:22:53Z";
  next.metadata.retrieved_at = next.data_status.retrieved_at;
  let finishRefresh: ((response: Response) => void) | undefined;
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL, options?: RequestInit) => {
      if (options?.method === "POST")
        return new Promise<Response>((resolve) => {
          finishRefresh = resolve;
        });
      return new Response(JSON.stringify(fixture), { status: 200 });
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("783");
  await user.click(screen.getByRole("button", { name: "Refresh from Elexon" }));
  expect(screen.getByRole("button", { name: "Refreshing…" })).toBeDisabled();
  finishRefresh!(new Response(JSON.stringify(next), { status: 200 }));
  expect(await screen.findByText("1,200")).toBeVisible();
  expect(screen.getByText(/Fetched 25 Oct 2026, 09:22:53 GMT/)).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "January", exact: true }),
  );
  expect(await screen.findByText("1,100")).toBeVisible();
  expect(
    fetchMock.mock.calls.map(([path, options]) => [
      String(path).split("?")[0],
      options?.method,
    ]),
  ).toEqual([
    ["/api/dashboard", "GET"],
    ["/api/refresh", "POST"],
  ]);
});

test("keeps actuals and accuracy visible when selecting another date, cutoff or publication", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const next = structuredClone(fixture);
    const query = new URL(String(input), "http://localhost").searchParams;
    next.replay.decision.date =
      query.get("decision_date") ?? next.replay.decision.date;
    next.replay.decision.cutoff =
      query.get("cutoff") ?? next.replay.decision.cutoff;
    return new Response(JSON.stringify(next), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByText("783");
  fireEvent.change(screen.getByLabelText("Decision date"), {
    target: { value: "2026-01-16" },
  });
  await screen.findByText("783");
  fireEvent.change(screen.getByLabelText("Decision cutoff in London time"), {
    target: { value: "08:00" },
  });
  await screen.findByText("783");
  await userEvent.click(screen.getByRole("button", { name: /04:30/ }));
  await screen.findByText("783");
  expect(
    screen.getByRole("img", { name: /with actual generation/i }),
  ).toBeVisible();
  expect(
    screen.queryByText(/available after|actuals hidden|reveal actuals/i),
  ).not.toBeInTheDocument();
  expect(
    fetchMock.mock.calls.every(([path]) =>
      String(path).startsWith("/api/dashboard?"),
    ),
  ).toBe(true);
  expect(String(fetchMock.mock.calls.at(-1)![0])).toContain("publication=");
});

test("labels an unavailable upstream as saved fallback and keeps refresh available", async () => {
  const saved = structuredClone(fixture);
  saved.data_status.mode = "snapshot_fallback";
  saved.data_status.stale = true;
  saved.data_status.refresh_error = "Elexon service unavailable";
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(saved), { status: 200 })),
  );
  render(<App />);
  await screen.findByText("783");
  expect(screen.getByText("Saved fallback / refresh failed")).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Elexon service unavailable",
  );
  expect(
    screen.queryByText("Fetched from Elexon", { exact: true }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Refresh from Elexon" }),
  ).toBeEnabled();
});

test("keeps decisions in January 2026 and explains monthly metrics with monthly samples", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("783");
  const dateInput = screen.getByLabelText("Decision date");
  expect(dateInput).toHaveAttribute("min", "2026-01-01");
  expect(dateInput).toHaveAttribute("max", "2026-01-31");
  fireEvent.change(dateInput, { target: { value: "2026-02-01" } });
  expect(dateInput).toHaveValue("2026-01-15");
  await user.click(
    screen.getByRole("button", { name: "January", exact: true }),
  );
  await user.click(
    screen.getByRole("button", { name: "Explain january mean absolute error" }),
  );
  await waitFor(() => expect(screen.getByRole("dialog")).toBeVisible());
  expect(
    screen.getByText(/January 2026 review: the headline metrics pool 744/),
  ).toBeVisible();
  expect(
    screen.queryByText("An hour from this decision"),
  ).not.toBeInTheDocument();
});

test("retains the last successful dataset and exposes a failed manual refresh", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, options?: RequestInit) => {
      if (options?.method === "POST")
        throw new Error("The data service could not be reached");
      return new Response(JSON.stringify(fixture), { status: 200 });
    }),
  );
  render(<App />);
  await screen.findByText("783");
  await userEvent.click(
    screen.getByRole("button", { name: "Refresh from Elexon" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("Refresh failed");
  expect(screen.getByText("783")).toBeVisible();
  expect(
    screen.getByText("Cached Elexon response / refresh failed"),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Refresh from Elexon" }),
  ).toBeEnabled();
});

test("does not claim cached data exists when both initial load and refresh fail", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw new Error("Service unavailable");
    }),
  );
  render(<App />);
  await screen.findByText("This decision could not be loaded.");
  await userEvent.click(
    screen.getByRole("button", { name: "Refresh from Elexon" }),
  );
  expect(await screen.findByText("Elexon refresh failed")).toBeVisible();
  expect(
    screen.queryByText("Cached Elexon response / refresh failed"),
  ).not.toBeInTheDocument();
  expect(
    screen.getByText("No dataset loaded. Retry or refresh from Elexon."),
  ).toBeVisible();
});

test("shows available actual generation even when the selected cutoff has no forecast", async () => {
  const noForecast = structuredClone(fixture) as Dashboard;
  noForecast.replay.coverage.forecast_hours = 0;
  noForecast.replay.coverage.matched_hours = 0;
  noForecast.replay.metrics.latest.mae = null;
  noForecast.replay.metrics.latest.n = 0;
  noForecast.replay.series.forEach((point) => {
    point.latest = null;
    point.previous = null;
    point.error = null;
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () => new Response(JSON.stringify(noForecast), { status: 200 }),
    ),
  );
  render(<App />);
  expect(
    await screen.findByRole("img", { name: /with actual generation/i }),
  ).toBeVisible();
});

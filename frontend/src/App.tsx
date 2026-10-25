import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDown,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  ChartNoAxesCombined,
  Check,
  CircleHelp,
  Clock3,
  Download,
  ExternalLink,
  Eye,
  EyeOff,
  FileText,
  Info,
  Layers3,
  LockKeyhole,
  Play,
  RefreshCw,
  ShieldCheck,
  Wind,
  X,
} from "lucide-react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Accuracy, Metadata, Point, Replay } from "./types";

type View = "replay" | "review";
type Explanation = "methodology" | "mae" | "rmse" | "bias" | "shortfall";
const TZ = "Europe/London";
const number = (value: number | null | undefined, digits = 0) =>
  value == null || !Number.isFinite(value)
    ? "—"
    : new Intl.NumberFormat("en-GB", { maximumFractionDigits: digits }).format(
        value,
      );
const signed = (value: number | null | undefined, digits = 0) =>
  value == null ? "—" : `${value > 0 ? "+" : ""}${number(value, digits)}`;
const dateLabel = (value: string, short = false) =>
  new Date(`${value.slice(0, 10)}T12:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: TZ,
    ...(short ? {} : { year: "numeric" }),
  });
const timeLabel = (value: string | null | undefined, withDate = false) =>
  !value
    ? "—"
    : new Date(value).toLocaleString("en-GB", {
        ...(withDate ? { day: "numeric", month: "short" } : {}),
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: TZ,
      });
const hourLabel = (value: string) =>
  new Date(value).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: TZ,
  });
const avg = (values: (number | null)[]) => {
  const valid = values.filter((v): v is number => v != null);
  return valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
};

async function readApi<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    let detail = `The data service returned ${response.status}.`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* retain status message */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function App() {
  const [view, setView] = useState<View>("replay");
  const [date, setDate] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState("09:00");
  const [publication, setPublication] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [accuracy, setAccuracy] = useState<Accuracy | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [retry, setRetry] = useState(0);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const query = new URLSearchParams({
    decision_date: date,
    cutoff,
    ...(publication ? { publication } : {}),
  }).toString();

  useEffect(() => {
    const controller = new AbortController();
    readApi<Metadata>("/api/metadata", controller.signal)
      .then(setMetadata)
      .catch(() => {
        /* replay carries its own source provenance */
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setRevealed(false);
    setLoading(true);
    setError(null);
    setReplay(null);
    readApi<Replay>(`/api/replay?${query}`, controller.signal)
      .then(setReplay)
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [query, retry]);

  useEffect(() => {
    if (view !== "review") return;
    const controller = new AbortController();
    setReviewLoading(true);
    setReviewError(null);
    setAccuracy(null);
    readApi<Accuracy>(
      `/api/accuracy?${new URLSearchParams({ cutoff })}`,
      controller.signal,
    )
      .then(setAccuracy)
      .catch((e: Error) => {
        if (e.name !== "AbortError") setReviewError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setReviewLoading(false);
      });
    return () => controller.abort();
  }, [view, cutoff, retry]);

  const chooseDate = (nextDate: string) => {
    setDate(nextDate);
    setPublication(null);
    setRevealed(false);
  };
  const chooseCutoff = (nextCutoff: string) => {
    setCutoff(nextCutoff);
    setPublication(null);
    setRevealed(false);
  };
  const openReplay = (nextDate: string) => {
    chooseDate(nextDate);
    setView("replay");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="app-shell">
      <aside className="nav-rail" aria-label="Main navigation">
        <a
          className="brand-mark"
          href="#"
          aria-label="Wind Decision Replay home"
          onClick={(e) => {
            e.preventDefault();
            setView("replay");
          }}
        >
          <Wind size={27} strokeWidth={1.7} />
        </a>
        <div className="rail-divider" />
        <button
          className={`rail-button ${view === "replay" ? "active" : ""}`}
          onClick={() => setView("replay")}
          aria-current={view === "replay" ? "page" : undefined}
        >
          <Play size={20} />
          <span>Replay</span>
        </button>
        <button
          className={`rail-button ${view === "review" ? "active" : ""}`}
          onClick={() => setView("review")}
          aria-current={view === "review" ? "page" : undefined}
        >
          <ChartNoAxesCombined size={21} />
          <span>January</span>
        </button>
        <button
          className="rail-button"
          onClick={() => setExplanation("methodology")}
        >
          <FileText size={20} />
          <span>Methods</span>
        </button>
        <div className="rail-bottom">
          <span className="pilot-dot" />
          <span>
            PILOT
            <br />
            01 / 26
          </span>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="product-wordmark">
            Wind <span>Decision Replay</span>
          </div>
          <div className="topbar-context">
            <span className="status-dot" />
            GB wind
            <span className="context-divider" />
            Historical pilot<span className="pilot-tag">JAN 2026</span>
          </div>
          <button
            className="icon-button topbar-help"
            aria-label="Open methodology"
            onClick={() => setExplanation("methodology")}
          >
            <CircleHelp size={18} />
          </button>
        </header>

        <main id="main-content" className="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span />
                {view === "replay"
                  ? "THE DAY-AHEAD DECISION DESK"
                  : "THE MONTH IN PERSPECTIVE"}
              </div>
              <h1>
                {view === "replay" ? (
                  <>
                    Tomorrow, with
                    <br className="mobile-break" /> hindsight removed.
                  </>
                ) : (
                  "A month of decisions. Measured."
                )}
              </h1>
              <p>
                {view === "replay"
                  ? "See the wind forecast a buyer could know. Then reveal what happened."
                  : "Evaluate every January decision with the same forecast selection rule."}
              </p>
            </div>
            <button
              className="text-button methodology-link"
              onClick={() => setExplanation("methodology")}
            >
              How this works <ArrowUpRight size={15} />
            </button>
          </div>

          <section className="decision-controls" aria-label="Decision settings">
            <div className="control-label">
              <span className="control-step">01</span>
              <div>
                <strong>
                  {view === "replay"
                    ? "Set the decision"
                    : "Set the daily cutoff"}
                </strong>
                <span>All times in London · GMT in January</span>
              </div>
            </div>
            <div className="control-fields">
              {view === "replay" && (
                <label className="field">
                  <span>
                    <CalendarDays size={14} />
                    Decision date
                  </span>
                  <input
                    type="date"
                    value={date}
                    min={metadata?.min_date ?? "2026-01-01"}
                    max={metadata?.max_date ?? "2026-01-31"}
                    onChange={(e) => {
                      if (e.target.value) chooseDate(e.target.value);
                    }}
                  />
                </label>
              )}
              <label className="field time-field">
                <span>
                  <Clock3 size={14} />
                  Decision cutoff
                </span>
                <input
                  aria-label="Decision cutoff in London time"
                  type="time"
                  step="900"
                  value={cutoff}
                  onChange={(e) => {
                    if (e.target.value) chooseCutoff(e.target.value);
                  }}
                />
              </label>
            </div>
            <div className="cutoff-note">
              <LockKeyhole size={15} />
              <span>
                Only forecasts published
                <br />
                <strong>at or before {cutoff}</strong>
              </span>
            </div>
          </section>

          {view === "replay" ? (
            <>
              <div className="section-heading">
                <div>
                  <h2>Decision replay</h2>
                  <span className="subtle">
                    Next-day national wind generation
                  </span>
                </div>
                <span className="delivery-label">
                  <ArrowRight size={14} />
                  Delivery{" "}
                  {replay
                    ? dateLabel(replay.decision.delivery_date)
                    : dateLabel(
                        new Date(
                          new Date(`${date}T12:00:00Z`).getTime() + 86400000,
                        ).toISOString(),
                      )}
                </span>
              </div>
              {loading ? (
                <ReplaySkeleton />
              ) : error ? (
                <ErrorState
                  message={error}
                  onRetry={() => setRetry((v) => v + 1)}
                />
              ) : (
                replay && (
                  <>
                    <div className="replay-layout">
                      <section
                        className="chart-card"
                        aria-label="Wind generation forecast chart"
                      >
                        <div className="chart-header">
                          <div className="chart-title">
                            <span className="small-label">
                              DELIVERY PROFILE
                            </span>
                            <h3>{dateLabel(replay.decision.delivery_date)}</h3>
                            <span className="chart-unit">
                              Wind generation · GW
                            </span>
                          </div>
                          <button
                            className={`reveal-button ${revealed ? "revealed" : ""}`}
                            disabled={!replay.coverage.actual_hours}
                            onClick={() => setRevealed((value) => !value)}
                          >
                            {revealed ? (
                              <EyeOff size={16} />
                            ) : (
                              <Eye size={16} />
                            )}
                            {revealed ? "Hide actuals" : "Reveal actuals"}
                            <span className="keycap">
                              {revealed ? <Check size={11} /> : "02"}
                            </span>
                          </button>
                        </div>
                        <div className="chart-legend">
                          <span>
                            <i className="legend-line latest" />
                            Selected forecast
                          </span>
                          <span>
                            <i className="legend-line previous" />
                            Previous forecast
                          </span>
                          <span className={!revealed ? "legend-muted" : ""}>
                            <i
                              className={`legend-line actual ${!revealed ? "hidden-line" : ""}`}
                            />
                            {revealed ? "Actual generation" : "Actuals hidden"}
                          </span>
                          {revealed && (
                            <span>
                              <i className="legend-area shortfall" />
                              Wind below forecast
                            </span>
                          )}
                        </div>
                        {replay.coverage.forecast_hours ? (
                          <GenerationChart
                            points={replay.series}
                            revealed={revealed}
                          />
                        ) : (
                          <div className="empty-chart">
                            <Wind size={32} />
                            <h3>No forecast available at this time</h3>
                            <p>
                              Try a later cutoff or another January decision
                              date.
                            </p>
                          </div>
                        )}
                        <div className="chart-footnote">
                          <ShieldCheck size={14} />
                          <span>
                            {revealed
                              ? "Hindsight revealed. Actuals are shown for retrospective evaluation."
                              : "Decision view. Future actuals are hidden from this replay."}
                          </span>
                          <span className="coverage-pill">
                            {replay.coverage.forecast_hours} /{" "}
                            {replay.coverage.expected_hours} forecast hours
                          </span>
                        </div>
                        <div className="publication-panel">
                          <div className="publication-heading">
                            <div>
                              <Layers3 size={14} />
                              <strong>Forecast publication</strong>
                            </div>
                            <span>
                              Step through information available by {cutoff}
                            </span>
                          </div>
                          <div className="publication-timeline">
                            {replay.publications.length ? (
                              replay.publications
                                .slice(-5)
                                .map((item, index, items) => (
                                  <button
                                    key={item.publish_time}
                                    className={`publication-button ${item.selected ? "selected" : ""}`}
                                    onClick={() => {
                                      setPublication(
                                        index === items.length - 1
                                          ? null
                                          : item.publish_time,
                                      );
                                      setRevealed(false);
                                    }}
                                    aria-pressed={item.selected}
                                  >
                                    <span className="timeline-node">
                                      {item.selected && <Check size={9} />}
                                    </span>
                                    <span className="publication-time">
                                      {timeLabel(item.publish_time)}
                                    </span>
                                    <span className="publication-date">
                                      {dateLabel(item.publish_time, true)}
                                      {index === items.length - 1
                                        ? " · latest"
                                        : ""}
                                    </span>
                                  </button>
                                ))
                            ) : (
                              <p className="subtle">
                                No eligible publications.
                              </p>
                            )}
                          </div>
                        </div>
                      </section>
                      <DecisionBrief
                        replay={replay}
                        revealed={revealed}
                        onExplain={() => setExplanation("methodology")}
                      />
                    </div>

                    <div className="section-heading results-heading">
                      <div>
                        <h2>
                          {revealed
                            ? "The forecast, held to account."
                            : "What happened comes next."}
                        </h2>
                        <span className="subtle">
                          {revealed
                            ? `${replay.metrics.latest.n} matched hourly observations · selected forecast versus actuals`
                            : "Reveal actuals to evaluate the forecast against recorded generation."}
                        </span>
                      </div>
                      {revealed && (
                        <a
                          className="text-button"
                          href={`/api/replay.csv?${query}`}
                          download
                        >
                          Export evaluated data <Download size={14} />
                        </a>
                      )}
                    </div>
                    <div
                      className={`metric-grid ${!revealed ? "metrics-locked" : ""}`}
                    >
                      <MetricCard
                        label="Mean absolute error"
                        value={number(replay.metrics.latest.mae)}
                        unit="MW"
                        note="Typical size of forecast error"
                        kind="mae"
                        revealed={revealed}
                        onExplain={setExplanation}
                      />
                      <MetricCard
                        label="Root mean square error"
                        value={number(replay.metrics.latest.rmse)}
                        unit="MW"
                        note="Gives larger misses more weight"
                        kind="rmse"
                        revealed={revealed}
                        onExplain={setExplanation}
                      />
                      <MetricCard
                        label="Forecast bias"
                        value={signed(replay.metrics.latest.bias)}
                        unit="MW"
                        note="Positive means wind was overforecast"
                        kind="bias"
                        revealed={revealed}
                        onExplain={setExplanation}
                      />
                      <MetricCard
                        label="Wind shortfall vs forecast"
                        value={number(replay.metrics.latest.positive_error_mwh)}
                        unit="MWh"
                        note="Sum of positive errors over time"
                        kind="shortfall"
                        revealed={revealed}
                        onExplain={setExplanation}
                        accent
                      />
                    </div>
                    {revealed && <RevisionComparison replay={replay} />}
                    <div className="case-study-strip">
                      <div>
                        <span className="small-label">
                          EXPLORE A REAL DECISION
                        </span>
                        <p>One month. Different conditions.</p>
                      </div>
                      <div className="case-links">
                        <button
                          onClick={() => chooseDate("2026-01-15")}
                          className={
                            date === "2026-01-15" ? "current-case" : ""
                          }
                        >
                          15 January <ArrowUpRight size={13} />
                        </button>
                        {(metadata?.case_studies ?? [])
                          .filter(
                            (item) =>
                              (item.date ?? item.decision_date) &&
                              (item.date ?? item.decision_date) !==
                                "2026-01-15",
                          )
                          .slice(0, 2)
                          .map((item) => (
                            <button
                              key={item.date ?? item.decision_date}
                              onClick={() =>
                                chooseDate((item.date ?? item.decision_date)!)
                              }
                            >
                              {dateLabel(
                                (item.date ?? item.decision_date)!,
                                true,
                              )}{" "}
                              <ArrowUpRight size={13} />
                            </button>
                          ))}
                        <button onClick={() => setView("review")}>
                          Review all of January <ArrowRight size={13} />
                        </button>
                      </div>
                    </div>
                  </>
                )
              )}
            </>
          ) : (
            <JanuaryReview
              accuracy={accuracy}
              loading={reviewLoading}
              error={reviewError}
              cutoff={cutoff}
              onRetry={() => setRetry((v) => v + 1)}
              onReplay={openReplay}
              onExplain={setExplanation}
            />
          )}

          <footer className="page-footer">
            <div>
              <span className="status-dot" />
              <span>Elexon Insights · National wind only</span>
              <span className="footer-divider">/</span>
              <span>January 2026 decision dates</span>
            </div>
            <button onClick={() => setExplanation("methodology")}>
              Sources & methodology <ArrowUpRight size={12} />
            </button>
          </footer>
        </main>
      </div>
      {explanation && (
        <ExplanationDrawer
          kind={explanation}
          replay={replay}
          revealed={revealed}
          metadata={metadata}
          context={view}
          accuracy={accuracy}
          onClose={() => setExplanation(null)}
        />
      )}
    </div>
  );
}

function GenerationChart({
  points,
  revealed,
}: {
  points: Point[];
  revealed: boolean;
}) {
  const chartPoints = points.map((point) => ({
    ...point,
    actual: revealed ? point.actual : null,
    error: revealed ? point.error : null,
    shortfallRange:
      revealed &&
      point.latest != null &&
      point.actual != null &&
      point.latest > point.actual
        ? [point.actual, point.latest]
        : null,
  }));
  return (
    <div
      className="generation-chart"
      role="img"
      aria-label={`Hourly wind generation chart comparing selected and previous forecasts${revealed ? " with actual generation" : "; actual generation is hidden"}`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={chartPoints}
          margin={{ top: 14, right: 16, bottom: 8, left: 3 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="#e9eeeb"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="start_time"
            tickFormatter={hourLabel}
            minTickGap={40}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#7a8781", fontSize: 11 }}
            dy={9}
          />
          <YAxis
            width={44}
            domain={[0, "auto"]}
            tickFormatter={(value: number) => number(value / 1000, 1)}
            tickCount={5}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#7a8781", fontSize: 11 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0].payload as Point;
              return (
                <div className="chart-tooltip">
                  <strong>
                    {hourLabel(point.start_time)}–
                    {hourLabel(
                      new Date(
                        new Date(point.start_time).getTime() + 3600000,
                      ).toISOString(),
                    )}
                  </strong>
                  <div>
                    <i className="tooltip-dot latest" />
                    Selected <b>{number(point.latest, 1)} MW</b>
                  </div>
                  <div>
                    <i className="tooltip-dot previous" />
                    Previous <b>{number(point.previous)} MW</b>
                  </div>
                  {revealed && (
                    <>
                      <div>
                        <i className="tooltip-dot actual" />
                        Actual <b>{number(point.actual, 1)} MW</b>
                      </div>
                      <div className="tooltip-error">
                        Forecast − actual <b>{signed(point.error, 1)} MW</b>
                      </div>
                    </>
                  )}
                  <p>Published {timeLabel(point.latest_publish_time, true)}</p>
                </div>
              );
            }}
          />
          {revealed && (
            <Area
              type="monotone"
              dataKey="shortfallRange"
              fill="#c49253"
              fillOpacity={0.18}
              stroke="none"
              connectNulls={false}
              isAnimationActive={false}
              tooltipType="none"
              activeDot={false}
            />
          )}
          <Line
            type="monotone"
            dataKey="previous"
            stroke="#a6afa9"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="latest"
            stroke="#198477"
            strokeWidth={2.8}
            dot={false}
            activeDot={{ r: 5, stroke: "#fff", strokeWidth: 3 }}
            connectNulls={false}
            isAnimationActive={false}
          />
          {revealed && (
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#253d36"
              strokeWidth={2.2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function DecisionBrief({
  replay,
  revealed,
  onExplain,
}: {
  replay: Replay;
  revealed: boolean;
  onExplain: () => void;
}) {
  const selectedTime =
    replay.publications.find((item) => item.selected)?.publish_time ??
    replay.decision.as_of;
  const at = new Date(replay.decision.at).getTime();
  const published = new Date(selectedTime).getTime();
  const age = Number.isFinite(at - published)
    ? Math.max(0, (at - published) / 3600000)
    : null;
  const meanForecast = avg(replay.series.map((point) => point.latest));
  return (
    <aside className="decision-brief">
      <div className="brief-top">
        <span className="brief-icon">
          <Wind size={20} />
        </span>
        <span className="small-label">DECISION BRIEF</span>
        <span className="brief-live-dot" />
      </div>
      <h3>
        {revealed
          ? replay.insight.title
          : "The information you had. Nothing from tomorrow."}
      </h3>
      <p>
        {revealed
          ? replay.insight.body
          : "This forecast was available before your decision cutoff. Actual generation stays hidden until you choose to reveal it."}
      </p>
      <div className="brief-stat">
        <span>Average forecast wind</span>
        <strong>
          {number(meanForecast)} <small>MW</small>
        </strong>
      </div>
      <div className="brief-detail">
        <span>Decision locked at</span>
        <strong>{timeLabel(replay.decision.at)} GMT</strong>
      </div>
      <div className="brief-detail">
        <span>Selected publication</span>
        <strong>{timeLabel(selectedTime, true)}</strong>
      </div>
      <div className="brief-detail">
        <span>Age at decision</span>
        <strong>{age == null ? "—" : `${number(age, 1)} hours`}</strong>
      </div>
      <div className="brief-detail">
        <span>Forecast coverage</span>
        <strong>
          {replay.coverage.forecast_hours}/{replay.coverage.expected_hours}{" "}
          hours
        </strong>
      </div>
      <div className="brief-notice">
        <LockKeyhole size={14} />
        <span>{publicationCapText(replay)}</span>
      </div>
      <button onClick={onExplain} className="brief-method-link">
        Inspect the selection rule <ArrowUpRight size={14} />
      </button>
    </aside>
  );
}

function publicationCapText(replay: Replay) {
  return `Forecasts after ${timeLabel(replay.decision.at)} on ${dateLabel(replay.decision.date, true)} are excluded.`;
}

function MetricCard({
  label,
  value,
  unit,
  note,
  kind,
  revealed = true,
  onExplain,
  accent = false,
}: {
  label: string;
  value: string;
  unit: string;
  note: string;
  kind: Explanation;
  revealed?: boolean;
  onExplain: (kind: Explanation) => void;
  accent?: boolean;
}) {
  return (
    <article className={`metric-card ${accent ? "metric-accent" : ""}`}>
      <div className="metric-label">
        {label}
        <button
          aria-label={`Explain ${label.toLowerCase()}`}
          onClick={() => onExplain(kind)}
        >
          <CircleHelp size={14} />
        </button>
      </div>
      <div className="metric-value">
        {revealed ? (
          <>
            {value}
            <span>{unit}</span>
          </>
        ) : (
          <>
            <span className="locked-dash">—</span>
            <LockKeyhole size={16} />
          </>
        )}
      </div>
      <p>{revealed ? note : "Available after revealing actuals"}</p>
    </article>
  );
}

function RevisionComparison({ replay }: { replay: Replay }) {
  const change = replay.metrics.mae_change_pct;
  const improved = change != null && change < 0;
  return (
    <section className="revision-comparison">
      <div className="revision-icon">
        <Layers3 size={19} />
      </div>
      <div className="revision-copy">
        <h3>Did the latest update help?</h3>
        <p>
          {change == null
            ? "Two eligible forecasts with matching actuals are needed for a fair comparison."
            : `${replay.metrics.comparison.n} common hours. Previous MAE ${number(replay.metrics.comparison.previous_mae)} MW → selected MAE ${number(replay.metrics.comparison.latest_mae)} MW.`}
        </p>
      </div>
      {change != null && (
        <div
          className={`revision-result ${improved ? "positive" : change > 0 ? "negative" : ""}`}
        >
          {improved ? <ArrowDownRight size={21} /> : <ArrowUpRight size={21} />}
          <strong>{number(Math.abs(change), 1)}%</strong>
          <span>
            {change < 0
              ? "lower error"
              : change > 0
                ? "higher error"
                : "no change"}
          </span>
        </div>
      )}
      <div className="revision-counts">
        <span>
          <strong>{replay.metrics.improved_hours}</strong> hours improved
        </span>
        <span>
          <strong>{replay.metrics.worsened_hours}</strong> hours worsened
        </span>
      </div>
    </section>
  );
}

function JanuaryReview({
  accuracy,
  loading,
  error,
  cutoff,
  onRetry,
  onReplay,
  onExplain,
}: {
  accuracy: Accuracy | null;
  loading: boolean;
  error: string | null;
  cutoff: string;
  onRetry: () => void;
  onReplay: (date: string) => void;
  onExplain: (kind: Explanation) => void;
}) {
  if (loading) return <ReplaySkeleton />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (!accuracy) return null;
  const { aggregate, days } = accuracy;
  return (
    <div className="january-review">
      <div className="review-context">
        <Info size={16} />
        <p>
          This is a retrospective review. Every day uses only the forecasts
          published by <strong>{cutoff} GMT</strong> on its decision date.
          Recorded actuals are included.
        </p>
      </div>
      <div className="metric-grid">
        <MetricCard
          label="January mean absolute error"
          value={number(aggregate.mae)}
          unit="MW"
          note={`${number(aggregate.n)} matched hourly observations`}
          kind="mae"
          onExplain={onExplain}
        />
        <MetricCard
          label="Root mean square error"
          value={number(aggregate.rmse)}
          unit="MW"
          note="Across all evaluated delivery hours"
          kind="rmse"
          onExplain={onExplain}
        />
        <MetricCard
          label="Forecast bias"
          value={signed(aggregate.bias)}
          unit="MW"
          note="Positive means wind was overforecast"
          kind="bias"
          onExplain={onExplain}
        />
        <article className="metric-card metric-accent">
          <div className="metric-label">
            Latest revision improved accuracy
            <Layers3 size={15} />
          </div>
          <div className="metric-value">
            {aggregate.revision_improved_days}
            <span>/ {aggregate.revision_compared_days} days</span>
          </div>
          <p>Compared on common matched hours</p>
        </article>
      </div>
      <section className="monthly-chart-card">
        <div className="chart-header">
          <div className="chart-title">
            <span className="small-label">DAILY FORECAST ACCURACY</span>
            <h3>The size of the miss.</h3>
            <span className="chart-unit">
              Mean absolute error · MW · common matched hours per day
            </span>
          </div>
          <span className="coverage-pill">
            {number(aggregate.coverage_pct, 1)}% evaluated coverage
          </span>
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-line latest" />
            Selected forecast MAE
          </span>
          <span>
            <i className="legend-line previous" />
            Previous forecast MAE
          </span>
        </div>
        <div
          className="monthly-chart"
          role="img"
          aria-label="Daily mean absolute forecast error throughout January"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={days}
              margin={{ left: 0, right: 15, bottom: 8, top: 15 }}
            >
              <CartesianGrid
                vertical={false}
                stroke="#e9eeeb"
                strokeDasharray="3 4"
              />
              <XAxis
                dataKey="decision_date"
                tickFormatter={(value: string) =>
                  `${new Date(`${value}T12:00:00Z`).getUTCDate()} Jan`
                }
                minTickGap={42}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#7a8781", fontSize: 11 }}
                dy={9}
              />
              <YAxis
                width={48}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#7a8781", fontSize: 11 }}
                tickFormatter={(value: number) => number(value)}
              />
              <Tooltip
                labelFormatter={(value) =>
                  typeof value === "string" ? dateLabel(value) : ""
                }
                formatter={(value, name) => [
                  `${number(typeof value === "number" ? value : null)} MW`,
                  name === "comparison_latest_mae"
                    ? "Selected MAE (paired)"
                    : "Previous MAE (paired)",
                ]}
                contentStyle={{
                  border: "1px solid #dce4df",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line
                dataKey="previous_mae"
                type="monotone"
                stroke="#a6afa9"
                strokeDasharray="5 5"
                strokeWidth={1.8}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                dataKey="comparison_latest_mae"
                type="monotone"
                stroke="#198477"
                strokeWidth={2.5}
                dot={{ r: 2, strokeWidth: 0, fill: "#198477" }}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <h2>Every decision, open to inspection.</h2>
          <span className="subtle">
            Paired MAEs compare identical hours. Select a day to inspect the
            decision.
          </span>
        </div>
      </div>
      <div className="daily-table-wrapper">
        <table className="daily-table">
          <thead>
            <tr>
              <th>Decision date</th>
              <th>Delivery date</th>
              <th>
                Paired selected MAE <span>MW</span>
              </th>
              <th>
                Paired previous MAE <span>MW</span>
              </th>
              <th>Revision impact</th>
              <th>
                Bias <span>MW</span>
              </th>
              <th>Paired hours</th>
              <th>
                <span className="sr-only">Open replay</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {days.map((day) => (
              <tr key={day.decision_date}>
                <td>
                  <button onClick={() => onReplay(day.decision_date)}>
                    {dateLabel(day.decision_date, true)}
                  </button>
                </td>
                <td>{dateLabel(day.delivery_date, true)}</td>
                <td className="numeric">{number(day.comparison_latest_mae)}</td>
                <td className="numeric muted-value">
                  {number(day.previous_mae)}
                </td>
                <td>
                  {day.mae_change_pct == null ? (
                    <span className="muted-value">Unavailable</span>
                  ) : day.mae_change_pct === 0 ? (
                    <span className="impact-tag">No change</span>
                  ) : (
                    <span
                      className={`impact-tag ${day.mae_change_pct < 0 ? "improved" : day.mae_change_pct > 0 ? "worsened" : ""}`}
                    >
                      {day.mae_change_pct < 0 ? (
                        <ArrowDown size={11} />
                      ) : (
                        <ArrowUpRight size={11} />
                      )}
                      {number(Math.abs(day.mae_change_pct), 1)}%{" "}
                      {day.mae_change_pct <= 0 ? "lower" : "higher"}
                    </span>
                  )}
                </td>
                <td className="numeric">{signed(day.bias)}</td>
                <td className="numeric">
                  {day.paired_hours}
                  <span className="muted-value"> / 24</span>
                </td>
                <td>
                  <button
                    className="table-open"
                    aria-label={`Replay ${dateLabel(day.decision_date)}`}
                    onClick={() => onReplay(day.decision_date)}
                  >
                    <ArrowUpRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExplanationDrawer({
  kind,
  replay,
  revealed,
  metadata,
  context,
  accuracy,
  onClose,
}: {
  kind: Explanation;
  replay: Replay | null;
  revealed: boolean;
  metadata: Metadata | null;
  context: View;
  accuracy: Accuracy | null;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const elements = drawerRef.current?.querySelectorAll<HTMLElement>(
          'button, a[href], input, [tabindex="0"]',
        );
        if (!elements?.length) return;
        const first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("keydown", key);
      document.body.style.overflow = originalOverflow;
      previousFocus?.focus();
    };
  }, [onClose]);
  const definitions: Record<
    Explanation,
    { title: string; description: string; formula: string; detail: string }
  > = {
    methodology: {
      title: "The decision, reconstructed.",
      description:
        "A historical replay built around the information available to the buyer.",
      formula: "publishTime ≤ decision cutoff",
      detail:
        "For each delivery hour, choose the most recently published eligible forecast. A publication checkpoint moves that information boundary earlier. The previous forecast is the next most recent distinct eligible publication.",
    },
    mae: {
      title: "Mean absolute error",
      description:
        "The average size of the forecast miss, regardless of direction.",
      formula: "MAE = Σ |forecast − actual| / n",
      detail:
        "A value of 500 MW means the forecast missed recorded wind generation by 500 MW on average across the evaluated hours. Lower is better.",
    },
    rmse: {
      title: "Root mean square error",
      description: "An error measure that gives large misses more weight.",
      formula: "RMSE = √[ Σ (forecast − actual)² / n ]",
      detail:
        "Squaring the errors makes larger misses count more strongly. RMSE is expressed in MW, just like generation. Lower is better.",
    },
    bias: {
      title: "Forecast bias",
      description: "The average direction of the forecast error.",
      formula: "Bias = Σ (forecast − actual) / n",
      detail:
        "A positive bias means wind generation was overforecast; a negative bias means it was underforecast. Positive and negative errors can cancel, so read bias alongside MAE.",
    },
    shortfall: {
      title: "Wind shortfall vs forecast",
      description:
        "The energy associated with hours where wind was lower than forecast.",
      formula: "Σ max(forecast − actual, 0) × 1 hour",
      detail:
        "This is an integrated wind forecast shortfall in MWh. It is not a purchase recommendation, total system imbalance, or a financial loss. Demand, contracted positions, and electricity prices are outside this pilot.",
    },
  };
  const definition = definitions[kind];
  const monthly = context === "review";
  const matchedHours = monthly
    ? accuracy?.aggregate.n
    : replay?.coverage.matched_hours;
  const pairedHours = monthly
    ? accuracy?.days.reduce((total, day) => total + day.paired_hours, 0)
    : replay?.coverage.paired_hours;
  const first =
    revealed && !monthly
      ? replay?.series.find(
          (point) => point.latest != null && point.actual != null,
        )
      : null;
  return (
    <div
      className="drawer-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside
        className="explanation-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        ref={drawerRef}
      >
        <div className="drawer-header">
          <span className="eyebrow">TRANSPARENCY BY DESIGN</span>
          <button
            className="icon-button"
            onClick={onClose}
            ref={closeRef}
            aria-label="Close explanation"
          >
            <X size={20} />
          </button>
        </div>
        <div className="drawer-content">
          <div className="drawer-symbol">
            {kind === "methodology" ? (
              <ShieldCheck size={26} />
            ) : (
              <CircleHelp size={26} />
            )}
          </div>
          <h2 id="drawer-title">{definition.title}</h2>
          <p className="drawer-intro">{definition.description}</p>
          <div className="formula">{definition.formula}</div>
          <p>{definition.detail}</p>
          {monthly && accuracy && (
            <p>
              January 2026 review: the headline metrics pool{" "}
              {number(accuracy.aggregate.n)} complete hourly observations across{" "}
              {accuracy.days.length} decision dates, using the daily{" "}
              {accuracy.cutoff} GMT cutoff.
            </p>
          )}
          {first && (
            <section className="worked-example">
              <h3>An hour from this decision</h3>
              <p>
                {dateLabel(first.start_time)} · {hourLabel(first.start_time)}
              </p>
              <div>
                <span>Selected forecast</span>
                <strong>{number(first.latest, 1)} MW</strong>
              </div>
              <div>
                <span>Recorded actual</span>
                <strong>{number(first.actual, 1)} MW</strong>
              </div>
              <div className="example-total">
                <span>Forecast − actual</span>
                <strong>{signed(first.latest! - first.actual!, 1)} MW</strong>
              </div>
              <small>
                Forecast published {timeLabel(first.latest_publish_time, true)}{" "}
                GMT.
              </small>
            </section>
          )}
          <DrawerSection title="One fair comparison">
            <p>
              Headline accuracy uses every complete selected forecast and actual
              match. Revision comparisons use only the common hours where both
              forecasts and actuals exist. Missing values remain missing; they
              are never counted as zero.
            </p>
            {matchedHours != null && (
              <div className="drawer-counts">
                <span>
                  <strong>{number(matchedHours)}</strong>{" "}
                  {monthly ? "January " : ""}selected + actual hours
                </span>
                <span>
                  <strong>{number(pairedHours)}</strong>{" "}
                  {monthly ? "January " : ""}paired comparison hours
                </span>
              </div>
            )}
          </DrawerSection>
          <DrawerSection title="Time alignment">
            <p>
              {replay?.provenance.alignment ??
                "Actual wind generation is reported every half hour. Both half-hours must exist before averaging their MW values into a complete hourly actual to match the hourly forecast."}
            </p>
            <p>
              All timestamps are interpreted in London time. January 2026 is
              GMT. Decision dates run from 1–31 January; the final delivery day
              is 1 February.
            </p>
          </DrawerSection>
          <DrawerSection title="The cutoff is a modelling choice">
            <p>
              The selected time represents when this buyer makes their decision.
              The default 09:00 is an illustrative cutoff, not a claim about a
              universal UK market deadline. Change it to inspect the information
              available at another time.
            </p>
          </DrawerSection>
          <DrawerSection title="Source and provenance">
            <p>
              National wind generation only, from Elexon Insights. FUELHH
              provides recorded generation filtered to WIND; WINDFOR provides
              forecasts and their publication times.
            </p>
            <a
              className="source-link"
              href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream"
              target="_blank"
              rel="noreferrer"
            >
              FUELHH · recorded generation <ExternalLink size={13} />
            </a>
            <a
              className="source-link"
              href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream"
              target="_blank"
              rel="noreferrer"
            >
              WINDFOR · published forecasts <ExternalLink size={13} />
            </a>
            {(replay?.provenance.retrieved_at ?? metadata?.retrieved_at) && (
              <p className="retrieval-note">
                Retrieved{" "}
                {timeLabel(
                  replay?.provenance.retrieved_at ?? metadata?.retrieved_at,
                  true,
                )}{" "}
                GMT
              </p>
            )}
            <p>{replay?.provenance.availability_note}</p>
          </DrawerSection>
        </div>
        <div className="drawer-footer">
          <ShieldCheck size={15} />
          Every result has a timestamp and a denominator.
        </div>
      </aside>
    </div>
  );
}

function DrawerSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="drawer-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}
function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <div className="error-icon">
        <Info size={23} />
      </div>
      <h3>This decision could not be loaded.</h3>
      <p>{message}</p>
      <button className="primary-button" onClick={onRetry}>
        <RefreshCw size={15} />
        Try again
      </button>
    </div>
  );
}
function ReplaySkeleton() {
  return (
    <div
      className="loading-state"
      role="status"
      aria-label="Loading historical wind data"
    >
      <div className="skeleton skeleton-chart">
        <div className="skeleton-line" />
        <div className="skeleton-wave" />
        <span>Reconstructing the decision…</span>
      </div>
      <div className="skeleton skeleton-brief">
        <Wind size={24} />
        <div className="skeleton-line" />
        <div className="skeleton-line short" />
        <div className="skeleton-line" />
      </div>
      <span className="sr-only">Loading historical wind data</span>
    </div>
  );
}

export default App;

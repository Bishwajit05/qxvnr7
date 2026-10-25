export type Metric = {
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  positive_error_mwh: number | null;
  net_error_mwh: number | null;
  n: number;
};
export type Insight = { title: string; body: string; tone: string };
export type Point = {
  start_time: string;
  hour: string | number;
  latest: number | null;
  previous: number | null;
  actual: number | null;
  latest_publish_time: string | null;
  previous_publish_time: string | null;
  error: number | null;
};
export type Replay = {
  decision: {
    date: string;
    cutoff: string;
    at: string;
    delivery_date: string;
    timezone: string;
    as_of: string;
  };
  coverage: {
    expected_hours: number;
    forecast_hours: number;
    actual_hours: number;
    matched_hours: number;
    paired_hours: number;
  };
  publications: {
    publish_time: string;
    label: string;
    hours_covered: number;
    selected: boolean;
  }[];
  series: Point[];
  metrics: {
    comparison: {
      latest_mae: number | null;
      previous_mae: number | null;
      n: number;
    };
    latest: Metric;
    previous: Metric;
    mae_change_pct: number | null;
    improved_hours: number;
    worsened_hours: number;
  };
  insight: Insight;
  provenance: {
    source: string;
    description: string;
    retrieved_at: string;
    alignment: string;
    availability_note: string;
  };
};
export type Accuracy = {
  cutoff: string;
  days: {
    decision_date: string;
    delivery_date: string;
    mae: number | null;
    rmse: number | null;
    bias: number | null;
    positive_error_mwh: number | null;
    matched_hours: number;
    paired_hours: number;
    previous_mae: number | null;
    comparison_latest_mae: number | null;
    mae_change_pct: number | null;
  }[];
  aggregate: Metric & {
    total_expected_hours: number;
    coverage_pct: number;
    revision_improved_days: number;
    revision_compared_days: number;
  };
  insights: Insight[];
};
export type Metadata = {
  decision_dates: string[];
  min_date: string;
  max_date: string;
  default_date: string;
  default_cutoff: string;
  coverage: unknown;
  source_urls: Record<string, string> | string[];
  retrieved_at: string;
  notes: string[];
  case_studies?: {
    date?: string;
    decision_date?: string;
    title?: string;
    label?: string;
    description?: string;
  }[];
};
export type DataStatus = {
  mode: "live_api" | "cached_api" | "snapshot_fallback";
  retrieved_at: string;
  last_refresh_attempt: string | null;
  cache_expires_at: string | null;
  stale: boolean;
  message: string;
  refresh_error: string | null;
  source_urls: Record<string, string> | string[];
};
export type Dashboard = {
  replay: Replay;
  accuracy: Accuracy;
  metadata: Metadata;
  data_status: DataStatus;
};

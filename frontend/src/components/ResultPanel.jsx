import SqlBlock from "./SqlBlock.jsx";
import ResultTable from "./ResultTable.jsx";
import AttemptsBadge from "./AttemptsBadge.jsx";
import styles from "./ResultPanel.module.css";

const LOADING_STAGES = [
  "Reading the schema…",
  "Drafting SQL…",
  "Checking it's read-only…",
  "Running it against the database…",
];

function LoadingState({ stage }) {
  return (
    <div className={styles.loading}>
      <span className={styles.spinner} aria-hidden="true" />
      <span className={styles.loadingLabel}>{LOADING_STAGES[stage % LOADING_STAGES.length]}</span>
    </div>
  );
}

function SuccessState({ data }) {
  return (
    <div className={styles.panel}>
      <div className={styles.panelHead}>
        <h3 className={styles.panelTitle}>Result</h3>
        <AttemptsBadge attempts={data.attempts} />
      </div>
      <SqlBlock sql={data.sql} />
      <ResultTable rows={data.rows} />
    </div>
  );
}

function RejectedState({ data }) {
  return (
    <div className={`${styles.panel} ${styles.dangerPanel}`}>
      <div className={styles.panelHead}>
        <h3 className={styles.panelTitle}>Blocked before it ran</h3>
      </div>
      <p className={styles.message}>
        The generated query wasn't a plain <code>SELECT</code>, so the safety layer rejected it before it ever
        reached the database.
      </p>
      <SqlBlock sql={data.sql} tone="danger" label="Rejected SQL" />
    </div>
  );
}

function ExhaustedState({ data }) {
  return (
    <div className={`${styles.panel} ${styles.dangerPanel}`}>
      <div className={styles.panelHead}>
        <h3 className={styles.panelTitle}>Couldn't land it in 3 tries</h3>
      </div>
      <p className={styles.message}>
        Each attempt's database error was fed back to the model, but it didn't converge in time. Here's the last
        thing it tried, and why that failed.
      </p>
      <SqlBlock sql={data.last_sql_tried} tone="danger" label="Last SQL tried" />
      <p className={styles.errorText}>{data.last_error}</p>
    </div>
  );
}

const ERROR_COPY = {
  session: {
    title: "Your demo session expired",
    body: "Demo connections close automatically after a while of inactivity. Reconnect your database to keep going.",
  },
  infra: {
    title: "The service hit a snag",
    body: "Something upstream — the model or the database connection — failed to respond. Worth a retry.",
  },
  network: {
    title: "Can't reach the API",
    body: "Make sure the backend is running and VITE_API_BASE_URL points at it.",
  },
  rate_limited: {
    title: "Slow down a little",
    body: "There's a request limit in place to keep things fair for everyone — try again in a moment.",
  },
  bad_request: {
    title: "That didn't go through",
    body: "The request was malformed or rejected — check the details below.",
  },
  unknown: {
    title: "Something went wrong",
    body: "An unexpected error occurred.",
  },
};

function ApiErrorState({ kind, message }) {
  const copy = ERROR_COPY[kind] ?? ERROR_COPY.unknown;
  return (
    <div className={`${styles.panel} ${styles.dangerPanel}`}>
      <div className={styles.panelHead}>
        <h3 className={styles.panelTitle}>{copy.title}</h3>
      </div>
      <p className={styles.message}>{copy.body}</p>
      {message && <p className={styles.errorText}>{message}</p>}
    </div>
  );
}

export default function ResultPanel({ state }) {
  if (!state) return null;

  switch (state.status) {
    case "loading":
      return <LoadingState stage={state.stage ?? 0} />;
    case "success":
      return <SuccessState data={state.data} />;
    case "rejected":
      return <RejectedState data={state.data} />;
    case "exhausted":
      return <ExhaustedState data={state.data} />;
    case "error":
      return <ApiErrorState kind={state.kind} message={state.message} />;
    default:
      return null;
  }
}

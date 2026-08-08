import styles from "./HowItWorks.module.css";

const STEPS = [
  { side: "human", title: "Your question", body: "Plain English. No SQL required." },
  { side: "data", title: "Schema introspection", body: "Reads the real tables and columns, cached in Redis." },
  { side: "human", title: "Draft SQL", body: "gpt-4o-mini writes a SELECT, temperature 0." },
  { side: "data", title: "Safety check", body: "Anything that isn't a bare SELECT is rejected in code." },
  { side: "data", title: "Execute", body: "Runs for real, inside a read-only transaction." },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className={styles.section}>
      <div className="container">
        <div className={styles.heading}>
          <p className={styles.eyebrow}>The mechanism</p>
          <h2 className={styles.title}>Five steps, one loop that catches itself</h2>
          <p className={styles.body}>
            If step four fails, the exact database error goes back to the model and it tries again — up to
            three times — before giving up honestly instead of guessing.
          </p>
        </div>

        <ol className={styles.steps}>
          {STEPS.map((step, i) => (
            <li key={step.title} className={styles.step}>
              <div className={`${styles.marker} ${styles[step.side]}`}>{i + 1}</div>
              <div>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepBody}>{step.body}</p>
              </div>
            </li>
          ))}
          <li className={`${styles.step} ${styles.loopStep}`}>
            <div className={`${styles.marker} ${styles.human}`} aria-hidden="true">
              ↺
            </div>
            <div>
              <h3 className={styles.stepTitle}>Self-correction, up to 3×</h3>
              <p className={styles.stepBody}>
                A failed query's real error feeds back into a new prompt — then it re-enters at the safety
                check, not straight into execution.
              </p>
            </div>
          </li>
        </ol>
      </div>
    </section>
  );
}

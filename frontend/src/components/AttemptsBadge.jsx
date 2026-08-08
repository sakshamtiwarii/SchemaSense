import styles from "./AttemptsBadge.module.css";

export default function AttemptsBadge({ attempts }) {
  if (attempts <= 1) {
    return <span className={`${styles.badge} ${styles.clean}`}>Ran clean, first try</span>;
  }

  return (
    <span className={`${styles.badge} ${styles.corrected}`}>
      Self-corrected · {attempts - 1} {attempts - 1 === 1 ? "retry" : "retries"}
    </span>
  );
}

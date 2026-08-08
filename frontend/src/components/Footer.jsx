import styles from "./Footer.module.css";

const STACK = ["FastAPI", "LangChain", "PostgreSQL", "Redis", "OpenAI gpt-4o-mini", "Docker"];

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`${styles.inner} container`}>
        <p className={styles.note}>
          Every query runs read-only, in a transaction Postgres itself won't let write — regardless of what the
          model generates.
        </p>
        <ul className={styles.stack}>
          {STACK.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </footer>
  );
}

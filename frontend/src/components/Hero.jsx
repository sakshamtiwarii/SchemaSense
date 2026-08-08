import styles from "./Hero.module.css";

export default function Hero({ children }) {
  return (
    <section id="top" className={styles.hero}>
      <div className={styles.glow} aria-hidden="true" />
      <div className={`${styles.inner} container`}>
        <p className={styles.eyebrow}>Natural language in — real, executed SQL out</p>
        <h1 className={styles.headline}>
          Ask your database <em>anything.</em>
        </h1>
        <p className={styles.subhead}>
          SchemaSense grounds your question in the real schema, runs the query for real, and fixes its own
          mistakes when the first attempt is wrong — instead of guessing and hoping.
        </p>
        <div className={styles.consoleSlot}>{children}</div>
      </div>
    </section>
  );
}

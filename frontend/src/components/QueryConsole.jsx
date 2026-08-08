import { useState } from "react";
import styles from "./QueryConsole.module.css";

const SAMPLE_QUESTIONS = [
  "Top 3 products by revenue",
  "Orders placed in the last 30 days",
  "Average order revenue by category",
];

export default function QueryConsole({ onSubmit, isLoading, contextLabel }) {
  const [question, setQuestion] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  }

  return (
    <form className={styles.console} onSubmit={handleSubmit}>
      <div className={styles.contextRow}>
        <span className={styles.contextDot} aria-hidden="true" />
        <span className={styles.contextLabel}>{contextLabel}</span>
      </div>

      <div className={styles.inputRow}>
        <textarea
          className={styles.input}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask it something — “what were our top 3 products by revenue?”"
          rows={2}
          disabled={isLoading}
          aria-label="Ask your database a question"
        />
        <button type="submit" className={styles.submit} disabled={isLoading || !question.trim()}>
          {isLoading ? "Running…" : "Run"}
        </button>
      </div>

      <div className={styles.chips}>
        {SAMPLE_QUESTIONS.map((sample) => (
          <button
            type="button"
            key={sample}
            className={styles.chip}
            onClick={() => setQuestion(sample)}
            disabled={isLoading}
          >
            {sample}
          </button>
        ))}
      </div>
    </form>
  );
}

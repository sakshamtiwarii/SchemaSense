import { useState } from "react";
import styles from "./QueryConsole.module.css";

export default function QueryConsole({ onSubmit, isLoading, contextLabel, sampleQuestions = [] }) {
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

  const placeholder = sampleQuestions[0]
    ? `Ask it something — “${sampleQuestions[0].toLowerCase()}?”`
    : "Ask it something about the tables on the right";

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
          placeholder={placeholder}
          rows={2}
          disabled={isLoading}
          aria-label="Ask your database a question"
        />
        <button type="submit" className={styles.submit} disabled={isLoading || !question.trim()}>
          {isLoading ? "Running…" : "Run"}
        </button>
      </div>

      {sampleQuestions.length > 0 && (
        <div className={styles.chips}>
          {sampleQuestions.map((sample) => (
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
      )}
    </form>
  );
}

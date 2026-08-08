import { useState } from "react";
import styles from "./LLMKeyPanel.module.css";

const PROVIDERS = [
  { value: "groq", label: "Groq", placeholder: "gsk_...", defaultModel: "llama-3.3-70b-versatile" },
  { value: "openai", label: "OpenAI", placeholder: "sk-...", defaultModel: "gpt-4o-mini" },
];

function providerMeta(value) {
  return PROVIDERS.find((p) => p.value === value) ?? PROVIDERS[0];
}

export default function LLMKeyPanel({ override, onSave, onClear }) {
  const [provider, setProvider] = useState("groq");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [reveal, setReveal] = useState(false);

  const meta = providerMeta(provider);

  function handleSubmit(event) {
    event.preventDefault();
    if (!apiKey.trim()) return;
    onSave({ provider, apiKey: apiKey.trim(), model: model.trim() || null });
  }

  if (override) {
    const activeMeta = providerMeta(override.provider);
    return (
      <div className={styles.panel}>
        <div className={styles.connectedHead}>
          <span className={styles.pulse} aria-hidden="true" />
          <h3 className={styles.title}>Using your own {activeMeta.label} key</h3>
        </div>
        <p className={styles.body}>
          <code className={styles.modelTag}>{override.model || activeMeta.defaultModel}</code> answers every
          question from here on, billed to your account instead of the server's.
        </p>
        <button type="button" className={styles.disconnect} onClick={onClear}>
          Switch back to the default
        </button>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      <h3 className={styles.title}>Bring your own LLM key</h3>
      <p className={styles.body}>
        Using the server's key by default. Paste your own Groq key to draft and fix SQL with your account
        instead — it's attached only to your requests and never stored.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.providerRow} role="radiogroup" aria-label="LLM provider">
          {PROVIDERS.map((p) => (
            <button
              type="button"
              key={p.value}
              role="radio"
              aria-checked={provider === p.value}
              className={`${styles.providerChip} ${provider === p.value ? styles.providerChipActive : ""}`}
              onClick={() => setProvider(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className={styles.inputWrap}>
          <input
            type={reveal ? "text" : "password"}
            className={styles.input}
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={meta.placeholder}
            autoComplete="off"
            spellCheck={false}
          />
          <button
            type="button"
            className={styles.reveal}
            onClick={() => setReveal((r) => !r)}
            aria-label={reveal ? "Hide API key" : "Show API key"}
          >
            {reveal ? "Hide" : "Show"}
          </button>
        </div>

        <input
          type="text"
          className={styles.modelInput}
          value={model}
          onChange={(event) => setModel(event.target.value)}
          placeholder={`Model (optional) — defaults to ${meta.defaultModel}`}
          autoComplete="off"
          spellCheck={false}
        />

        <button type="submit" className={styles.save} disabled={!apiKey.trim()}>
          Use this key
        </button>
      </form>

      <p className={styles.fineprint}>Kept in memory for this browser tab only — gone on refresh, never sent anywhere but your own requests.</p>
    </div>
  );
}

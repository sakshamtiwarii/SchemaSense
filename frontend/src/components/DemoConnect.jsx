import { useState } from "react";
import styles from "./DemoConnect.module.css";

export default function DemoConnect({ session, onConnect, onDisconnect, isConnecting, isDisconnecting, error }) {
  const [connectionString, setConnectionString] = useState("");
  const [reveal, setReveal] = useState(false);

  function handleSubmit(event) {
    event.preventDefault();
    if (!connectionString.trim() || isConnecting) return;
    onConnect(connectionString.trim());
  }

  if (session) {
    return (
      <div className={styles.panel}>
        <div className={styles.connectedHead}>
          <span className={styles.pulse} aria-hidden="true" />
          <h3 className={styles.title}>Connected to your database</h3>
        </div>
        <p className={styles.body}>
          Queries above now run against it. Nothing about this connection was ever written to disk — it lives
          only in the API's memory for this session.
        </p>
        <button type="button" className={styles.disconnect} onClick={onDisconnect} disabled={isDisconnecting}>
          {isDisconnecting ? "Disconnecting…" : "Disconnect"}
        </button>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      <h3 className={styles.title}>Bring your own database</h3>
      <p className={styles.body}>
        Paste a Postgres connection string — ideally for a read-only user — and try the same pipeline against
        your own schema. Every query still runs inside a read-only transaction regardless, so it can't write
        even if that account technically could.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.inputWrap}>
          <input
            type={reveal ? "text" : "password"}
            className={styles.input}
            value={connectionString}
            onChange={(event) => setConnectionString(event.target.value)}
            placeholder="postgresql://user:pass@host:5432/dbname"
            autoComplete="off"
            spellCheck={false}
            disabled={isConnecting}
          />
          <button
            type="button"
            className={styles.reveal}
            onClick={() => setReveal((r) => !r)}
            aria-label={reveal ? "Hide connection string" : "Show connection string"}
          >
            {reveal ? "Hide" : "Show"}
          </button>
        </div>
        <button type="submit" className={styles.connect} disabled={isConnecting || !connectionString.trim()}>
          {isConnecting ? "Connecting…" : "Connect"}
        </button>
      </form>

      {error && <p className={styles.error}>{error}</p>}

      <p className={styles.fineprint}>
        Connections to private/internal networks are blocked. Sessions expire automatically after a period of
        inactivity.
      </p>
    </div>
  );
}

import ThemeToggle from "./ThemeToggle.jsx";
import styles from "./NavBar.module.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function NavBar({ theme, onToggleTheme }) {
  return (
    <header className={styles.bar}>
      <div className={`${styles.inner} container`}>
        <a href="#top" className={styles.wordmark}>
          <svg width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="8" fill="var(--ink)" />
            <g fill="none" stroke="var(--paper)" strokeWidth="1.6">
              <rect x="7" y="7" width="18" height="18" rx="2" />
              <line x1="7" y1="14.3" x2="25" y2="14.3" />
              <line x1="7" y1="19.7" x2="25" y2="19.7" />
              <line x1="14.3" y1="7" x2="14.3" y2="25" />
            </g>
            <rect x="14.3" y="14.3" width="5.4" height="5.4" fill="var(--accent)" />
          </svg>
          SchemaSense
        </a>

        <nav className={styles.links}>
          <a href="#how-it-works">How it works</a>
          <a href="#workspace">Workspace</a>
          <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
            API docs ↗
          </a>
        </nav>

        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}

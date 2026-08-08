import styles from "./ThemeToggle.module.css";

export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === "dark";
  const label = theme === null ? "Switch theme (following system)" : isDark ? "Switch to light" : "Switch to dark";

  return (
    <button type="button" className={styles.toggle} onClick={onToggle} aria-label={label} title={label}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        {isDark ? (
          <path
            d="M13.5 9.6A5.6 5.6 0 0 1 6.4 2.5a5.7 5.7 0 1 0 7.1 7.1Z"
            fill="currentColor"
          />
        ) : (
          <>
            <circle cx="8" cy="8" r="3" fill="currentColor" />
            <g stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
              <line x1="8" y1="0.8" x2="8" y2="2.4" />
              <line x1="8" y1="13.6" x2="8" y2="15.2" />
              <line x1="0.8" y1="8" x2="2.4" y2="8" />
              <line x1="13.6" y1="8" x2="15.2" y2="8" />
              <line x1="2.7" y1="2.7" x2="3.8" y2="3.8" />
              <line x1="12.2" y1="12.2" x2="13.3" y2="13.3" />
              <line x1="2.7" y1="13.3" x2="3.8" y2="12.2" />
              <line x1="12.2" y1="3.8" x2="13.3" y2="2.7" />
            </g>
          </>
        )}
      </svg>
    </button>
  );
}

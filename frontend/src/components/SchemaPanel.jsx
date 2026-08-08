import { parseSchema } from "../lib/parseSchema.js";
import styles from "./SchemaPanel.module.css";

export default function SchemaPanel({ schemaContext, isLoading, error, onRefresh, sourceLabel }) {
  const tables = parseSchema(schemaContext);

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <div>
          <h3 className={styles.title}>What it can see</h3>
          <p className={styles.subtitle}>{sourceLabel}</p>
        </div>
        <button type="button" className={styles.refresh} onClick={onRefresh} disabled={isLoading}>
          {isLoading ? "Reading…" : "Refresh"}
        </button>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {!error && tables.length === 0 && !isLoading && (
        <p className={styles.empty}>No tables found in the public schema.</p>
      )}

      <div className={styles.grid}>
        {tables.map((table) => (
          <div key={table.name} className={styles.card}>
            <p className={styles.tableName}>{table.name}</p>
            <ul className={styles.columns}>
              {table.columns.map((col) => (
                <li key={col.name}>
                  <span className={styles.colName}>{col.name}</span>
                  <span className={styles.colType}>{col.type}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

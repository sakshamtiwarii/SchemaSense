import styles from "./ResultTable.module.css";

function formatCell(value) {
  if (value === null || value === undefined) return <span className={styles.nullValue}>null</span>;
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

export default function ResultTable({ rows }) {
  if (!rows || rows.length === 0) {
    return <p className={styles.empty}>The query ran fine — it just didn't match any rows.</p>;
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className={styles.card}>
      <div className={styles.scrollArea}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col}>{formatCell(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={styles.count}>
        {rows.length} row{rows.length === 1 ? "" : "s"}
      </p>
    </div>
  );
}

import styles from "./SqlBlock.module.css";

const KEYWORDS = [
  "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON",
  "GROUP BY", "ORDER BY", "LIMIT", "AS", "AND", "OR", "NOT", "IN", "COUNT",
  "SUM", "AVG", "MIN", "MAX", "DISTINCT", "CURRENT_DATE", "INTERVAL",
  "BETWEEN", "IS", "NULL", "DESC", "ASC", "HAVING",
];

const KEYWORD_PATTERN = new RegExp(`\\b(${KEYWORDS.join("|")})\\b`, "gi");

function tokenize(sql) {
  const tokens = [];
  let lastIndex = 0;
  for (const match of sql.matchAll(KEYWORD_PATTERN)) {
    if (match.index > lastIndex) {
      tokens.push({ text: sql.slice(lastIndex, match.index), kind: "plain" });
    }
    tokens.push({ text: match[0], kind: "keyword" });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < sql.length) {
    tokens.push({ text: sql.slice(lastIndex), kind: "plain" });
  }
  return tokens;
}

export default function SqlBlock({ sql, tone = "data", label = "Generated SQL" }) {
  const tokens = tokenize(sql);

  return (
    <div className={`${styles.block} ${styles[tone]}`}>
      <div className={styles.head}>
        <span className={styles.label}>{label}</span>
      </div>
      <pre className={styles.pre}>
        <code>
          {tokens.map((token, i) =>
            token.kind === "keyword" ? (
              <span key={i} className={styles.keyword}>
                {token.text}
              </span>
            ) : (
              <span key={i}>{token.text}</span>
            ),
          )}
        </code>
      </pre>
    </div>
  );
}

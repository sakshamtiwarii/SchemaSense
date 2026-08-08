// Turns a parsed schema (see parseSchema.js) into a handful of plausible
// example questions, so the console's quick-start chips actually match
// whatever database is currently connected instead of always showing
// "top 3 products by revenue" for a schema that has no products table.
//
// This is a naming-convention heuristic, not a semantic understanding of
// the schema — it only has table/column names and types to work with (the
// backend's introspection doesn't expose foreign keys), so it favors
// always-valid questions over clever ones it can't verify.

const NUMERIC_TYPES = ["integer", "numeric", "real", "double precision", "bigint", "smallint", "decimal", "money", "float"];
const DATE_TYPES = ["date", "timestamp"];
const LABEL_TYPES = ["text", "char"];
const AMOUNT_HINTS = ["revenue", "price", "amount", "total", "cost", "value", "salary", "spend", "sales", "balance"];

function isIdColumn(name) {
  return name === "id" || name.endsWith("_id");
}

function isForeignKeyColumn(name) {
  return name !== "id" && name.endsWith("_id");
}

function isNumeric(col) {
  return !isIdColumn(col.name) && NUMERIC_TYPES.some((t) => col.type.toLowerCase().includes(t));
}

function isDate(col) {
  return DATE_TYPES.some((t) => col.type.toLowerCase().includes(t));
}

function isAmountLike(col) {
  return isNumeric(col) && AMOUNT_HINTS.some((hint) => col.name.toLowerCase().includes(hint));
}

function isLabelLike(col) {
  return LABEL_TYPES.some((t) => col.type.toLowerCase().includes(t));
}

function humanize(identifier) {
  return identifier.replace(/_/g, " ");
}

// "product_id" -> guesses the related table is named "products" (or
// "productes"/"product", for irregular pluralization) — the standard
// Rails/Django/Postgres foreign-key naming convention.
function guessRelatedTable(fkColumnName, allTables) {
  const base = fkColumnName.slice(0, -3);
  const candidates = new Set([`${base}s`, `${base}es`, base]);
  return allTables.find((t) => candidates.has(t.name)) ?? null;
}

function findRelatedLabelTable(table, allTables) {
  const fkColumns = table.columns.filter((c) => isForeignKeyColumn(c.name));
  for (const fk of fkColumns) {
    const related = guessRelatedTable(fk.name, allTables);
    if (related && related.columns.some(isLabelLike)) return related;
  }
  return null;
}

function bestQuestionForTable(table, allTables) {
  const cols = table.columns;
  const amountCol = cols.find(isAmountLike);
  const labelCol = cols.find(isLabelLike);
  const dateCol = cols.find(isDate);
  const numCol = cols.find(isNumeric);

  // A number that looks like a foreign key to a table with a name/label
  // column — e.g. orders.revenue + orders.product_id -> products.product_name
  // — reconstructs cross-table questions without ever joining anything itself.
  if (amountCol) {
    const related = findRelatedLabelTable(table, allTables);
    if (related) {
      return { tier: 0, text: `Top 3 ${humanize(related.name)} by ${humanize(amountCol.name)}` };
    }
  }
  if (amountCol && labelCol) {
    return { tier: 1, text: `Top 3 ${humanize(table.name)} by ${humanize(amountCol.name)}` };
  }
  if (dateCol) {
    return { tier: 2, text: `How many ${humanize(table.name)} were added in the last 30 days?` };
  }
  if (amountCol) {
    return { tier: 3, text: `What's the total ${humanize(amountCol.name)} across all ${humanize(table.name)}?` };
  }
  if (numCol) {
    return { tier: 4, text: `What's the average ${humanize(numCol.name)} in ${humanize(table.name)}?` };
  }
  return { tier: 5, text: `How many ${humanize(table.name)} are there?` };
}

export function generateSampleQuestions(tables, { max = 3 } = {}) {
  if (!tables || tables.length === 0) return [];

  const seen = new Set();
  const picks = [];
  for (const table of tables) {
    const candidate = bestQuestionForTable(table, tables);
    const key = candidate.text.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      picks.push(candidate);
    }
  }

  return picks
    .sort((a, b) => a.tier - b.tier)
    .slice(0, max)
    .map((c) => c.text);
}

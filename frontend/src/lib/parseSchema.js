// Parses the "Table x: col (type), col2 (type)" text the backend's
// introspection.get_schema_context() produces into structured data for
// rendering. See backend/app/core/introspection.py.
export function parseSchema(schemaContext) {
  if (!schemaContext) return [];

  return schemaContext
    .split("\n")
    .map((line) => line.match(/^Table (\S+):\s*(.*)$/))
    .filter(Boolean)
    .map(([, name, columnsPart]) => ({
      name,
      columns: columnsPart
        .split(/,\s*(?![^()]*\))/)
        .map((col) => col.match(/^(\S+)\s*\((.+)\)$/))
        .filter(Boolean)
        .map(([, colName, colType]) => ({ name: colName, type: colType })),
    }));
}

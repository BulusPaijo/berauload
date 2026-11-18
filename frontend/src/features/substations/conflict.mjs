/** Compare only locally edited cells with the server revision; never coerce blank to zero. */
export function conflictCells(drafts, id, serverValues, parameters) {
  const byCode = new Map(parameters.map(p => [p.code, p]));
  return Object.entries(drafts).filter(([key]) => key.startsWith(`${id}|`)).flatMap(([key, mine]) => {
    const [, code, part] = key.split('|');
    const line = Number(part);
    const param = byCode.get(code);
    const item = serverValues.find(v => v.param_id === param?.id && v.line_no === line);
    const server = item?.flag ? `@${item.flag}` : item?.value == null ? '' : String(item.value);
    const normalize = v => v === '' ? '' : v.startsWith('@') ? v : Number.isFinite(Number(v.replace(',', '.'))) ? Number(v.replace(',', '.')) : v;
    if (normalize(String(mine)) === normalize(server)) return [];
    return [{ key, code, label: param?.name || code, line, mine, server }];
  });
}

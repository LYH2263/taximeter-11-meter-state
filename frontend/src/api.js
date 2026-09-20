async function errText(r) {
  const t = await r.text()
  try { return JSON.parse(t).detail || t } catch { return t }
}
export async function getJSON(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(await errText(r))
  return r.json()
}
export async function postJSON(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await errText(r))
  return r.json()
}

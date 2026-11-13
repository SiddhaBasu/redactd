// Row layout for the virtualised document viewer. The document is shown in a monospace font and soft-wrapped into
// fixed-height rows at a known column count, so every row has the same height (cheap virtualisation of a 1 MB
// file) and every character keeps an exact [start, end) offset (findings never drift).
export interface Rows { start: Int32Array; end: Int32Array; count: number; cols: number }

const isWide = (code: number) =>
  (code >= 0x1100 && code <= 0x115f) || (code >= 0x2e80 && code <= 0xa4cf) || (code >= 0xac00 && code <= 0xd7a3) ||
  (code >= 0xf900 && code <= 0xfaff) || (code >= 0xfe30 && code <= 0xfe4f) || (code >= 0xff00 && code <= 0xff60) || (code >= 0xffe0 && code <= 0xffe6);

/** Split `text` into rows of at most `cols` columns, breaking after spaces where possible. Rows cover every
 *  character except the newline that ends a line; a row never splits a surrogate pair. */
export function wrapRows(text: string, cols: number): Rows {
  cols = Math.max(8, Math.floor(cols));
  let cap = Math.max(16, Math.ceil(text.length / 40)), n = 0;
  let start = new Int32Array(cap), end = new Int32Array(cap);
  const push = (a: number, b: number) => {
    if (n === cap) { cap *= 2; const s2 = new Int32Array(cap), e2 = new Int32Array(cap); s2.set(start); e2.set(end); start = s2; end = e2; }
    start[n] = a; end[n] = b; n++;
  };
  let ls = 0;
  const L = text.length;
  while (ls <= L) {
    let le = text.indexOf("\n", ls);
    if (le < 0) le = L;
    const lineEnd = le > ls && text.charCodeAt(le - 1) === 13 ? le - 1 : le;   // hide \r of \r\n
    if (lineEnd - ls <= cols && !/[^\x00-ჿ]/.test(text.slice(ls, lineEnd))) push(ls, lineEnd);
    else {
      let pos = ls;
      for (;;) {
        // advance up to `cols` columns
        let i = pos, w = 0, lastSpace = -1;
        while (i < lineEnd) {
          const c = text.charCodeAt(i);
          const pair = c >= 0xd800 && c <= 0xdbff && i + 1 < lineEnd;
          const cw = pair || isWide(c) ? 2 : 1;
          if (w + cw > cols) break;
          w += cw; i += pair ? 2 : 1;
          if (c === 32 || c === 9) lastSpace = i;
        }
        if (i >= lineEnd) { push(pos, lineEnd); break; }
        const cut = lastSpace > pos ? lastSpace : Math.max(i, pos + 1);
        push(pos, cut); pos = cut;
      }
    }
    if (le >= L) break;
    ls = le + 1;
  }
  return { start: start.subarray(0, n), end: end.subarray(0, n), count: n, cols };
}

/** Index of the row containing `offset` (the last row whose start <= offset). */
export function rowAt(rows: Rows, offset: number): number {
  let lo = 0, hi = rows.count - 1;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (rows.start[mid] <= offset) lo = mid; else hi = mid - 1; }
  return lo;
}

/** Index of the first span (sorted, non-overlapping) whose end is after `offset`. */
export function firstSpanAfter(spans: { start: number; end: number }[], offset: number): number {
  let lo = 0, hi = spans.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (spans[mid].end <= offset) lo = mid + 1; else hi = mid; }
  return lo;
}

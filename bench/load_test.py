"""C3: load test against a running API.  Writes bench/out/load.md.

    python bench/load_test.py --url http://127.0.0.1:8000 --mode thorough --concurrency 1,2,4 --requests 40 \
        --instance "4 vCPU / 16 GB, MODEL_THREADS=2, MAX_CONCURRENT_RUNS=2"

Document mix (by request count): 70% under 10 KB, 25% 10-200 KB, 5% 200 KB-1 MB. Documents are built from the
committed synthetic eval sets (concatenated to reach the size), so nothing sensitive is sent. Requests under the
sync limit use POST /v1/detect; larger ones use POST /v1/jobs + the SSE progress stream + one GET for the result.
Also reports the two fixed targets: 10 KB Thorough p95 and a single 1 MB job.
"""
import argparse, asyncio, json, os, random, statistics, time
import httpx
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

def corpus():
    rows = []
    for n in ("eval_gretel_fin", "eval_nemotron_fin", "dev_nemotron_fin_structured"):
        rows += [json.loads(l)["text"] for l in open(f"{ROOT}/data/eval/{n}.jsonl")]
    return rows

def make_doc(rows, rnd, size):
    parts, n = [], 0
    while n < size:
        t = rnd.choice(rows); parts.append(t); n += len(t) + 2
    return "\n\n".join(parts)[:size]

def mix(rows, n, seed=0):
    rnd = random.Random(seed); docs = []
    for i in range(n):
        u = rnd.random()
        size = rnd.randint(300, 10_000) if u < 0.70 else rnd.randint(10_000, 200_000) if u < 0.95 else rnd.randint(200_000, 1_000_000)
        docs.append(make_doc(rows, rnd, size))
    return docs

async def one(client, url, text, mode, sync_limit):
    t0 = time.perf_counter(); body = {"text": text, "mode": mode, "raw": True}
    if len(text) <= sync_limit:
        r = await client.post(f"{url}/v1/detect", json=body); r.raise_for_status(); n = len(r.json()["spans"])
    else:
        r = await client.post(f"{url}/v1/jobs", json=body); r.raise_for_status(); jid = r.json()["job_id"]
        async with client.stream("GET", f"{url}/v1/jobs/{jid}/events") as s:
            async for line in s.aiter_lines():
                if line.startswith("event: done") or line.startswith("event: failed"): break
        r = await client.get(f"{url}/v1/jobs/{jid}"); r.raise_for_status(); n = len(r.json()["result"]["spans"])
    return time.perf_counter() - t0, len(text), n

async def run(url, docs, mode, conc, sync_limit):
    sem = asyncio.Semaphore(conc); out = []
    async with httpx.AsyncClient(timeout=600) as client:
        async def task(d):
            async with sem:
                try: out.append(await one(client, url, d, mode, sync_limit))
                except Exception as e: out.append((None, len(d), type(e).__name__))   # noqa: BLE001
        t0 = time.perf_counter(); await asyncio.gather(*(task(d) for d in docs)); wall = time.perf_counter() - t0
    return out, wall

def pct(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000"); ap.add_argument("--mode", default="thorough")
    ap.add_argument("--concurrency", default="1,2,4"); ap.add_argument("--requests", type=int, default=40)
    ap.add_argument("--instance", default=f"{os.cpu_count()} vCPU (this machine)"); ap.add_argument("--out", default=f"{ROOT}/bench/out/load.md")
    ap.add_argument("--skip-mix", action="store_true")
    a = ap.parse_args(); rows = corpus(); rnd = random.Random(1)
    h = httpx.get(f"{a.url}/health", timeout=30).json(); sync_limit = h.get("sync_limit_chars", 200_000)
    httpx.post(f"{a.url}/v1/detect", json={"text": make_doc(rows, rnd, 2000), "mode": a.mode}, timeout=600).raise_for_status()   # warm-up
    L = [f"# Load test", "", f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} · mode **{a.mode}** · instance: {a.instance} · API versions {h.get('versions')}", "",
         "Latency is end to end from the client (HTTP + queueing + detection). Raw findings are requested (`raw: true`), as the web app does.", ""]
    # fixed targets
    ten = [make_doc(rows, rnd, 10_000) for _ in range(20)]
    res, _ = asyncio.run(run(a.url, ten, a.mode, 1, sync_limit)); lat = [r[0] for r in res if r[0] is not None]
    p95 = pct(lat, .95)
    L += ["## Targets", "", "| Target | Result | Met |", "|---|---|---|",
          f"| 10 KB, {a.mode}, p95 < 1.5 s (20 sequential requests) | p50 {pct(lat, .5):.2f} s, p95 {p95:.2f} s | {'yes' if p95 < 1.5 else 'NO'} |"]
    big = make_doc(rows, rnd, 1_000_000)
    res, _ = asyncio.run(run(a.url, [big], a.mode, 1, sync_limit)); t1 = res[0][0]
    L += [f"| 1 MB via /v1/jobs + SSE < 60 s | {'failed: ' + str(res[0][2]) if t1 is None else f'{t1:.1f} s, {res[0][2]} raw findings'} | {'yes' if t1 is not None and t1 < 60 else 'NO'} |", ""]
    print("\n".join(L[-5:]), flush=True)
    if not a.skip_mix:
        docs = mix(rows, a.requests)
        sizes = [len(d) for d in docs]
        L += ["## Realistic mix", "", f"{a.requests} requests: {sum(s < 10_000 for s in sizes)} under 10 KB, {sum(10_000 <= s < 200_000 for s in sizes)} of 10-200 KB, "
              f"{sum(s >= 200_000 for s in sizes)} of 200 KB-1 MB; {sum(sizes) / 1e6:.1f} MB in total.", "",
              "| Concurrency | p50 s | p95 s | p99 s | max s | req/s | KB/s | errors |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for c in [int(x) for x in a.concurrency.split(",")]:
            res, wall = asyncio.run(run(a.url, docs, a.mode, c, sync_limit)); lat = [r[0] for r in res if r[0] is not None]
            row = f"| {c} | {pct(lat, .5):.2f} | {pct(lat, .95):.2f} | {pct(lat, .99):.2f} | {max(lat):.2f} | {len(lat) / wall:.2f} | {sum(r[1] for r in res if r[0] is not None) / 1000 / wall:.0f} | {len(res) - len(lat)} |"
            L.append(row); print(row, flush=True)
        small = [r for r in res if r[0] is not None and r[1] < 10_000]
        L += ["", f"At the highest concurrency, requests under 10 KB: p50 {pct([r[0] for r in small], .5):.2f} s, p95 {pct([r[0] for r in small], .95):.2f} s.", ""]
    os.makedirs(os.path.dirname(a.out), exist_ok=True); open(a.out, "w").write("\n".join(L) + "\n"); print("wrote", a.out)

if __name__ == "__main__":
    main()

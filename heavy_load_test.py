"""Heavy load concurrent API test."""

import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"

async def make_request(session, method, url, **kwargs):
    start = time.perf_counter()
    try:
        async with session.request(method, url, **kwargs) as resp:
            await resp.read()
            return {"success": resp.status < 400, "time": (time.perf_counter() - start) * 1000, "status": resp.status}
    except Exception as e:
        return {"success": False, "time": (time.perf_counter() - start) * 1000, "error": str(e)[:50]}

async def test_health(session, user_id, count):
    results = []
    for _ in range(count):
        results.append(await make_request(session, "GET", f"{BASE_URL}/health"))
    return results

async def test_formats(session, user_id, count):
    results = []
    for _ in range(count):
        results.append(await make_request(session, "GET", f"{BASE_URL}/formats"))
    return results

async def test_file_upload(session, user_id, count):
    results = []
    for i in range(count):
        data = aiohttp.FormData()
        data.add_field("file", f"# Test {user_id}-{i}\n\nContent".encode(), filename=f"t{i}.md")
        results.append(await make_request(session, "POST", f"{BASE_URL}/convert/file", data=data))
    return results

async def test_url_convert(session, user_id, count):
    results = []
    for i in range(count):
        results.append(await make_request(
            session, "POST", f"{BASE_URL}/convert/url",
            json={"url": "https://httpbin.org/json"}
        ))
    return results

async def run_scenario(name, users, per_user, test_func):
    print(f"\n{'='*60}\n{name} ({users} users x {per_user} = {users*per_user} requests)")
    print('='*60)

    connector = aiohttp.TCPConnector(limit=users+50)
    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=180)) as session:
        start = time.perf_counter()
        tasks = [test_func(session, i, per_user) for i in range(users)]
        all_results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

    flat = [r for rs in all_results for r in rs]
    success = [r for r in flat if r["success"]]
    failed = [r for r in flat if not r["success"]]

    times = [r["time"] for r in success]
    times.sort()

    print(f"Results: {len(success)}/{len(flat)} success ({len(success)/len(flat)*100:.1f}%)")
    if times:
        p95_idx = int(len(times) * 0.95)
        p99_idx = int(len(times) * 0.99)
        print(f"Latency: avg={sum(times)/len(times):.1f}ms, p95={times[p95_idx]:.1f}ms, p99={times[p99_idx]:.1f}ms, max={max(times):.1f}ms")
    print(f"Throughput: {len(flat)/total_time:.1f} req/s")

    if failed:
        errors = {}
        for r in failed:
            k = r.get("error") or f"HTTP_{r['status']}"
            errors[k] = errors.get(k, 0) + 1
        print(f"Errors: {dict(list(errors.items())[:5])}")

async def main():
    print("MARKITDOWN API - HEAVY LOAD TEST")
    print("="*60)

    # Heavy load tests
    scenarios = [
        ("Health Check - Heavy", 50, 20, test_health),
        ("Formats - Heavy", 50, 20, test_formats),
        ("File Upload - Heavy", 30, 10, test_file_upload),
        ("URL Convert - Light", 10, 5, test_url_convert),
    ]

    for name, users, per_user, test_func in scenarios:
        await run_scenario(name, users, per_user, test_func)

    print("\n" + "="*60)
    print("Heavy load tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

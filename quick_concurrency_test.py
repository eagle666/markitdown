"""Quick concurrent API test."""

import asyncio
import aiohttp
import time
from typing import List

BASE_URL = "http://localhost:8000"
API_KEYS = [f"tenant-{i:03d}" for i in range(50)]

async def make_request(session, method, url, headers=None, **kwargs):
    start = time.perf_counter()
    try:
        async with session.request(method, url, headers=headers, **kwargs) as resp:
            await resp.read()
            return {"success": resp.status < 400, "time": (time.perf_counter() - start) * 1000, "status": resp.status}
    except Exception as e:
        return {"success": False, "time": (time.perf_counter() - start) * 1000, "status": 0, "error": str(e)[:50]}

async def test_health(session, user_id, count):
    results = []
    for _ in range(count):
        results.append(await make_request(session, "GET", f"{BASE_URL}/health"))
    return results

async def test_formats(session, user_id, count):
    headers = {"X-API-Key": API_KEYS[user_id % len(API_KEYS)]}
    results = []
    for _ in range(count):
        results.append(await make_request(session, "GET", f"{BASE_URL}/formats", headers=headers))
    return results

async def test_url_convert(session, user_id, count):
    headers = {"X-API-Key": API_KEYS[user_id % len(API_KEYS)], "Content-Type": "application/json"}
    results = []
    for i in range(count):
        results.append(await make_request(session, "POST", f"{BASE_URL}/convert/url", headers=headers, json={"url": "https://httpbin.org/json"}))
    return results

async def test_file_upload(session, user_id, count):
    headers = {"X-API-Key": API_KEYS[user_id % len(API_KEYS)]}
    results = []
    for i in range(count):
        data = aiohttp.FormData()
        data.add_field("file", f"# Test {user_id}-{i}".encode(), filename=f"t{i}.md")
        results.append(await make_request(session, "POST", f"{BASE_URL}/convert/file", headers=headers, data=data))
    return results

async def run_scenario(name, users, per_user, test_func):
    print(f"\n{'='*60}\n{name} ({users} users x {per_user} = {users*per_user} requests)")
    print('='*60)

    connector = aiohttp.TCPConnector(limit=users+20)
    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=60)) as session:
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
        print(f"Latency: avg={sum(times)/len(times):.1f}ms, p95={times[int(len(times)*0.95)]:.1f}ms, max={max(times):.1f}ms")
    print(f"Throughput: {len(flat)/total_time:.1f} req/s")

    if failed:
        errors = {}
        for r in failed:
            k = r.get("error") or f"HTTP_{r['status']}"
            errors[k] = errors.get(k, 0) + 1
        print(f"Errors: {errors}")

async def main():
    print("MARKITDOWN API - Quick Concurrency Test")
    print("Multi-tenant simulation: each user has unique API key\n")

    # Test 1: Health endpoint (no auth) - high concurrency
    await run_scenario("Health Check (no auth)", 30, 10, test_health)

    # Test 2: Formats (auth, simple request)
    await run_scenario("Formats (auth)", 30, 10, test_formats)

    # Test 3: URL conversion (POST with body)
    await run_scenario("URL Conversion", 20, 5, test_url_convert)

    # Test 4: File upload (multipart)
    await run_scenario("File Upload", 20, 3, test_file_upload)

    print("\n" + "="*60)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

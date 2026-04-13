"""Multi-tenant concurrent API load testing script."""

import asyncio
import aiohttp
import time
import statistics
from dataclasses import dataclass
from typing import List
import random

# Configuration
BASE_URL = "http://localhost:8000"

# Generate multiple API keys for different users
API_KEYS = [f"tenant-{i:03d}-key" for i in range(100)]

HEADERS_TEMPLATE = {"Content-Type": "application/json"}


@dataclass
class RequestResult:
    success: bool
    status_code: int
    duration_ms: float
    tenant_id: str
    error: str = None


async def make_request(session: aiohttp.ClientSession, method: str, url: str, headers: dict = None, **kwargs) -> RequestResult:
    """Make a single HTTP request and measure latency."""
    start = time.perf_counter()
    tenant_id = "unknown"
    try:
        async with session.request(method, url, headers=headers, **kwargs) as response:
            await response.read()
            duration_ms = (time.perf_counter() - start) * 1000
            return RequestResult(
                success=response.status < 400,
                status_code=response.status,
                duration_ms=duration_ms,
                tenant_id=tenant_id,
            )
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            success=False,
            status_code=0,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            error=str(e),
        )


async def concurrent_health_check(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate users making health check requests (no auth)."""
    results = []
    for i in range(count):
        result = await make_request(session, "GET", f"{BASE_URL}/health")
        results.append(result)
    return results


async def concurrent_formats_check(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate users making formats requests (with per-tenant auth)."""
    api_key = API_KEYS[user_id % len(API_KEYS)]
    headers = {"X-API-Key": api_key}
    results = []
    for i in range(count):
        result = await make_request(session, "GET", f"{BASE_URL}/formats", headers=headers)
        results.append(result)
    return results


async def concurrent_url_convert(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate users making URL conversion requests."""
    api_key = API_KEYS[user_id % len(API_KEYS)]
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    results = []
    urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/html",
        "https://httpbin.org/xml",
    ]
    for i in range(count):
        url_data = {"url": urls[i % len(urls)]}
        result = await make_request(
            session, "POST",
            f"{BASE_URL}/convert/url",
            headers=headers,
            json=url_data,
        )
        results.append(result)
    return results


async def concurrent_file_convert(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate users uploading files."""
    api_key = API_KEYS[user_id % len(API_KEYS)]
    headers = {"X-API-Key": api_key}
    results = []
    for i in range(count):
        data = aiohttp.FormData()
        content = f"# Test Document {user_id}-{i}\n\nContent for testing."
        data.add_field("file", content.encode(), filename=f"test_{i}.md", content_type="text/markdown")
        result = await make_request(
            session, "POST",
            f"{BASE_URL}/convert/file",
            headers=headers,
            data=data,
        )
        results.append(result)
    return results


async def run_load_test(scenario_name: str, user_count: int, requests_per_user: int, endpoint: str):
    """Run simulation with multiple concurrent users, each with their own API key."""
    print(f"\n{'='*70}")
    print(f"Scenario: {scenario_name}")
    print(f"Users: {user_count} (each with unique API key) | Requests/User: {requests_per_user}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*70}")

    connector = aiohttp.TCPConnector(limit=user_count + 50, force_close=True)
    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        if endpoint == "/health":
            user_func = concurrent_health_check
        elif endpoint == "/formats":
            user_func = concurrent_formats_check
        elif endpoint == "/convert/url":
            user_func = concurrent_url_convert
        elif endpoint == "/convert/file":
            user_func = concurrent_file_convert
        else:
            raise ValueError(f"Unknown endpoint: {endpoint}")

        start_time = time.perf_counter()
        tasks = [user_func(session, i, requests_per_user) for i in range(user_count)]
        all_results = await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - start_time

        flat_results = [r for user_results in all_results for r in user_results]
        return flat_results, total_duration


def analyze_results(results: List[RequestResult], duration: float, scenario: str) -> dict:
    """Analyze and generate report from results."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    latencies = [r.duration_ms for r in successful]
    latencies.sort()

    total = len(results)
    success_rate = len(successful) / total * 100 if total > 0 else 0

    p95_idx = int(len(latencies) * 0.95) if latencies else 0
    p99_idx = int(len(latencies) * 0.99) if latencies else 0

    errors = {}
    for r in failed:
        key = r.error or f"HTTP_{r.status_code}"
        errors[key] = errors.get(key, 0) + 1

    return {
        "scenario": scenario,
        "total_requests": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": success_rate,
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "p95_latency_ms": latencies[p95_idx] if latencies and p95_idx < len(latencies) else 0,
        "p99_latency_ms": latencies[p99_idx] if latencies and p99_idx < len(latencies) else 0,
        "requests_per_second": total / duration if duration > 0 else 0,
        "errors": errors,
    }


def print_report(report: dict):
    """Print formatted test report."""
    print(f"\n{'='*70}")
    print(f"TEST REPORT: {report['scenario']}")
    print(f"{'='*70}")
    print(f"Total Requests:      {report['total_requests']}")
    print(f"Successful:          {report['successful']}")
    print(f"Failed:              {report['failed']}")
    print(f"Success Rate:        {report['success_rate']:.2f}%")
    print(f"\nLatency (ms):")
    print(f"  Average:           {report['avg_latency_ms']:.2f}")
    print(f"  Min:               {report['min_latency_ms']:.2f}")
    print(f"  Max:               {report['max_latency_ms']:.2f}")
    print(f"  P95:               {report['p95_latency_ms']:.2f}")
    print(f"  P99:               {report['p99_latency_ms']:.2f}")
    print(f"\nThroughput:          {report['requests_per_second']:.2f} req/s")
    if report['errors']:
        print(f"\nErrors (top 5):")
        sorted_errors = sorted(report['errors'].items(), key=lambda x: x[1], reverse=True)[:5]
        for error, count in sorted_errors:
            print(f"  {error}: {count}")
    print(f"{'='*70}")


async def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "="*70)
    print("MARKITDOWN API MULTI-TENANT CONCURRENCY TEST")
    print("="*70)
    print(f"\nEach simulated user has a UNIQUE API key")
    print(f"Total available API keys: {len(API_KEYS)}")
    print(f"Rate limit: 100 req/min per API key")

    scenarios = [
        ("Multi-Tenant Light", 20, 5),
        ("Multi-Tenant Medium", 50, 5),
        ("Multi-Tenant Heavy", 80, 10),
    ]

    endpoints = ["/health", "/formats", "/convert/url", "/convert/file"]
    all_reports = []

    for scenario_name, user_count, requests_per_user in scenarios:
        for endpoint in endpoints:
            full_scenario = f"{scenario_name}-{endpoint.replace('/', '')}"
            results, duration = await run_load_test(
                full_scenario, user_count, requests_per_user, endpoint
            )
            report = analyze_results(results, duration, full_scenario)
            all_reports.append(report)
            print_report(report)
            await asyncio.sleep(0.5)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY - MULTI-TENANT SCENARIOS")
    print("="*70)
    print(f"{'Scenario':<35} {'Total':<8} {'Success':<8} {'Failed':<8} {'Rate%':<8} {'RPS':<10}")
    print("-"*70)
    for report in all_reports:
        print(f"{report['scenario']:<35} {report['total_requests']:<8} {report['successful']:<8} {report['failed']:<8} {report['success_rate']:<8.2f} {report['requests_per_second']:<10.2f}")

    total_requests = sum(r['total_requests'] for r in all_reports)
    total_successful = sum(r['successful'] for r in all_reports)
    overall_rate = total_successful / total_requests * 100 if total_requests > 0 else 0

    print("-"*70)
    print(f"{'OVERALL':<35} {total_requests:<8} {total_successful:<8} {total_requests - total_successful:<8} {overall_rate:<8.2f}")

    return all_reports


if __name__ == "__main__":
    print("\nStarting multi-tenant concurrency tests...")
    print("Each user gets a unique API key (simulating multi-tenancy)")
    print("Make sure the API server is running at http://localhost:8000\n")

    reports = asyncio.run(run_all_tests())
    print("\n\nAll multi-tenant tests completed!")

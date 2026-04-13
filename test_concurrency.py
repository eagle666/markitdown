"""Concurrent API load testing script."""

import asyncio
import aiohttp
import time
import statistics
from dataclasses import dataclass
from typing import List
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-123"
HEADERS = {"X-API-Key": API_KEY}

# Test scenarios
SCENARIOS = {
    "light": {"users": 10, "requests_per_user": 5},
    "medium": {"users": 50, "requests_per_user": 10},
    "heavy": {"users": 100, "requests_per_user": 20},
}


@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    status_code: int
    duration_ms: float
    error: str = None


@dataclass
class TestReport:
    """Aggregated test results."""
    scenario: str
    total_requests: int
    successful: int
    failed: int
    success_rate: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    errors: dict


async def make_request(session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> RequestResult:
    """Make a single HTTP request and measure latency."""
    start = time.perf_counter()
    try:
        async with session.request(method, url, **kwargs) as response:
            await response.read()
            duration_ms = (time.perf_counter() - start) * 1000
            return RequestResult(
                success=response.status < 400,
                status_code=response.status,
                duration_ms=duration_ms,
            )
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            success=False,
            status_code=0,
            duration_ms=duration_ms,
            error=str(e),
        )


async def concurrent_health_check(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate a user making multiple health check requests."""
    results = []
    for i in range(count):
        result = await make_request(session, "GET", f"{BASE_URL}/health")
        results.append(result)
    return results


async def concurrent_formats_check(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate a user making multiple formats requests."""
    results = []
    for i in range(count):
        result = await make_request(session, "GET", f"{BASE_URL}/formats", headers=HEADERS)
        results.append(result)
    return results


async def concurrent_url_convert(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate a user making multiple URL conversion requests."""
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
            headers={**HEADERS, "Content-Type": "application/json"},
            json=url_data,
        )
        results.append(result)
    return results


async def concurrent_file_convert(session: aiohttp.ClientSession, user_id: int, count: int) -> List[RequestResult]:
    """Simulate a user uploading files."""
    results = []
    for i in range(count):
        # Create test content
        data = aiohttp.FormData()
        content = f"# Test Document {user_id}-{i}\n\nContent for testing."
        data.add_field("file", content.encode(), filename=f"test_{i}.md", content_type="text/markdown")
        result = await make_request(
            session, "POST",
            f"{BASE_URL}/convert/file",
            headers=HEADERS,
            data=data,
        )
        results.append(result)
    return results


async def run_user_simulation(scenario_name: str, user_count: int, requests_per_user: int, endpoint: str):
    """Run simulation for a specific endpoint with multiple concurrent users."""
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario_name} | Users: {user_count} | Requests/User: {requests_per_user}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*60}")

    connector = aiohttp.TCPConnector(limit=100, force_close=True)
    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Select the endpoint test function
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

        # Create tasks for all users
        start_time = time.perf_counter()
        tasks = [user_func(session, i, requests_per_user) for i in range(user_count)]

        # Execute all tasks concurrently
        all_results = await asyncio.gather(*tasks)

        total_duration = time.perf_counter() - start_time

        # Flatten results
        flat_results = [r for user_results in all_results for r in user_results]

        return flat_results, total_duration


def analyze_results(results: List[RequestResult], duration: float, scenario: str) -> TestReport:
    """Analyze and generate report from results."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    latencies = [r.duration_ms for r in successful]
    latencies.sort()

    total = len(results)
    success_rate = len(successful) / total * 100 if total > 0 else 0

    # Calculate percentiles
    p95_idx = int(len(latencies) * 0.95) if latencies else 0
    p99_idx = int(len(latencies) * 0.99) if latencies else 0

    # Group errors
    errors = {}
    for r in failed:
        key = r.error or f"HTTP_{r.status_code}"
        errors[key] = errors.get(key, 0) + 1

    return TestReport(
        scenario=scenario,
        total_requests=total,
        successful=len(successful),
        failed=len(failed),
        success_rate=success_rate,
        avg_latency_ms=statistics.mean(latencies) if latencies else 0,
        min_latency_ms=min(latencies) if latencies else 0,
        max_latency_ms=max(latencies) if latencies else 0,
        p95_latency_ms=latencies[p95_idx] if latencies and p95_idx < len(latencies) else 0,
        p99_latency_ms=latencies[p99_idx] if latencies and p99_idx < len(latencies) else 0,
        requests_per_second=total / duration if duration > 0 else 0,
        errors=errors,
    )


def print_report(report: TestReport):
    """Print formatted test report."""
    print(f"\n{'='*60}")
    print(f"TEST REPORT: {report.scenario}")
    print(f"{'='*60}")
    print(f"Total Requests:      {report.total_requests}")
    print(f"Successful:          {report.successful}")
    print(f"Failed:              {report.failed}")
    print(f"Success Rate:        {report.success_rate:.2f}%")
    print(f"\nLatency (ms):")
    print(f"  Average:           {report.avg_latency_ms:.2f}")
    print(f"  Min:               {report.min_latency_ms:.2f}")
    print(f"  Max:               {report.max_latency_ms:.2f}")
    print(f"  P95:               {report.p95_latency_ms:.2f}")
    print(f"  P99:               {report.p99_latency_ms:.2f}")
    print(f"\nThroughput:          {report.requests_per_second:.2f} req/s")
    if report.errors:
        print(f"\nErrors:")
        for error, count in report.errors.items():
            print(f"  {error}: {count}")
    print(f"{'='*60}")


async def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "="*60)
    print("MARKITDOWN API CONCURRENCY TEST SUITE")
    print("="*60)

    endpoints = ["/health", "/formats", "/convert/url", "/convert/file"]
    all_reports = []

    for scenario_name, config in SCENARIOS.items():
        user_count = config["users"]
        requests_per_user = config["requests_per_user"]

        for endpoint in endpoints:
            # Skip auth-required endpoints for health
            if endpoint == "/health":
                scenario = f"{scenario_name}-{endpoint}"
            else:
                scenario = f"{scenario_name}-{endpoint}"

            results, duration = await run_user_simulation(
                scenario, user_count, requests_per_user, endpoint
            )

            report = analyze_results(results, duration, scenario)
            all_reports.append(report)
            print_report(report)

            # Small delay between scenarios
            await asyncio.sleep(1)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY - ALL SCENARIOS")
    print("="*60)
    print(f"{'Scenario':<30} {'Total':<8} {'Success':<8} {'Failed':<8} {'Rate%':<8} {'RPS':<10}")
    print("-"*60)
    for report in all_reports:
        print(f"{report.scenario:<30} {report.total_requests:<8} {report.successful:<8} {report.failed:<8} {report.success_rate:<8.2f} {report.requests_per_second:<10.2f}")

    # Overall stats
    total_requests = sum(r.total_requests for r in all_reports)
    total_successful = sum(r.successful for r in all_reports)
    overall_success_rate = total_successful / total_requests * 100 if total_requests > 0 else 0

    print("-"*60)
    print(f"{'OVERALL':<30} {total_requests:<8} {total_successful:<8} {total_requests - total_successful:<8} {overall_success_rate:<8.2f}")

    return all_reports


if __name__ == "__main__":
    print("\nStarting concurrency tests...")
    print("Make sure the API server is running at http://localhost:8000")
    print(f"Using API Key: {API_KEY}\n")

    reports = asyncio.run(run_all_tests())

    print("\n\nAll tests completed!")

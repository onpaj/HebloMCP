# Comprehensive Tool Tests Design

**Date:** 2026-02-26
**Status:** Approved
**Author:** Development Team

## Overview & Goals

### What We're Building

A comprehensive integration test suite for HebloMCP tools that validates real API behavior against known test scenarios.

### Scope

**Tool Categories:**
- **Catalog tools** (15 tools): Search, autocomplete, detail, composition, materials, usage, warehouse stats, weight calculations, stock-taking
- **Manufacturing tools** (14 tools): ManufactureOrder (10) + ManufactureBatch (4) - orders, batches, calendars, responsible persons

**Test Coverage per Tool:**
1. **Happy path**: Valid inputs with expected results from known fixtures
2. **Edge cases**: Empty results, pagination, special characters, optional parameters
3. **Error scenarios**: 404 for invalid codes, 400 for bad filters

### Success Criteria

- All 29 tools have test coverage across 3 scenario types
- Tests run against staging Heblo API with real authentication
- Fixtures capture real product codes, search terms, and expected results
- Tests fail when API behavior changes unexpectedly (regression detection)

### Out of Scope (for this phase)

- Mocked unit tests (already covered in existing test suite)
- Write operations that modify production data (read-only tests)
- Performance/load testing
- Other tool categories (Analytics, Invoices, Dashboard, etc.)

## Test Architecture

### Directory Structure

```
tests/
├── conftest.py                    # Existing fixtures + new API client fixture
├── fixtures/
│   ├── catalog_scenarios.json     # Catalog tool test data
│   └── manufacture_scenarios.json # Manufacturing tool test data
├── integration/
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── test_catalog_tools.py      # 15 catalog tool tests
│   │   └── test_manufacture_tools.py  # 14 manufacturing tool tests
│   └── ... (existing integration tests)
└── unit/
    └── ... (existing unit tests)
```

### New Files

- `.env.test` - Staging API credentials (gitignored, documented in TESTING.md)
- `tests/fixtures/*.json` - Known test scenarios with expected results
- `tests/integration/tools/test_catalog_tools.py` - ~45 test functions (15 tools × 3 scenarios)
- `tests/integration/tools/test_manufacture_tools.py` - ~42 test functions (14 tools × 3 scenarios)

### Test Naming Convention

```python
# Pattern: test_{tool_name}_{scenario_type}
def test_catalog_autocomplete_happy_path()
def test_catalog_autocomplete_edge_cases()
def test_catalog_autocomplete_errors()

def test_manufacture_order_create_happy_path()
def test_manufacture_order_create_edge_cases()
def test_manufacture_order_create_errors()
```

### Fixture Loading

```python
# In conftest.py
@pytest.fixture
def catalog_scenarios():
    """Load catalog test scenarios from JSON fixture."""
    with open("tests/fixtures/catalog_scenarios.json") as f:
        return json.load(f)

@pytest.fixture
async def api_client(monkeypatch):
    """Authenticated API client using test credentials."""
    # Load .env.test, create real authenticated client
    # Return FastMCP server or httpx client
```

### Pytest Markers

```python
@pytest.mark.integration  # Marks as integration test
@pytest.mark.slow         # Real API calls, slower than unit tests
@pytest.mark.catalog      # Filter by category
@pytest.mark.manufacturing
```

## Fixture Design

### Fixture Structure (catalog_scenarios.json)

```json
{
  "catalog_autocomplete": {
    "happy_path": {
      "description": "Search for boots returns expected products",
      "request": {
        "query": "heel boots",
        "productTypes": ["Product"]
      },
      "expected": {
        "should_contain_codes": ["BOOT001", "BOOT002"],
        "min_results": 2,
        "response_structure": {
          "type": "array",
          "items_have_fields": ["code", "name", "productType"]
        }
      }
    },
    "edge_cases": {
      "empty_query": {
        "request": {"query": ""},
        "expected": {"error_or_empty": true}
      },
      "special_chars": {
        "request": {"query": "boot's & \"heel\""},
        "expected": {"min_results": 0}
      },
      "pagination": {
        "request": {"query": "product", "limit": 5},
        "expected": {"max_results": 5}
      }
    },
    "errors": {
      "invalid_product_type": {
        "request": {"query": "test", "productTypes": ["InvalidType"]},
        "expected": {"status_code": 400}
      }
    }
  },
  "catalog_detail": {
    "happy_path": {
      "description": "Get details for known product",
      "request": {"productCode": "BOOT001"},
      "expected": {
        "has_fields": ["code", "name", "productType", "price"],
        "code_equals": "BOOT001",
        "productType": "Product"
      }
    },
    "errors": {
      "nonexistent_product": {
        "request": {"productCode": "NOTEXIST999"},
        "expected": {"status_code": 404}
      }
    }
  }
}
```

### Fixture for Manufacturing (manufacture_scenarios.json)

```json
{
  "manufacture_order_list": {
    "happy_path": {
      "description": "List orders returns known orders",
      "request": {
        "status": "InProgress",
        "limit": 10
      },
      "expected": {
        "min_results": 1,
        "response_structure": {
          "type": "array",
          "items_have_fields": ["id", "status", "products"]
        }
      }
    }
  },
  "manufacture_order_detail": {
    "happy_path": {
      "description": "Get details for known order",
      "request": {"orderId": "ORD-TEST-001"},
      "expected": {
        "has_fields": ["id", "status", "createdDate", "products"],
        "id_equals": "ORD-TEST-001"
      }
    },
    "errors": {
      "nonexistent_order": {
        "request": {"orderId": "ORD-NOTEXIST-999"},
        "expected": {"status_code": 404}
      }
    }
  }
}
```

### Key Design Decisions

1. **Flexible Validation**: Use `should_contain_codes` (not exact match) since API data may grow
2. **Structure + Content**: Validate both response structure AND specific known values
3. **Maintainable**: When "BOOT001" changes, update fixture in one place
4. **Self-Documenting**: `description` field explains what scenario tests
5. **Realistic**: Use actual product codes, order IDs from staging environment

### Data Provider Responsibility

The team provides actual product codes, search keywords, order IDs that exist in staging API:
- Which search term returns which products?
- Which product codes have compositions?
- Which manufacture order IDs exist for testing?

## Authentication & Configuration

### Test Environment Configuration (.env.test)

```bash
# Shared test credentials for staging API
HEBLO_TENANT_ID=your-test-tenant-id
HEBLO_CLIENT_ID=your-test-client-id
HEBLO_API_BASE_URL=https://heblo.stg.anela.cz
HEBLO_OPENAPI_SPEC_URL=https://heblo.stg.anela.cz/swagger/v1/swagger.json
HEBLO_API_SCOPE=api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user

# Test-specific settings
HEBLO_TOKEN_CACHE_PATH=.pytest_cache/test_token_cache.json
```

### Authentication Strategy

**Initial Setup** (one-time per developer/CI):
```bash
# Set test credentials
export $(cat .env.test | xargs)

# Authenticate once
heblo-mcp login
# This caches token to .pytest_cache/test_token_cache.json
```

**Test Execution**:
- Tests load `.env.test` configuration
- Reuse cached token from previous login
- Token auto-refreshes if expired (via MSALBearerAuth)
- No interactive login during test runs

### Conftest Setup

```python
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from heblo_mcp.server import get_mcp_server

@pytest.fixture(scope="session")
def load_test_env():
    """Load test environment variables from .env.test."""
    test_env = Path(__file__).parent.parent / ".env.test"
    if test_env.exists():
        load_dotenv(test_env)
    else:
        pytest.skip(".env.test not found - integration tests require test credentials")

@pytest.fixture(scope="session")
async def mcp_server(load_test_env):
    """Create authenticated MCP server for integration tests."""
    server = await get_mcp_server()
    yield server

@pytest.fixture
def catalog_scenarios():
    """Load catalog test scenarios."""
    import json
    fixture_path = Path(__file__).parent / "fixtures" / "catalog_scenarios.json"
    with open(fixture_path) as f:
        return json.load(f)

@pytest.fixture
def manufacture_scenarios():
    """Load manufacturing test scenarios."""
    import json
    fixture_path = Path(__file__).parent / "fixtures" / "manufacture_scenarios.json"
    with open(fixture_path) as f:
        return json.load(f)
```

### CI/CD Integration

```yaml
# GitHub Actions / GitLab CI
env:
  HEBLO_TENANT_ID: ${{ secrets.TEST_TENANT_ID }}
  HEBLO_CLIENT_ID: ${{ secrets.TEST_CLIENT_ID }}

steps:
  - name: Authenticate with test account
    run: heblo-mcp login

  - name: Run integration tests
    run: pytest tests/integration/tools/ -v --tb=short
```

### Security Considerations

- `.env.test` gitignored (never commit credentials)
- Document setup in `TESTING.md`
- Use dedicated test Azure AD app (not production credentials)
- Token cache in `.pytest_cache/` (gitignored)
- CI secrets for automation

## Test Implementation Pattern

### Test Template

```python
"""Integration tests for Catalog tools."""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.catalog]


class TestCatalogAutocomplete:
    """Test catalog_autocomplete tool."""

    @pytest.mark.asyncio
    async def test_happy_path(self, mcp_server, catalog_scenarios):
        """Search with valid query returns expected products."""
        scenario = catalog_scenarios["catalog_autocomplete"]["happy_path"]
        request = scenario["request"]
        expected = scenario["expected"]

        # Call the MCP tool
        result = await mcp_server.call_tool(
            "catalog_autocomplete",
            arguments=request
        )

        # Validate response structure
        assert isinstance(result, list)
        assert len(result) >= expected["min_results"]

        # Validate expected products are present
        result_codes = [item["code"] for item in result]
        for expected_code in expected["should_contain_codes"]:
            assert expected_code in result_codes, \
                f"Expected product {expected_code} not found in results"

        # Validate response structure
        for item in result:
            for field in expected["response_structure"]["items_have_fields"]:
                assert field in item, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_edge_cases_empty_query(self, mcp_server, catalog_scenarios):
        """Empty query returns empty results or error."""
        scenario = catalog_scenarios["catalog_autocomplete"]["edge_cases"]["empty_query"]

        result = await mcp_server.call_tool(
            "catalog_autocomplete",
            arguments=scenario["request"]
        )

        # Should return empty list or handle gracefully
        assert isinstance(result, list)
        assert len(result) == 0 or result is not None

    @pytest.mark.asyncio
    async def test_errors_invalid_product_type(self, mcp_server, catalog_scenarios):
        """Invalid product type returns 400 error."""
        scenario = catalog_scenarios["catalog_autocomplete"]["errors"]["invalid_product_type"]

        with pytest.raises(Exception) as exc_info:
            await mcp_server.call_tool(
                "catalog_autocomplete",
                arguments=scenario["request"]
            )

        # Verify it's a 400 error
        assert "400" in str(exc_info.value) or "Bad Request" in str(exc_info.value)


class TestCatalogDetail:
    """Test catalog_detail tool."""

    @pytest.mark.asyncio
    async def test_happy_path(self, mcp_server, catalog_scenarios):
        """Get details for known product returns correct data."""
        scenario = catalog_scenarios["catalog_detail"]["happy_path"]

        result = await mcp_server.call_tool(
            "catalog_detail",
            arguments=scenario["request"]
        )

        expected = scenario["expected"]

        # Validate required fields present
        for field in expected["has_fields"]:
            assert field in result, f"Missing field: {field}"

        # Validate specific values
        assert result["code"] == expected["code_equals"]
        assert result["productType"] == expected["productType"]

    @pytest.mark.asyncio
    async def test_errors_nonexistent_product(self, mcp_server, catalog_scenarios):
        """Nonexistent product code returns 404."""
        scenario = catalog_scenarios["catalog_detail"]["errors"]["nonexistent_product"]

        with pytest.raises(Exception) as exc_info:
            await mcp_server.call_tool(
                "catalog_detail",
                arguments=scenario["request"]
            )

        assert "404" in str(exc_info.value) or "Not Found" in str(exc_info.value)
```

### Key Patterns

1. **Class per tool**: Groups related test functions
2. **Scenario-driven**: Each test loads scenario from fixture
3. **Clear assertions**: Specific error messages for failures
4. **async/await**: All tool calls are async
5. **Pytest markers**: Easy to run subsets (`pytest -m catalog`)

### Helper Utilities (optional)

```python
# tests/integration/tools/helpers.py

def assert_has_fields(obj, fields):
    """Assert object has all required fields."""
    for field in fields:
        assert field in obj, f"Missing field: {field}"

def assert_status_code(exception, expected_code):
    """Assert exception contains expected HTTP status code."""
    exc_str = str(exception.value)
    assert str(expected_code) in exc_str or \
           HTTP_STATUS_NAMES[expected_code] in exc_str
```

## Execution & CI Integration

### Running Tests Locally

```bash
# 1. One-time setup: Authenticate with test credentials
export $(cat .env.test | xargs)
heblo-mcp login

# 2. Run all integration tool tests
pytest tests/integration/tools/ -v

# 3. Run specific category
pytest tests/integration/tools/ -m catalog
pytest tests/integration/tools/ -m manufacturing

# 4. Run specific tool tests
pytest tests/integration/tools/test_catalog_tools.py::TestCatalogAutocomplete

# 5. Run only happy path tests (fast smoke test)
pytest tests/integration/tools/ -k "happy_path"

# 6. Run with detailed output on failures
pytest tests/integration/tools/ -vv --tb=long

# 7. Run in parallel (faster execution)
pip install pytest-xdist
pytest tests/integration/tools/ -n auto
```

### Test Execution Time Estimates

- Per tool test: ~1-3 seconds (real API call)
- All catalog tests (45 tests): ~2-3 minutes
- All manufacturing tests (42 tests): ~2-3 minutes
- **Total suite**: ~5-6 minutes

### Pytest Configuration

```ini
[tool.pytest.ini_options]
markers = [
    "integration: Integration tests requiring real API",
    "slow: Tests that take longer to execute",
    "catalog: Catalog tool tests",
    "manufacturing: Manufacturing tool tests",
]

# Don't run slow integration tests by default
addopts = "-m 'not slow'"

# To run integration tests explicitly:
# pytest tests/integration/tools/ -m slow
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Integration Tests

on:
  push:
    branches: [main, master]
  pull_request:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6am

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Create .env.test from secrets
        run: |
          echo "HEBLO_TENANT_ID=${{ secrets.TEST_TENANT_ID }}" >> .env.test
          echo "HEBLO_CLIENT_ID=${{ secrets.TEST_CLIENT_ID }}" >> .env.test
          echo "HEBLO_API_BASE_URL=https://heblo.stg.anela.cz" >> .env.test
          echo "HEBLO_OPENAPI_SPEC_URL=https://heblo.stg.anela.cz/swagger/v1/swagger.json" >> .env.test
          echo "HEBLO_API_SCOPE=api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user" >> .env.test
          echo "HEBLO_TOKEN_CACHE_PATH=.pytest_cache/test_token_cache.json" >> .env.test

      - name: Authenticate with test account
        run: |
          export $(cat .env.test | xargs)
          heblo-mcp login

      - name: Run integration tests
        run: pytest tests/integration/tools/ -v --tb=short --junitxml=test-results.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results.xml
```

### CI Strategy

- **On every commit**: Run unit tests (fast, mocked)
- **On PR/merge**: Run integration tests (slower, real API)
- **Nightly**: Full integration suite + check for fixture staleness
- **Manual trigger**: For debugging specific issues

## Maintenance Strategy

### Fixture Maintenance

**When Fixtures Need Updates:**
- Test fails because expected product code changed
- New products added to staging that better represent test scenarios
- API response structure changes
- Product codes renamed or deprecated

**Update Process:**
```bash
# 1. Identify what changed
pytest tests/integration/tools/ -v
# Test failure shows: "Expected product BOOT001 not found"

# 2. Verify staging API directly
heblo-mcp  # Start server
# Use MCP inspector or Claude to check current data

# 3. Update fixture
# Edit tests/fixtures/catalog_scenarios.json
# Replace "BOOT001" with "BOOT_NEW_001"

# 4. Re-run tests to verify
pytest tests/integration/tools/test_catalog_tools.py::TestCatalogDetail
```

**Fixture Validation Script** (optional helper):
```python
# scripts/validate_fixtures.py
"""Validate that all fixture product codes still exist in API."""

async def validate_catalog_fixtures():
    scenarios = load_json("tests/fixtures/catalog_scenarios.json")

    for tool, test_cases in scenarios.items():
        for scenario_type, scenario in flatten(test_cases):
            if "productCode" in scenario.get("request", {}):
                code = scenario["request"]["productCode"]
                exists = await check_product_exists(code)
                if not exists:
                    print(f"⚠️  Product {code} not found in {tool}/{scenario_type}")

# Run: python scripts/validate_fixtures.py
```

**Documentation in Fixtures:**
```json
{
  "_metadata": {
    "last_updated": "2026-02-26",
    "staging_api_version": "v1",
    "notes": "Product codes verified against staging on 2026-02-26"
  },
  "catalog_autocomplete": {
    // ... scenarios
  }
}
```

### Handling API Changes

1. **Breaking Changes** (response structure):
   - Test fails with missing field error
   - Update fixture's `expected.response_structure`
   - Update test assertions if needed
   - Document change in git commit

2. **New Fields Added** (non-breaking):
   - Tests continue passing
   - Optionally update fixtures to validate new fields
   - No immediate action required

3. **Deprecations**:
   - API returns deprecation warnings
   - Update fixtures to use new endpoints/parameters
   - Update tool tests before old endpoint removed

### Test Health Monitoring

**Nightly CI Run:**
- Catch drift between fixtures and staging API
- Alert team if multiple tests start failing
- Run fixture validation script

**Fixture Staleness Indicators:**
```python
# In conftest.py
def check_fixture_age(fixture_path):
    age_days = (datetime.now() - fixture_path.stat().st_mtime).days
    if age_days > 90:
        warnings.warn(f"Fixture {fixture_path.name} is {age_days} days old")
```

**Test Stability Metrics:**
- Track flaky tests (pass/fail intermittently)
- If test fails >2 times, investigate fixture vs API issue
- Maintain >95% pass rate on stable branch

### Documentation Requirements

Update `TESTING.md` with:
- How to set up `.env.test`
- Where to find test credentials (team password manager)
- How to update fixtures when tests fail
- Who to contact if staging API is down
- How to add new tool tests

### Responsibilities

- **Developers**: Keep fixtures updated when changing tools
- **CI**: Run integration tests on PR + nightly
- **Team lead**: Review fixture updates in PRs
- **DevOps**: Maintain test credentials and staging API access

### Rollout Strategy

1. **Week 1**: Set up infrastructure (fixtures, conftest, CI)
2. **Week 2**: Implement Catalog tools tests (15 tools)
3. **Week 3**: Implement Manufacturing tools tests (14 tools)
4. **Week 4**: Documentation, refinement, team training

## Summary

This design provides a sustainable approach to comprehensive tool testing:

- **Real API integration tests** validate actual behavior against staging
- **Tool-by-tool organization** makes tests easy to understand and maintain
- **Specific fixtures** catch regressions when API behavior changes
- **Shared test account** ensures consistent test data across developers/CI
- **Three-tier coverage** (happy path, edge cases, errors) validates robustness

The result is a test suite that:
- Runs in ~5-6 minutes
- Covers 29 critical tools
- Catches API changes early
- Maintains itself through clear documentation and validation scripts

# Testing Guide for HebloMCP

## Overview

HebloMCP now has a comprehensive test suite covering all critical functionality, especially API error handling and schema validation issues.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests for individual modules
│   ├── test_auth.py        # Authentication and token management
│   ├── test_config.py      # Configuration loading and validation
│   ├── test_routes.py      # Route metadata and tool definitions
│   └── test_spec.py        # OpenAPI spec patching and validation
└── integration/             # Integration and API error tests
    ├── test_server.py      # MCP server creation and setup
    └── test_api_errors.py  # API error handling scenarios
```

## Test Coverage

### ✅ **48 Total Tests** covering:

#### Unit Tests (35 tests)
- **Authentication (10 tests)**
  - Token acquisition and caching
  - Device code flow
  - Bearer auth with 401 retry logic
  - Token persistence

- **Configuration (5 tests)**
  - Default values
  - Environment variable loading
  - Required field validation
  - Custom configuration

- **Routes (7 tests)**
  - Tool metadata structure
  - Product type hints and guidance
  - Operation ID uniqueness
  - Category coverage

- **OpenAPI Spec Patching (13 tests)**
  - Metadata injection
  - Schema validation fixes
  - ErrorCodes enum nullability
  - DateOnly format correction
  - Idempotency

#### Integration Tests (13 tests)
- **Server Creation (3 tests)**
  - Successful server initialization
  - Default config loading
  - HTTP client configuration

- **API Error Handling (10 tests)**
  - Network errors
  - HTTP status errors (401, 404, 429)
  - Timeout handling
  - Invalid JSON responses
  - Null error codes (common API issue)
  - Date format mismatches
  - Product type filtering
  - Schema validation fixes

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific module
pytest tests/unit/test_auth.py

# Specific test
pytest tests/unit/test_auth.py::test_heblo_auth_get_token_success
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pip install pytest-cov
pytest tests/ --cov=heblo_mcp --cov-report=html
open htmlcov/index.html
```

### Run with Detailed Failure Information
```bash
pytest tests/ -vv --tb=long
```

## Key Test Fixtures

### Mock Configuration (`mock_config`)
Provides isolated test configuration without loading .env files.

### Mock MSAL App (`mock_msal_app`)
Mocks Azure AD authentication for testing without real credentials.

### Mock Heblo Auth (`mock_heblo_auth`)
Complete authentication handler with mocked MSAL dependencies.

### Sample OpenAPI Spec (`sample_openapi_spec`)
Realistic OpenAPI spec including known API issues for testing fixes.

## Critical API Issues Covered

### 1. **Null Error Codes**
**Problem**: API returns `null` for `errorCode` on success, but schema doesn't allow it.
**Test**: `test_api_response_with_null_error_code`
**Fix**: Make `ErrorCodes` and `IssuedInvoiceErrorType` enums nullable.

### 2. **Date Format Mismatch**
**Problem**: API returns dates as `"2026-08-31"` but schema defines object with year/month/day.
**Test**: `test_api_response_with_date_string`
**Fix**: Change `DateOnly` schema from object to string with date format.

### 3. **401 Token Refresh**
**Problem**: Access tokens expire and need refresh.
**Test**: `test_401_unauthorized_token_refresh`
**Fix**: MSALBearerAuth automatically retries with fresh token.

### 4. **Product Type Filtering**
**Problem**: Ambiguous product/material terminology.
**Tests**: `test_product_type_enum_values`, `test_product_code_patterns`
**Fix**: Add hints to tool descriptions for proper ProductType filtering.

## Adding New Tests

### Unit Test Template
```python
def test_new_feature():
    """Test description."""
    # Arrange
    input_data = setup_test_data()

    # Act
    result = function_to_test(input_data)

    # Assert
    assert result == expected_value
```

### Async Test Template
```python
@pytest.mark.asyncio
async def test_async_feature():
    """Test async operation."""
    result = await async_function()
    assert result is not None
```

### Using Fixtures
```python
def test_with_fixtures(mock_config, mock_heblo_auth):
    """Test using shared fixtures."""
    auth = mock_heblo_auth
    token = auth.get_token()
    assert token == "mock-access-token"
```

## Continuous Integration

Add to your CI pipeline (GitHub Actions, GitLab CI, etc.):

```yaml
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest tests/ -v --tb=short
```

## Test Development Guidelines

1. **Isolation**: Tests should not depend on external services or files
2. **Repeatability**: Tests should produce same results every run
3. **Speed**: Unit tests should complete in milliseconds
4. **Clarity**: Test names should clearly describe what is being tested
5. **Coverage**: Test both success and failure paths
6. **Mocking**: Mock external dependencies (MSAL, HTTP, file system)

## Common Testing Patterns

### Testing Exceptions
```python
with pytest.raises(ExpectedException) as exc_info:
    function_that_raises()
assert "expected message" in str(exc_info.value)
```

### Testing with Environment Variables
```python
def test_env_loading(monkeypatch):
    monkeypatch.setenv("HEBLO_TENANT_ID", "test-value")
    config = HebloMCPConfig()
    assert config.tenant_id == "test-value"
```

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_operation()
    assert result is not None
```

## Debugging Failed Tests

### Get Detailed Output
```bash
pytest tests/unit/test_auth.py::test_specific_test -vv --tb=long -s
```

### Run in Debug Mode
```python
import pytest
pytest.main(["-v", "--pdb", "tests/unit/test_auth.py"])
```

### Print Debug Information
```python
def test_with_debug(capsys):
    print("Debug info")
    result = function_to_test()
    captured = capsys.readouterr()
    assert "Debug info" in captured.out
```

## Performance Testing

For performance-critical paths, consider adding benchmark tests:

```bash
pip install pytest-benchmark

# Run benchmarks
pytest tests/ --benchmark-only
```

## Security Testing

The test suite also covers:
- Token security and caching
- Bearer auth header injection
- Credential handling in mock scenarios

## Next Steps

### Recommended Additions
1. **End-to-End Tests**: Test actual MCP protocol communication
2. **Load Testing**: Test behavior under high request volumes
3. **Mutation Testing**: Verify test quality with mutmut
4. **Property-Based Testing**: Use hypothesis for edge cases

### Monitoring Test Health
- Run tests before every commit
- Monitor test execution time
- Keep test coverage above 80%
- Review and update tests when code changes

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [HebloMCP README](./README.md)

## Docker Health Check Testing

### Health Check Issue Fixed
The HEALTHCHECK in the Dockerfile was attempting to access `/health` which is an MCP tool, not an HTTP endpoint. FastMCP SSE servers expose endpoints at `/` (root) or `/sse`, not `/health`.

### Testing the Health Check

**Prerequisites:**
- Valid Azure AD credentials (HEBLO_TENANT_ID and HEBLO_CLIENT_ID)
- Docker installed

**Steps:**

1. **Build the Docker image:**
   ```bash
   docker build -t heblo-mcp:test .
   ```

2. **Run the container with valid credentials:**
   ```bash
   docker run -d -p 8000:8000 --name test-health \
     -e HEBLO_TENANT_ID=<your-tenant-id> \
     -e HEBLO_CLIENT_ID=<your-client-id> \
     heblo-mcp:test
   ```

3. **Wait for health check to complete (30 seconds start period):**
   ```bash
   sleep 35
   ```

4. **Check health status:**
   ```bash
   docker inspect test-health --format='{{json .State.Health}}' | python -m json.tool
   ```

   Expected output should show `"Status": "healthy"` with successful health check logs.

5. **Test the endpoint directly:**
   ```bash
   curl -v http://localhost:8000/
   ```

   This should return a 200 status code.

6. **Check container logs:**
   ```bash
   docker logs test-health
   ```

   Logs should show the server starting successfully without health check errors.

7. **Cleanup:**
   ```bash
   docker stop test-health && docker rm test-health
   ```

### Health Check Configuration

The health check now:
- Tests the root endpoint `/` which is exposed by FastMCP SSE server
- Uses proper Python syntax with `sys.exit()` for correct exit codes
- Has a 30-second start period to allow for:
  - Package loading
  - OpenAPI spec fetching
  - SSE transport initialization
  - Azure AD authentication

### Troubleshooting Docker Health Checks

**Container fails to start:**
- Verify Azure AD credentials are valid
- Check that the tenant ID and client ID are correct
- Review container logs: `docker logs test-health`

**Health check fails:**
- Wait longer (the start-period is 30 seconds)
- Check if the server is actually running: `docker logs test-health`
- Test the endpoint manually: `curl http://localhost:8000/`

**Connection refused:**
- Server may still be initializing (wait for start-period)
- Check if authentication failed (review logs)
- Verify port 8000 is not already in use

---

**Questions or Issues?** Open an issue on the GitHub repository.

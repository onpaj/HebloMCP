"""Unit tests for CLI serve-sse command."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


def test_serve_sse_command_exists():
    """Test that serve-sse command is registered."""
    from heblo_mcp.__main__ import main
    import sys

    # Test that serve-sse is recognized and calls start_server_sse
    with patch.object(sys, 'argv', ['heblo-mcp', 'serve-sse']):
        with patch('heblo_mcp.__main__.start_server_sse') as mock_serve:
            main()
            # Should call serve-sse function
            assert mock_serve.called


@pytest.mark.asyncio
async def test_start_server_sse_runs():
    """Test that SSE server starts correctly."""
    from heblo_mcp.__main__ import start_server_sse

    # Mock create_server_with_health which is imported inside start_server_sse
    with patch('heblo_mcp.server.create_server_with_health') as mock_create_server:
        mock_mcp = AsyncMock()
        mock_mcp.run = AsyncMock(return_value=None)
        mock_create_server.return_value = mock_mcp

        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = None

            # This should not raise
            start_server_sse()

            # Verify asyncio.run was called
            assert mock_asyncio_run.called

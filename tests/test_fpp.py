"""Tests for `fpp.FPP`."""

import asyncio

import aiohttp
import pytest
from aresponses import Response, ResponsesMockServer

from fppclient import FPP
from fppclient.exceptions import FPPConnectionError, FPPError


@pytest.mark.asyncio
async def test_json_request(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "example.com",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session)
        response = await fpp.request("/")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_text_request(aresponses: ResponsesMockServer) -> None:
    """Test non JSON response is handled correctly."""
    aresponses.add(
        "example.com",
        "/",
        "GET",
        aresponses.Response(status=200, text="OK"),
    )
    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session)
        response = await fpp.request("/")
        assert response == "OK"


@pytest.mark.asyncio
async def test_internal_session(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "example.com",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with FPP("example.com") as fpp:
        response = await fpp.request("/")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_post_request(aresponses: ResponsesMockServer) -> None:
    """Test POST requests are handled correctly."""
    aresponses.add(
        "example.com",
        "/",
        "POST",
        aresponses.Response(status=200, text="OK"),
    )
    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session)
        response = await fpp.request("/", method="POST")
        assert response == "OK"


@pytest.mark.asyncio
async def test_backoff(aresponses: ResponsesMockServer) -> None:
    """Test requests are handled with retries."""

    async def response_handler(_: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    aresponses.add(
        "example.com",
        "/",
        "GET",
        response_handler,
        repeat=2,
    )
    aresponses.add(
        "example.com",
        "/",
        "GET",
        aresponses.Response(status=200, text="OK"),
    )

    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session, request_timeout=0.1)
        response = await fpp.request("/")
        assert response == "OK"


@pytest.mark.asyncio
async def test_timeout(aresponses: ResponsesMockServer) -> None:
    """Test request timeout from FPP."""

    # Faking a timeout by sleeping
    async def response_handler(_: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    # Backoff will try 3 times
    aresponses.add("example.com", "/", "GET", response_handler)
    aresponses.add("example.com", "/", "GET", response_handler)
    aresponses.add("example.com", "/", "GET", response_handler)

    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session, request_timeout=0.1)
        with pytest.raises(FPPConnectionError):
            assert await fpp.request("/")


@pytest.mark.asyncio
async def test_http_error400(aresponses: ResponsesMockServer) -> None:
    """Test HTTP 404 response handling."""
    aresponses.add(
        "example.com",
        "/",
        "GET",
        aresponses.Response(text="OMG PUPPIES!", status=404),
    )

    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session)
        with pytest.raises(FPPError):
            assert await fpp.request("/")


@pytest.mark.asyncio
async def test_http_error500(aresponses: ResponsesMockServer) -> None:
    """Test HTTP 500 response handling."""
    aresponses.add(
        "example.com",
        "/",
        "GET",
        aresponses.Response(
            body=b'{"status":"nok"}',
            status=500,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        fpp = FPP("example.com", session=session)
        with pytest.raises(FPPError):
            assert await fpp.request("/")

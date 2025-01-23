#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TCP Ping Utility

Description:
    A Python implementation of TCP ping that tests connectivity to a remote host
    by attempting TCP connections. It measures connection establishment times
    and provides detailed statistics about the connection attempts.

Features:
    - Supports both IPv4 and IPv6 connections
    - Measures TCP connection establishment times
    - Provides detailed statistics (min/max/avg/median/stddev)
    - Handles connection timeouts and errors gracefully
    - Supports infinite pinging mode
    - Allows forcing specific IP version (v4/v6)

Usage:
    python tcping.py [-h] [-c COUNT] [-t TIMEOUT] [-4] [-6] [-v] host [port]

Arguments:
    host                Target hostname or IP address to ping
    port                Target port number (default: 80)

Options:
    -h, --help         Show this help message and exit
    -c, --count COUNT  Number of pings to send (default: 4, 0 = infinite)
    -t, --timeout SEC  Connection timeout in seconds (default: 1.0)
    -4                 Force using IPv4
    -6                 Force using IPv6
    -v, --version      Show program version

Examples:
    # Basic usage - ping port 80 on example.com
    python tcping.py example.com

    # Ping HTTPS port with 10 attempts and 2 second timeout
    python tcping.py example.com 443 -c 10 -t 2

    # Force IPv6 and ping custom port
    python tcping.py example.com 8080 -6

    # Continuous ping until interrupted
    python tcping.py example.com -c 0

Notes:
    - Requires Python 3.7 or higher
    - Uses only standard Python libraries
    - Ctrl+C to interrupt the ping process
    - Returns exit code:
        0: At least one ping succeeded
        1: All pings failed
        2: Argument error or interrupted

Author:
    NanoApe

Version:
    1.0.0

License:
    MIT License
    Copyright (c) 2025 NanoApe
"""

import sys

if sys.version_info < (3, 7):
    raise RuntimeError(
        f"Python 3.7 or higher is required. Current version: {sys.version.split()[0]}"
    )

import argparse
import signal
import socket
import statistics
import time
from dataclasses import dataclass  # Requires Python 3.7+
from enum import Enum, auto
from typing import Any, List, NoReturn, Optional, Tuple

__version__ = "1.0.0"


@dataclass
class PingResult:
    """Store single ping result"""
    __slots__ = ['success', 'time_ms', 'error']
    success: bool
    time_ms: float
    error: Optional[str] = None


@dataclass
class PingStatistics:
    """Store overall ping statistics"""
    host: str
    port: int
    total: int
    succeeded: int
    failed: int
    success_rate: float
    min_time: float
    max_time: float
    avg_time: float
    med_time: float
    mdev_time: float
    times: List[float]


class IPVersion(Enum):
    """IP version enumeration"""
    V4 = auto()
    V6 = auto()


def signal_handler(signum: int, frame: Any) -> NoReturn:
    """Handle interrupt signals"""
    print("\nInterrupted by user")
    sys.exit(2)


# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def _resolve_ip(host: str, force_v4: bool = False, force_v6: bool = False) -> Tuple[str, IPVersion]:
    """
    Resolve hostname to IP address

    Args:
        host: Target hostname or IP
        force_v4: Whether to force IPv4
        force_v6: Whether to force IPv6

    Returns:
        Tuple[str, IPVersion]: (IP address, IP version)

    Raises:
        ValueError: Empty hostname
        RuntimeError: Domain resolution failure
    """
    if not host:
        raise ValueError("Host cannot be empty")
    if len(host) > 255:  # DNS name length limit
        raise ValueError("Host name too long")

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(10)
    try:
        if force_v4:
            ip = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
            return ip, IPVersion.V4
        elif force_v6:
            ip = socket.getaddrinfo(host, None, socket.AF_INET6)[0][4][0]
            return ip, IPVersion.V6
        else:
            # Prefer IPv4 by default
            try:
                ip = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
                return ip, IPVersion.V4
            except socket.gaierror:
                ip = socket.getaddrinfo(host, None, socket.AF_INET6)[0][4][0]
                return ip, IPVersion.V6
    except socket.herror as e:
        raise RuntimeError(f"Host resolution error: {e}") from e
    except socket.gaierror as e:
        raise RuntimeError(f"Could not resolve hostname: {host}") from e
    except socket.timeout:
        raise RuntimeError("DNS resolution timed out") from None
    except OSError as e:
        raise RuntimeError(f"Network error: {e}") from e
    finally:
        socket.setdefaulttimeout(old_timeout)


def _try_connection(host: str, port: int, timeout: float, ip_version: IPVersion) -> PingResult:
    """
    Attempt a single TCP connection and measure time

    Args:
        host: Target hostname or IP
        port: Target port
        timeout: Timeout in seconds (0 means no timeout)
        ip_version: IP version

    Returns:
        PingResult: Object containing connection result
    """
    family = socket.AF_INET if ip_version == IPVersion.V4 else socket.AF_INET6

    # Handle IPv6 scope ID
    if ip_version == IPVersion.V6 and "%" in host:
        host = host.split("%")[0]

    with socket.socket(family, socket.SOCK_STREAM) as sock:
        if timeout > 0:  # Only set timeout if timeout > 0
            sock.settimeout(timeout)
        # Disable Nagle's algorithm to reduce latency
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        start_time = time.time()
        try:
            sock.connect((host, port))
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # Some systems might error on shutdown, ignore this error
            elapsed_time = (time.time() - start_time) * 1000
            return PingResult(success=True, time_ms=elapsed_time)
        except socket.timeout:
            return PingResult(success=False, time_ms=0, error="Timeout")
        except socket.gaierror:
            return PingResult(success=False, time_ms=0, error="Name resolution failed")
        except ConnectionRefusedError:
            return PingResult(success=False, time_ms=0, error="Connection refused")
        except ConnectionResetError:
            return PingResult(success=False, time_ms=0, error="Connection reset by peer")
        except ConnectionAbortedError:
            return PingResult(success=False, time_ms=0, error="Connection aborted")
        except OSError as e:
            return PingResult(success=False, time_ms=0, error=f"Network error: {e.strerror}")
        except Exception as e:
            return PingResult(success=False, time_ms=0, error=str(e))


def ping(host: str, port: int = 80, count: int = 10, timeout: float = 1.0,
         force_v4: bool = False, force_v6: bool = False, quiet: bool = True) -> PingStatistics:
    """
    Perform TCP ping

    Args:
        host: Target hostname or IP
        port: Target port
        count: Number of pings (0 means infinite)
        timeout: Timeout in seconds (0 means no timeout)
        force_v4: Force IPv4
        force_v6: Force IPv6
        quiet: Whether to suppress output

    Returns:
        PingStatistics object containing statistics
    """
    if timeout < 0 or count < 0 or port < 1 or port > 65535:
        raise ValueError("Invalid parameters")

    # Resolve and display IP address
    ip, ip_version = _resolve_ip(host, force_v4, force_v6)
    if not quiet:
        print(f"TCPING {host} ({ip})[:{port}]")
        sys.stdout.flush()

    successful_times = []
    succeeded = 0
    completed_count = 0
    stats = None

    try:
        i = 0
        while count == 0 or i < count:
            start_time = time.time()

            result = _try_connection(ip, port, timeout, ip_version)
            completed_count += 1

            if result.success:
                succeeded += 1
                successful_times.append(result.time_ms)
                if not quiet:
                    print(
                        f"Connected to {host}[:{port}]: seq={i+1} time={result.time_ms:.2f} ms", flush=True)
            else:
                if not quiet:
                    print(
                        f"Failed to connect to {host}[:{port}]: seq={i+1} error={result.error}", flush=True)

            i += 1
            if count == 0 or i < count:
                elapsed = time.time() - start_time
                sleep_time = max(0, 1 - elapsed)
                time.sleep(sleep_time)

    finally:
        # Calculate statistics
        stats = PingStatistics(
            host=host,
            port=port,
            total=completed_count,
            succeeded=succeeded,
            failed=completed_count - succeeded,
            success_rate=(succeeded / completed_count * 100) if completed_count > 0 else 0,
            min_time=min(successful_times) if successful_times else 0,
            max_time=max(successful_times) if successful_times else 0,
            avg_time=statistics.mean(successful_times) if successful_times else 0,
            med_time=statistics.median(successful_times) if successful_times else 0,
            mdev_time=statistics.pstdev(successful_times) if successful_times else 0,
            times=successful_times
        )

        if not quiet and completed_count > 0:
            print(f"\n--- {stats.host}[:{stats.port}] tcping statistics ---")
            print(f"{stats.total} connections, {stats.succeeded} successed, {stats.failed} failed, {stats.success_rate:.2f}% success rate")
            if stats.times:
                print(
                    f"min = {stats.min_time:.2f}ms, max = {stats.max_time:.2f}ms, "
                    f"avg = {stats.avg_time:.2f}ms, med = {stats.med_time:.2f}ms, mdev = {stats.mdev_time:.2f}ms")
            sys.stdout.flush()

    return stats


def main() -> int:
    """
    Main function, returns exit status code:
    0: At least one ping succeeded
    1: All pings failed
    2: Argument error or other error
    """
    parser = argparse.ArgumentParser(description='TCP ping utility')
    parser.add_argument('host', help='Target host')
    parser.add_argument('port', nargs='?', type=int, default=80,
                        help='Target port (default: 80)')
    parser.add_argument('-c', '--count', type=int, default=4,
                        help='Try connections counts (default 4, 0 means infinite)')
    parser.add_argument('-t', '--timeout', type=float, default=1.0,
                        help='Timeout seconds (default 1, 0 means no timeout)')
    parser.add_argument('-4', dest='ipv4', action='store_true',
                        help='Force using IPv4')
    parser.add_argument('-6', dest='ipv6', action='store_true',
                        help='Force using IPv6')
    parser.add_argument('-v', '--version', action='version',
                        version=f'%(prog)s {__version__}')

    try:
        args = parser.parse_args()

        # Validate arguments
        if not 1 <= args.port <= 65535:
            print("Error: Port must be between 1 and 65535", file=sys.stderr)
            return 2
        if args.count < 0:
            print("Error: Count must be greater than or equal to 0", file=sys.stderr)
            return 2
        if args.timeout < 0:
            print("Error: Timeout must be greater than or equal to 0", file=sys.stderr)
            return 2

        if args.ipv4 and args.ipv6:
            print("Error: Cannot force both IPv4 and IPv6 at the same time", file=sys.stderr)
            return 2

        stats = ping(args.host, args.port, args.count, args.timeout,
                     force_v4=args.ipv4, force_v6=args.ipv6, quiet=False)

        return 0 if stats.succeeded > 0 else 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 2
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 2

    finally:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.default_int_handler)


if __name__ == "__main__":
    sys.exit(main())

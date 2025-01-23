# tcpp

A Python implementation of TCP ping that tests connectivity to a remote host by attempting TCP connections. It measures connection establishment times and provides detailed statistics.

## Features

- 🚀 Pure Python implementation, no external dependencies
- 📦 Lightweight and easy to use
- 🌐 Supports both IPv4 and IPv6
- 🔄 Supports continuous ping mode

## Installation

You can install `tcpp` directly from PyPI:

```bash
pip install tcpp
```

## Usage

### Command Line

Basic usage:
```bash
tcpp bing.com
```

With custom port and count:
```bash
tcpp bing.com 443 -c 10
```

All available options:
```bash
tcpp [-h] [-c COUNT] [-t TIMEOUT] [-4] [-6] [-v] host [port]

positional arguments:
  host                  Target hostname or IP address to ping
  port                  Target port number (default: 80)

options:
  -h, --help           Show this help message and exit
  -c, --count COUNT    Number of pings to send (default: 10, 0 = infinite)
  -t, --timeout SEC    Connection timeout in seconds (default: 1.0)
  -4                   Force using IPv4
  -6                   Force using IPv6
  -v, --version        Show program version
```

### Python API

You can also use tcpp as a Python library:

```python
import tcpp

# Basic usage
stats = tcpp.ping("bing.com", port=80)

# Access statistics
print(f"Success rate: {stats.success_rate}%")
print(f"Average time: {stats.avg_time:.2f}ms")
```

## bing Output

```
TCPING bing.com (13.107.21.200)[:80]
Connected to bing.com[:80]: seq=1 time=61.64 ms
Connected to bing.com[:80]: seq=2 time=61.39 ms
Connected to bing.com[:80]: seq=3 time=59.84 ms
Connected to bing.com[:80]: seq=4 time=59.29 ms

--- bing.com[:80] tcping statistics ---
4 connections, 4 successed, 0 failed, 100.00% success rate
min = 59.29ms, max = 61.64ms, avg = 60.54ms, med = 60.62ms, mdev = 1.00ms
```

## Requirements

- Python 3.7 or higher
- No external dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

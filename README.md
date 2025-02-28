# HTTP Client with Circuit Breaker Integration

Asynchronous HTTP client with Circuit Breaker integration for failure handling and retries.

## Features

- 🚀 **Asynchronous client** based on `httpx.AsyncClient`
- ⚡ **Circuit Breaker integration** [circuit-breaker-box](https://github.com/community-of-python/circuit-breaker-box)
- 🔄 **Automatic retries** [tenacity](https://tenacity.readthedocs.io/en/latest/)
- 📝 **Detailed logging**
- 🛡️ **Flexible response validation**
- 🔧 **Flexible request preparation** supporting all `httpx` parameters
- 🧩 **Customizable response handlers** via inheritance

## Installation

```bash
pip install base-client
```

## Usage
See -> [Examples](examples/)

## Development
### Commands
Use -> [Justfile](Justfile)


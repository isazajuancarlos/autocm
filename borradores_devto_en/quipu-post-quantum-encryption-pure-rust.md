---
title: "Quipu: post-quantum encryption in pure Rust, with a Python wheel"
tags: cryptography, rust, security, postquantum
tema: criptografia
origen_es: https://xiliux.com/blog/quipu-cifrado-multilenguaje-rust-python-node-go
canonical_url:
---

Protecting data that must stay secret ten years from now is a **problem for today**: an adversary can capture your encrypted traffic now and decrypt it once quantum capability exists (*harvest now, decrypt later*). [Quipu](https://xiliux.com/blog/que-es-criptografia-post-cuantica) is a free **hybrid post-quantum** encryption library for data at rest: it combines proven classical cryptography with the new kind, so that it only breaks if **both** fall at once.

## Pure Rust, and why

Quipu started out aiming at several languages: a Rust core with a **C ABI** on top and bindings for Python, Node and Go. It worked, but the lesson was clear: maintaining a stable C interface plus four bindings, each with its own packaging and interoperability tests, was **complexity that did not pay for itself** against the real goal — protecting data at rest — and it widened the attack surface with `unsafe` we did not want.

Today Quipu is **pure Rust**: memory safe, no garbage collector, **no first-party `unsafe`**. And for people who do not write Rust, it ships as a **native Python wheel** via PyO3 — the surface that non-Rust users actually need. One codebase, one thing to audit. It is the same philosophy that guides the rest: where good cryptography exists, reuse it; simplicity is a security decision, not a convenience.

## Installation

```
cargo add quipu              # Rust
pip install quipu-crypto     # Python (native wheel, PyO3)
```

## Encrypt and decrypt in Python

```python
import quipu

# Symmetric, with a passphrase
blob = quipu.encrypt_stream(b"sensitive data", "my-passphrase")
assert quipu.decrypt_stream(blob, "my-passphrase") == b"sensitive data"

# Post-quantum, for a recipient
pub, sec = quipu.generate_keypair()          # X25519 + ML-KEM-1024
c = quipu.encode_to_recipient(b"secret", pub)
assert quipu.decode_as_recipient(c, sec) == b"secret"
```

## What is underneath

* **Encryption:** XChaCha20-Poly1305 (authenticated AEAD).
* **Key derivation:** Argon2id (brute-force resistant) + HKDF.
* **Post-quantum:** X25519 + ML-KEM-1024 for keys; Ed25519 + ML-DSA-87 for signatures.
* **Security level:** NIST category 5 (CNSA 2.0).

These are all **standard, verified primitives** — the ML-KEM-1024 and ML-DSA-87 known-answer tests run against NIST's official ACVP vectors. Quipu **composes** them; it does not invent its own cryptography.

## Free and transparent

Quipu is **open source** (AGPL-3.0). You can read every line and audit the format, which is specified byte by byte. It is published on [crates.io](https://crates.io/crates/quipu) and, as a Python wheel, on [PyPI](https://pypi.org/project/quipu-crypto/).

> Honest status: the composition has not yet passed an **independent cryptographic audit**. Until that external seal exists, treat it as software for review and experimentation, not for protecting real high-value secrets.

The code is at [github.com/isazajuancarlos/quipu](https://github.com/isazajuancarlos/quipu).

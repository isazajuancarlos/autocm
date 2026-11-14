---
title: "Hybrid encryption: why combine classical and post-quantum cryptography"
tags: cryptography, rust, security, postquantum
tema: criptografia
origen_es: https://xiliux.com/blog/cifrado-hibrido-clasico-post-cuantico
canonical_url:
---

When a new cryptographic algorithm appears, a tension shows up: **classical** algorithms such as X25519 or Ed25519 have resisted attacks for years, but are vulnerable to a future quantum computer; **post-quantum** ones such as ML-KEM or ML-DSA resist quantum attacks, but are newer and less tested. Hybrid encryption resolves the tension: **use both at once**.

## The idea in one sentence

> Combine a classical and a post-quantum algorithm so that the system **only breaks if both fail simultaneously**.

A classical attacker would have to break the post-quantum algorithm; a quantum attacker would have to break the classical one *and* the post-quantum one. You gain security against the future without betting everything on a young algorithm.

## Two places to apply it

**Key exchange (encrypting for a recipient).** You combine:

* **X25519** — classical key exchange, fast and heavily tested.
* **ML-KEM-1024** — NIST's post-quantum key encapsulation mechanism, at its highest level.

The two resulting keys are mixed with a context-bound derivation function (HKDF), so that neither one alone is enough.

**Digital signatures (authenticity).** You combine:

* **Ed25519** — classical signature.
* **ML-DSA-87** — NIST post-quantum signature.

The message is accepted only if **both** signatures verify — an AND combiner.

## One principle that never breaks

There is a golden rule in cryptography, **Kerckhoffs's principle**: a system must be secure even if the attacker knows its entire design; security lives in the **key**, not in hiding the format. A good hybrid system uses public, audited primitives — XChaCha20-Poly1305 to encrypt, Argon2id to derive keys from passwords, HKDF to separate domains — and **never invents its own cryptography**.

## How Quipu applies it

[Quipu](https://xiliux.com/blog/quipu-cifrado-multilenguaje-rust-python-node-go) is a free library implementing exactly this approach for **data at rest**: hybrid X25519 + ML-KEM-1024 encryption, hybrid Ed25519 + ML-DSA-87 signatures, and only verified primitives underneath. It targets NIST security level 5 (CNSA 2.0) and is open source, so anyone can review how it works.

> An honest note: Quipu composes standard primitives, but the composition has not yet passed an **independent** cryptographic audit. For real high-value secrets, that external review is the seal worth waiting for.

The code is at [github.com/isazajuancarlos/quipu](https://github.com/isazajuancarlos/quipu), AGPL-3.0.

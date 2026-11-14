---
title: What is post-quantum cryptography, and why migrate now?
tags: cryptography, rust, security, postquantum
tema: criptografia
origen_es: https://xiliux.com/blog/que-es-criptografia-post-cuantica
canonical_url:
---

The cryptography protecting your data today — keys, HTTPS, signatures — rests on mathematical problems that current computers cannot solve in any reasonable time. A large enough quantum computer **could** solve some of them. That is what post-quantum cryptography is: algorithms designed to resist both classical and quantum computers.

## The threat is not only in the future

You might think: "no quantum computer can break my encryption yet, so I can wait." The problem is an attack called **harvest now, decrypt later**:

> An adversary **captures your encrypted traffic today** and stores it. Once quantum capability exists years from now, they **decrypt it**.

If your data must stay secret ten years from now — medical records, trade secrets, personal data — the threat is **present**, not future. What you encrypt today with classical cryptography could be read tomorrow.

## The new NIST standards

NIST, the US standards body, finalised the first post-quantum algorithms in 2024 after years of public analysis:

* **ML-KEM** (formerly CRYSTALS-Kyber): for **key exchange** — how two parties agree on a shared secret securely.
* **ML-DSA** (formerly CRYSTALS-Dilithium): for **digital signatures** — how to verify a message is authentic and unaltered.

These are no longer academic experiments. They are standards that governments and large companies are starting to require.

## Hybrid encryption: the prudent approach

Post-quantum algorithms are new, and "new" in cryptography means "less battle-tested". That is why current best practice is **hybrid**: combine a well-established classical algorithm with a post-quantum one. The result only breaks if **both** fall at once. You gain post-quantum protection without giving up decades of confidence in classical cryptography.

## Where to start

1. **Inventory** where you use cryptography and which data must last years.
2. **Prioritise** long-lived data at rest — the most exposed to "harvest now".
3. **Adopt hybrid encryption** rather than wholesale replacement.
4. **Use libraries that compose verified primitives**, not home-made cryptography.

That last point is the key one, and it is the philosophy behind [Quipu](https://xiliux.com/blog/quipu-cifrado-multilenguaje-rust-python-node-go), a free hybrid post-quantum encryption library for data at rest.

The code is at [github.com/isazajuancarlos/quipu](https://github.com/isazajuancarlos/quipu). It is AGPL-3.0, and the composition has not yet passed an independent cryptographic audit — which is worth saying out loud.

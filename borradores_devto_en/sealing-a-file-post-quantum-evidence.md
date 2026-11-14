---
title: Sealing a file so nobody can argue you touched it
tags: cryptography, rust, security, postquantum
tema: criptografia
origen_es: https://xiliux.com/blog/sellar-evidencia-digital-firma-post-cuantica
canonical_url:
---

An argument about a digital file is almost never lost over what the file says. It is lost one question earlier:

> How do we know that is the file you received, and not the one you edited last night?

If the answer is "trust me", you have already lost. However right you are on the substance.

This problem is not exclusive to a courtroom. The auditor receiving a log dump has it. So does the team documenting an incident, or anyone keeping a copy of a contract signed over email. In every case the need is the same: being able to prove that a set of bytes has not changed since a given moment — and having that proved by **someone who is not you**.

That is why I wrote [Tunjo](https://github.com/isazajuancarlos/tunjo): a Rust tool that walks material read-only, computes its fingerprint, and signs a record anyone can verify.

## Why a tree and not a hash

The obvious approach would be to concatenate everything and take one SHA-256. It works, and it is useless in practice.

When someone disputes **one** file — a specific email out of four thousand — a single hash leaves you two options: hand over the complete set so it can be recomputed, or ask to be believed. The first exposes material that has no business being exposed; the second is not evidence.

A Merkle tree solves exactly that. Each file is a leaf, each pair of nodes combines upward, and a root remains. To prove a leaf belongs to that root, you only need to show that leaf and the path of hashes to the top: a few kilobytes. The rest of the set is never touched.

Two details of the tree that are not optional:

```rust
// Domain separation: a leaf can never pass itself off as an internal node.
h.update([0x00]);          // leaf
h.update([0x01]);          // internal node

// And the root binds the number of leaves.
h.update([0x02]);
h.update(n.to_be_bytes());
```

Without the first, a leaf hash could be presented as if it were a node of the tree. Without the second you get the classic ambiguity of trees with an odd number of leaves: two **different** sets can produce the same root. It is an old, well-known bug, and it keeps showing up in new implementations.

## The fingerprint covers state, not just content

The leaf is not the hash of the file: it is the hash of the **complete element** — path, size, timestamp, status and content hash.

The difference matters. If the fingerprint covered only content, moving a file to another folder, renaming it, or replacing it with a link pointing at the same content would leave the root intact. And those three moves change what the set means: where a document was is part of the fact being documented, not a presentation detail.

## Signing for ten years from now

The record is signed with the triple-hybrid signature from [Quipu](https://github.com/isazajuancarlos/quipu): Ed25519 + ML-DSA-87 (FIPS 204) + SLH-DSA-SHA2-256s (FIPS 205) — and **all three** must validate.

This is not algorithm collecting. The useful life of this is not measured in months: a case file can take years to resolve, and the signature has to still verify at the end. The three pieces fail for different reasons — Ed25519 against a quantum computer; ML-DSA for being recent and lattice-based; SLH-DSA only if the hash function breaks — and all three are needed at once for the seal to hold. One falling does not bring down the record.

The cost is honest: the signature weighs about 34 KB. To seal a set of files, that is noise.

## Verifying the signature is not enough

This is the easiest mistake to make when implementing something like this. The signature covers the complete JSON of the record, **including the integrity root**. If verification stops at checking the signature, you have accepted a root nobody recomputed: someone holding the key could sign a record whose root does not correspond to the elements it lists, and it would pass.

That is why verification always recomputes the tree, and only then looks at the signature. There is a dedicated test for that exact case: an authentic signature over a lying root must fail.

```
$ tunjo verificar acta.json --origen ./evidence
SEAL VALID
  content:  4 elements, 3 with verifiable content
  root:     d9f6f68f591c6af087838dc27049a4194ab70525c350b79ec22446f9c12f9e33

1 DISCREPANCY(IES) against evidence:

ALTERED    attachments/c.pdf
           record: 3fdbaf9c795e22f14e16974c37b62ed381b9c8c4ac7bcbe1a01f13d08ec46643
           disk:   9af5d94042eafbf2c335aa874085b263ff0201aee5e5033fd4c432e92de0093d
```

## When a fact is missing, make noise

An integrity tool that hides its own failures is worse than not having one, because it produces confidence without backing. Three decisions on that:

**An unreadable file stops the sealing.** It is not skipped silently. If it really is unreadable, you have to ask for that explicitly, and then the record logs it as an error: of that element it is recorded that it existed and that reading failed, and nothing more.

**About the clock, the truth is told.** The record requires declaring how it was checked against an external source. If nothing is declared, it writes "NOT VERIFIED" rather than staying quiet. Without a third-party timestamp this proves relative order, not a certain date — and it says that too.

**Symbolic links are not followed.** Where they point is recorded. Following them would take the acquisition outside the material that was received.

## What it deliberately does not do

It does not detect intrusions, does not attribute authorship, and concludes nothing. I could add heuristics saying "there was an attack here", and it would be a mistake: whoever signs a report has to be able to defend every statement line by line, and nobody defends a heuristic they did not write. When that statement falls, it drags the rest of the report with it.

Nor does it prove the past. It attests from the instant of acquisition: if the material arrived already altered, the seal faithfully certifies altered material. That is written in the record it generates, not in the fine print.

## The verifier is public, and not out of generosity

If the only person who can check a seal is the one who issued it, it is not evidence — it is a claim in technical formatting. That is why the verifier is free software and its code is published.

I checked it the only way that counts: I cloned the public repository on a clean machine, built it from scratch, and used **that** binary to verify a record sealed elsewhere. Valid. Then I altered one byte of an attachment and the same binary flagged that file and only that one.

```
git clone https://github.com/isazajuancarlos/tunjo
cd tunjo && cargo build --release
./target/release/tunjo verificar acta.json --origen ./evidence
```

Rust, AGPL-3.0, and the tests include a simulation of 240 comparisons: one byte is altered in each of 120 files, and it is required to flag that one and only that one, and to leave no false positives once restored. Detecting is easy; discriminating is the work.

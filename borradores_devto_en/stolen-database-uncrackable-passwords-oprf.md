---
title: They steal your database and cannot crack a single password
tags: cryptography, rust, security, postquantum
tema: criptografia
origen_es: https://xiliux.com/blog/te-roban-la-base-de-datos-y-no-crackean-ni-una-contrasena
canonical_url:
---

Picture the worst Monday: someone walked off with a dump of your users table. Emails, names, and the password column.

The good news is that you do not store passwords in the clear — you store hashes, with [Argon2id](https://www.rfc-editor.org/rfc/rfc9106.html). The bad news is that this matters **less than it seems**.

## Why the hash alone is not enough

Argon2id makes every attempt cost memory and time. It is a real defence and you should use it. But look at what holds it up: making **each** attacker attempt expensive.

And the attacker holding your database plays by different rules:

* **They are not in a hurry.** No rate limit, no account lockout, no logs to give them away. They can take months.
* **They do not guess randomly.** They start with leaked password lists, which cover an uncomfortable fraction of any real user base.
* **They do not use your server.** They use GPUs rented by the hour.

Raising Argon2's cost helps, but you pay it on every legitimate login and they pay it once per candidate. The arithmetic is not on your side: if a password sits in the first ten thousand entries of a leaked list, no reasonable parameter saves it.

The underlying problem is that **the attacker has everything they need**. The hash, the salt and the parameters are all in the same dump. They can compute the whole function on their own.

## The idea: make a piece missing

What if computing the hash depended on a secret that is **not in the database**?

The simple version is a *pepper*: a key in the application config that gets mixed with the password before hashing. It helps, and it has two serious problems:

1. **It usually leaks along with the database.** If the attacker got into the server, the environment variable was one `cat` away.
2. **It cannot be rotated.** Changing the pepper invalidates every hash at once.

An OPRF solves the first one at the root: the secret **lives in another service**, and the elegant part is that this service **never sees the password**.

## What an OPRF is, without the maths

An *Oblivious Pseudo-Random Function* is a computation between two parties with an unusual property:

* You send your password **blinded** — mathematically masked. The server receives noise.
* The server applies its secret key `k` to that noise and returns more noise.
* You *unblind* it and get a value that **can only be obtained with that key `k`** and that password.

The server does not learn your password. You do not learn its key. And without talking to it, **nobody can compute that value**.

That value is what you hash with Argon2id and store.

Now the attacker holding your database has the hash, the salt, the parameters… and is missing `k`. They cannot test a single candidate offline. To attack, they have to talk to the OPRF service once per attempt — and there you do have rate limits, quotas and logs.

**They have turned an unlimited offline attack into a measurable online one.** That is the whole trick, and it is enormous.

## The part almost nobody implements: the "verifiable"

There is a catch. If the OPRF server is compromised, or simply uses the wrong key, it returns garbage values and **you never find out**: you hash garbage, store it, and lock out all your users. Worse, someone controlling the server could answer with a key they know.

That is why the variant that matters is the **verifiable** one (VOPRF, [RFC 9497](https://www.rfc-editor.org/rfc/rfc9497.html)): the server attaches a **DLEQ proof** that it used the correct key, and the client verifies it against a public key it has pinned.

And here is the detail that makes half the integrations you will find out there decorative: **that public key has to be pinned out of band**. If your client asks for it from the same server it is about to verify, you have verified nothing — you asked the examinee to bring their own answer key.

It is an easy mistake to make. I made it: two of my own clients would fetch the key from the server if the integrator omitted it. It was fixed by making it mandatory.

## What breaks, said before it happens to you

No architectural decision is free, and this one has three real costs:

**1. Your logins depend on another service.** If the OPRF does not answer, you cannot verify passwords. And here the only correct answer is to **fail closed**: if the service is down or the proof does not validate, the login fails. The temptation to "degrade to unhardened" turns an outage into a bypass — and an attacker who can take the service down skips the whole protection.

**2. The key `k` never rotates.** Rotating it invalidates every secret hardened with it. It is a once-and-for-all decision and must be treated as one.

**3. It adds latency** to login: one network round trip. Measurable, small, but not zero.

If your application cannot accept point 1, this is not for you. I would rather say so here than afterwards.

## How it is used in Django

I wrote the primitives in Rust following RFC 9497 and verified them against the official Appendix A.1.2 vectors, then packaged them for Python. The Django integration is a hasher that plugs in where yours already sits:

```
pip install quipu-oprf-django
```

```python
# settings.py
PASSWORD_HASHERS = [
    "quipu_oprf_django.hashers.OprfArgon2PasswordHasher",   # preferred
    "django.contrib.auth.hashers.Argon2PasswordHasher",     # migration
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

QUIPU_OPRF = {
    "BASE_URL":   os.environ["QUIPU_OPRF_URL"],
    "API_KEY":    os.environ["QUIPU_OPRF_API_KEY"],
    # 64 hex, PINNED OUT OF BAND. Do not ask the server for it.
    "PUBLIC_KEY": os.environ["QUIPU_OPRF_PUBKEY"],
    "TIMEOUT":    5.0,
}
```

Migration is gradual: existing users keep logging in with their old hasher and get hardened the next time they sign in.

The package is **Apache-2.0** on purpose. It lives inside your authentication server, and putting a network copyleft licence in there would be indefensible.

## Self-host it or pay for it

The server is open source ([AGPL](https://github.com/isazajuancarlos/quipu)) and you can run it yourself: it is one binary with SQLite and needs nothing else. If you do that, you pay me nothing, and that is perfectly fine.

What is charged for at [`oprf.xiliux.com`](https://xiliux.com/quipu/precios) is **not having to operate it**: availability, quota, and making sure the key `k` survives your deployments. Because the day you lose that key, you lose every password at once.

## What this is not

It is not magic and it replaces nothing you should already be doing: keep using Argon2id with serious parameters, keep your second factor, keep limiting attempts.

What it does is take away the most profitable attack an adversary has against a stolen database. That is not nothing.

---

*The code is at [github.com/isazajuancarlos/quipu](https://github.com/isazajuancarlos/quipu). The VOPRF primitives are Apache-2.0 and conform to RFC 9497. The project does not yet have an independent cryptographic audit, and that has to be said too.*

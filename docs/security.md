# Local Phase 1 security

Every audio, result, edit, export and deletion route checks ownership against a random 256-bit workspace bearer token. Only a SHA-256 digest is stored in SQLite. Tokens expire after 24 hours; the browser retains its token in tab-scoped sessionStorage. This is temporary local workspace isolation, not an account authentication system.

File names never form storage paths. UUID storage, signature checks, upload limits, decoded duration limits, local-protocol FFmpeg decoding, subprocess deadlines and private authenticated audio responses reduce upload abuse. Decoder subprocesses run without a shell. Docker runs application processes as a non-root user. Original uploads are removed after decoding; deletion removes decoded audio and results. The worker cleans expired data, so retention requires a running worker. Redis has no host port. API and UI ports bind to loopback in Compose.

Corrections verify pitch/string/fret consistency, timing, unique note IDs, ordering and edit versions. Raw model predictions cannot be overwritten through the edit API. Tests exercise foreign-session reads, audio, exports, deletion and edits, invalid audio, duration limits and conflicting edits.

Residual risks: FastAPI's multipart parser can spool a body before route-level limits apply; ingress must enforce request size and timeouts on any public deployment. Anonymous session creation and single-host quotas are not an internet-grade rate limiter. FFmpeg runs with the worker's filesystem permissions; hard isolation, restricted mounts, network egress policies, CPU/memory limits and timely binary patches belong to hosted deployment. XSS can expose sessionStorage tokens, so avoid untrusted HTML; UI text is escaped by React.

Before public hosting, introduce real accounts, TLS, ingress limits, per-account/global quotas, distributed rate limiting, secured broker credentials, encrypted object storage, comprehensive retention tooling, and monitored worker resource limits. This project intentionally does not advertise a production deployment.

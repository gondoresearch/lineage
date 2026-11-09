# Security model

lineage is meant for one person or a small group on a server they control. This page says what it protects and what it leaves to you.

## What is protected

- **Authentication.** Every API route except login and version needs a session. Passwords are hashed with scrypt (n = 2¹⁴, r = 8, p = 1, 16-byte random salt) and compared in constant time; logins for unknown users take the same time as for known ones.
- **Sessions.** The cookie is `HttpOnly` (scripts cannot read it), `SameSite=Strict`, valid 30 days, and signed with HMAC-SHA256 using a random key in `data/.secret` (file mode 600). It carries the user's *epoch*: a password change or deleting the account invalidates every session of that user at once.
- **Guessing.** After 5 failed logins for a (user, address) pair, logins are refused for 30 s, doubling each time up to an hour.
- **Cross-site requests.** Besides `SameSite=Strict`, every request that changes data must carry `X-Lineage: 1`. Other websites cannot add that header without a CORS preflight, which lineage never allows.
- **Isolation between users.** Each user's data is in its own folder, reached only through their own session. User names are restricted to `[a-z0-9_-]`, so they are always safe folder names.
- **Content.** Descriptions are sanitised with DOMPurify before being shown, so Markdown cannot inject scripts. Uploaded backups are checked for unsafe paths, links and unexpected files before anything is written, and their size is limited.
- **Data integrity.** Every change is validated before writing; writes are atomic; the last 20 states are kept for Undo.

## What is not

- **Transport.** lineage speaks plain HTTP. Anyone who can see the traffic can read passwords and cookies. Expose it only through an HTTPS proxy, with `LINEAGE_SECURE_COOKIE=1` ([HTTPS](../hosting/https.md)).
- **The demo account** has a public password. Delete it or change it on any reachable server.
- **The server's owner** can read every workspace: data is not encrypted at rest. Protect the data folder like any other private files, and its backups.
- **Roles and sharing.** There are no administrators in the app, no shared workspaces and no audit log.
- **Throttling** is kept in memory and counted per address; it resets when the server restarts, and behind a proxy all requests share the proxy's address.
- **Password recovery** is manual (`manage passwd`).

## Reporting a problem

Please report security issues privately to the maintainer through GitHub rather than in a public issue.

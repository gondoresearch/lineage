# Accounts

Every user logs in, and every account has its own **private workspace** in `data/users/<name>/`. Users cannot see or change each other's data; undo, hand edits, backups and restores only ever touch the user's own folder.

There is no sign-up page and no administrator role: the person running the server manages accounts from the [command line](../reference/cli.md).

## Managing accounts

In Docker, prefix each command with `docker compose exec -it lineage`. From source, set `DATA_DIR` and use `.venv/bin/python`:

```sh
python -m backend.manage list                       # list the accounts
python -m backend.manage adduser NAME               # asks for a password (at least 8 characters)
python -m backend.manage adduser NAME --from DIR    # start from a copy of a data folder, e.g. examples/papers
python -m backend.manage adduser NAME --adopt       # take over a pre-0.2 single-user workspace
python -m backend.manage passwd NAME                # set a password; logs that user out everywhere
python -m backend.manage deluser NAME               # delete an account; its workspace folder stays
python -m backend.manage deluser NAME --purge       # … and delete its workspace too
```

- `--password-stdin` reads the password from the first line of standard input instead of asking, for scripts.
- The running server picks up changes right away; there is no need to restart it.
- **User names** are 1 to 32 characters: lowercase letters, digits, `-` and `_`, starting with a letter or digit.
- A **new account** starts with the [starter vocabulary](../guide/vocabulary.md#the-starter-vocabulary) and no projects, unless created with `--from` or `--adopt`.
- If you delete an account without `--purge` and later create one with the same name, it gets the old workspace back.

## Changing your own password

Any user can change their password in **Settings → Account**. Their other sessions (other browsers, other devices) are logged out; the current one stays logged in.

## Sessions

Logging in sets a cookie that keeps you logged in for **30 days**, or until you press **Log out**. Changing a password — from Settings or with `manage passwd` — and deleting the account end every session of that user.

After **5 failed logins** for the same user from the same address, further attempts are refused for 30 seconds, then 60, 120 and so on (up to an hour). A successful login resets the count.

## The demo account

On the **first start** — when `data/accounts.yaml` does not exist yet — lineage creates the account **demo** with the password **demo**, whose workspace is a copy of the example data. It is there so you can look around right away.

- It is created only once. If you delete it, it stays deleted.
- To skip it entirely, start the first time with `LINEAGE_DEMO=0`. lineage then starts with no accounts, and logs a reminder to create one.
- While the demo account still has the password `demo`, the server log warns about it on every start.

!!! warning
    Before you make lineage reachable from other machines, delete the demo account (`manage deluser demo --purge`) or give it a real password (`manage passwd demo`).

## Forgotten passwords

There is no password reset by email. Whoever runs the server sets a new one with `manage passwd NAME`.

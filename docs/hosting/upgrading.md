# Upgrading

1. Make a backup: copy the whole data folder (or download a backup from each account).
2. Get the new code (`git pull`).
3. Restart: `docker compose up -d --build` with Docker, or `make install && make build && make restart` from source.
4. Check below for steps specific to the version you are upgrading to, and read the [changelog](../changelog.md).

## To 0.2 (accounts)

0.2 adds accounts and changes the layout of the data folder: each user's workspace now lives in `data/users/<name>/`, and your existing workspace at the top of `data/` is not visible to any account until you move it.

On the first start of 0.2:

- the **demo** account is created (unless you set `LINEAGE_DEMO=0`);
- the log warns that the data folder holds a workspace from before accounts.

Move your workspace into an account of your own:

=== "Docker"

    ```sh
    docker compose exec -it lineage python -m backend.manage adduser NAME --adopt
    ```

=== "From source"

    ```sh
    DATA_DIR=./data .venv/bin/python -m backend.manage adduser NAME --adopt
    ```

This moves `workspace.yaml`, `descriptions/` and `.history/` (so Undo still works) into `data/users/NAME/` and asks for the account's password. Log in as NAME and your projects are there.

Then delete the demo account or change its password if the server is reachable from other machines.

## Backups across versions

A backup records the lineage version that made it. Restoring a backup from another version asks for confirmation, because the data format may differ. Backups made by 0.1 restore fine into an account on 0.2: the format of a workspace did not change, only where it is stored.

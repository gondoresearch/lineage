# Command line

Accounts are managed with `python -m backend.manage`. It works on the data folder given by `DATA_DIR` (or `--data-dir`), like the server, and the running server picks up its changes immediately. See [Accounts](../hosting/accounts.md) for how it fits together.

=== "Docker"

    ```sh
    docker compose exec -it lineage python -m backend.manage <command>
    ```

=== "From source"

    ```sh
    DATA_DIR=./data .venv/bin/python -m backend.manage <command>
    ```

Exit status is `0` on success and `1` on an error (unknown user, invalid name, password too short…), with the reason on standard error.

The help texts below are generated from the code (`backend/manage.py`).

<!-- gen:cli -->

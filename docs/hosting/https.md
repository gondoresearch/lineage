# HTTPS and exposing it

lineage speaks plain HTTP. On your own machine that is fine: the Docker setup publishes it on `127.0.0.1:8080` only, and `make start` binds the backend to `127.0.0.1`. To use it from other machines, put a **reverse proxy that does HTTPS** in front of it, so that passwords and session cookies are never sent unencrypted.

## Checklist

1. Delete the demo account or change its password ([Accounts](accounts.md#the-demo-account)).
2. Put lineage behind an HTTPS reverse proxy (examples below).
3. Set `LINEAGE_SECURE_COOKIE=1`, so browsers send the login cookie over HTTPS only.
4. Keep the published port on `127.0.0.1` if the proxy runs on the same machine; otherwise publish `8080:8000` and make sure only the proxy can reach it.

## Caddy

Caddy gets and renews certificates by itself:

```caddy
lineage.example.org {
    reverse_proxy 127.0.0.1:8080
}
```

## nginx

```nginx
server {
    listen 443 ssl;
    server_name lineage.example.org;
    ssl_certificate     /etc/letsencrypt/live/lineage.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lineage.example.org/privkey.pem;

    client_max_body_size 60m;          # backup uploads (restore) can be up to 50 MB

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Things to know

- **Login throttling counts per address.** Behind a proxy, every request seems to come from the proxy, so throttling then applies per user name only. That is still effective against guessing one account's password.
- **Serve it at the root of a host name** (such as `lineage.example.org`), not under a path like `example.org/lineage/`: the app expects to live at `/`.
- **One worker only.** lineage serialises writes with a lock inside its single process; do not run several workers or replicas against the same data folder.
- What is and is not protected is described in the [security model](../internals/security.md).

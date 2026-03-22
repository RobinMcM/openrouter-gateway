# Deployment Rules: Models API Domain

This repository serves the models API on `models.rapidmvp.io`.

## Fixed Domain Mapping

- Primary public host: `models.rapidmvp.io`
- Droplet: `134.209.184.66`
- Legacy host `usageflows.info` is deprecated for this service.

## TLS Requirements

- HTTPS is mandatory for all public API traffic.
- Port 80 is only for ACME challenge and HTTP -> HTTPS redirect.
- Active certificate path must be:
  - `/etc/letsencrypt/live/models.rapidmvp.io/fullchain.pem`
  - `/etc/letsencrypt/live/models.rapidmvp.io/privkey.pem`
- Auto-renew must be enabled (`certbot renew` loop/container).

## Nginx Configuration Rules

- Use `nginx/conf.d/models.rapidmvp.io.conf` as the active SSL virtual host.
- Use `nginx/conf.d/models.rapidmvp.io-http-only.conf` only during initial certificate bootstrap.
- Do not reintroduce `usageflows.info` server blocks in this repo.

## Verification Gates Before Cutover

1. DNS resolves:
   - `dig +short models.rapidmvp.io` -> `134.209.184.66`
2. Health over HTTPS:
   - `curl -I https://models.rapidmvp.io/health` -> `200`
3. Auth endpoint over HTTPS:
   - `curl -H "X-Internal-API-Key: <KEY>" https://models.rapidmvp.io/api/instructions`
4. Canary pass:
   - execute + status + result flow succeeds.

## Client Configuration Rule

- MovieShaker `GATEWAY_BASE_URL` must use:
  - `https://models.rapidmvp.io`

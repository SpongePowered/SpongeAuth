#!/bin/sh
# Mount at /docker-entrypoint.d/40-trusted-proxies.sh in the official nginx image; its entrypoint runs it before nginx starts.
# Turns NGINX_TRUSTED_PROXIES (comma- or space-separated IPs/CIDRs) into set_real_ip_from directives for nginx.conf.
# Unset or empty trusts no proxy, so $remote_addr stays the proxy's own address.
set -eu

out=/run/nginx/trusted-proxies.conf
mkdir -p "${out%/*}"
: > "$out"

for cidr in $(echo "${NGINX_TRUSTED_PROXIES:-}" | tr ',' ' '); do
    case "$cidr" in
        *[!0-9a-fA-F.:/]*)
            echo "$0: invalid entry in NGINX_TRUSTED_PROXIES: $cidr" >&2
            exit 1
            ;;
    esac
    echo "set_real_ip_from $cidr;" >> "$out"
done

[ -s "$out" ] || echo "$0: NGINX_TRUSTED_PROXIES is empty, client IPs will be the proxy's" >&2

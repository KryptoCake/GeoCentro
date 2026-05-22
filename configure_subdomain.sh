#!/bin/bash
# Script to configure geocentro.grupopy.me subdomain in Coolify proxy

PROXY_DIR="/data/coolify/proxy"
DYNAMIC_DIR="$PROXY_DIR/dynamic"

if [ ! -d "$DYNAMIC_DIR" ]; then
    echo "Error: Coolify dynamic proxy directory not found at $DYNAMIC_DIR"
    exit 1
fi

# Detect Coolify proxy gateway IP
GATEWAY_IP=$(docker network inspect coolify --format='{{range .IPAM.Config}}{{.Gateway}}{{printf "\n"}}{{end}}' 2>/dev/null | head -n 1)
if [ -z "$GATEWAY_IP" ]; then
    GATEWAY_IP="10.0.1.1"
fi
echo "Using Gateway IP $GATEWAY_IP for routing"

echo "Adding Traefik configuration..."
cat << EOF > "$DYNAMIC_DIR/geocentro.yaml"
http:
  routers:
    geocentro-router:
      rule: "Host(\`geocentro.grupopy.me\`)"
      service: geocentro-service
      entryPoints:
        - https
      tls:
        certResolver: letsencrypt
  services:
    geocentro-service:
      loadBalancer:
        servers:
          - url: "http://$GATEWAY_IP:8082"
EOF
echo "Traefik config written to $DYNAMIC_DIR/geocentro.yaml"

echo "Adding Caddy configuration (overwriting Caddyfile)..."
CADDYFILE="$DYNAMIC_DIR/Caddyfile"
cat << EOF > "$CADDYFILE"
import /dynamic/*.caddy

geocentro.grupopy.me {
    reverse_proxy $GATEWAY_IP:8082
}
EOF
echo "Caddy config written to $CADDYFILE"

echo "Configuration completed successfully!"
echo "Please make sure to point your DNS A record for 'geocentro.grupopy.me' to this VPS IP address."

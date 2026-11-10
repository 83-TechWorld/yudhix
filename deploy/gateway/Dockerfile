# yudhix-gateway: nginx reverse proxy / API gateway (non-root).
#   docker build -t yudhix/gateway:local deploy/gateway
FROM nginxinc/nginx-unprivileged:1.27-alpine
ENV PORT=8080
COPY gateway.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 05-gateway.envsh /docker-entrypoint.d/05-gateway.envsh
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- "http://127.0.0.1:${PORT}/gateway/healthz" >/dev/null || exit 1

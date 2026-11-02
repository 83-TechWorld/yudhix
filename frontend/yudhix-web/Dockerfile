# yudhix-web: Angular app served by nginx (non-root).
#   docker build -t yudhix/web:local frontend/yudhix-web
# Runtime settings come from env vars -> /config.json: API_URL, KEYCLOAK_URL, KEYCLOAK_REALM,
# KEYCLOAK_CLIENT_ID, SALES_EMAIL. Leave the URLs empty when served behind the Yudhix gateway.
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx ng build --configuration production

FROM nginxinc/nginx-unprivileged:1.27-alpine
ENV PORT=8080
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d-yudhix.envsh /docker-entrypoint.d/05-yudhix.envsh
COPY --from=build /src/dist/yudhix-web/browser /usr/share/nginx/html
USER root
RUN chown -R nginx:nginx /usr/share/nginx/html && chmod +x /docker-entrypoint.d/05-yudhix.envsh
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- "http://127.0.0.1:${PORT}/healthz" >/dev/null || exit 1

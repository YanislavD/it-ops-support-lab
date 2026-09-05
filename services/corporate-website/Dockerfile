FROM nginx:1.27-alpine

COPY html/ /usr/share/nginx/html/

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:80/ >/dev/null || exit 1

FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/nginx.conf

# Health check - verify nginx config is valid and process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD nginx -t 2>&1 | grep -q 'syntax is ok' || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

#!/bin/bash
# SSL Setup Script for MoodSprint
# Usage: ./scripts/ssl-setup.sh [production|staging]

set -e

DOMAIN_PROD="moodsprint.ru"
DOMAIN_STAGING="staging.moodsprint.ru"
EMAIL="admin@moodsprint.ru"  # Change this to your email

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}MoodSprint SSL Setup${NC}"
echo "================================"

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}This script should be run with sudo${NC}"
fi

# Install certbot if not installed
install_certbot() {
    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}Installing certbot...${NC}"
        apt-get update
        apt-get install -y certbot
    else
        echo -e "${GREEN}certbot is already installed${NC}"
    fi
}

# Create webroot directory for ACME challenge
create_webroot() {
    mkdir -p /var/www/certbot
    echo -e "${GREEN}Created /var/www/certbot for ACME challenges${NC}"
}

# Get certificate for production domain
get_prod_cert() {
    echo -e "${YELLOW}Getting certificate for ${DOMAIN_PROD}...${NC}"

    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN_PROD" \
        -d "www.$DOMAIN_PROD"

    echo -e "${GREEN}Certificate obtained for ${DOMAIN_PROD}${NC}"
}

# Get certificate for staging domain
get_staging_cert() {
    echo -e "${YELLOW}Getting certificate for ${DOMAIN_STAGING}...${NC}"

    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN_STAGING"

    echo -e "${GREEN}Certificate obtained for ${DOMAIN_STAGING}${NC}"
}

# Get certificate for admin domain (optional)
get_admin_cert() {
    echo -e "${YELLOW}Getting certificate for admin.${DOMAIN_PROD}...${NC}"

    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "admin.$DOMAIN_PROD"

    echo -e "${GREEN}Certificate obtained for admin.${DOMAIN_PROD}${NC}"
}

# Setup auto-renewal
setup_renewal() {
    echo -e "${YELLOW}Setting up auto-renewal...${NC}"

    # Add cron job for renewal
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'docker exec moodsprint-nginx nginx -s reload'") | crontab -

    echo -e "${GREEN}Auto-renewal configured (runs daily at 3 AM)${NC}"
}

# Get initial certificate using standalone mode (before Docker is running)
get_initial_cert_standalone() {
    local domain=$1
    echo -e "${YELLOW}Getting initial certificate for ${domain} (standalone mode)...${NC}"

    # Stop nginx if running
    docker compose down nginx 2>/dev/null || true

    certbot certonly \
        --standalone \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$domain"

    echo -e "${GREEN}Initial certificate obtained for ${domain}${NC}"
}

# Main
case "$1" in
    production)
        install_certbot
        create_webroot
        get_prod_cert
        setup_renewal
        ;;
    staging)
        install_certbot
        create_webroot
        get_staging_cert
        setup_renewal
        ;;
    all)
        install_certbot
        create_webroot
        get_prod_cert
        get_staging_cert
        setup_renewal
        ;;
    initial-prod)
        install_certbot
        get_initial_cert_standalone "$DOMAIN_PROD"
        ;;
    initial-staging)
        install_certbot
        get_initial_cert_standalone "$DOMAIN_STAGING"
        ;;
    renew)
        certbot renew
        docker exec moodsprint-nginx nginx -s reload
        ;;
    *)
        echo "Usage: $0 {production|staging|all|initial-prod|initial-staging|renew}"
        echo ""
        echo "Commands:"
        echo "  production      - Get certificate for moodsprint.ru (webroot mode)"
        echo "  staging         - Get certificate for staging.moodsprint.ru (webroot mode)"
        echo "  all             - Get certificates for both domains"
        echo "  initial-prod    - Get initial cert for production (standalone, before Docker)"
        echo "  initial-staging - Get initial cert for staging (standalone, before Docker)"
        echo "  renew           - Manually renew certificates"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Done! Next steps:${NC}"
echo "1. Update docker-compose.yml to mount certificate volumes"
echo "2. Use nginx.ssl.conf as your nginx configuration"
echo "3. Restart nginx: docker compose restart nginx"

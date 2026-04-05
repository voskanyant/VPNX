FROM wordpress:6.8.1-php8.2-apache

RUN apt-get update \
    && apt-get install -y --no-install-recommends libzip-dev unzip zip \
    && docker-php-ext-install zip \
    && rm -rf /var/lib/apt/lists/*

COPY php.ini /usr/local/etc/php/conf.d/uploads.ini

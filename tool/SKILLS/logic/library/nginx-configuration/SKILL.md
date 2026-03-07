---
name: nginx-configuration
description: Nginx configuration patterns for web servers and reverse proxies. Use when working with nginx configuration concepts or setting up related projects.
---

# Nginx Configuration

## Core Patterns

### Reverse Proxy
```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/TLS (Let's Encrypt)
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
}
```

### Static Files with Cache
```nginx
location /static/ {
    root /var/www;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### Load Balancing
```nginx
upstream backend {
    server 10.0.0.1:3000 weight=3;
    server 10.0.0.2:3000;
}
```

## Performance Tips
- Enable gzip compression
- Use `worker_connections 1024` or higher
- Set `keepalive_timeout 65`
- Use `proxy_cache` for response caching

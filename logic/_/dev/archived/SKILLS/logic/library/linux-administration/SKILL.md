---
name: linux-administration
description: Linux server administration essentials. Use when working with linux administration concepts or setting up related projects.
---

# Linux Administration

## Essential Commands

### Process Management
```bash
ps aux | grep nginx         # Find process
top / htop                  # Interactive process viewer
kill -SIGTERM <pid>         # Graceful stop
systemctl status nginx      # Service status
journalctl -u nginx -f      # Follow service logs
```

### Disk & Memory
```bash
df -h                       # Disk usage
du -sh /var/log/*           # Directory sizes
free -h                     # Memory usage
lsof +D /var/log            # Files open in directory
```

### Networking
```bash
ss -tlnp                    # Listening ports
curl -v https://example.com # Verbose HTTP request
dig example.com             # DNS lookup
iptables -L -n              # Firewall rules
```

## File Permissions
```
chmod 644 file.txt   # rw-r--r-- (owner read/write, others read)
chmod 755 script.sh  # rwxr-xr-x (owner all, others read/execute)
chown user:group file
```

## Security Hardening
- Disable root SSH login; use key-based auth
- Keep packages updated (`unattended-upgrades`)
- Configure firewall (ufw/iptables) to allow only needed ports
- Use fail2ban for brute-force protection

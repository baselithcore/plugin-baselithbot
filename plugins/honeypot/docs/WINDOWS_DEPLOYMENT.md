# Windows Server Honeypot - Quick Deployment Guide

## Opzione 1: Single Windows Instance (Sostituisce Linux)

Modifica `.env.prod`:

```bash
# Cambia solo questa riga:
HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=windows_server

# Opzionale: personalizza nome server Windows
HONEYPOT_SSH_SERVER_NAME=WIN-SRV-2022-DC01
HONEYPOT_SSH_BANNER=SSH-2.0-OpenSSH_for_Windows_8.9
```

Poi restart del servizio.

---

## Opzione 2: Multi-OS Deployment (Consigliato)

Deploy simultaneo di Linux + Windows honeypots su porte diverse.

### Configurazione Docker Compose

Aggiungi a `docker-compose.yml`:

```yaml
services:
  # Honeypot Linux esistente (porta 2222)
  honeypot:
    # ... configurazione esistente ...
    environment:
      - HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=linux_ubuntu
      - HONEYPOT_SSH_PORT=2222
    ports:
      - "2222:2222"
  
  # Nuovo: Windows Server Honeypot
  honeypot-windows:
    image: your-honeypot-image  # Stessa immagine, config diversa
    container_name: honeypot_windows
    environment:
      # Eredita da .env.prod, override per Windows
      - HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=windows_server
      - HONEYPOT_SSH_PORT=3390
      - HONEYPOT_SSH_SERVER_NAME=WIN-SRV-2022-DC01
      - HONEYPOT_SSH_BANNER=SSH-2.0-OpenSSH_for_Windows_8.9
      
      # Stesse credenziali ML e Cluster
      - HONEYPOT_ML_ENABLED=true
      - HONEYPOT_CLUSTER_ENABLED=true
      - HONEYPOT_CLUSTER_REDIS_URL=redis://falkordb:6379/0
      
    ports:
      - "3390:3390"  # Porta Windows SSH
    networks:
      - ai_net
    depends_on:
      - falkordb
      - postgres_db
```

### Port Forwarding su Firewall

```bash
# Linux honeypot
iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222

# Windows honeypot
iptables -t nat -A PREROUTING -p tcp --dport 3389 -j REDIRECT --to-port 3390
# ^ Nota: 3389 è RDP standard, attrarrà attacchi Windows-specific
```

---

## Verifica Windows Honeypot

Test rapido:

```bash
# Connetti localmente
ssh -p 3390 root@localhost

# Testa comandi Windows
whoami              # → WIN-SRV-2022-DC01\Administrator
systeminfo          # → Microsoft Windows [Version 10.0.20348.2322]
dir C:\             # → Lista directory Windows-style
```

---

## Features Abilitate per Windows

✅ **OS Fingerprinting accurato**:

- TCP TTL: 128 (Windows signature vs Linux 64)
- SSH Banner: OpenSSH_for_Windows_8.9
- Latency pattern Windows-like (leggermente più lento di Linux)

✅ **Command emulation Windows-native**:

- `dir` invece di `ls`
- `systeminfo` invece di `uname`
- PowerShell-style output

✅ **ML & Cluster**:

- Stesso baseline model (funziona cross-OS)
- State sync su FalkorDB condiviso
- TTP detection compatibile

---

## Best Practice Multi-OS

1. **Port Assignment**:
   - Linux Ubuntu: 2222 (redirect da 22)
   - Windows Server: 3390 (redirect da 3389 RDP)
   - Linux CentOS: 2223 (opzionale)

2. **Naming Convention**:
   - Linux: `ubuntu-server`, `centos-stream-9`
   - Windows: `WIN-SRV-2022-DC01`, `WIN-SRV-2019-WEB`

3. **Monitoring**:
   - Cluster sync permette di tracciare lateral movement Windows → Linux
   - Dashboard mostra quale OS profile attira più attacchi

---

## Quick Start

```bash
# 1. Aggiungi servizio Windows a docker-compose.yml
# 2. Deploy
docker-compose up -d honeypot-windows

# 3. Verifica logs
docker logs -f honeypot_windows

# Dovresti vedere:
# "ADS enabled with profile: windows_server"
# "ML prediction enabled"
# "Connected to cluster"
```

**Il honeypot Windows è pronto! 🪟**

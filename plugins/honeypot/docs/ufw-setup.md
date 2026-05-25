# Guida alla Configurazione Sicura del Firewall (DNAT)

Questa guida spiega come configurare il firewall per ospitare in sicurezza gli honeypot, utilizzando la strategia **Secure DNAT** che aggira le limitazioni di sicurezza di Docker.

## 1. Architettura di Sicurezza

Invece di esporre direttamente le porte via Docker (che bypassa UFW/Firewall Host e usa il Docker Proxy Userland), utilizziamo:

1. **IP Statici** per i container honeypot (`10.254.254.x`).
2. **IPTables DNAT** per inoltrare il traffico dalla porta Host -> IP Container.
3. **Forwarding Rules** esplicite per loggare e accettare il traffico.

Questo garantisce che:

- Il firewall dell'host (UFW/IPTables) veda l'IP reale dell'attaccante.
- Docker non apra porte arbitrariamente.
- Si possa usare `LOG` e `DROP` prima che il pacchetto raggiunga il container.

---

## 2. Configurazione Automatica (`honeypot_firewall.sh`)

Lo script `scripts/honeypot_firewall.sh` è l'UNICO metodo supportato per esporre le porte.

### Sincronizzazione Automatica

Per applicare le regole per tutti gli honeypot configurati nei file YAML:

```bash
sudo ./scripts/honeypot_firewall.sh sync
```

Questo comando:

1. Legge la configurazione in `plugins.yaml` e `honeypots/*.yaml`.
2. Rileva dinamicamente l'IP del container `baselith-core-honeypot`.
3. Applica le regole DNAT + FORWARD + UFW per ogni porta attiva.

### Forward Manuale

Per esporre una porta specifica manualmente (es. test):

```bash
# Sintassi: forward <porta> [ip_container] [descrizione]
# Se l'IP è omesso, viene rilevato automaticamente.

sudo ./scripts/honeypot_firewall.sh forward 5678
# Oppure esplicito:
sudo ./scripts/honeypot_firewall.sh forward 5678 172.18.0.2 "N8N Vulnerable"
```

### Rimozione Regole

```bash
sudo ./scripts/honeypot_firewall.sh remove 5678
```

---

## 3. Gestione UFW

Se usi UFW sull'host, lo script gestirà automaticamente **tutto**:

1. Apre la porta in ingresso (`ufw allow <port>`) per permettere il traffico Host.
2. Abilita il routing verso il container (`ufw route allow ...`).

Puoi verificare lo stato con:

```bash
sudo ufw status numbered
```

> [!NOTE]
> Non modificare manualmente le regole UFW per gli honeypot. Usa sempre `honeypot_firewall.sh sync` per garantire coerenza tra DNAT, IPTables e UFW.

---

## 4. Verifica e Troubleshooting

### Controllare se le regole sono attive

```bash
# Tabella NAT (dovresti vedere DNAT)
sudo iptables -t nat -L PREROUTING -n

# Tabella Filter (dovresti vedere LOG e ACCEPT nella catena FORWARD)
sudo iptables -L FORWARD -n | grep HONEYPOT
```

### Vedere i Log degli Attacchi

```bash
sudo journalctl -kf | grep HONEYPOT
```

### Test di Connessione

Da un host esterno (o via `nc` sull'IP pubblico):

```bash
nc -zv <TUO_IP_PUBBLICO> 2222
```

Dovrebbe connettersi e generare un log in `journalctl`.

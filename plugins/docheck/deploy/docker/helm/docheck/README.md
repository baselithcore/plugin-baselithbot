# doCheck Helm Chart

Deploy on-prem o VPC isolata. Multi-tenant ready (gated F5+).

## Install

```bash
helm install docheck ./docker/helm/docheck \
  --namespace docheck --create-namespace \
  --values custom-values.yaml
```

## Values key

| Key | Default | Description |
|-----|---------|-------------|
| `engine.replicas` | 1 | Engine pods (StatefulSet) |
| `engine.persistence.size` | 50Gi | Volume per `/data` (DB + chunks + traces) |
| `vllm.enabled` | true | Deploy vLLM intra-cluster (richiede GPU) |
| `multiTenant.enabled` | false | Switch Postgres + Qdrant + OIDC |
| `networkPolicy.enabled` | true | NetworkPolicy egress lockdown |
| `audit.signingKeySecret` | docheck-audit-signing-key | K8s Secret con Ed25519 master key |

## Pre-install

Genera signing key Ed25519 e salva in Secret:

```bash
python -c "from nacl.signing import SigningKey; \
  open('audit.key','wb').write(SigningKey.generate().encode())"
kubectl create secret generic docheck-audit-signing-key \
  --from-file=audit.key --namespace docheck
```

## Multi-tenant activation (F5+)

```yaml
multiTenant:
  enabled: true
  postgres:
    host: postgres.example.local
    secretRef: docheck-postgres-credentials
  qdrant:
    host: qdrant.example.local
  oidc:
    issuer: https://keycloak.example.local/realms/docheck
    clientId: docheck-engine
```

## Egress validation

```bash
kubectl exec -n docheck docheck-engine-0 -- \
  apt-get install -y tcpdump && \
  kubectl exec -n docheck docheck-engine-0 -- \
  timeout 60 tcpdump -nn 'not (host 127.0.0.1 or host docheck-vllm)'
```

Zero pacchetti durante analisi = goal raggiunto.

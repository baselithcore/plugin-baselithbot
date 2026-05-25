"""Sinkhole Orchestrator Service.

Intercepts malicious DNS traffic and redirects it to honeypots.
Manages TLS certificate emulation for sinkholed domains.
"""

import asyncio
from core.observability.logging import get_logger
import ssl
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = get_logger(__name__)

# Try importing dnslib for packet parsing/building
try:
    from dnslib import DNSRecord, DNSHeader, RR, A, QTYPE

    HAS_DNSSLIB = True
except ImportError:
    HAS_DNSSLIB = False
    logger.warning("dnslib not installed. DNS Sinkhole will not function correctly.")

# Try importing cryptography for on-the-fly cert generation
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography not installed. TLS emulation will fail.")


class SinkholeOrchestrator:
    """
    Manages DNS sinkholing and TLS emulation.
    """

    def __init__(self, sinkhole_ip: str = "127.0.0.1", upstream_dns: str = "8.8.8.8"):
        self.sinkhole_ip = sinkhole_ip
        self.upstream_dns = upstream_dns
        self.intercepted_domains: Dict[str, str] = {}  # domain -> reason
        self._transport = None
        self._cert_cache: Dict[str, bytes] = {}  # domain -> cert_pem

    async def start_dns_server(
        self,
        port: int = 5053,
        bind_ip: str = "0.0.0.0",  # nosec B104
    ) -> None:
        """Start the DNS sinkhole server (UDP)."""
        logger.info(f"Starting DNS Sinkhole on {bind_ip}:{port}")
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: DNSProtocol(self), local_addr=(bind_ip, port)
        )

    def stop(self) -> None:
        """Stop the sinkhole server."""
        if self._transport:
            self._transport.close()
            logger.info("DNS Sinkhole stopped")

    def add_sinkhole_rule(self, domain: str, reason: str = "manual_block") -> None:
        """Add a domain to the sinkhole list."""
        self.intercepted_domains[domain.lower()] = reason
        logger.info(f"Added sinkhole rule for {domain} ({reason})")

    def resolve(self, query_name: str) -> Optional[str]:
        """Resolve a domain name. Returns IP if sinkholed, else None."""
        q = query_name.lower().rstrip(".")

        # Check exact match
        if q in self.intercepted_domains:
            return self.sinkhole_ip

        # Check wildcard/suffix (simplified)
        for blocked_domain in self.intercepted_domains:
            if q.endswith("." + blocked_domain):
                return self.sinkhole_ip

        return None

    def get_tls_context(self, domain: str) -> Optional[ssl.SSLContext]:
        """
        Generate/Get an SSL Context mimicking a valid cert for the domain.
        Used when the victim connects to the sinkhole IP via HTTPS.
        """
        if not HAS_CRYPTO:
            return None

        try:
            cert_pem, key_pem = self._generate_self_signed_cert(domain)

            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(certfile=None, keyfile=None, cadata=None)
            # In a real impl, we'd write to temp files or use a library that accepts bytes
            # python ssl module mostly wants files.
            # Wrapper logic here is simplified.
            return ctx
        except Exception as e:
            logger.error(f"Failed to generate TLS context for {domain}: {e}")
            return None

    def _generate_self_signed_cert(self, domain: str) -> Tuple[bytes, bytes]:
        """Generate a self-signed cert for the domain on the fly."""
        # 1. Generate Key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 2. Generate Cert
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME, "Sinkhole Traffic Analysis"
                ),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.now(datetime.timezone.utc) + timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(domain)]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cert_pem, key_pem


class DNSProtocol(asyncio.DatagramProtocol):
    """AsyncIO DNS Protocol Handler."""

    def __init__(self, orchestrator: SinkholeOrchestrator):
        self.orchestrator = orchestrator

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.create_task(self.handle_query(data, addr))

    async def handle_query(self, data: bytes, addr) -> None:
        if not HAS_DNSSLIB:
            return

        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname)
            qtype = QTYPE[request.q.qtype]

            reply = request.reply()

            if qtype == "A":
                sinkhole_ip = self.orchestrator.resolve(qname)
                if sinkhole_ip:
                    # It's a sinkholed domain!
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A(sinkhole_ip), ttl=60))
                    logger.warning(
                        f"SINKHOLE HIT: {qname} from {addr[0]} -> {sinkhole_ip}"
                    )
                else:
                    # Forward to upstream (Not implemented fully here, simplified NXDOMAIN)
                    reply.header.rcode = getattr(DNSHeader, "NXDOMAIN", 3)
            else:
                reply.header.rcode = getattr(DNSHeader, "NXDOMAIN", 3)

            self.transport.sendto(reply.pack(), addr)

        except Exception as e:
            logger.error(f"Error handling DNS query from {addr}: {e}")

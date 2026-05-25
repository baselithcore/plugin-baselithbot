"""JA4+ Fingerprinting Service.

Implements JA4, JA4H, and JA4SSH fingerprinting generation logic.
"""

import hashlib
from core.observability.logging import get_logger
from typing import List

logger = get_logger(__name__)


class JA4Fingerprinter:
    """Generates JA4+ fingerprints from raw protocol data."""

    @staticmethod
    def generate_ja4(
        protocol: str = "TCP",
        version: str = "00",
        ciphers: List[str] = None,
        extensions: List[str] = None,
        algos: List[str] = None,
    ) -> str:
        """
        Generate JA4 TLS fingerprint.
        Format: JA4_a_b_c
        a: TLS Version, SNI, ALPN, Extension count, Cipher count
        b: Sorted Ciphers Hash
        c: Sorted Extensions Hash
        """
        if not ciphers:
            ciphers = []
        if not extensions:
            extensions = []
        if not algos:
            algos = []

        # Part A Construction (Simplified simulation as we might not have raw packets here)
        # Real impl would parse ClientHello
        # For this template we assume 'version' is e.g. "13" (TLS 1.3) or "12" (TLS 1.2)
        # protocol is "t" (tcp) or "q" (quic)

        proto_char = "q" if protocol.lower() == "quic" else "t"

        # SNI (d = domain, i = ip) - heuristic
        sni_char = "d"

        ciphers_len = len(ciphers)
        ext_len = len(extensions)

        # Format: 2 chars metric (e.g. 13), sni (d/i), 2 chars ciphers, 2 chars ext, 1 char algo (if any)
        # Standard JA4: t13d1516h2
        # t = protocol
        # 13 = TLS 1.3
        # d = SNI present
        # 15 = 15 ciphers
        # 16 = 16 extensions
        # alpn = 00 (no alpn) -> mapped later

        # Simplified Part A for simulation/demo if we don't have full pcap
        part_a = f"{proto_char}{version}{sni_char}{ciphers_len:02}{ext_len:02}"

        # Part B: SHA256 of sorted ciphers (truncated)
        ciphers_str = ",".join(sorted(ciphers))
        part_b = hashlib.sha256(ciphers_str.encode()).hexdigest()[:12]

        # Part C: SHA256 of sorted extensions (truncated)
        ext_str = ",".join(sorted(extensions))
        part_c = hashlib.sha256(ext_str.encode()).hexdigest()[:12]

        return f"{part_a}_{part_b}_{part_c}"

    @staticmethod
    def generate_ja4h(
        method: str,
        version: str,
        cookies: bool,
        headers: List[str],
        language: str = "00",
    ) -> str:
        """
        Generate JA4H HTTP fingerprint.
        Format: JA4H_a_b_c_d
        """
        # Canonicalize
        method = method.upper()[:2]
        version = version.replace(".", "")[:2]
        cookie_char = "c" if cookies else "n"

        # Part A: method, version, cookie, header count
        part_a = f"{method}{version}{cookie_char}{len(headers):02}"

        # Part B: Header Hash (headers content is NOT hashed, only names in order)
        # JA4H standard uses header names order as they appear, not sorted.
        # But we must be consistent.
        headers_str = ",".join([h.lower() for h in headers])
        part_b = hashlib.sha256(headers_str.encode()).hexdigest()[:12]

        return f"{part_a}_{part_b}_{language}_00"  # Simplified C/D

    @staticmethod
    def generate_ja4ssh(
        client_kex: List[str],
        client_shk: List[str],
        client_enc: List[str],
        client_mac: List[str],
        client_com: List[str],
    ) -> str:
        """Generate JA4SSH fingerprint."""
        raw_str = f"{client_kex}{client_shk}{client_enc}{client_mac}{client_com}"
        return hashlib.sha256(raw_str.encode()).hexdigest()[:32]

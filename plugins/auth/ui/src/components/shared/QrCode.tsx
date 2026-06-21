/**
 * QR code image with a server fast-path and a client-side fallback.
 *
 * The backend renders the TOTP QR as a base64 PNG (`qr_code`) only when the
 * optional `qrcode`/`Pillow` Python deps are present — slim deployments ship
 * without them, so `qr_code` arrives `null` and only the manual secret shows.
 * To make the image always render, this component prefers the server PNG when
 * available and otherwise generates the QR in the browser from the
 * `otpauth://` provisioning URI. No secret ever leaves the page.
 */

import { useEffect, useState } from 'react';
import QRCode from 'qrcode';

interface Props {
  /** Server-rendered PNG data URI; used as-is when present. */
  src?: string | null;
  /** otpauth:// provisioning URI; used to generate the QR client-side. */
  value: string;
  alt: string;
  className?: string;
}

const QrCode = ({ src, value, alt, className }: Props) => {
  const [generated, setGenerated] = useState<string | null>(null);

  useEffect(() => {
    // Server already gave us an image — nothing to do.
    if (src || !value) return;
    let cancelled = false;
    QRCode.toDataURL(value, { errorCorrectionLevel: 'M', margin: 2, width: 220 })
      .then((url: string) => {
        if (!cancelled) setGenerated(url);
      })
      .catch(() => {
        if (!cancelled) setGenerated(null);
      });
    return () => {
      cancelled = true;
    };
  }, [src, value]);

  const resolved = src || generated;
  if (!resolved) return null;
  return <img className={className} src={resolved} alt={alt} />;
};

export default QrCode;

/**
 * @license
 * Copyright 2010-2026 Three.js Authors
 * SPDX-License-Identifier: MIT
 */ const Ba = '183',
  Hg = { ROTATE: 0, DOLLY: 1, PAN: 2 },
  kg = { ROTATE: 0, PAN: 1, DOLLY_PAN: 2, DOLLY_ROTATE: 3 },
  Tc = 0,
  ho = 1,
  Ac = 2,
  Wg = 0,
  Ns = 1,
  wc = 2,
  Oi = 3,
  Un = 0,
  Pe = 1,
  gn = 2,
  vn = 0,
  vi = 1,
  uo = 2,
  fo = 3,
  po = 4,
  Rc = 5,
  Xg = 6,
  Wn = 100,
  Cc = 101,
  Pc = 102,
  Lc = 103,
  Dc = 104,
  Ic = 200,
  Uc = 201,
  Nc = 202,
  Fc = 203,
  Gr = 204,
  Hr = 205,
  Oc = 206,
  Bc = 207,
  zc = 208,
  Vc = 209,
  Gc = 210,
  Hc = 211,
  kc = 212,
  Wc = 213,
  Xc = 214,
  kr = 0,
  Wr = 1,
  Xr = 2,
  Si = 3,
  qr = 4,
  Yr = 5,
  Zr = 6,
  Jr = 7,
  Zs = 0,
  qc = 1,
  Yc = 2,
  nn = 0,
  yl = 1,
  El = 2,
  bl = 3,
  Tl = 4,
  Al = 5,
  wl = 6,
  Rl = 7,
  Cl = 300,
  Jn = 301,
  yi = 302,
  ir = 303,
  sr = 304,
  Js = 306,
  $r = 1e3,
  xn = 1001,
  Kr = 1002,
  me = 1003,
  Zc = 1004,
  is = 1005,
  Ae = 1006,
  rr = 1007,
  qn = 1008,
  qg = 1008,
  Oe = 1009,
  Pl = 1010,
  Ll = 1011,
  Wi = 1012,
  za = 1013,
  an = 1014,
  en = 1015,
  Sn = 1016,
  Va = 1017,
  Ga = 1018,
  Xi = 1020,
  Dl = 35902,
  Il = 35899,
  Ul = 1021,
  Nl = 1022,
  Ye = 1023,
  yn = 1026,
  Yn = 1027,
  Fl = 1028,
  Ha = 1029,
  Ei = 1030,
  ka = 1031,
  Yg = 1032,
  Wa = 1033,
  Fs = 33776,
  Os = 33777,
  Bs = 33778,
  zs = 33779,
  jr = 35840,
  Qr = 35841,
  ta = 35842,
  ea = 35843,
  na = 36196,
  ia = 37492,
  sa = 37496,
  ra = 37488,
  aa = 37489,
  oa = 37490,
  la = 37491,
  ca = 37808,
  ha = 37809,
  ua = 37810,
  fa = 37811,
  da = 37812,
  pa = 37813,
  ma = 37814,
  ga = 37815,
  _a = 37816,
  xa = 37817,
  va = 37818,
  Ma = 37819,
  Sa = 37820,
  ya = 37821,
  Ea = 36492,
  ba = 36494,
  Ta = 36495,
  Aa = 36283,
  wa = 36284,
  Ra = 36285,
  Ca = 36286,
  Zg = 0,
  Jg = 1,
  $g = 2,
  Jc = 3200,
  Kn = 0,
  $c = 1,
  Dn = '',
  Ve = 'srgb',
  bi = 'srgb-linear',
  Hs = 'linear',
  te = 'srgb',
  Kg = '',
  jg = 'rg',
  Qg = 'ga',
  t0 = 0,
  ni = 7680,
  e0 = 7681,
  n0 = 7682,
  i0 = 7683,
  s0 = 34055,
  r0 = 34056,
  a0 = 5386,
  o0 = 512,
  l0 = 513,
  c0 = 514,
  h0 = 515,
  u0 = 516,
  f0 = 517,
  d0 = 518,
  mo = 519,
  Kc = 512,
  jc = 513,
  Qc = 514,
  Xa = 515,
  th = 516,
  eh = 517,
  qa = 518,
  nh = 519,
  Pa = 35044,
  p0 = 35048,
  go = '300 es',
  Ze = 2e3,
  qi = 2001,
  m0 = { COMPUTE: 'compute', RENDER: 'render' },
  g0 = { TEXTURE_COMPARE: 'depthTextureCompare' };
function ih(i) {
  for (let t = i.length - 1; t >= 0; --t) if (i[t] >= 65535) return !0;
  return !1;
}
function _0(i) {
  return ArrayBuffer.isView(i) && !(i instanceof DataView);
}
function Yi(i) {
  return document.createElementNS('http://www.w3.org/1999/xhtml', i);
}
function sh() {
  const i = Yi('canvas');
  return ((i.style.display = 'block'), i);
}
const _o = {};
function ks(...i) {
  const t = 'THREE.' + i.shift();
  console.log(t, ...i);
}
function Ol(i) {
  const t = i[0];
  if (typeof t == 'string' && t.startsWith('TSL:')) {
    const e = i[1];
    e && e.isStackTrace
      ? (i[0] += ' ' + e.getLocation())
      : (i[1] =
          'Stack trace not available. Enable "THREE.Node.captureStackTrace" to capture stack traces.');
  }
  return i;
}
function Ft(...i) {
  i = Ol(i);
  const t = 'THREE.' + i.shift();
  {
    const e = i[0];
    e && e.isStackTrace ? console.warn(e.getError(t)) : console.warn(t, ...i);
  }
}
function Jt(...i) {
  i = Ol(i);
  const t = 'THREE.' + i.shift();
  {
    const e = i[0];
    e && e.isStackTrace ? console.error(e.getError(t)) : console.error(t, ...i);
  }
}
function Ws(...i) {
  const t = i.join(' ');
  t in _o || ((_o[t] = !0), Ft(...i));
}
function rh(i, t, e) {
  return new Promise(function (n, s) {
    function r() {
      switch (i.clientWaitSync(t, i.SYNC_FLUSH_COMMANDS_BIT, 0)) {
        case i.WAIT_FAILED:
          s();
          break;
        case i.TIMEOUT_EXPIRED:
          setTimeout(r, e);
          break;
        default:
          n();
      }
    }
    setTimeout(r, e);
  });
}
const ah = { [kr]: Wr, [Xr]: Zr, [qr]: Jr, [Si]: Yr, [Wr]: kr, [Zr]: Xr, [Jr]: qr, [Yr]: Si };
class jn {
  addEventListener(t, e) {
    this._listeners === void 0 && (this._listeners = {});
    const n = this._listeners;
    (n[t] === void 0 && (n[t] = []), n[t].indexOf(e) === -1 && n[t].push(e));
  }
  hasEventListener(t, e) {
    const n = this._listeners;
    return n === void 0 ? !1 : n[t] !== void 0 && n[t].indexOf(e) !== -1;
  }
  removeEventListener(t, e) {
    const n = this._listeners;
    if (n === void 0) return;
    const s = n[t];
    if (s !== void 0) {
      const r = s.indexOf(e);
      r !== -1 && s.splice(r, 1);
    }
  }
  dispatchEvent(t) {
    const e = this._listeners;
    if (e === void 0) return;
    const n = e[t.type];
    if (n !== void 0) {
      t.target = this;
      const s = n.slice(0);
      for (let r = 0, a = s.length; r < a; r++) s[r].call(this, t);
      t.target = null;
    }
  }
}
const be = [
  '00',
  '01',
  '02',
  '03',
  '04',
  '05',
  '06',
  '07',
  '08',
  '09',
  '0a',
  '0b',
  '0c',
  '0d',
  '0e',
  '0f',
  '10',
  '11',
  '12',
  '13',
  '14',
  '15',
  '16',
  '17',
  '18',
  '19',
  '1a',
  '1b',
  '1c',
  '1d',
  '1e',
  '1f',
  '20',
  '21',
  '22',
  '23',
  '24',
  '25',
  '26',
  '27',
  '28',
  '29',
  '2a',
  '2b',
  '2c',
  '2d',
  '2e',
  '2f',
  '30',
  '31',
  '32',
  '33',
  '34',
  '35',
  '36',
  '37',
  '38',
  '39',
  '3a',
  '3b',
  '3c',
  '3d',
  '3e',
  '3f',
  '40',
  '41',
  '42',
  '43',
  '44',
  '45',
  '46',
  '47',
  '48',
  '49',
  '4a',
  '4b',
  '4c',
  '4d',
  '4e',
  '4f',
  '50',
  '51',
  '52',
  '53',
  '54',
  '55',
  '56',
  '57',
  '58',
  '59',
  '5a',
  '5b',
  '5c',
  '5d',
  '5e',
  '5f',
  '60',
  '61',
  '62',
  '63',
  '64',
  '65',
  '66',
  '67',
  '68',
  '69',
  '6a',
  '6b',
  '6c',
  '6d',
  '6e',
  '6f',
  '70',
  '71',
  '72',
  '73',
  '74',
  '75',
  '76',
  '77',
  '78',
  '79',
  '7a',
  '7b',
  '7c',
  '7d',
  '7e',
  '7f',
  '80',
  '81',
  '82',
  '83',
  '84',
  '85',
  '86',
  '87',
  '88',
  '89',
  '8a',
  '8b',
  '8c',
  '8d',
  '8e',
  '8f',
  '90',
  '91',
  '92',
  '93',
  '94',
  '95',
  '96',
  '97',
  '98',
  '99',
  '9a',
  '9b',
  '9c',
  '9d',
  '9e',
  '9f',
  'a0',
  'a1',
  'a2',
  'a3',
  'a4',
  'a5',
  'a6',
  'a7',
  'a8',
  'a9',
  'aa',
  'ab',
  'ac',
  'ad',
  'ae',
  'af',
  'b0',
  'b1',
  'b2',
  'b3',
  'b4',
  'b5',
  'b6',
  'b7',
  'b8',
  'b9',
  'ba',
  'bb',
  'bc',
  'bd',
  'be',
  'bf',
  'c0',
  'c1',
  'c2',
  'c3',
  'c4',
  'c5',
  'c6',
  'c7',
  'c8',
  'c9',
  'ca',
  'cb',
  'cc',
  'cd',
  'ce',
  'cf',
  'd0',
  'd1',
  'd2',
  'd3',
  'd4',
  'd5',
  'd6',
  'd7',
  'd8',
  'd9',
  'da',
  'db',
  'dc',
  'dd',
  'de',
  'df',
  'e0',
  'e1',
  'e2',
  'e3',
  'e4',
  'e5',
  'e6',
  'e7',
  'e8',
  'e9',
  'ea',
  'eb',
  'ec',
  'ed',
  'ee',
  'ef',
  'f0',
  'f1',
  'f2',
  'f3',
  'f4',
  'f5',
  'f6',
  'f7',
  'f8',
  'f9',
  'fa',
  'fb',
  'fc',
  'fd',
  'fe',
  'ff',
];
let xo = 1234567;
const Vi = Math.PI / 180,
  Ti = 180 / Math.PI;
function sn() {
  const i = (Math.random() * 4294967295) | 0,
    t = (Math.random() * 4294967295) | 0,
    e = (Math.random() * 4294967295) | 0,
    n = (Math.random() * 4294967295) | 0;
  return (
    be[i & 255] +
    be[(i >> 8) & 255] +
    be[(i >> 16) & 255] +
    be[(i >> 24) & 255] +
    '-' +
    be[t & 255] +
    be[(t >> 8) & 255] +
    '-' +
    be[((t >> 16) & 15) | 64] +
    be[(t >> 24) & 255] +
    '-' +
    be[(e & 63) | 128] +
    be[(e >> 8) & 255] +
    '-' +
    be[(e >> 16) & 255] +
    be[(e >> 24) & 255] +
    be[n & 255] +
    be[(n >> 8) & 255] +
    be[(n >> 16) & 255] +
    be[(n >> 24) & 255]
  ).toLowerCase();
}
function Bt(i, t, e) {
  return Math.max(t, Math.min(e, i));
}
function Ya(i, t) {
  return ((i % t) + t) % t;
}
function oh(i, t, e, n, s) {
  return n + ((i - t) * (s - n)) / (e - t);
}
function lh(i, t, e) {
  return i !== t ? (e - i) / (t - i) : 0;
}
function Gi(i, t, e) {
  return (1 - e) * i + e * t;
}
function ch(i, t, e, n) {
  return Gi(i, t, 1 - Math.exp(-e * n));
}
function hh(i, t = 1) {
  return t - Math.abs(Ya(i, t * 2) - t);
}
function uh(i, t, e) {
  return i <= t ? 0 : i >= e ? 1 : ((i = (i - t) / (e - t)), i * i * (3 - 2 * i));
}
function fh(i, t, e) {
  return i <= t ? 0 : i >= e ? 1 : ((i = (i - t) / (e - t)), i * i * i * (i * (i * 6 - 15) + 10));
}
function dh(i, t) {
  return i + Math.floor(Math.random() * (t - i + 1));
}
function ph(i, t) {
  return i + Math.random() * (t - i);
}
function mh(i) {
  return i * (0.5 - Math.random());
}
function gh(i) {
  i !== void 0 && (xo = i);
  let t = (xo += 1831565813);
  return (
    (t = Math.imul(t ^ (t >>> 15), t | 1)),
    (t ^= t + Math.imul(t ^ (t >>> 7), t | 61)),
    ((t ^ (t >>> 14)) >>> 0) / 4294967296
  );
}
function _h(i) {
  return i * Vi;
}
function xh(i) {
  return i * Ti;
}
function vh(i) {
  return (i & (i - 1)) === 0 && i !== 0;
}
function Mh(i) {
  return Math.pow(2, Math.ceil(Math.log(i) / Math.LN2));
}
function Sh(i) {
  return Math.pow(2, Math.floor(Math.log(i) / Math.LN2));
}
function yh(i, t, e, n, s) {
  const r = Math.cos,
    a = Math.sin,
    o = r(e / 2),
    l = a(e / 2),
    c = r((t + n) / 2),
    h = a((t + n) / 2),
    f = r((t - n) / 2),
    u = a((t - n) / 2),
    p = r((n - t) / 2),
    g = a((n - t) / 2);
  switch (s) {
    case 'XYX':
      i.set(o * h, l * f, l * u, o * c);
      break;
    case 'YZY':
      i.set(l * u, o * h, l * f, o * c);
      break;
    case 'ZXZ':
      i.set(l * f, l * u, o * h, o * c);
      break;
    case 'XZX':
      i.set(o * h, l * g, l * p, o * c);
      break;
    case 'YXY':
      i.set(l * p, o * h, l * g, o * c);
      break;
    case 'ZYZ':
      i.set(l * g, l * p, o * h, o * c);
      break;
    default:
      Ft('MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: ' + s);
  }
}
function Ce(i, t) {
  switch (t.constructor) {
    case Float32Array:
      return i;
    case Uint32Array:
      return i / 4294967295;
    case Uint16Array:
      return i / 65535;
    case Uint8Array:
      return i / 255;
    case Int32Array:
      return Math.max(i / 2147483647, -1);
    case Int16Array:
      return Math.max(i / 32767, -1);
    case Int8Array:
      return Math.max(i / 127, -1);
    default:
      throw new Error('Invalid component type.');
  }
}
function Wt(i, t) {
  switch (t.constructor) {
    case Float32Array:
      return i;
    case Uint32Array:
      return Math.round(i * 4294967295);
    case Uint16Array:
      return Math.round(i * 65535);
    case Uint8Array:
      return Math.round(i * 255);
    case Int32Array:
      return Math.round(i * 2147483647);
    case Int16Array:
      return Math.round(i * 32767);
    case Int8Array:
      return Math.round(i * 127);
    default:
      throw new Error('Invalid component type.');
  }
}
const x0 = {
  DEG2RAD: Vi,
  RAD2DEG: Ti,
  generateUUID: sn,
  clamp: Bt,
  euclideanModulo: Ya,
  mapLinear: oh,
  inverseLerp: lh,
  lerp: Gi,
  damp: ch,
  pingpong: hh,
  smoothstep: uh,
  smootherstep: fh,
  randInt: dh,
  randFloat: ph,
  randFloatSpread: mh,
  seededRandom: gh,
  degToRad: _h,
  radToDeg: xh,
  isPowerOfTwo: vh,
  ceilPowerOfTwo: Mh,
  floorPowerOfTwo: Sh,
  setQuaternionFromProperEuler: yh,
  normalize: Wt,
  denormalize: Ce,
};
class ct {
  constructor(t = 0, e = 0) {
    ((ct.prototype.isVector2 = !0), (this.x = t), (this.y = e));
  }
  get width() {
    return this.x;
  }
  set width(t) {
    this.x = t;
  }
  get height() {
    return this.y;
  }
  set height(t) {
    this.y = t;
  }
  set(t, e) {
    return ((this.x = t), (this.y = e), this);
  }
  setScalar(t) {
    return ((this.x = t), (this.y = t), this);
  }
  setX(t) {
    return ((this.x = t), this);
  }
  setY(t) {
    return ((this.y = t), this);
  }
  setComponent(t, e) {
    switch (t) {
      case 0:
        this.x = e;
        break;
      case 1:
        this.y = e;
        break;
      default:
        throw new Error('index is out of range: ' + t);
    }
    return this;
  }
  getComponent(t) {
    switch (t) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      default:
        throw new Error('index is out of range: ' + t);
    }
  }
  clone() {
    return new this.constructor(this.x, this.y);
  }
  copy(t) {
    return ((this.x = t.x), (this.y = t.y), this);
  }
  add(t) {
    return ((this.x += t.x), (this.y += t.y), this);
  }
  addScalar(t) {
    return ((this.x += t), (this.y += t), this);
  }
  addVectors(t, e) {
    return ((this.x = t.x + e.x), (this.y = t.y + e.y), this);
  }
  addScaledVector(t, e) {
    return ((this.x += t.x * e), (this.y += t.y * e), this);
  }
  sub(t) {
    return ((this.x -= t.x), (this.y -= t.y), this);
  }
  subScalar(t) {
    return ((this.x -= t), (this.y -= t), this);
  }
  subVectors(t, e) {
    return ((this.x = t.x - e.x), (this.y = t.y - e.y), this);
  }
  multiply(t) {
    return ((this.x *= t.x), (this.y *= t.y), this);
  }
  multiplyScalar(t) {
    return ((this.x *= t), (this.y *= t), this);
  }
  divide(t) {
    return ((this.x /= t.x), (this.y /= t.y), this);
  }
  divideScalar(t) {
    return this.multiplyScalar(1 / t);
  }
  applyMatrix3(t) {
    const e = this.x,
      n = this.y,
      s = t.elements;
    return ((this.x = s[0] * e + s[3] * n + s[6]), (this.y = s[1] * e + s[4] * n + s[7]), this);
  }
  min(t) {
    return ((this.x = Math.min(this.x, t.x)), (this.y = Math.min(this.y, t.y)), this);
  }
  max(t) {
    return ((this.x = Math.max(this.x, t.x)), (this.y = Math.max(this.y, t.y)), this);
  }
  clamp(t, e) {
    return ((this.x = Bt(this.x, t.x, e.x)), (this.y = Bt(this.y, t.y, e.y)), this);
  }
  clampScalar(t, e) {
    return ((this.x = Bt(this.x, t, e)), (this.y = Bt(this.y, t, e)), this);
  }
  clampLength(t, e) {
    const n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Bt(n, t, e));
  }
  floor() {
    return ((this.x = Math.floor(this.x)), (this.y = Math.floor(this.y)), this);
  }
  ceil() {
    return ((this.x = Math.ceil(this.x)), (this.y = Math.ceil(this.y)), this);
  }
  round() {
    return ((this.x = Math.round(this.x)), (this.y = Math.round(this.y)), this);
  }
  roundToZero() {
    return ((this.x = Math.trunc(this.x)), (this.y = Math.trunc(this.y)), this);
  }
  negate() {
    return ((this.x = -this.x), (this.y = -this.y), this);
  }
  dot(t) {
    return this.x * t.x + this.y * t.y;
  }
  cross(t) {
    return this.x * t.y - this.y * t.x;
  }
  lengthSq() {
    return this.x * this.x + this.y * this.y;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y);
  }
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y);
  }
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  angle() {
    return Math.atan2(-this.y, -this.x) + Math.PI;
  }
  angleTo(t) {
    const e = Math.sqrt(this.lengthSq() * t.lengthSq());
    if (e === 0) return Math.PI / 2;
    const n = this.dot(t) / e;
    return Math.acos(Bt(n, -1, 1));
  }
  distanceTo(t) {
    return Math.sqrt(this.distanceToSquared(t));
  }
  distanceToSquared(t) {
    const e = this.x - t.x,
      n = this.y - t.y;
    return e * e + n * n;
  }
  manhattanDistanceTo(t) {
    return Math.abs(this.x - t.x) + Math.abs(this.y - t.y);
  }
  setLength(t) {
    return this.normalize().multiplyScalar(t);
  }
  lerp(t, e) {
    return ((this.x += (t.x - this.x) * e), (this.y += (t.y - this.y) * e), this);
  }
  lerpVectors(t, e, n) {
    return ((this.x = t.x + (e.x - t.x) * n), (this.y = t.y + (e.y - t.y) * n), this);
  }
  equals(t) {
    return t.x === this.x && t.y === this.y;
  }
  fromArray(t, e = 0) {
    return ((this.x = t[e]), (this.y = t[e + 1]), this);
  }
  toArray(t = [], e = 0) {
    return ((t[e] = this.x), (t[e + 1] = this.y), t);
  }
  fromBufferAttribute(t, e) {
    return ((this.x = t.getX(e)), (this.y = t.getY(e)), this);
  }
  rotateAround(t, e) {
    const n = Math.cos(e),
      s = Math.sin(e),
      r = this.x - t.x,
      a = this.y - t.y;
    return ((this.x = r * n - a * s + t.x), (this.y = r * s + a * n + t.y), this);
  }
  random() {
    return ((this.x = Math.random()), (this.y = Math.random()), this);
  }
  *[Symbol.iterator]() {
    (yield this.x, yield this.y);
  }
}
class Ri {
  constructor(t = 0, e = 0, n = 0, s = 1) {
    ((this.isQuaternion = !0), (this._x = t), (this._y = e), (this._z = n), (this._w = s));
  }
  static slerpFlat(t, e, n, s, r, a, o) {
    let l = n[s + 0],
      c = n[s + 1],
      h = n[s + 2],
      f = n[s + 3],
      u = r[a + 0],
      p = r[a + 1],
      g = r[a + 2],
      M = r[a + 3];
    if (f !== M || l !== u || c !== p || h !== g) {
      let m = l * u + c * p + h * g + f * M;
      m < 0 && ((u = -u), (p = -p), (g = -g), (M = -M), (m = -m));
      let d = 1 - o;
      if (m < 0.9995) {
        const E = Math.acos(m),
          y = Math.sin(E);
        ((d = Math.sin(d * E) / y),
          (o = Math.sin(o * E) / y),
          (l = l * d + u * o),
          (c = c * d + p * o),
          (h = h * d + g * o),
          (f = f * d + M * o));
      } else {
        ((l = l * d + u * o), (c = c * d + p * o), (h = h * d + g * o), (f = f * d + M * o));
        const E = 1 / Math.sqrt(l * l + c * c + h * h + f * f);
        ((l *= E), (c *= E), (h *= E), (f *= E));
      }
    }
    ((t[e] = l), (t[e + 1] = c), (t[e + 2] = h), (t[e + 3] = f));
  }
  static multiplyQuaternionsFlat(t, e, n, s, r, a) {
    const o = n[s],
      l = n[s + 1],
      c = n[s + 2],
      h = n[s + 3],
      f = r[a],
      u = r[a + 1],
      p = r[a + 2],
      g = r[a + 3];
    return (
      (t[e] = o * g + h * f + l * p - c * u),
      (t[e + 1] = l * g + h * u + c * f - o * p),
      (t[e + 2] = c * g + h * p + o * u - l * f),
      (t[e + 3] = h * g - o * f - l * u - c * p),
      t
    );
  }
  get x() {
    return this._x;
  }
  set x(t) {
    ((this._x = t), this._onChangeCallback());
  }
  get y() {
    return this._y;
  }
  set y(t) {
    ((this._y = t), this._onChangeCallback());
  }
  get z() {
    return this._z;
  }
  set z(t) {
    ((this._z = t), this._onChangeCallback());
  }
  get w() {
    return this._w;
  }
  set w(t) {
    ((this._w = t), this._onChangeCallback());
  }
  set(t, e, n, s) {
    return (
      (this._x = t),
      (this._y = e),
      (this._z = n),
      (this._w = s),
      this._onChangeCallback(),
      this
    );
  }
  clone() {
    return new this.constructor(this._x, this._y, this._z, this._w);
  }
  copy(t) {
    return (
      (this._x = t.x),
      (this._y = t.y),
      (this._z = t.z),
      (this._w = t.w),
      this._onChangeCallback(),
      this
    );
  }
  setFromEuler(t, e = !0) {
    const n = t._x,
      s = t._y,
      r = t._z,
      a = t._order,
      o = Math.cos,
      l = Math.sin,
      c = o(n / 2),
      h = o(s / 2),
      f = o(r / 2),
      u = l(n / 2),
      p = l(s / 2),
      g = l(r / 2);
    switch (a) {
      case 'XYZ':
        ((this._x = u * h * f + c * p * g),
          (this._y = c * p * f - u * h * g),
          (this._z = c * h * g + u * p * f),
          (this._w = c * h * f - u * p * g));
        break;
      case 'YXZ':
        ((this._x = u * h * f + c * p * g),
          (this._y = c * p * f - u * h * g),
          (this._z = c * h * g - u * p * f),
          (this._w = c * h * f + u * p * g));
        break;
      case 'ZXY':
        ((this._x = u * h * f - c * p * g),
          (this._y = c * p * f + u * h * g),
          (this._z = c * h * g + u * p * f),
          (this._w = c * h * f - u * p * g));
        break;
      case 'ZYX':
        ((this._x = u * h * f - c * p * g),
          (this._y = c * p * f + u * h * g),
          (this._z = c * h * g - u * p * f),
          (this._w = c * h * f + u * p * g));
        break;
      case 'YZX':
        ((this._x = u * h * f + c * p * g),
          (this._y = c * p * f + u * h * g),
          (this._z = c * h * g - u * p * f),
          (this._w = c * h * f - u * p * g));
        break;
      case 'XZY':
        ((this._x = u * h * f - c * p * g),
          (this._y = c * p * f - u * h * g),
          (this._z = c * h * g + u * p * f),
          (this._w = c * h * f + u * p * g));
        break;
      default:
        Ft('Quaternion: .setFromEuler() encountered an unknown order: ' + a);
    }
    return (e === !0 && this._onChangeCallback(), this);
  }
  setFromAxisAngle(t, e) {
    const n = e / 2,
      s = Math.sin(n);
    return (
      (this._x = t.x * s),
      (this._y = t.y * s),
      (this._z = t.z * s),
      (this._w = Math.cos(n)),
      this._onChangeCallback(),
      this
    );
  }
  setFromRotationMatrix(t) {
    const e = t.elements,
      n = e[0],
      s = e[4],
      r = e[8],
      a = e[1],
      o = e[5],
      l = e[9],
      c = e[2],
      h = e[6],
      f = e[10],
      u = n + o + f;
    if (u > 0) {
      const p = 0.5 / Math.sqrt(u + 1);
      ((this._w = 0.25 / p),
        (this._x = (h - l) * p),
        (this._y = (r - c) * p),
        (this._z = (a - s) * p));
    } else if (n > o && n > f) {
      const p = 2 * Math.sqrt(1 + n - o - f);
      ((this._w = (h - l) / p),
        (this._x = 0.25 * p),
        (this._y = (s + a) / p),
        (this._z = (r + c) / p));
    } else if (o > f) {
      const p = 2 * Math.sqrt(1 + o - n - f);
      ((this._w = (r - c) / p),
        (this._x = (s + a) / p),
        (this._y = 0.25 * p),
        (this._z = (l + h) / p));
    } else {
      const p = 2 * Math.sqrt(1 + f - n - o);
      ((this._w = (a - s) / p),
        (this._x = (r + c) / p),
        (this._y = (l + h) / p),
        (this._z = 0.25 * p));
    }
    return (this._onChangeCallback(), this);
  }
  setFromUnitVectors(t, e) {
    let n = t.dot(e) + 1;
    return (
      n < 1e-8
        ? ((n = 0),
          Math.abs(t.x) > Math.abs(t.z)
            ? ((this._x = -t.y), (this._y = t.x), (this._z = 0), (this._w = n))
            : ((this._x = 0), (this._y = -t.z), (this._z = t.y), (this._w = n)))
        : ((this._x = t.y * e.z - t.z * e.y),
          (this._y = t.z * e.x - t.x * e.z),
          (this._z = t.x * e.y - t.y * e.x),
          (this._w = n)),
      this.normalize()
    );
  }
  angleTo(t) {
    return 2 * Math.acos(Math.abs(Bt(this.dot(t), -1, 1)));
  }
  rotateTowards(t, e) {
    const n = this.angleTo(t);
    if (n === 0) return this;
    const s = Math.min(1, e / n);
    return (this.slerp(t, s), this);
  }
  identity() {
    return this.set(0, 0, 0, 1);
  }
  invert() {
    return this.conjugate();
  }
  conjugate() {
    return ((this._x *= -1), (this._y *= -1), (this._z *= -1), this._onChangeCallback(), this);
  }
  dot(t) {
    return this._x * t._x + this._y * t._y + this._z * t._z + this._w * t._w;
  }
  lengthSq() {
    return this._x * this._x + this._y * this._y + this._z * this._z + this._w * this._w;
  }
  length() {
    return Math.sqrt(this._x * this._x + this._y * this._y + this._z * this._z + this._w * this._w);
  }
  normalize() {
    let t = this.length();
    return (
      t === 0
        ? ((this._x = 0), (this._y = 0), (this._z = 0), (this._w = 1))
        : ((t = 1 / t),
          (this._x = this._x * t),
          (this._y = this._y * t),
          (this._z = this._z * t),
          (this._w = this._w * t)),
      this._onChangeCallback(),
      this
    );
  }
  multiply(t) {
    return this.multiplyQuaternions(this, t);
  }
  premultiply(t) {
    return this.multiplyQuaternions(t, this);
  }
  multiplyQuaternions(t, e) {
    const n = t._x,
      s = t._y,
      r = t._z,
      a = t._w,
      o = e._x,
      l = e._y,
      c = e._z,
      h = e._w;
    return (
      (this._x = n * h + a * o + s * c - r * l),
      (this._y = s * h + a * l + r * o - n * c),
      (this._z = r * h + a * c + n * l - s * o),
      (this._w = a * h - n * o - s * l - r * c),
      this._onChangeCallback(),
      this
    );
  }
  slerp(t, e) {
    let n = t._x,
      s = t._y,
      r = t._z,
      a = t._w,
      o = this.dot(t);
    o < 0 && ((n = -n), (s = -s), (r = -r), (a = -a), (o = -o));
    let l = 1 - e;
    if (o < 0.9995) {
      const c = Math.acos(o),
        h = Math.sin(c);
      ((l = Math.sin(l * c) / h),
        (e = Math.sin(e * c) / h),
        (this._x = this._x * l + n * e),
        (this._y = this._y * l + s * e),
        (this._z = this._z * l + r * e),
        (this._w = this._w * l + a * e),
        this._onChangeCallback());
    } else
      ((this._x = this._x * l + n * e),
        (this._y = this._y * l + s * e),
        (this._z = this._z * l + r * e),
        (this._w = this._w * l + a * e),
        this.normalize());
    return this;
  }
  slerpQuaternions(t, e, n) {
    return this.copy(t).slerp(e, n);
  }
  random() {
    const t = 2 * Math.PI * Math.random(),
      e = 2 * Math.PI * Math.random(),
      n = Math.random(),
      s = Math.sqrt(1 - n),
      r = Math.sqrt(n);
    return this.set(s * Math.sin(t), s * Math.cos(t), r * Math.sin(e), r * Math.cos(e));
  }
  equals(t) {
    return t._x === this._x && t._y === this._y && t._z === this._z && t._w === this._w;
  }
  fromArray(t, e = 0) {
    return (
      (this._x = t[e]),
      (this._y = t[e + 1]),
      (this._z = t[e + 2]),
      (this._w = t[e + 3]),
      this._onChangeCallback(),
      this
    );
  }
  toArray(t = [], e = 0) {
    return ((t[e] = this._x), (t[e + 1] = this._y), (t[e + 2] = this._z), (t[e + 3] = this._w), t);
  }
  fromBufferAttribute(t, e) {
    return (
      (this._x = t.getX(e)),
      (this._y = t.getY(e)),
      (this._z = t.getZ(e)),
      (this._w = t.getW(e)),
      this._onChangeCallback(),
      this
    );
  }
  toJSON() {
    return this.toArray();
  }
  _onChange(t) {
    return ((this._onChangeCallback = t), this);
  }
  _onChangeCallback() {}
  *[Symbol.iterator]() {
    (yield this._x, yield this._y, yield this._z, yield this._w);
  }
}
class L {
  constructor(t = 0, e = 0, n = 0) {
    ((L.prototype.isVector3 = !0), (this.x = t), (this.y = e), (this.z = n));
  }
  set(t, e, n) {
    return (n === void 0 && (n = this.z), (this.x = t), (this.y = e), (this.z = n), this);
  }
  setScalar(t) {
    return ((this.x = t), (this.y = t), (this.z = t), this);
  }
  setX(t) {
    return ((this.x = t), this);
  }
  setY(t) {
    return ((this.y = t), this);
  }
  setZ(t) {
    return ((this.z = t), this);
  }
  setComponent(t, e) {
    switch (t) {
      case 0:
        this.x = e;
        break;
      case 1:
        this.y = e;
        break;
      case 2:
        this.z = e;
        break;
      default:
        throw new Error('index is out of range: ' + t);
    }
    return this;
  }
  getComponent(t) {
    switch (t) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      case 2:
        return this.z;
      default:
        throw new Error('index is out of range: ' + t);
    }
  }
  clone() {
    return new this.constructor(this.x, this.y, this.z);
  }
  copy(t) {
    return ((this.x = t.x), (this.y = t.y), (this.z = t.z), this);
  }
  add(t) {
    return ((this.x += t.x), (this.y += t.y), (this.z += t.z), this);
  }
  addScalar(t) {
    return ((this.x += t), (this.y += t), (this.z += t), this);
  }
  addVectors(t, e) {
    return ((this.x = t.x + e.x), (this.y = t.y + e.y), (this.z = t.z + e.z), this);
  }
  addScaledVector(t, e) {
    return ((this.x += t.x * e), (this.y += t.y * e), (this.z += t.z * e), this);
  }
  sub(t) {
    return ((this.x -= t.x), (this.y -= t.y), (this.z -= t.z), this);
  }
  subScalar(t) {
    return ((this.x -= t), (this.y -= t), (this.z -= t), this);
  }
  subVectors(t, e) {
    return ((this.x = t.x - e.x), (this.y = t.y - e.y), (this.z = t.z - e.z), this);
  }
  multiply(t) {
    return ((this.x *= t.x), (this.y *= t.y), (this.z *= t.z), this);
  }
  multiplyScalar(t) {
    return ((this.x *= t), (this.y *= t), (this.z *= t), this);
  }
  multiplyVectors(t, e) {
    return ((this.x = t.x * e.x), (this.y = t.y * e.y), (this.z = t.z * e.z), this);
  }
  applyEuler(t) {
    return this.applyQuaternion(vo.setFromEuler(t));
  }
  applyAxisAngle(t, e) {
    return this.applyQuaternion(vo.setFromAxisAngle(t, e));
  }
  applyMatrix3(t) {
    const e = this.x,
      n = this.y,
      s = this.z,
      r = t.elements;
    return (
      (this.x = r[0] * e + r[3] * n + r[6] * s),
      (this.y = r[1] * e + r[4] * n + r[7] * s),
      (this.z = r[2] * e + r[5] * n + r[8] * s),
      this
    );
  }
  applyNormalMatrix(t) {
    return this.applyMatrix3(t).normalize();
  }
  applyMatrix4(t) {
    const e = this.x,
      n = this.y,
      s = this.z,
      r = t.elements,
      a = 1 / (r[3] * e + r[7] * n + r[11] * s + r[15]);
    return (
      (this.x = (r[0] * e + r[4] * n + r[8] * s + r[12]) * a),
      (this.y = (r[1] * e + r[5] * n + r[9] * s + r[13]) * a),
      (this.z = (r[2] * e + r[6] * n + r[10] * s + r[14]) * a),
      this
    );
  }
  applyQuaternion(t) {
    const e = this.x,
      n = this.y,
      s = this.z,
      r = t.x,
      a = t.y,
      o = t.z,
      l = t.w,
      c = 2 * (a * s - o * n),
      h = 2 * (o * e - r * s),
      f = 2 * (r * n - a * e);
    return (
      (this.x = e + l * c + a * f - o * h),
      (this.y = n + l * h + o * c - r * f),
      (this.z = s + l * f + r * h - a * c),
      this
    );
  }
  project(t) {
    return this.applyMatrix4(t.matrixWorldInverse).applyMatrix4(t.projectionMatrix);
  }
  unproject(t) {
    return this.applyMatrix4(t.projectionMatrixInverse).applyMatrix4(t.matrixWorld);
  }
  transformDirection(t) {
    const e = this.x,
      n = this.y,
      s = this.z,
      r = t.elements;
    return (
      (this.x = r[0] * e + r[4] * n + r[8] * s),
      (this.y = r[1] * e + r[5] * n + r[9] * s),
      (this.z = r[2] * e + r[6] * n + r[10] * s),
      this.normalize()
    );
  }
  divide(t) {
    return ((this.x /= t.x), (this.y /= t.y), (this.z /= t.z), this);
  }
  divideScalar(t) {
    return this.multiplyScalar(1 / t);
  }
  min(t) {
    return (
      (this.x = Math.min(this.x, t.x)),
      (this.y = Math.min(this.y, t.y)),
      (this.z = Math.min(this.z, t.z)),
      this
    );
  }
  max(t) {
    return (
      (this.x = Math.max(this.x, t.x)),
      (this.y = Math.max(this.y, t.y)),
      (this.z = Math.max(this.z, t.z)),
      this
    );
  }
  clamp(t, e) {
    return (
      (this.x = Bt(this.x, t.x, e.x)),
      (this.y = Bt(this.y, t.y, e.y)),
      (this.z = Bt(this.z, t.z, e.z)),
      this
    );
  }
  clampScalar(t, e) {
    return (
      (this.x = Bt(this.x, t, e)),
      (this.y = Bt(this.y, t, e)),
      (this.z = Bt(this.z, t, e)),
      this
    );
  }
  clampLength(t, e) {
    const n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Bt(n, t, e));
  }
  floor() {
    return (
      (this.x = Math.floor(this.x)),
      (this.y = Math.floor(this.y)),
      (this.z = Math.floor(this.z)),
      this
    );
  }
  ceil() {
    return (
      (this.x = Math.ceil(this.x)),
      (this.y = Math.ceil(this.y)),
      (this.z = Math.ceil(this.z)),
      this
    );
  }
  round() {
    return (
      (this.x = Math.round(this.x)),
      (this.y = Math.round(this.y)),
      (this.z = Math.round(this.z)),
      this
    );
  }
  roundToZero() {
    return (
      (this.x = Math.trunc(this.x)),
      (this.y = Math.trunc(this.y)),
      (this.z = Math.trunc(this.z)),
      this
    );
  }
  negate() {
    return ((this.x = -this.x), (this.y = -this.y), (this.z = -this.z), this);
  }
  dot(t) {
    return this.x * t.x + this.y * t.y + this.z * t.z;
  }
  lengthSq() {
    return this.x * this.x + this.y * this.y + this.z * this.z;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
  }
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y) + Math.abs(this.z);
  }
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  setLength(t) {
    return this.normalize().multiplyScalar(t);
  }
  lerp(t, e) {
    return (
      (this.x += (t.x - this.x) * e),
      (this.y += (t.y - this.y) * e),
      (this.z += (t.z - this.z) * e),
      this
    );
  }
  lerpVectors(t, e, n) {
    return (
      (this.x = t.x + (e.x - t.x) * n),
      (this.y = t.y + (e.y - t.y) * n),
      (this.z = t.z + (e.z - t.z) * n),
      this
    );
  }
  cross(t) {
    return this.crossVectors(this, t);
  }
  crossVectors(t, e) {
    const n = t.x,
      s = t.y,
      r = t.z,
      a = e.x,
      o = e.y,
      l = e.z;
    return ((this.x = s * l - r * o), (this.y = r * a - n * l), (this.z = n * o - s * a), this);
  }
  projectOnVector(t) {
    const e = t.lengthSq();
    if (e === 0) return this.set(0, 0, 0);
    const n = t.dot(this) / e;
    return this.copy(t).multiplyScalar(n);
  }
  projectOnPlane(t) {
    return (ar.copy(this).projectOnVector(t), this.sub(ar));
  }
  reflect(t) {
    return this.sub(ar.copy(t).multiplyScalar(2 * this.dot(t)));
  }
  angleTo(t) {
    const e = Math.sqrt(this.lengthSq() * t.lengthSq());
    if (e === 0) return Math.PI / 2;
    const n = this.dot(t) / e;
    return Math.acos(Bt(n, -1, 1));
  }
  distanceTo(t) {
    return Math.sqrt(this.distanceToSquared(t));
  }
  distanceToSquared(t) {
    const e = this.x - t.x,
      n = this.y - t.y,
      s = this.z - t.z;
    return e * e + n * n + s * s;
  }
  manhattanDistanceTo(t) {
    return Math.abs(this.x - t.x) + Math.abs(this.y - t.y) + Math.abs(this.z - t.z);
  }
  setFromSpherical(t) {
    return this.setFromSphericalCoords(t.radius, t.phi, t.theta);
  }
  setFromSphericalCoords(t, e, n) {
    const s = Math.sin(e) * t;
    return (
      (this.x = s * Math.sin(n)),
      (this.y = Math.cos(e) * t),
      (this.z = s * Math.cos(n)),
      this
    );
  }
  setFromCylindrical(t) {
    return this.setFromCylindricalCoords(t.radius, t.theta, t.y);
  }
  setFromCylindricalCoords(t, e, n) {
    return ((this.x = t * Math.sin(e)), (this.y = n), (this.z = t * Math.cos(e)), this);
  }
  setFromMatrixPosition(t) {
    const e = t.elements;
    return ((this.x = e[12]), (this.y = e[13]), (this.z = e[14]), this);
  }
  setFromMatrixScale(t) {
    const e = this.setFromMatrixColumn(t, 0).length(),
      n = this.setFromMatrixColumn(t, 1).length(),
      s = this.setFromMatrixColumn(t, 2).length();
    return ((this.x = e), (this.y = n), (this.z = s), this);
  }
  setFromMatrixColumn(t, e) {
    return this.fromArray(t.elements, e * 4);
  }
  setFromMatrix3Column(t, e) {
    return this.fromArray(t.elements, e * 3);
  }
  setFromEuler(t) {
    return ((this.x = t._x), (this.y = t._y), (this.z = t._z), this);
  }
  setFromColor(t) {
    return ((this.x = t.r), (this.y = t.g), (this.z = t.b), this);
  }
  equals(t) {
    return t.x === this.x && t.y === this.y && t.z === this.z;
  }
  fromArray(t, e = 0) {
    return ((this.x = t[e]), (this.y = t[e + 1]), (this.z = t[e + 2]), this);
  }
  toArray(t = [], e = 0) {
    return ((t[e] = this.x), (t[e + 1] = this.y), (t[e + 2] = this.z), t);
  }
  fromBufferAttribute(t, e) {
    return ((this.x = t.getX(e)), (this.y = t.getY(e)), (this.z = t.getZ(e)), this);
  }
  random() {
    return ((this.x = Math.random()), (this.y = Math.random()), (this.z = Math.random()), this);
  }
  randomDirection() {
    const t = Math.random() * Math.PI * 2,
      e = Math.random() * 2 - 1,
      n = Math.sqrt(1 - e * e);
    return ((this.x = n * Math.cos(t)), (this.y = e), (this.z = n * Math.sin(t)), this);
  }
  *[Symbol.iterator]() {
    (yield this.x, yield this.y, yield this.z);
  }
}
const ar = new L(),
  vo = new Ri();
class Xt {
  constructor(t, e, n, s, r, a, o, l, c) {
    ((Xt.prototype.isMatrix3 = !0),
      (this.elements = [1, 0, 0, 0, 1, 0, 0, 0, 1]),
      t !== void 0 && this.set(t, e, n, s, r, a, o, l, c));
  }
  set(t, e, n, s, r, a, o, l, c) {
    const h = this.elements;
    return (
      (h[0] = t),
      (h[1] = s),
      (h[2] = o),
      (h[3] = e),
      (h[4] = r),
      (h[5] = l),
      (h[6] = n),
      (h[7] = a),
      (h[8] = c),
      this
    );
  }
  identity() {
    return (this.set(1, 0, 0, 0, 1, 0, 0, 0, 1), this);
  }
  copy(t) {
    const e = this.elements,
      n = t.elements;
    return (
      (e[0] = n[0]),
      (e[1] = n[1]),
      (e[2] = n[2]),
      (e[3] = n[3]),
      (e[4] = n[4]),
      (e[5] = n[5]),
      (e[6] = n[6]),
      (e[7] = n[7]),
      (e[8] = n[8]),
      this
    );
  }
  extractBasis(t, e, n) {
    return (
      t.setFromMatrix3Column(this, 0),
      e.setFromMatrix3Column(this, 1),
      n.setFromMatrix3Column(this, 2),
      this
    );
  }
  setFromMatrix4(t) {
    const e = t.elements;
    return (this.set(e[0], e[4], e[8], e[1], e[5], e[9], e[2], e[6], e[10]), this);
  }
  multiply(t) {
    return this.multiplyMatrices(this, t);
  }
  premultiply(t) {
    return this.multiplyMatrices(t, this);
  }
  multiplyMatrices(t, e) {
    const n = t.elements,
      s = e.elements,
      r = this.elements,
      a = n[0],
      o = n[3],
      l = n[6],
      c = n[1],
      h = n[4],
      f = n[7],
      u = n[2],
      p = n[5],
      g = n[8],
      M = s[0],
      m = s[3],
      d = s[6],
      E = s[1],
      y = s[4],
      S = s[7],
      R = s[2],
      w = s[5],
      P = s[8];
    return (
      (r[0] = a * M + o * E + l * R),
      (r[3] = a * m + o * y + l * w),
      (r[6] = a * d + o * S + l * P),
      (r[1] = c * M + h * E + f * R),
      (r[4] = c * m + h * y + f * w),
      (r[7] = c * d + h * S + f * P),
      (r[2] = u * M + p * E + g * R),
      (r[5] = u * m + p * y + g * w),
      (r[8] = u * d + p * S + g * P),
      this
    );
  }
  multiplyScalar(t) {
    const e = this.elements;
    return (
      (e[0] *= t),
      (e[3] *= t),
      (e[6] *= t),
      (e[1] *= t),
      (e[4] *= t),
      (e[7] *= t),
      (e[2] *= t),
      (e[5] *= t),
      (e[8] *= t),
      this
    );
  }
  determinant() {
    const t = this.elements,
      e = t[0],
      n = t[1],
      s = t[2],
      r = t[3],
      a = t[4],
      o = t[5],
      l = t[6],
      c = t[7],
      h = t[8];
    return e * a * h - e * o * c - n * r * h + n * o * l + s * r * c - s * a * l;
  }
  invert() {
    const t = this.elements,
      e = t[0],
      n = t[1],
      s = t[2],
      r = t[3],
      a = t[4],
      o = t[5],
      l = t[6],
      c = t[7],
      h = t[8],
      f = h * a - o * c,
      u = o * l - h * r,
      p = c * r - a * l,
      g = e * f + n * u + s * p;
    if (g === 0) return this.set(0, 0, 0, 0, 0, 0, 0, 0, 0);
    const M = 1 / g;
    return (
      (t[0] = f * M),
      (t[1] = (s * c - h * n) * M),
      (t[2] = (o * n - s * a) * M),
      (t[3] = u * M),
      (t[4] = (h * e - s * l) * M),
      (t[5] = (s * r - o * e) * M),
      (t[6] = p * M),
      (t[7] = (n * l - c * e) * M),
      (t[8] = (a * e - n * r) * M),
      this
    );
  }
  transpose() {
    let t;
    const e = this.elements;
    return (
      (t = e[1]),
      (e[1] = e[3]),
      (e[3] = t),
      (t = e[2]),
      (e[2] = e[6]),
      (e[6] = t),
      (t = e[5]),
      (e[5] = e[7]),
      (e[7] = t),
      this
    );
  }
  getNormalMatrix(t) {
    return this.setFromMatrix4(t).invert().transpose();
  }
  transposeIntoArray(t) {
    const e = this.elements;
    return (
      (t[0] = e[0]),
      (t[1] = e[3]),
      (t[2] = e[6]),
      (t[3] = e[1]),
      (t[4] = e[4]),
      (t[5] = e[7]),
      (t[6] = e[2]),
      (t[7] = e[5]),
      (t[8] = e[8]),
      this
    );
  }
  setUvTransform(t, e, n, s, r, a, o) {
    const l = Math.cos(r),
      c = Math.sin(r);
    return (
      this.set(
        n * l,
        n * c,
        -n * (l * a + c * o) + a + t,
        -s * c,
        s * l,
        -s * (-c * a + l * o) + o + e,
        0,
        0,
        1
      ),
      this
    );
  }
  scale(t, e) {
    return (this.premultiply(or.makeScale(t, e)), this);
  }
  rotate(t) {
    return (this.premultiply(or.makeRotation(-t)), this);
  }
  translate(t, e) {
    return (this.premultiply(or.makeTranslation(t, e)), this);
  }
  makeTranslation(t, e) {
    return (
      t.isVector2 ? this.set(1, 0, t.x, 0, 1, t.y, 0, 0, 1) : this.set(1, 0, t, 0, 1, e, 0, 0, 1),
      this
    );
  }
  makeRotation(t) {
    const e = Math.cos(t),
      n = Math.sin(t);
    return (this.set(e, -n, 0, n, e, 0, 0, 0, 1), this);
  }
  makeScale(t, e) {
    return (this.set(t, 0, 0, 0, e, 0, 0, 0, 1), this);
  }
  equals(t) {
    const e = this.elements,
      n = t.elements;
    for (let s = 0; s < 9; s++) if (e[s] !== n[s]) return !1;
    return !0;
  }
  fromArray(t, e = 0) {
    for (let n = 0; n < 9; n++) this.elements[n] = t[n + e];
    return this;
  }
  toArray(t = [], e = 0) {
    const n = this.elements;
    return (
      (t[e] = n[0]),
      (t[e + 1] = n[1]),
      (t[e + 2] = n[2]),
      (t[e + 3] = n[3]),
      (t[e + 4] = n[4]),
      (t[e + 5] = n[5]),
      (t[e + 6] = n[6]),
      (t[e + 7] = n[7]),
      (t[e + 8] = n[8]),
      t
    );
  }
  clone() {
    return new this.constructor().fromArray(this.elements);
  }
}
const or = new Xt(),
  Mo = new Xt().set(
    0.4123908,
    0.3575843,
    0.1804808,
    0.212639,
    0.7151687,
    0.0721923,
    0.0193308,
    0.1191948,
    0.9505322
  ),
  So = new Xt().set(
    3.2409699,
    -1.5373832,
    -0.4986108,
    -0.9692436,
    1.8759675,
    0.0415551,
    0.0556301,
    -0.203977,
    1.0569715
  );
function Eh() {
  const i = {
      enabled: !0,
      workingColorSpace: bi,
      spaces: {},
      convert: function (s, r, a) {
        return (
          this.enabled === !1 ||
            r === a ||
            !r ||
            !a ||
            (this.spaces[r].transfer === te && ((s.r = Mn(s.r)), (s.g = Mn(s.g)), (s.b = Mn(s.b))),
            this.spaces[r].primaries !== this.spaces[a].primaries &&
              (s.applyMatrix3(this.spaces[r].toXYZ), s.applyMatrix3(this.spaces[a].fromXYZ)),
            this.spaces[a].transfer === te && ((s.r = Mi(s.r)), (s.g = Mi(s.g)), (s.b = Mi(s.b)))),
          s
        );
      },
      workingToColorSpace: function (s, r) {
        return this.convert(s, this.workingColorSpace, r);
      },
      colorSpaceToWorking: function (s, r) {
        return this.convert(s, r, this.workingColorSpace);
      },
      getPrimaries: function (s) {
        return this.spaces[s].primaries;
      },
      getTransfer: function (s) {
        return s === Dn ? Hs : this.spaces[s].transfer;
      },
      getToneMappingMode: function (s) {
        return this.spaces[s].outputColorSpaceConfig.toneMappingMode || 'standard';
      },
      getLuminanceCoefficients: function (s, r = this.workingColorSpace) {
        return s.fromArray(this.spaces[r].luminanceCoefficients);
      },
      define: function (s) {
        Object.assign(this.spaces, s);
      },
      _getMatrix: function (s, r, a) {
        return s.copy(this.spaces[r].toXYZ).multiply(this.spaces[a].fromXYZ);
      },
      _getDrawingBufferColorSpace: function (s) {
        return this.spaces[s].outputColorSpaceConfig.drawingBufferColorSpace;
      },
      _getUnpackColorSpace: function (s = this.workingColorSpace) {
        return this.spaces[s].workingColorSpaceConfig.unpackColorSpace;
      },
      fromWorkingColorSpace: function (s, r) {
        return (
          Ws(
            'ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace().'
          ),
          i.workingToColorSpace(s, r)
        );
      },
      toWorkingColorSpace: function (s, r) {
        return (
          Ws('ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking().'),
          i.colorSpaceToWorking(s, r)
        );
      },
    },
    t = [0.64, 0.33, 0.3, 0.6, 0.15, 0.06],
    e = [0.2126, 0.7152, 0.0722],
    n = [0.3127, 0.329];
  return (
    i.define({
      [bi]: {
        primaries: t,
        whitePoint: n,
        transfer: Hs,
        toXYZ: Mo,
        fromXYZ: So,
        luminanceCoefficients: e,
        workingColorSpaceConfig: { unpackColorSpace: Ve },
        outputColorSpaceConfig: { drawingBufferColorSpace: Ve },
      },
      [Ve]: {
        primaries: t,
        whitePoint: n,
        transfer: te,
        toXYZ: Mo,
        fromXYZ: So,
        luminanceCoefficients: e,
        outputColorSpaceConfig: { drawingBufferColorSpace: Ve },
      },
    }),
    i
  );
}
const $t = Eh();
function Mn(i) {
  return i < 0.04045 ? i * 0.0773993808 : Math.pow(i * 0.9478672986 + 0.0521327014, 2.4);
}
function Mi(i) {
  return i < 0.0031308 ? i * 12.92 : 1.055 * Math.pow(i, 0.41666) - 0.055;
}
let ii;
class bh {
  static getDataURL(t, e = 'image/png') {
    if (/^data:/i.test(t.src) || typeof HTMLCanvasElement > 'u') return t.src;
    let n;
    if (t instanceof HTMLCanvasElement) n = t;
    else {
      (ii === void 0 && (ii = Yi('canvas')), (ii.width = t.width), (ii.height = t.height));
      const s = ii.getContext('2d');
      (t instanceof ImageData ? s.putImageData(t, 0, 0) : s.drawImage(t, 0, 0, t.width, t.height),
        (n = ii));
    }
    return n.toDataURL(e);
  }
  static sRGBToLinear(t) {
    if (
      (typeof HTMLImageElement < 'u' && t instanceof HTMLImageElement) ||
      (typeof HTMLCanvasElement < 'u' && t instanceof HTMLCanvasElement) ||
      (typeof ImageBitmap < 'u' && t instanceof ImageBitmap)
    ) {
      const e = Yi('canvas');
      ((e.width = t.width), (e.height = t.height));
      const n = e.getContext('2d');
      n.drawImage(t, 0, 0, t.width, t.height);
      const s = n.getImageData(0, 0, t.width, t.height),
        r = s.data;
      for (let a = 0; a < r.length; a++) r[a] = Mn(r[a] / 255) * 255;
      return (n.putImageData(s, 0, 0), e);
    } else if (t.data) {
      const e = t.data.slice(0);
      for (let n = 0; n < e.length; n++)
        e instanceof Uint8Array || e instanceof Uint8ClampedArray
          ? (e[n] = Math.floor(Mn(e[n] / 255) * 255))
          : (e[n] = Mn(e[n]));
      return { data: e, width: t.width, height: t.height };
    } else
      return (
        Ft('ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied.'),
        t
      );
  }
}
let Th = 0;
class Za {
  constructor(t = null) {
    ((this.isSource = !0),
      Object.defineProperty(this, 'id', { value: Th++ }),
      (this.uuid = sn()),
      (this.data = t),
      (this.dataReady = !0),
      (this.version = 0));
  }
  getSize(t) {
    const e = this.data;
    return (
      typeof HTMLVideoElement < 'u' && e instanceof HTMLVideoElement
        ? t.set(e.videoWidth, e.videoHeight, 0)
        : typeof VideoFrame < 'u' && e instanceof VideoFrame
          ? t.set(e.displayHeight, e.displayWidth, 0)
          : e !== null
            ? t.set(e.width, e.height, e.depth || 0)
            : t.set(0, 0, 0),
      t
    );
  }
  set needsUpdate(t) {
    t === !0 && this.version++;
  }
  toJSON(t) {
    const e = t === void 0 || typeof t == 'string';
    if (!e && t.images[this.uuid] !== void 0) return t.images[this.uuid];
    const n = { uuid: this.uuid, url: '' },
      s = this.data;
    if (s !== null) {
      let r;
      if (Array.isArray(s)) {
        r = [];
        for (let a = 0, o = s.length; a < o; a++)
          s[a].isDataTexture ? r.push(lr(s[a].image)) : r.push(lr(s[a]));
      } else r = lr(s);
      n.url = r;
    }
    return (e || (t.images[this.uuid] = n), n);
  }
}
function lr(i) {
  return (typeof HTMLImageElement < 'u' && i instanceof HTMLImageElement) ||
    (typeof HTMLCanvasElement < 'u' && i instanceof HTMLCanvasElement) ||
    (typeof ImageBitmap < 'u' && i instanceof ImageBitmap)
    ? bh.getDataURL(i)
    : i.data
      ? {
          data: Array.from(i.data),
          width: i.width,
          height: i.height,
          type: i.data.constructor.name,
        }
      : (Ft('Texture: Unable to serialize Texture.'), {});
}
let Ah = 0;
const cr = new L();
class ye extends jn {
  constructor(
    t = ye.DEFAULT_IMAGE,
    e = ye.DEFAULT_MAPPING,
    n = xn,
    s = xn,
    r = Ae,
    a = qn,
    o = Ye,
    l = Oe,
    c = ye.DEFAULT_ANISOTROPY,
    h = Dn
  ) {
    (super(),
      (this.isTexture = !0),
      Object.defineProperty(this, 'id', { value: Ah++ }),
      (this.uuid = sn()),
      (this.name = ''),
      (this.source = new Za(t)),
      (this.mipmaps = []),
      (this.mapping = e),
      (this.channel = 0),
      (this.wrapS = n),
      (this.wrapT = s),
      (this.magFilter = r),
      (this.minFilter = a),
      (this.anisotropy = c),
      (this.format = o),
      (this.internalFormat = null),
      (this.type = l),
      (this.offset = new ct(0, 0)),
      (this.repeat = new ct(1, 1)),
      (this.center = new ct(0, 0)),
      (this.rotation = 0),
      (this.matrixAutoUpdate = !0),
      (this.matrix = new Xt()),
      (this.generateMipmaps = !0),
      (this.premultiplyAlpha = !1),
      (this.flipY = !0),
      (this.unpackAlignment = 4),
      (this.colorSpace = h),
      (this.userData = {}),
      (this.updateRanges = []),
      (this.version = 0),
      (this.onUpdate = null),
      (this.renderTarget = null),
      (this.isRenderTargetTexture = !1),
      (this.isArrayTexture = !!(t && t.depth && t.depth > 1)),
      (this.pmremVersion = 0));
  }
  get width() {
    return this.source.getSize(cr).x;
  }
  get height() {
    return this.source.getSize(cr).y;
  }
  get depth() {
    return this.source.getSize(cr).z;
  }
  get image() {
    return this.source.data;
  }
  set image(t = null) {
    this.source.data = t;
  }
  updateMatrix() {
    this.matrix.setUvTransform(
      this.offset.x,
      this.offset.y,
      this.repeat.x,
      this.repeat.y,
      this.rotation,
      this.center.x,
      this.center.y
    );
  }
  addUpdateRange(t, e) {
    this.updateRanges.push({ start: t, count: e });
  }
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    return (
      (this.name = t.name),
      (this.source = t.source),
      (this.mipmaps = t.mipmaps.slice(0)),
      (this.mapping = t.mapping),
      (this.channel = t.channel),
      (this.wrapS = t.wrapS),
      (this.wrapT = t.wrapT),
      (this.magFilter = t.magFilter),
      (this.minFilter = t.minFilter),
      (this.anisotropy = t.anisotropy),
      (this.format = t.format),
      (this.internalFormat = t.internalFormat),
      (this.type = t.type),
      this.offset.copy(t.offset),
      this.repeat.copy(t.repeat),
      this.center.copy(t.center),
      (this.rotation = t.rotation),
      (this.matrixAutoUpdate = t.matrixAutoUpdate),
      this.matrix.copy(t.matrix),
      (this.generateMipmaps = t.generateMipmaps),
      (this.premultiplyAlpha = t.premultiplyAlpha),
      (this.flipY = t.flipY),
      (this.unpackAlignment = t.unpackAlignment),
      (this.colorSpace = t.colorSpace),
      (this.renderTarget = t.renderTarget),
      (this.isRenderTargetTexture = t.isRenderTargetTexture),
      (this.isArrayTexture = t.isArrayTexture),
      (this.userData = JSON.parse(JSON.stringify(t.userData))),
      (this.needsUpdate = !0),
      this
    );
  }
  setValues(t) {
    for (const e in t) {
      const n = t[e];
      if (n === void 0) {
        Ft(`Texture.setValues(): parameter '${e}' has value of undefined.`);
        continue;
      }
      const s = this[e];
      if (s === void 0) {
        Ft(`Texture.setValues(): property '${e}' does not exist.`);
        continue;
      }
      (s && n && s.isVector2 && n.isVector2) ||
      (s && n && s.isVector3 && n.isVector3) ||
      (s && n && s.isMatrix3 && n.isMatrix3)
        ? s.copy(n)
        : (this[e] = n);
    }
  }
  toJSON(t) {
    const e = t === void 0 || typeof t == 'string';
    if (!e && t.textures[this.uuid] !== void 0) return t.textures[this.uuid];
    const n = {
      metadata: { version: 4.7, type: 'Texture', generator: 'Texture.toJSON' },
      uuid: this.uuid,
      name: this.name,
      image: this.source.toJSON(t).uuid,
      mapping: this.mapping,
      channel: this.channel,
      repeat: [this.repeat.x, this.repeat.y],
      offset: [this.offset.x, this.offset.y],
      center: [this.center.x, this.center.y],
      rotation: this.rotation,
      wrap: [this.wrapS, this.wrapT],
      format: this.format,
      internalFormat: this.internalFormat,
      type: this.type,
      colorSpace: this.colorSpace,
      minFilter: this.minFilter,
      magFilter: this.magFilter,
      anisotropy: this.anisotropy,
      flipY: this.flipY,
      generateMipmaps: this.generateMipmaps,
      premultiplyAlpha: this.premultiplyAlpha,
      unpackAlignment: this.unpackAlignment,
    };
    return (
      Object.keys(this.userData).length > 0 && (n.userData = this.userData),
      e || (t.textures[this.uuid] = n),
      n
    );
  }
  dispose() {
    this.dispatchEvent({ type: 'dispose' });
  }
  transformUv(t) {
    if (this.mapping !== Cl) return t;
    if ((t.applyMatrix3(this.matrix), t.x < 0 || t.x > 1))
      switch (this.wrapS) {
        case $r:
          t.x = t.x - Math.floor(t.x);
          break;
        case xn:
          t.x = t.x < 0 ? 0 : 1;
          break;
        case Kr:
          Math.abs(Math.floor(t.x) % 2) === 1
            ? (t.x = Math.ceil(t.x) - t.x)
            : (t.x = t.x - Math.floor(t.x));
          break;
      }
    if (t.y < 0 || t.y > 1)
      switch (this.wrapT) {
        case $r:
          t.y = t.y - Math.floor(t.y);
          break;
        case xn:
          t.y = t.y < 0 ? 0 : 1;
          break;
        case Kr:
          Math.abs(Math.floor(t.y) % 2) === 1
            ? (t.y = Math.ceil(t.y) - t.y)
            : (t.y = t.y - Math.floor(t.y));
          break;
      }
    return (this.flipY && (t.y = 1 - t.y), t);
  }
  set needsUpdate(t) {
    t === !0 && (this.version++, (this.source.needsUpdate = !0));
  }
  set needsPMREMUpdate(t) {
    t === !0 && this.pmremVersion++;
  }
}
ye.DEFAULT_IMAGE = null;
ye.DEFAULT_MAPPING = Cl;
ye.DEFAULT_ANISOTROPY = 1;
class ue {
  constructor(t = 0, e = 0, n = 0, s = 1) {
    ((ue.prototype.isVector4 = !0), (this.x = t), (this.y = e), (this.z = n), (this.w = s));
  }
  get width() {
    return this.z;
  }
  set width(t) {
    this.z = t;
  }
  get height() {
    return this.w;
  }
  set height(t) {
    this.w = t;
  }
  set(t, e, n, s) {
    return ((this.x = t), (this.y = e), (this.z = n), (this.w = s), this);
  }
  setScalar(t) {
    return ((this.x = t), (this.y = t), (this.z = t), (this.w = t), this);
  }
  setX(t) {
    return ((this.x = t), this);
  }
  setY(t) {
    return ((this.y = t), this);
  }
  setZ(t) {
    return ((this.z = t), this);
  }
  setW(t) {
    return ((this.w = t), this);
  }
  setComponent(t, e) {
    switch (t) {
      case 0:
        this.x = e;
        break;
      case 1:
        this.y = e;
        break;
      case 2:
        this.z = e;
        break;
      case 3:
        this.w = e;
        break;
      default:
        throw new Error('index is out of range: ' + t);
    }
    return this;
  }
  getComponent(t) {
    switch (t) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      case 2:
        return this.z;
      case 3:
        return this.w;
      default:
        throw new Error('index is out of range: ' + t);
    }
  }
  clone() {
    return new this.constructor(this.x, this.y, this.z, this.w);
  }
  copy(t) {
    return (
      (this.x = t.x),
      (this.y = t.y),
      (this.z = t.z),
      (this.w = t.w !== void 0 ? t.w : 1),
      this
    );
  }
  add(t) {
    return ((this.x += t.x), (this.y += t.y), (this.z += t.z), (this.w += t.w), this);
  }
  addScalar(t) {
    return ((this.x += t), (this.y += t), (this.z += t), (this.w += t), this);
  }
  addVectors(t, e) {
    return (
      (this.x = t.x + e.x),
      (this.y = t.y + e.y),
      (this.z = t.z + e.z),
      (this.w = t.w + e.w),
      this
    );
  }
  addScaledVector(t, e) {
    return (
      (this.x += t.x * e),
      (this.y += t.y * e),
      (this.z += t.z * e),
      (this.w += t.w * e),
      this
    );
  }
  sub(t) {
    return ((this.x -= t.x), (this.y -= t.y), (this.z -= t.z), (this.w -= t.w), this);
  }
  subScalar(t) {
    return ((this.x -= t), (this.y -= t), (this.z -= t), (this.w -= t), this);
  }
  subVectors(t, e) {
    return (
      (this.x = t.x - e.x),
      (this.y = t.y - e.y),
      (this.z = t.z - e.z),
      (this.w = t.w - e.w),
      this
    );
  }
  multiply(t) {
    return ((this.x *= t.x), (this.y *= t.y), (this.z *= t.z), (this.w *= t.w), this);
  }
  multiplyScalar(t) {
    return ((this.x *= t), (this.y *= t), (this.z *= t), (this.w *= t), this);
  }
  applyMatrix4(t) {
    const e = this.x,
      n = this.y,
      s = this.z,
      r = this.w,
      a = t.elements;
    return (
      (this.x = a[0] * e + a[4] * n + a[8] * s + a[12] * r),
      (this.y = a[1] * e + a[5] * n + a[9] * s + a[13] * r),
      (this.z = a[2] * e + a[6] * n + a[10] * s + a[14] * r),
      (this.w = a[3] * e + a[7] * n + a[11] * s + a[15] * r),
      this
    );
  }
  divide(t) {
    return ((this.x /= t.x), (this.y /= t.y), (this.z /= t.z), (this.w /= t.w), this);
  }
  divideScalar(t) {
    return this.multiplyScalar(1 / t);
  }
  setAxisAngleFromQuaternion(t) {
    this.w = 2 * Math.acos(t.w);
    const e = Math.sqrt(1 - t.w * t.w);
    return (
      e < 1e-4
        ? ((this.x = 1), (this.y = 0), (this.z = 0))
        : ((this.x = t.x / e), (this.y = t.y / e), (this.z = t.z / e)),
      this
    );
  }
  setAxisAngleFromRotationMatrix(t) {
    let e, n, s, r;
    const l = t.elements,
      c = l[0],
      h = l[4],
      f = l[8],
      u = l[1],
      p = l[5],
      g = l[9],
      M = l[2],
      m = l[6],
      d = l[10];
    if (Math.abs(h - u) < 0.01 && Math.abs(f - M) < 0.01 && Math.abs(g - m) < 0.01) {
      if (
        Math.abs(h + u) < 0.1 &&
        Math.abs(f + M) < 0.1 &&
        Math.abs(g + m) < 0.1 &&
        Math.abs(c + p + d - 3) < 0.1
      )
        return (this.set(1, 0, 0, 0), this);
      e = Math.PI;
      const y = (c + 1) / 2,
        S = (p + 1) / 2,
        R = (d + 1) / 2,
        w = (h + u) / 4,
        P = (f + M) / 4,
        x = (g + m) / 4;
      return (
        y > S && y > R
          ? y < 0.01
            ? ((n = 0), (s = 0.707106781), (r = 0.707106781))
            : ((n = Math.sqrt(y)), (s = w / n), (r = P / n))
          : S > R
            ? S < 0.01
              ? ((n = 0.707106781), (s = 0), (r = 0.707106781))
              : ((s = Math.sqrt(S)), (n = w / s), (r = x / s))
            : R < 0.01
              ? ((n = 0.707106781), (s = 0.707106781), (r = 0))
              : ((r = Math.sqrt(R)), (n = P / r), (s = x / r)),
        this.set(n, s, r, e),
        this
      );
    }
    let E = Math.sqrt((m - g) * (m - g) + (f - M) * (f - M) + (u - h) * (u - h));
    return (
      Math.abs(E) < 0.001 && (E = 1),
      (this.x = (m - g) / E),
      (this.y = (f - M) / E),
      (this.z = (u - h) / E),
      (this.w = Math.acos((c + p + d - 1) / 2)),
      this
    );
  }
  setFromMatrixPosition(t) {
    const e = t.elements;
    return ((this.x = e[12]), (this.y = e[13]), (this.z = e[14]), (this.w = e[15]), this);
  }
  min(t) {
    return (
      (this.x = Math.min(this.x, t.x)),
      (this.y = Math.min(this.y, t.y)),
      (this.z = Math.min(this.z, t.z)),
      (this.w = Math.min(this.w, t.w)),
      this
    );
  }
  max(t) {
    return (
      (this.x = Math.max(this.x, t.x)),
      (this.y = Math.max(this.y, t.y)),
      (this.z = Math.max(this.z, t.z)),
      (this.w = Math.max(this.w, t.w)),
      this
    );
  }
  clamp(t, e) {
    return (
      (this.x = Bt(this.x, t.x, e.x)),
      (this.y = Bt(this.y, t.y, e.y)),
      (this.z = Bt(this.z, t.z, e.z)),
      (this.w = Bt(this.w, t.w, e.w)),
      this
    );
  }
  clampScalar(t, e) {
    return (
      (this.x = Bt(this.x, t, e)),
      (this.y = Bt(this.y, t, e)),
      (this.z = Bt(this.z, t, e)),
      (this.w = Bt(this.w, t, e)),
      this
    );
  }
  clampLength(t, e) {
    const n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Bt(n, t, e));
  }
  floor() {
    return (
      (this.x = Math.floor(this.x)),
      (this.y = Math.floor(this.y)),
      (this.z = Math.floor(this.z)),
      (this.w = Math.floor(this.w)),
      this
    );
  }
  ceil() {
    return (
      (this.x = Math.ceil(this.x)),
      (this.y = Math.ceil(this.y)),
      (this.z = Math.ceil(this.z)),
      (this.w = Math.ceil(this.w)),
      this
    );
  }
  round() {
    return (
      (this.x = Math.round(this.x)),
      (this.y = Math.round(this.y)),
      (this.z = Math.round(this.z)),
      (this.w = Math.round(this.w)),
      this
    );
  }
  roundToZero() {
    return (
      (this.x = Math.trunc(this.x)),
      (this.y = Math.trunc(this.y)),
      (this.z = Math.trunc(this.z)),
      (this.w = Math.trunc(this.w)),
      this
    );
  }
  negate() {
    return ((this.x = -this.x), (this.y = -this.y), (this.z = -this.z), (this.w = -this.w), this);
  }
  dot(t) {
    return this.x * t.x + this.y * t.y + this.z * t.z + this.w * t.w;
  }
  lengthSq() {
    return this.x * this.x + this.y * this.y + this.z * this.z + this.w * this.w;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z + this.w * this.w);
  }
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y) + Math.abs(this.z) + Math.abs(this.w);
  }
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  setLength(t) {
    return this.normalize().multiplyScalar(t);
  }
  lerp(t, e) {
    return (
      (this.x += (t.x - this.x) * e),
      (this.y += (t.y - this.y) * e),
      (this.z += (t.z - this.z) * e),
      (this.w += (t.w - this.w) * e),
      this
    );
  }
  lerpVectors(t, e, n) {
    return (
      (this.x = t.x + (e.x - t.x) * n),
      (this.y = t.y + (e.y - t.y) * n),
      (this.z = t.z + (e.z - t.z) * n),
      (this.w = t.w + (e.w - t.w) * n),
      this
    );
  }
  equals(t) {
    return t.x === this.x && t.y === this.y && t.z === this.z && t.w === this.w;
  }
  fromArray(t, e = 0) {
    return ((this.x = t[e]), (this.y = t[e + 1]), (this.z = t[e + 2]), (this.w = t[e + 3]), this);
  }
  toArray(t = [], e = 0) {
    return ((t[e] = this.x), (t[e + 1] = this.y), (t[e + 2] = this.z), (t[e + 3] = this.w), t);
  }
  fromBufferAttribute(t, e) {
    return (
      (this.x = t.getX(e)),
      (this.y = t.getY(e)),
      (this.z = t.getZ(e)),
      (this.w = t.getW(e)),
      this
    );
  }
  random() {
    return (
      (this.x = Math.random()),
      (this.y = Math.random()),
      (this.z = Math.random()),
      (this.w = Math.random()),
      this
    );
  }
  *[Symbol.iterator]() {
    (yield this.x, yield this.y, yield this.z, yield this.w);
  }
}
class wh extends jn {
  constructor(t = 1, e = 1, n = {}) {
    (super(),
      (n = Object.assign(
        {
          generateMipmaps: !1,
          internalFormat: null,
          minFilter: Ae,
          depthBuffer: !0,
          stencilBuffer: !1,
          resolveDepthBuffer: !0,
          resolveStencilBuffer: !0,
          depthTexture: null,
          samples: 0,
          count: 1,
          depth: 1,
          multiview: !1,
        },
        n
      )),
      (this.isRenderTarget = !0),
      (this.width = t),
      (this.height = e),
      (this.depth = n.depth),
      (this.scissor = new ue(0, 0, t, e)),
      (this.scissorTest = !1),
      (this.viewport = new ue(0, 0, t, e)),
      (this.textures = []));
    const s = { width: t, height: e, depth: n.depth },
      r = new ye(s),
      a = n.count;
    for (let o = 0; o < a; o++)
      ((this.textures[o] = r.clone()),
        (this.textures[o].isRenderTargetTexture = !0),
        (this.textures[o].renderTarget = this));
    (this._setTextureOptions(n),
      (this.depthBuffer = n.depthBuffer),
      (this.stencilBuffer = n.stencilBuffer),
      (this.resolveDepthBuffer = n.resolveDepthBuffer),
      (this.resolveStencilBuffer = n.resolveStencilBuffer),
      (this._depthTexture = null),
      (this.depthTexture = n.depthTexture),
      (this.samples = n.samples),
      (this.multiview = n.multiview));
  }
  _setTextureOptions(t = {}) {
    const e = { minFilter: Ae, generateMipmaps: !1, flipY: !1, internalFormat: null };
    (t.mapping !== void 0 && (e.mapping = t.mapping),
      t.wrapS !== void 0 && (e.wrapS = t.wrapS),
      t.wrapT !== void 0 && (e.wrapT = t.wrapT),
      t.wrapR !== void 0 && (e.wrapR = t.wrapR),
      t.magFilter !== void 0 && (e.magFilter = t.magFilter),
      t.minFilter !== void 0 && (e.minFilter = t.minFilter),
      t.format !== void 0 && (e.format = t.format),
      t.type !== void 0 && (e.type = t.type),
      t.anisotropy !== void 0 && (e.anisotropy = t.anisotropy),
      t.colorSpace !== void 0 && (e.colorSpace = t.colorSpace),
      t.flipY !== void 0 && (e.flipY = t.flipY),
      t.generateMipmaps !== void 0 && (e.generateMipmaps = t.generateMipmaps),
      t.internalFormat !== void 0 && (e.internalFormat = t.internalFormat));
    for (let n = 0; n < this.textures.length; n++) this.textures[n].setValues(e);
  }
  get texture() {
    return this.textures[0];
  }
  set texture(t) {
    this.textures[0] = t;
  }
  set depthTexture(t) {
    (this._depthTexture !== null && (this._depthTexture.renderTarget = null),
      t !== null && (t.renderTarget = this),
      (this._depthTexture = t));
  }
  get depthTexture() {
    return this._depthTexture;
  }
  setSize(t, e, n = 1) {
    if (this.width !== t || this.height !== e || this.depth !== n) {
      ((this.width = t), (this.height = e), (this.depth = n));
      for (let s = 0, r = this.textures.length; s < r; s++)
        ((this.textures[s].image.width = t),
          (this.textures[s].image.height = e),
          (this.textures[s].image.depth = n),
          this.textures[s].isData3DTexture !== !0 &&
            (this.textures[s].isArrayTexture = this.textures[s].image.depth > 1));
      this.dispose();
    }
    (this.viewport.set(0, 0, t, e), this.scissor.set(0, 0, t, e));
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    ((this.width = t.width),
      (this.height = t.height),
      (this.depth = t.depth),
      this.scissor.copy(t.scissor),
      (this.scissorTest = t.scissorTest),
      this.viewport.copy(t.viewport),
      (this.textures.length = 0));
    for (let e = 0, n = t.textures.length; e < n; e++) {
      ((this.textures[e] = t.textures[e].clone()),
        (this.textures[e].isRenderTargetTexture = !0),
        (this.textures[e].renderTarget = this));
      const s = Object.assign({}, t.textures[e].image);
      this.textures[e].source = new Za(s);
    }
    return (
      (this.depthBuffer = t.depthBuffer),
      (this.stencilBuffer = t.stencilBuffer),
      (this.resolveDepthBuffer = t.resolveDepthBuffer),
      (this.resolveStencilBuffer = t.resolveStencilBuffer),
      t.depthTexture !== null && (this.depthTexture = t.depthTexture.clone()),
      (this.samples = t.samples),
      this
    );
  }
  dispose() {
    this.dispatchEvent({ type: 'dispose' });
  }
}
class rn extends wh {
  constructor(t = 1, e = 1, n = {}) {
    (super(t, e, n), (this.isWebGLRenderTarget = !0));
  }
}
class Bl extends ye {
  constructor(t = null, e = 1, n = 1, s = 1) {
    (super(null),
      (this.isDataArrayTexture = !0),
      (this.image = { data: t, width: e, height: n, depth: s }),
      (this.magFilter = me),
      (this.minFilter = me),
      (this.wrapR = xn),
      (this.generateMipmaps = !1),
      (this.flipY = !1),
      (this.unpackAlignment = 1),
      (this.layerUpdates = new Set()));
  }
  addLayerUpdate(t) {
    this.layerUpdates.add(t);
  }
  clearLayerUpdates() {
    this.layerUpdates.clear();
  }
}
class Rh extends ye {
  constructor(t = null, e = 1, n = 1, s = 1) {
    (super(null),
      (this.isData3DTexture = !0),
      (this.image = { data: t, width: e, height: n, depth: s }),
      (this.magFilter = me),
      (this.minFilter = me),
      (this.wrapR = xn),
      (this.generateMipmaps = !1),
      (this.flipY = !1),
      (this.unpackAlignment = 1));
  }
}
class oe {
  constructor(t, e, n, s, r, a, o, l, c, h, f, u, p, g, M, m) {
    ((oe.prototype.isMatrix4 = !0),
      (this.elements = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
      t !== void 0 && this.set(t, e, n, s, r, a, o, l, c, h, f, u, p, g, M, m));
  }
  set(t, e, n, s, r, a, o, l, c, h, f, u, p, g, M, m) {
    const d = this.elements;
    return (
      (d[0] = t),
      (d[4] = e),
      (d[8] = n),
      (d[12] = s),
      (d[1] = r),
      (d[5] = a),
      (d[9] = o),
      (d[13] = l),
      (d[2] = c),
      (d[6] = h),
      (d[10] = f),
      (d[14] = u),
      (d[3] = p),
      (d[7] = g),
      (d[11] = M),
      (d[15] = m),
      this
    );
  }
  identity() {
    return (this.set(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1), this);
  }
  clone() {
    return new oe().fromArray(this.elements);
  }
  copy(t) {
    const e = this.elements,
      n = t.elements;
    return (
      (e[0] = n[0]),
      (e[1] = n[1]),
      (e[2] = n[2]),
      (e[3] = n[3]),
      (e[4] = n[4]),
      (e[5] = n[5]),
      (e[6] = n[6]),
      (e[7] = n[7]),
      (e[8] = n[8]),
      (e[9] = n[9]),
      (e[10] = n[10]),
      (e[11] = n[11]),
      (e[12] = n[12]),
      (e[13] = n[13]),
      (e[14] = n[14]),
      (e[15] = n[15]),
      this
    );
  }
  copyPosition(t) {
    const e = this.elements,
      n = t.elements;
    return ((e[12] = n[12]), (e[13] = n[13]), (e[14] = n[14]), this);
  }
  setFromMatrix3(t) {
    const e = t.elements;
    return (
      this.set(e[0], e[3], e[6], 0, e[1], e[4], e[7], 0, e[2], e[5], e[8], 0, 0, 0, 0, 1),
      this
    );
  }
  extractBasis(t, e, n) {
    return this.determinant() === 0
      ? (t.set(1, 0, 0), e.set(0, 1, 0), n.set(0, 0, 1), this)
      : (t.setFromMatrixColumn(this, 0),
        e.setFromMatrixColumn(this, 1),
        n.setFromMatrixColumn(this, 2),
        this);
  }
  makeBasis(t, e, n) {
    return (this.set(t.x, e.x, n.x, 0, t.y, e.y, n.y, 0, t.z, e.z, n.z, 0, 0, 0, 0, 1), this);
  }
  extractRotation(t) {
    if (t.determinant() === 0) return this.identity();
    const e = this.elements,
      n = t.elements,
      s = 1 / si.setFromMatrixColumn(t, 0).length(),
      r = 1 / si.setFromMatrixColumn(t, 1).length(),
      a = 1 / si.setFromMatrixColumn(t, 2).length();
    return (
      (e[0] = n[0] * s),
      (e[1] = n[1] * s),
      (e[2] = n[2] * s),
      (e[3] = 0),
      (e[4] = n[4] * r),
      (e[5] = n[5] * r),
      (e[6] = n[6] * r),
      (e[7] = 0),
      (e[8] = n[8] * a),
      (e[9] = n[9] * a),
      (e[10] = n[10] * a),
      (e[11] = 0),
      (e[12] = 0),
      (e[13] = 0),
      (e[14] = 0),
      (e[15] = 1),
      this
    );
  }
  makeRotationFromEuler(t) {
    const e = this.elements,
      n = t.x,
      s = t.y,
      r = t.z,
      a = Math.cos(n),
      o = Math.sin(n),
      l = Math.cos(s),
      c = Math.sin(s),
      h = Math.cos(r),
      f = Math.sin(r);
    if (t.order === 'XYZ') {
      const u = a * h,
        p = a * f,
        g = o * h,
        M = o * f;
      ((e[0] = l * h),
        (e[4] = -l * f),
        (e[8] = c),
        (e[1] = p + g * c),
        (e[5] = u - M * c),
        (e[9] = -o * l),
        (e[2] = M - u * c),
        (e[6] = g + p * c),
        (e[10] = a * l));
    } else if (t.order === 'YXZ') {
      const u = l * h,
        p = l * f,
        g = c * h,
        M = c * f;
      ((e[0] = u + M * o),
        (e[4] = g * o - p),
        (e[8] = a * c),
        (e[1] = a * f),
        (e[5] = a * h),
        (e[9] = -o),
        (e[2] = p * o - g),
        (e[6] = M + u * o),
        (e[10] = a * l));
    } else if (t.order === 'ZXY') {
      const u = l * h,
        p = l * f,
        g = c * h,
        M = c * f;
      ((e[0] = u - M * o),
        (e[4] = -a * f),
        (e[8] = g + p * o),
        (e[1] = p + g * o),
        (e[5] = a * h),
        (e[9] = M - u * o),
        (e[2] = -a * c),
        (e[6] = o),
        (e[10] = a * l));
    } else if (t.order === 'ZYX') {
      const u = a * h,
        p = a * f,
        g = o * h,
        M = o * f;
      ((e[0] = l * h),
        (e[4] = g * c - p),
        (e[8] = u * c + M),
        (e[1] = l * f),
        (e[5] = M * c + u),
        (e[9] = p * c - g),
        (e[2] = -c),
        (e[6] = o * l),
        (e[10] = a * l));
    } else if (t.order === 'YZX') {
      const u = a * l,
        p = a * c,
        g = o * l,
        M = o * c;
      ((e[0] = l * h),
        (e[4] = M - u * f),
        (e[8] = g * f + p),
        (e[1] = f),
        (e[5] = a * h),
        (e[9] = -o * h),
        (e[2] = -c * h),
        (e[6] = p * f + g),
        (e[10] = u - M * f));
    } else if (t.order === 'XZY') {
      const u = a * l,
        p = a * c,
        g = o * l,
        M = o * c;
      ((e[0] = l * h),
        (e[4] = -f),
        (e[8] = c * h),
        (e[1] = u * f + M),
        (e[5] = a * h),
        (e[9] = p * f - g),
        (e[2] = g * f - p),
        (e[6] = o * h),
        (e[10] = M * f + u));
    }
    return (
      (e[3] = 0),
      (e[7] = 0),
      (e[11] = 0),
      (e[12] = 0),
      (e[13] = 0),
      (e[14] = 0),
      (e[15] = 1),
      this
    );
  }
  makeRotationFromQuaternion(t) {
    return this.compose(Ch, t, Ph);
  }
  lookAt(t, e, n) {
    const s = this.elements;
    return (
      Ie.subVectors(t, e),
      Ie.lengthSq() === 0 && (Ie.z = 1),
      Ie.normalize(),
      An.crossVectors(n, Ie),
      An.lengthSq() === 0 &&
        (Math.abs(n.z) === 1 ? (Ie.x += 1e-4) : (Ie.z += 1e-4),
        Ie.normalize(),
        An.crossVectors(n, Ie)),
      An.normalize(),
      ss.crossVectors(Ie, An),
      (s[0] = An.x),
      (s[4] = ss.x),
      (s[8] = Ie.x),
      (s[1] = An.y),
      (s[5] = ss.y),
      (s[9] = Ie.y),
      (s[2] = An.z),
      (s[6] = ss.z),
      (s[10] = Ie.z),
      this
    );
  }
  multiply(t) {
    return this.multiplyMatrices(this, t);
  }
  premultiply(t) {
    return this.multiplyMatrices(t, this);
  }
  multiplyMatrices(t, e) {
    const n = t.elements,
      s = e.elements,
      r = this.elements,
      a = n[0],
      o = n[4],
      l = n[8],
      c = n[12],
      h = n[1],
      f = n[5],
      u = n[9],
      p = n[13],
      g = n[2],
      M = n[6],
      m = n[10],
      d = n[14],
      E = n[3],
      y = n[7],
      S = n[11],
      R = n[15],
      w = s[0],
      P = s[4],
      x = s[8],
      b = s[12],
      H = s[1],
      C = s[5],
      N = s[9],
      z = s[13],
      k = s[2],
      F = s[6],
      O = s[10],
      B = s[14],
      nt = s[3],
      j = s[7],
      mt = s[11],
      _t = s[15];
    return (
      (r[0] = a * w + o * H + l * k + c * nt),
      (r[4] = a * P + o * C + l * F + c * j),
      (r[8] = a * x + o * N + l * O + c * mt),
      (r[12] = a * b + o * z + l * B + c * _t),
      (r[1] = h * w + f * H + u * k + p * nt),
      (r[5] = h * P + f * C + u * F + p * j),
      (r[9] = h * x + f * N + u * O + p * mt),
      (r[13] = h * b + f * z + u * B + p * _t),
      (r[2] = g * w + M * H + m * k + d * nt),
      (r[6] = g * P + M * C + m * F + d * j),
      (r[10] = g * x + M * N + m * O + d * mt),
      (r[14] = g * b + M * z + m * B + d * _t),
      (r[3] = E * w + y * H + S * k + R * nt),
      (r[7] = E * P + y * C + S * F + R * j),
      (r[11] = E * x + y * N + S * O + R * mt),
      (r[15] = E * b + y * z + S * B + R * _t),
      this
    );
  }
  multiplyScalar(t) {
    const e = this.elements;
    return (
      (e[0] *= t),
      (e[4] *= t),
      (e[8] *= t),
      (e[12] *= t),
      (e[1] *= t),
      (e[5] *= t),
      (e[9] *= t),
      (e[13] *= t),
      (e[2] *= t),
      (e[6] *= t),
      (e[10] *= t),
      (e[14] *= t),
      (e[3] *= t),
      (e[7] *= t),
      (e[11] *= t),
      (e[15] *= t),
      this
    );
  }
  determinant() {
    const t = this.elements,
      e = t[0],
      n = t[4],
      s = t[8],
      r = t[12],
      a = t[1],
      o = t[5],
      l = t[9],
      c = t[13],
      h = t[2],
      f = t[6],
      u = t[10],
      p = t[14],
      g = t[3],
      M = t[7],
      m = t[11],
      d = t[15],
      E = l * p - c * u,
      y = o * p - c * f,
      S = o * u - l * f,
      R = a * p - c * h,
      w = a * u - l * h,
      P = a * f - o * h;
    return (
      e * (M * E - m * y + d * S) -
      n * (g * E - m * R + d * w) +
      s * (g * y - M * R + d * P) -
      r * (g * S - M * w + m * P)
    );
  }
  transpose() {
    const t = this.elements;
    let e;
    return (
      (e = t[1]),
      (t[1] = t[4]),
      (t[4] = e),
      (e = t[2]),
      (t[2] = t[8]),
      (t[8] = e),
      (e = t[6]),
      (t[6] = t[9]),
      (t[9] = e),
      (e = t[3]),
      (t[3] = t[12]),
      (t[12] = e),
      (e = t[7]),
      (t[7] = t[13]),
      (t[13] = e),
      (e = t[11]),
      (t[11] = t[14]),
      (t[14] = e),
      this
    );
  }
  setPosition(t, e, n) {
    const s = this.elements;
    return (
      t.isVector3
        ? ((s[12] = t.x), (s[13] = t.y), (s[14] = t.z))
        : ((s[12] = t), (s[13] = e), (s[14] = n)),
      this
    );
  }
  invert() {
    const t = this.elements,
      e = t[0],
      n = t[1],
      s = t[2],
      r = t[3],
      a = t[4],
      o = t[5],
      l = t[6],
      c = t[7],
      h = t[8],
      f = t[9],
      u = t[10],
      p = t[11],
      g = t[12],
      M = t[13],
      m = t[14],
      d = t[15],
      E = e * o - n * a,
      y = e * l - s * a,
      S = e * c - r * a,
      R = n * l - s * o,
      w = n * c - r * o,
      P = s * c - r * l,
      x = h * M - f * g,
      b = h * m - u * g,
      H = h * d - p * g,
      C = f * m - u * M,
      N = f * d - p * M,
      z = u * d - p * m,
      k = E * z - y * N + S * C + R * H - w * b + P * x;
    if (k === 0) return this.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    const F = 1 / k;
    return (
      (t[0] = (o * z - l * N + c * C) * F),
      (t[1] = (s * N - n * z - r * C) * F),
      (t[2] = (M * P - m * w + d * R) * F),
      (t[3] = (u * w - f * P - p * R) * F),
      (t[4] = (l * H - a * z - c * b) * F),
      (t[5] = (e * z - s * H + r * b) * F),
      (t[6] = (m * S - g * P - d * y) * F),
      (t[7] = (h * P - u * S + p * y) * F),
      (t[8] = (a * N - o * H + c * x) * F),
      (t[9] = (n * H - e * N - r * x) * F),
      (t[10] = (g * w - M * S + d * E) * F),
      (t[11] = (f * S - h * w - p * E) * F),
      (t[12] = (o * b - a * C - l * x) * F),
      (t[13] = (e * C - n * b + s * x) * F),
      (t[14] = (M * y - g * R - m * E) * F),
      (t[15] = (h * R - f * y + u * E) * F),
      this
    );
  }
  scale(t) {
    const e = this.elements,
      n = t.x,
      s = t.y,
      r = t.z;
    return (
      (e[0] *= n),
      (e[4] *= s),
      (e[8] *= r),
      (e[1] *= n),
      (e[5] *= s),
      (e[9] *= r),
      (e[2] *= n),
      (e[6] *= s),
      (e[10] *= r),
      (e[3] *= n),
      (e[7] *= s),
      (e[11] *= r),
      this
    );
  }
  getMaxScaleOnAxis() {
    const t = this.elements,
      e = t[0] * t[0] + t[1] * t[1] + t[2] * t[2],
      n = t[4] * t[4] + t[5] * t[5] + t[6] * t[6],
      s = t[8] * t[8] + t[9] * t[9] + t[10] * t[10];
    return Math.sqrt(Math.max(e, n, s));
  }
  makeTranslation(t, e, n) {
    return (
      t.isVector3
        ? this.set(1, 0, 0, t.x, 0, 1, 0, t.y, 0, 0, 1, t.z, 0, 0, 0, 1)
        : this.set(1, 0, 0, t, 0, 1, 0, e, 0, 0, 1, n, 0, 0, 0, 1),
      this
    );
  }
  makeRotationX(t) {
    const e = Math.cos(t),
      n = Math.sin(t);
    return (this.set(1, 0, 0, 0, 0, e, -n, 0, 0, n, e, 0, 0, 0, 0, 1), this);
  }
  makeRotationY(t) {
    const e = Math.cos(t),
      n = Math.sin(t);
    return (this.set(e, 0, n, 0, 0, 1, 0, 0, -n, 0, e, 0, 0, 0, 0, 1), this);
  }
  makeRotationZ(t) {
    const e = Math.cos(t),
      n = Math.sin(t);
    return (this.set(e, -n, 0, 0, n, e, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1), this);
  }
  makeRotationAxis(t, e) {
    const n = Math.cos(e),
      s = Math.sin(e),
      r = 1 - n,
      a = t.x,
      o = t.y,
      l = t.z,
      c = r * a,
      h = r * o;
    return (
      this.set(
        c * a + n,
        c * o - s * l,
        c * l + s * o,
        0,
        c * o + s * l,
        h * o + n,
        h * l - s * a,
        0,
        c * l - s * o,
        h * l + s * a,
        r * l * l + n,
        0,
        0,
        0,
        0,
        1
      ),
      this
    );
  }
  makeScale(t, e, n) {
    return (this.set(t, 0, 0, 0, 0, e, 0, 0, 0, 0, n, 0, 0, 0, 0, 1), this);
  }
  makeShear(t, e, n, s, r, a) {
    return (this.set(1, n, r, 0, t, 1, a, 0, e, s, 1, 0, 0, 0, 0, 1), this);
  }
  compose(t, e, n) {
    const s = this.elements,
      r = e._x,
      a = e._y,
      o = e._z,
      l = e._w,
      c = r + r,
      h = a + a,
      f = o + o,
      u = r * c,
      p = r * h,
      g = r * f,
      M = a * h,
      m = a * f,
      d = o * f,
      E = l * c,
      y = l * h,
      S = l * f,
      R = n.x,
      w = n.y,
      P = n.z;
    return (
      (s[0] = (1 - (M + d)) * R),
      (s[1] = (p + S) * R),
      (s[2] = (g - y) * R),
      (s[3] = 0),
      (s[4] = (p - S) * w),
      (s[5] = (1 - (u + d)) * w),
      (s[6] = (m + E) * w),
      (s[7] = 0),
      (s[8] = (g + y) * P),
      (s[9] = (m - E) * P),
      (s[10] = (1 - (u + M)) * P),
      (s[11] = 0),
      (s[12] = t.x),
      (s[13] = t.y),
      (s[14] = t.z),
      (s[15] = 1),
      this
    );
  }
  decompose(t, e, n) {
    const s = this.elements;
    ((t.x = s[12]), (t.y = s[13]), (t.z = s[14]));
    const r = this.determinant();
    if (r === 0) return (n.set(1, 1, 1), e.identity(), this);
    let a = si.set(s[0], s[1], s[2]).length();
    const o = si.set(s[4], s[5], s[6]).length(),
      l = si.set(s[8], s[9], s[10]).length();
    (r < 0 && (a = -a), ke.copy(this));
    const c = 1 / a,
      h = 1 / o,
      f = 1 / l;
    return (
      (ke.elements[0] *= c),
      (ke.elements[1] *= c),
      (ke.elements[2] *= c),
      (ke.elements[4] *= h),
      (ke.elements[5] *= h),
      (ke.elements[6] *= h),
      (ke.elements[8] *= f),
      (ke.elements[9] *= f),
      (ke.elements[10] *= f),
      e.setFromRotationMatrix(ke),
      (n.x = a),
      (n.y = o),
      (n.z = l),
      this
    );
  }
  makePerspective(t, e, n, s, r, a, o = Ze, l = !1) {
    const c = this.elements,
      h = (2 * r) / (e - t),
      f = (2 * r) / (n - s),
      u = (e + t) / (e - t),
      p = (n + s) / (n - s);
    let g, M;
    if (l) ((g = r / (a - r)), (M = (a * r) / (a - r)));
    else if (o === Ze) ((g = -(a + r) / (a - r)), (M = (-2 * a * r) / (a - r)));
    else if (o === qi) ((g = -a / (a - r)), (M = (-a * r) / (a - r)));
    else throw new Error('THREE.Matrix4.makePerspective(): Invalid coordinate system: ' + o);
    return (
      (c[0] = h),
      (c[4] = 0),
      (c[8] = u),
      (c[12] = 0),
      (c[1] = 0),
      (c[5] = f),
      (c[9] = p),
      (c[13] = 0),
      (c[2] = 0),
      (c[6] = 0),
      (c[10] = g),
      (c[14] = M),
      (c[3] = 0),
      (c[7] = 0),
      (c[11] = -1),
      (c[15] = 0),
      this
    );
  }
  makeOrthographic(t, e, n, s, r, a, o = Ze, l = !1) {
    const c = this.elements,
      h = 2 / (e - t),
      f = 2 / (n - s),
      u = -(e + t) / (e - t),
      p = -(n + s) / (n - s);
    let g, M;
    if (l) ((g = 1 / (a - r)), (M = a / (a - r)));
    else if (o === Ze) ((g = -2 / (a - r)), (M = -(a + r) / (a - r)));
    else if (o === qi) ((g = -1 / (a - r)), (M = -r / (a - r)));
    else throw new Error('THREE.Matrix4.makeOrthographic(): Invalid coordinate system: ' + o);
    return (
      (c[0] = h),
      (c[4] = 0),
      (c[8] = 0),
      (c[12] = u),
      (c[1] = 0),
      (c[5] = f),
      (c[9] = 0),
      (c[13] = p),
      (c[2] = 0),
      (c[6] = 0),
      (c[10] = g),
      (c[14] = M),
      (c[3] = 0),
      (c[7] = 0),
      (c[11] = 0),
      (c[15] = 1),
      this
    );
  }
  equals(t) {
    const e = this.elements,
      n = t.elements;
    for (let s = 0; s < 16; s++) if (e[s] !== n[s]) return !1;
    return !0;
  }
  fromArray(t, e = 0) {
    for (let n = 0; n < 16; n++) this.elements[n] = t[n + e];
    return this;
  }
  toArray(t = [], e = 0) {
    const n = this.elements;
    return (
      (t[e] = n[0]),
      (t[e + 1] = n[1]),
      (t[e + 2] = n[2]),
      (t[e + 3] = n[3]),
      (t[e + 4] = n[4]),
      (t[e + 5] = n[5]),
      (t[e + 6] = n[6]),
      (t[e + 7] = n[7]),
      (t[e + 8] = n[8]),
      (t[e + 9] = n[9]),
      (t[e + 10] = n[10]),
      (t[e + 11] = n[11]),
      (t[e + 12] = n[12]),
      (t[e + 13] = n[13]),
      (t[e + 14] = n[14]),
      (t[e + 15] = n[15]),
      t
    );
  }
}
const si = new L(),
  ke = new oe(),
  Ch = new L(0, 0, 0),
  Ph = new L(1, 1, 1),
  An = new L(),
  ss = new L(),
  Ie = new L(),
  yo = new oe(),
  Eo = new Ri();
class Ge {
  constructor(t = 0, e = 0, n = 0, s = Ge.DEFAULT_ORDER) {
    ((this.isEuler = !0), (this._x = t), (this._y = e), (this._z = n), (this._order = s));
  }
  get x() {
    return this._x;
  }
  set x(t) {
    ((this._x = t), this._onChangeCallback());
  }
  get y() {
    return this._y;
  }
  set y(t) {
    ((this._y = t), this._onChangeCallback());
  }
  get z() {
    return this._z;
  }
  set z(t) {
    ((this._z = t), this._onChangeCallback());
  }
  get order() {
    return this._order;
  }
  set order(t) {
    ((this._order = t), this._onChangeCallback());
  }
  set(t, e, n, s = this._order) {
    return (
      (this._x = t),
      (this._y = e),
      (this._z = n),
      (this._order = s),
      this._onChangeCallback(),
      this
    );
  }
  clone() {
    return new this.constructor(this._x, this._y, this._z, this._order);
  }
  copy(t) {
    return (
      (this._x = t._x),
      (this._y = t._y),
      (this._z = t._z),
      (this._order = t._order),
      this._onChangeCallback(),
      this
    );
  }
  setFromRotationMatrix(t, e = this._order, n = !0) {
    const s = t.elements,
      r = s[0],
      a = s[4],
      o = s[8],
      l = s[1],
      c = s[5],
      h = s[9],
      f = s[2],
      u = s[6],
      p = s[10];
    switch (e) {
      case 'XYZ':
        ((this._y = Math.asin(Bt(o, -1, 1))),
          Math.abs(o) < 0.9999999
            ? ((this._x = Math.atan2(-h, p)), (this._z = Math.atan2(-a, r)))
            : ((this._x = Math.atan2(u, c)), (this._z = 0)));
        break;
      case 'YXZ':
        ((this._x = Math.asin(-Bt(h, -1, 1))),
          Math.abs(h) < 0.9999999
            ? ((this._y = Math.atan2(o, p)), (this._z = Math.atan2(l, c)))
            : ((this._y = Math.atan2(-f, r)), (this._z = 0)));
        break;
      case 'ZXY':
        ((this._x = Math.asin(Bt(u, -1, 1))),
          Math.abs(u) < 0.9999999
            ? ((this._y = Math.atan2(-f, p)), (this._z = Math.atan2(-a, c)))
            : ((this._y = 0), (this._z = Math.atan2(l, r))));
        break;
      case 'ZYX':
        ((this._y = Math.asin(-Bt(f, -1, 1))),
          Math.abs(f) < 0.9999999
            ? ((this._x = Math.atan2(u, p)), (this._z = Math.atan2(l, r)))
            : ((this._x = 0), (this._z = Math.atan2(-a, c))));
        break;
      case 'YZX':
        ((this._z = Math.asin(Bt(l, -1, 1))),
          Math.abs(l) < 0.9999999
            ? ((this._x = Math.atan2(-h, c)), (this._y = Math.atan2(-f, r)))
            : ((this._x = 0), (this._y = Math.atan2(o, p))));
        break;
      case 'XZY':
        ((this._z = Math.asin(-Bt(a, -1, 1))),
          Math.abs(a) < 0.9999999
            ? ((this._x = Math.atan2(u, c)), (this._y = Math.atan2(o, r)))
            : ((this._x = Math.atan2(-h, p)), (this._y = 0)));
        break;
      default:
        Ft('Euler: .setFromRotationMatrix() encountered an unknown order: ' + e);
    }
    return ((this._order = e), n === !0 && this._onChangeCallback(), this);
  }
  setFromQuaternion(t, e, n) {
    return (yo.makeRotationFromQuaternion(t), this.setFromRotationMatrix(yo, e, n));
  }
  setFromVector3(t, e = this._order) {
    return this.set(t.x, t.y, t.z, e);
  }
  reorder(t) {
    return (Eo.setFromEuler(this), this.setFromQuaternion(Eo, t));
  }
  equals(t) {
    return t._x === this._x && t._y === this._y && t._z === this._z && t._order === this._order;
  }
  fromArray(t) {
    return (
      (this._x = t[0]),
      (this._y = t[1]),
      (this._z = t[2]),
      t[3] !== void 0 && (this._order = t[3]),
      this._onChangeCallback(),
      this
    );
  }
  toArray(t = [], e = 0) {
    return (
      (t[e] = this._x),
      (t[e + 1] = this._y),
      (t[e + 2] = this._z),
      (t[e + 3] = this._order),
      t
    );
  }
  _onChange(t) {
    return ((this._onChangeCallback = t), this);
  }
  _onChangeCallback() {}
  *[Symbol.iterator]() {
    (yield this._x, yield this._y, yield this._z, yield this._order);
  }
}
Ge.DEFAULT_ORDER = 'XYZ';
class Ja {
  constructor() {
    this.mask = 1;
  }
  set(t) {
    this.mask = ((1 << t) | 0) >>> 0;
  }
  enable(t) {
    this.mask |= (1 << t) | 0;
  }
  enableAll() {
    this.mask = -1;
  }
  toggle(t) {
    this.mask ^= (1 << t) | 0;
  }
  disable(t) {
    this.mask &= ~((1 << t) | 0);
  }
  disableAll() {
    this.mask = 0;
  }
  test(t) {
    return (this.mask & t.mask) !== 0;
  }
  isEnabled(t) {
    return (this.mask & ((1 << t) | 0)) !== 0;
  }
}
let Lh = 0;
const bo = new L(),
  ri = new Ri(),
  un = new oe(),
  rs = new L(),
  Pi = new L(),
  Dh = new L(),
  Ih = new Ri(),
  To = new L(1, 0, 0),
  Ao = new L(0, 1, 0),
  wo = new L(0, 0, 1),
  Ro = { type: 'added' },
  Uh = { type: 'removed' },
  ai = { type: 'childadded', child: null },
  hr = { type: 'childremoved', child: null };
class de extends jn {
  constructor() {
    (super(),
      (this.isObject3D = !0),
      Object.defineProperty(this, 'id', { value: Lh++ }),
      (this.uuid = sn()),
      (this.name = ''),
      (this.type = 'Object3D'),
      (this.parent = null),
      (this.children = []),
      (this.up = de.DEFAULT_UP.clone()));
    const t = new L(),
      e = new Ge(),
      n = new Ri(),
      s = new L(1, 1, 1);
    function r() {
      n.setFromEuler(e, !1);
    }
    function a() {
      e.setFromQuaternion(n, void 0, !1);
    }
    (e._onChange(r),
      n._onChange(a),
      Object.defineProperties(this, {
        position: { configurable: !0, enumerable: !0, value: t },
        rotation: { configurable: !0, enumerable: !0, value: e },
        quaternion: { configurable: !0, enumerable: !0, value: n },
        scale: { configurable: !0, enumerable: !0, value: s },
        modelViewMatrix: { value: new oe() },
        normalMatrix: { value: new Xt() },
      }),
      (this.matrix = new oe()),
      (this.matrixWorld = new oe()),
      (this.matrixAutoUpdate = de.DEFAULT_MATRIX_AUTO_UPDATE),
      (this.matrixWorldAutoUpdate = de.DEFAULT_MATRIX_WORLD_AUTO_UPDATE),
      (this.matrixWorldNeedsUpdate = !1),
      (this.layers = new Ja()),
      (this.visible = !0),
      (this.castShadow = !1),
      (this.receiveShadow = !1),
      (this.frustumCulled = !0),
      (this.renderOrder = 0),
      (this.animations = []),
      (this.customDepthMaterial = void 0),
      (this.customDistanceMaterial = void 0),
      (this.static = !1),
      (this.userData = {}),
      (this.pivot = null));
  }
  onBeforeShadow() {}
  onAfterShadow() {}
  onBeforeRender() {}
  onAfterRender() {}
  applyMatrix4(t) {
    (this.matrixAutoUpdate && this.updateMatrix(),
      this.matrix.premultiply(t),
      this.matrix.decompose(this.position, this.quaternion, this.scale));
  }
  applyQuaternion(t) {
    return (this.quaternion.premultiply(t), this);
  }
  setRotationFromAxisAngle(t, e) {
    this.quaternion.setFromAxisAngle(t, e);
  }
  setRotationFromEuler(t) {
    this.quaternion.setFromEuler(t, !0);
  }
  setRotationFromMatrix(t) {
    this.quaternion.setFromRotationMatrix(t);
  }
  setRotationFromQuaternion(t) {
    this.quaternion.copy(t);
  }
  rotateOnAxis(t, e) {
    return (ri.setFromAxisAngle(t, e), this.quaternion.multiply(ri), this);
  }
  rotateOnWorldAxis(t, e) {
    return (ri.setFromAxisAngle(t, e), this.quaternion.premultiply(ri), this);
  }
  rotateX(t) {
    return this.rotateOnAxis(To, t);
  }
  rotateY(t) {
    return this.rotateOnAxis(Ao, t);
  }
  rotateZ(t) {
    return this.rotateOnAxis(wo, t);
  }
  translateOnAxis(t, e) {
    return (
      bo.copy(t).applyQuaternion(this.quaternion),
      this.position.add(bo.multiplyScalar(e)),
      this
    );
  }
  translateX(t) {
    return this.translateOnAxis(To, t);
  }
  translateY(t) {
    return this.translateOnAxis(Ao, t);
  }
  translateZ(t) {
    return this.translateOnAxis(wo, t);
  }
  localToWorld(t) {
    return (this.updateWorldMatrix(!0, !1), t.applyMatrix4(this.matrixWorld));
  }
  worldToLocal(t) {
    return (this.updateWorldMatrix(!0, !1), t.applyMatrix4(un.copy(this.matrixWorld).invert()));
  }
  lookAt(t, e, n) {
    t.isVector3 ? rs.copy(t) : rs.set(t, e, n);
    const s = this.parent;
    (this.updateWorldMatrix(!0, !1),
      Pi.setFromMatrixPosition(this.matrixWorld),
      this.isCamera || this.isLight ? un.lookAt(Pi, rs, this.up) : un.lookAt(rs, Pi, this.up),
      this.quaternion.setFromRotationMatrix(un),
      s &&
        (un.extractRotation(s.matrixWorld),
        ri.setFromRotationMatrix(un),
        this.quaternion.premultiply(ri.invert())));
  }
  add(t) {
    if (arguments.length > 1) {
      for (let e = 0; e < arguments.length; e++) this.add(arguments[e]);
      return this;
    }
    return t === this
      ? (Jt("Object3D.add: object can't be added as a child of itself.", t), this)
      : (t && t.isObject3D
          ? (t.removeFromParent(),
            (t.parent = this),
            this.children.push(t),
            t.dispatchEvent(Ro),
            (ai.child = t),
            this.dispatchEvent(ai),
            (ai.child = null))
          : Jt('Object3D.add: object not an instance of THREE.Object3D.', t),
        this);
  }
  remove(t) {
    if (arguments.length > 1) {
      for (let n = 0; n < arguments.length; n++) this.remove(arguments[n]);
      return this;
    }
    const e = this.children.indexOf(t);
    return (
      e !== -1 &&
        ((t.parent = null),
        this.children.splice(e, 1),
        t.dispatchEvent(Uh),
        (hr.child = t),
        this.dispatchEvent(hr),
        (hr.child = null)),
      this
    );
  }
  removeFromParent() {
    const t = this.parent;
    return (t !== null && t.remove(this), this);
  }
  clear() {
    return this.remove(...this.children);
  }
  attach(t) {
    return (
      this.updateWorldMatrix(!0, !1),
      un.copy(this.matrixWorld).invert(),
      t.parent !== null && (t.parent.updateWorldMatrix(!0, !1), un.multiply(t.parent.matrixWorld)),
      t.applyMatrix4(un),
      t.removeFromParent(),
      (t.parent = this),
      this.children.push(t),
      t.updateWorldMatrix(!1, !0),
      t.dispatchEvent(Ro),
      (ai.child = t),
      this.dispatchEvent(ai),
      (ai.child = null),
      this
    );
  }
  getObjectById(t) {
    return this.getObjectByProperty('id', t);
  }
  getObjectByName(t) {
    return this.getObjectByProperty('name', t);
  }
  getObjectByProperty(t, e) {
    if (this[t] === e) return this;
    for (let n = 0, s = this.children.length; n < s; n++) {
      const a = this.children[n].getObjectByProperty(t, e);
      if (a !== void 0) return a;
    }
  }
  getObjectsByProperty(t, e, n = []) {
    this[t] === e && n.push(this);
    const s = this.children;
    for (let r = 0, a = s.length; r < a; r++) s[r].getObjectsByProperty(t, e, n);
    return n;
  }
  getWorldPosition(t) {
    return (this.updateWorldMatrix(!0, !1), t.setFromMatrixPosition(this.matrixWorld));
  }
  getWorldQuaternion(t) {
    return (this.updateWorldMatrix(!0, !1), this.matrixWorld.decompose(Pi, t, Dh), t);
  }
  getWorldScale(t) {
    return (this.updateWorldMatrix(!0, !1), this.matrixWorld.decompose(Pi, Ih, t), t);
  }
  getWorldDirection(t) {
    this.updateWorldMatrix(!0, !1);
    const e = this.matrixWorld.elements;
    return t.set(e[8], e[9], e[10]).normalize();
  }
  raycast() {}
  traverse(t) {
    t(this);
    const e = this.children;
    for (let n = 0, s = e.length; n < s; n++) e[n].traverse(t);
  }
  traverseVisible(t) {
    if (this.visible === !1) return;
    t(this);
    const e = this.children;
    for (let n = 0, s = e.length; n < s; n++) e[n].traverseVisible(t);
  }
  traverseAncestors(t) {
    const e = this.parent;
    e !== null && (t(e), e.traverseAncestors(t));
  }
  updateMatrix() {
    this.matrix.compose(this.position, this.quaternion, this.scale);
    const t = this.pivot;
    if (t !== null) {
      const e = t.x,
        n = t.y,
        s = t.z,
        r = this.matrix.elements;
      ((r[12] += e - r[0] * e - r[4] * n - r[8] * s),
        (r[13] += n - r[1] * e - r[5] * n - r[9] * s),
        (r[14] += s - r[2] * e - r[6] * n - r[10] * s));
    }
    this.matrixWorldNeedsUpdate = !0;
  }
  updateMatrixWorld(t) {
    (this.matrixAutoUpdate && this.updateMatrix(),
      (this.matrixWorldNeedsUpdate || t) &&
        (this.matrixWorldAutoUpdate === !0 &&
          (this.parent === null
            ? this.matrixWorld.copy(this.matrix)
            : this.matrixWorld.multiplyMatrices(this.parent.matrixWorld, this.matrix)),
        (this.matrixWorldNeedsUpdate = !1),
        (t = !0)));
    const e = this.children;
    for (let n = 0, s = e.length; n < s; n++) e[n].updateMatrixWorld(t);
  }
  updateWorldMatrix(t, e) {
    const n = this.parent;
    if (
      (t === !0 && n !== null && n.updateWorldMatrix(!0, !1),
      this.matrixAutoUpdate && this.updateMatrix(),
      this.matrixWorldAutoUpdate === !0 &&
        (this.parent === null
          ? this.matrixWorld.copy(this.matrix)
          : this.matrixWorld.multiplyMatrices(this.parent.matrixWorld, this.matrix)),
      e === !0)
    ) {
      const s = this.children;
      for (let r = 0, a = s.length; r < a; r++) s[r].updateWorldMatrix(!1, !0);
    }
  }
  toJSON(t) {
    const e = t === void 0 || typeof t == 'string',
      n = {};
    e &&
      ((t = {
        geometries: {},
        materials: {},
        textures: {},
        images: {},
        shapes: {},
        skeletons: {},
        animations: {},
        nodes: {},
      }),
      (n.metadata = { version: 4.7, type: 'Object', generator: 'Object3D.toJSON' }));
    const s = {};
    ((s.uuid = this.uuid),
      (s.type = this.type),
      this.name !== '' && (s.name = this.name),
      this.castShadow === !0 && (s.castShadow = !0),
      this.receiveShadow === !0 && (s.receiveShadow = !0),
      this.visible === !1 && (s.visible = !1),
      this.frustumCulled === !1 && (s.frustumCulled = !1),
      this.renderOrder !== 0 && (s.renderOrder = this.renderOrder),
      this.static !== !1 && (s.static = this.static),
      Object.keys(this.userData).length > 0 && (s.userData = this.userData),
      (s.layers = this.layers.mask),
      (s.matrix = this.matrix.toArray()),
      (s.up = this.up.toArray()),
      this.pivot !== null && (s.pivot = this.pivot.toArray()),
      this.matrixAutoUpdate === !1 && (s.matrixAutoUpdate = !1),
      this.morphTargetDictionary !== void 0 &&
        (s.morphTargetDictionary = Object.assign({}, this.morphTargetDictionary)),
      this.morphTargetInfluences !== void 0 &&
        (s.morphTargetInfluences = this.morphTargetInfluences.slice()),
      this.isInstancedMesh &&
        ((s.type = 'InstancedMesh'),
        (s.count = this.count),
        (s.instanceMatrix = this.instanceMatrix.toJSON()),
        this.instanceColor !== null && (s.instanceColor = this.instanceColor.toJSON())),
      this.isBatchedMesh &&
        ((s.type = 'BatchedMesh'),
        (s.perObjectFrustumCulled = this.perObjectFrustumCulled),
        (s.sortObjects = this.sortObjects),
        (s.drawRanges = this._drawRanges),
        (s.reservedRanges = this._reservedRanges),
        (s.geometryInfo = this._geometryInfo.map((o) => ({
          ...o,
          boundingBox: o.boundingBox ? o.boundingBox.toJSON() : void 0,
          boundingSphere: o.boundingSphere ? o.boundingSphere.toJSON() : void 0,
        }))),
        (s.instanceInfo = this._instanceInfo.map((o) => ({ ...o }))),
        (s.availableInstanceIds = this._availableInstanceIds.slice()),
        (s.availableGeometryIds = this._availableGeometryIds.slice()),
        (s.nextIndexStart = this._nextIndexStart),
        (s.nextVertexStart = this._nextVertexStart),
        (s.geometryCount = this._geometryCount),
        (s.maxInstanceCount = this._maxInstanceCount),
        (s.maxVertexCount = this._maxVertexCount),
        (s.maxIndexCount = this._maxIndexCount),
        (s.geometryInitialized = this._geometryInitialized),
        (s.matricesTexture = this._matricesTexture.toJSON(t)),
        (s.indirectTexture = this._indirectTexture.toJSON(t)),
        this._colorsTexture !== null && (s.colorsTexture = this._colorsTexture.toJSON(t)),
        this.boundingSphere !== null && (s.boundingSphere = this.boundingSphere.toJSON()),
        this.boundingBox !== null && (s.boundingBox = this.boundingBox.toJSON())));
    function r(o, l) {
      return (o[l.uuid] === void 0 && (o[l.uuid] = l.toJSON(t)), l.uuid);
    }
    if (this.isScene)
      (this.background &&
        (this.background.isColor
          ? (s.background = this.background.toJSON())
          : this.background.isTexture && (s.background = this.background.toJSON(t).uuid)),
        this.environment &&
          this.environment.isTexture &&
          this.environment.isRenderTargetTexture !== !0 &&
          (s.environment = this.environment.toJSON(t).uuid));
    else if (this.isMesh || this.isLine || this.isPoints) {
      s.geometry = r(t.geometries, this.geometry);
      const o = this.geometry.parameters;
      if (o !== void 0 && o.shapes !== void 0) {
        const l = o.shapes;
        if (Array.isArray(l))
          for (let c = 0, h = l.length; c < h; c++) {
            const f = l[c];
            r(t.shapes, f);
          }
        else r(t.shapes, l);
      }
    }
    if (
      (this.isSkinnedMesh &&
        ((s.bindMode = this.bindMode),
        (s.bindMatrix = this.bindMatrix.toArray()),
        this.skeleton !== void 0 &&
          (r(t.skeletons, this.skeleton), (s.skeleton = this.skeleton.uuid))),
      this.material !== void 0)
    )
      if (Array.isArray(this.material)) {
        const o = [];
        for (let l = 0, c = this.material.length; l < c; l++)
          o.push(r(t.materials, this.material[l]));
        s.material = o;
      } else s.material = r(t.materials, this.material);
    if (this.children.length > 0) {
      s.children = [];
      for (let o = 0; o < this.children.length; o++)
        s.children.push(this.children[o].toJSON(t).object);
    }
    if (this.animations.length > 0) {
      s.animations = [];
      for (let o = 0; o < this.animations.length; o++) {
        const l = this.animations[o];
        s.animations.push(r(t.animations, l));
      }
    }
    if (e) {
      const o = a(t.geometries),
        l = a(t.materials),
        c = a(t.textures),
        h = a(t.images),
        f = a(t.shapes),
        u = a(t.skeletons),
        p = a(t.animations),
        g = a(t.nodes);
      (o.length > 0 && (n.geometries = o),
        l.length > 0 && (n.materials = l),
        c.length > 0 && (n.textures = c),
        h.length > 0 && (n.images = h),
        f.length > 0 && (n.shapes = f),
        u.length > 0 && (n.skeletons = u),
        p.length > 0 && (n.animations = p),
        g.length > 0 && (n.nodes = g));
    }
    return ((n.object = s), n);
    function a(o) {
      const l = [];
      for (const c in o) {
        const h = o[c];
        (delete h.metadata, l.push(h));
      }
      return l;
    }
  }
  clone(t) {
    return new this.constructor().copy(this, t);
  }
  copy(t, e = !0) {
    if (
      ((this.name = t.name),
      this.up.copy(t.up),
      this.position.copy(t.position),
      (this.rotation.order = t.rotation.order),
      this.quaternion.copy(t.quaternion),
      this.scale.copy(t.scale),
      t.pivot !== null && (this.pivot = t.pivot.clone()),
      this.matrix.copy(t.matrix),
      this.matrixWorld.copy(t.matrixWorld),
      (this.matrixAutoUpdate = t.matrixAutoUpdate),
      (this.matrixWorldAutoUpdate = t.matrixWorldAutoUpdate),
      (this.matrixWorldNeedsUpdate = t.matrixWorldNeedsUpdate),
      (this.layers.mask = t.layers.mask),
      (this.visible = t.visible),
      (this.castShadow = t.castShadow),
      (this.receiveShadow = t.receiveShadow),
      (this.frustumCulled = t.frustumCulled),
      (this.renderOrder = t.renderOrder),
      (this.static = t.static),
      (this.animations = t.animations.slice()),
      (this.userData = JSON.parse(JSON.stringify(t.userData))),
      e === !0)
    )
      for (let n = 0; n < t.children.length; n++) {
        const s = t.children[n];
        this.add(s.clone());
      }
    return this;
  }
}
de.DEFAULT_UP = new L(0, 1, 0);
de.DEFAULT_MATRIX_AUTO_UPDATE = !0;
de.DEFAULT_MATRIX_WORLD_AUTO_UPDATE = !0;
class as extends de {
  constructor() {
    (super(), (this.isGroup = !0), (this.type = 'Group'));
  }
}
const Nh = { type: 'move' };
class ur {
  constructor() {
    ((this._targetRay = null), (this._grip = null), (this._hand = null));
  }
  getHandSpace() {
    return (
      this._hand === null &&
        ((this._hand = new as()),
        (this._hand.matrixAutoUpdate = !1),
        (this._hand.visible = !1),
        (this._hand.joints = {}),
        (this._hand.inputState = { pinching: !1 })),
      this._hand
    );
  }
  getTargetRaySpace() {
    return (
      this._targetRay === null &&
        ((this._targetRay = new as()),
        (this._targetRay.matrixAutoUpdate = !1),
        (this._targetRay.visible = !1),
        (this._targetRay.hasLinearVelocity = !1),
        (this._targetRay.linearVelocity = new L()),
        (this._targetRay.hasAngularVelocity = !1),
        (this._targetRay.angularVelocity = new L())),
      this._targetRay
    );
  }
  getGripSpace() {
    return (
      this._grip === null &&
        ((this._grip = new as()),
        (this._grip.matrixAutoUpdate = !1),
        (this._grip.visible = !1),
        (this._grip.hasLinearVelocity = !1),
        (this._grip.linearVelocity = new L()),
        (this._grip.hasAngularVelocity = !1),
        (this._grip.angularVelocity = new L())),
      this._grip
    );
  }
  dispatchEvent(t) {
    return (
      this._targetRay !== null && this._targetRay.dispatchEvent(t),
      this._grip !== null && this._grip.dispatchEvent(t),
      this._hand !== null && this._hand.dispatchEvent(t),
      this
    );
  }
  connect(t) {
    if (t && t.hand) {
      const e = this._hand;
      if (e) for (const n of t.hand.values()) this._getHandJoint(e, n);
    }
    return (this.dispatchEvent({ type: 'connected', data: t }), this);
  }
  disconnect(t) {
    return (
      this.dispatchEvent({ type: 'disconnected', data: t }),
      this._targetRay !== null && (this._targetRay.visible = !1),
      this._grip !== null && (this._grip.visible = !1),
      this._hand !== null && (this._hand.visible = !1),
      this
    );
  }
  update(t, e, n) {
    let s = null,
      r = null,
      a = null;
    const o = this._targetRay,
      l = this._grip,
      c = this._hand;
    if (t && e.session.visibilityState !== 'visible-blurred') {
      if (c && t.hand) {
        a = !0;
        for (const M of t.hand.values()) {
          const m = e.getJointPose(M, n),
            d = this._getHandJoint(c, M);
          (m !== null &&
            (d.matrix.fromArray(m.transform.matrix),
            d.matrix.decompose(d.position, d.rotation, d.scale),
            (d.matrixWorldNeedsUpdate = !0),
            (d.jointRadius = m.radius)),
            (d.visible = m !== null));
        }
        const h = c.joints['index-finger-tip'],
          f = c.joints['thumb-tip'],
          u = h.position.distanceTo(f.position),
          p = 0.02,
          g = 0.005;
        c.inputState.pinching && u > p + g
          ? ((c.inputState.pinching = !1),
            this.dispatchEvent({ type: 'pinchend', handedness: t.handedness, target: this }))
          : !c.inputState.pinching &&
            u <= p - g &&
            ((c.inputState.pinching = !0),
            this.dispatchEvent({ type: 'pinchstart', handedness: t.handedness, target: this }));
      } else
        l !== null &&
          t.gripSpace &&
          ((r = e.getPose(t.gripSpace, n)),
          r !== null &&
            (l.matrix.fromArray(r.transform.matrix),
            l.matrix.decompose(l.position, l.rotation, l.scale),
            (l.matrixWorldNeedsUpdate = !0),
            r.linearVelocity
              ? ((l.hasLinearVelocity = !0), l.linearVelocity.copy(r.linearVelocity))
              : (l.hasLinearVelocity = !1),
            r.angularVelocity
              ? ((l.hasAngularVelocity = !0), l.angularVelocity.copy(r.angularVelocity))
              : (l.hasAngularVelocity = !1)));
      o !== null &&
        ((s = e.getPose(t.targetRaySpace, n)),
        s === null && r !== null && (s = r),
        s !== null &&
          (o.matrix.fromArray(s.transform.matrix),
          o.matrix.decompose(o.position, o.rotation, o.scale),
          (o.matrixWorldNeedsUpdate = !0),
          s.linearVelocity
            ? ((o.hasLinearVelocity = !0), o.linearVelocity.copy(s.linearVelocity))
            : (o.hasLinearVelocity = !1),
          s.angularVelocity
            ? ((o.hasAngularVelocity = !0), o.angularVelocity.copy(s.angularVelocity))
            : (o.hasAngularVelocity = !1),
          this.dispatchEvent(Nh)));
    }
    return (
      o !== null && (o.visible = s !== null),
      l !== null && (l.visible = r !== null),
      c !== null && (c.visible = a !== null),
      this
    );
  }
  _getHandJoint(t, e) {
    if (t.joints[e.jointName] === void 0) {
      const n = new as();
      ((n.matrixAutoUpdate = !1), (n.visible = !1), (t.joints[e.jointName] = n), t.add(n));
    }
    return t.joints[e.jointName];
  }
}
const zl = {
    aliceblue: 15792383,
    antiquewhite: 16444375,
    aqua: 65535,
    aquamarine: 8388564,
    azure: 15794175,
    beige: 16119260,
    bisque: 16770244,
    black: 0,
    blanchedalmond: 16772045,
    blue: 255,
    blueviolet: 9055202,
    brown: 10824234,
    burlywood: 14596231,
    cadetblue: 6266528,
    chartreuse: 8388352,
    chocolate: 13789470,
    coral: 16744272,
    cornflowerblue: 6591981,
    cornsilk: 16775388,
    crimson: 14423100,
    cyan: 65535,
    darkblue: 139,
    darkcyan: 35723,
    darkgoldenrod: 12092939,
    darkgray: 11119017,
    darkgreen: 25600,
    darkgrey: 11119017,
    darkkhaki: 12433259,
    darkmagenta: 9109643,
    darkolivegreen: 5597999,
    darkorange: 16747520,
    darkorchid: 10040012,
    darkred: 9109504,
    darksalmon: 15308410,
    darkseagreen: 9419919,
    darkslateblue: 4734347,
    darkslategray: 3100495,
    darkslategrey: 3100495,
    darkturquoise: 52945,
    darkviolet: 9699539,
    deeppink: 16716947,
    deepskyblue: 49151,
    dimgray: 6908265,
    dimgrey: 6908265,
    dodgerblue: 2003199,
    firebrick: 11674146,
    floralwhite: 16775920,
    forestgreen: 2263842,
    fuchsia: 16711935,
    gainsboro: 14474460,
    ghostwhite: 16316671,
    gold: 16766720,
    goldenrod: 14329120,
    gray: 8421504,
    green: 32768,
    greenyellow: 11403055,
    grey: 8421504,
    honeydew: 15794160,
    hotpink: 16738740,
    indianred: 13458524,
    indigo: 4915330,
    ivory: 16777200,
    khaki: 15787660,
    lavender: 15132410,
    lavenderblush: 16773365,
    lawngreen: 8190976,
    lemonchiffon: 16775885,
    lightblue: 11393254,
    lightcoral: 15761536,
    lightcyan: 14745599,
    lightgoldenrodyellow: 16448210,
    lightgray: 13882323,
    lightgreen: 9498256,
    lightgrey: 13882323,
    lightpink: 16758465,
    lightsalmon: 16752762,
    lightseagreen: 2142890,
    lightskyblue: 8900346,
    lightslategray: 7833753,
    lightslategrey: 7833753,
    lightsteelblue: 11584734,
    lightyellow: 16777184,
    lime: 65280,
    limegreen: 3329330,
    linen: 16445670,
    magenta: 16711935,
    maroon: 8388608,
    mediumaquamarine: 6737322,
    mediumblue: 205,
    mediumorchid: 12211667,
    mediumpurple: 9662683,
    mediumseagreen: 3978097,
    mediumslateblue: 8087790,
    mediumspringgreen: 64154,
    mediumturquoise: 4772300,
    mediumvioletred: 13047173,
    midnightblue: 1644912,
    mintcream: 16121850,
    mistyrose: 16770273,
    moccasin: 16770229,
    navajowhite: 16768685,
    navy: 128,
    oldlace: 16643558,
    olive: 8421376,
    olivedrab: 7048739,
    orange: 16753920,
    orangered: 16729344,
    orchid: 14315734,
    palegoldenrod: 15657130,
    palegreen: 10025880,
    paleturquoise: 11529966,
    palevioletred: 14381203,
    papayawhip: 16773077,
    peachpuff: 16767673,
    peru: 13468991,
    pink: 16761035,
    plum: 14524637,
    powderblue: 11591910,
    purple: 8388736,
    rebeccapurple: 6697881,
    red: 16711680,
    rosybrown: 12357519,
    royalblue: 4286945,
    saddlebrown: 9127187,
    salmon: 16416882,
    sandybrown: 16032864,
    seagreen: 3050327,
    seashell: 16774638,
    sienna: 10506797,
    silver: 12632256,
    skyblue: 8900331,
    slateblue: 6970061,
    slategray: 7372944,
    slategrey: 7372944,
    snow: 16775930,
    springgreen: 65407,
    steelblue: 4620980,
    tan: 13808780,
    teal: 32896,
    thistle: 14204888,
    tomato: 16737095,
    turquoise: 4251856,
    violet: 15631086,
    wheat: 16113331,
    white: 16777215,
    whitesmoke: 16119285,
    yellow: 16776960,
    yellowgreen: 10145074,
  },
  wn = { h: 0, s: 0, l: 0 },
  os = { h: 0, s: 0, l: 0 };
function fr(i, t, e) {
  return (
    e < 0 && (e += 1),
    e > 1 && (e -= 1),
    e < 1 / 6 ? i + (t - i) * 6 * e : e < 1 / 2 ? t : e < 2 / 3 ? i + (t - i) * 6 * (2 / 3 - e) : i
  );
}
class zt {
  constructor(t, e, n) {
    return ((this.isColor = !0), (this.r = 1), (this.g = 1), (this.b = 1), this.set(t, e, n));
  }
  set(t, e, n) {
    if (e === void 0 && n === void 0) {
      const s = t;
      s && s.isColor
        ? this.copy(s)
        : typeof s == 'number'
          ? this.setHex(s)
          : typeof s == 'string' && this.setStyle(s);
    } else this.setRGB(t, e, n);
    return this;
  }
  setScalar(t) {
    return ((this.r = t), (this.g = t), (this.b = t), this);
  }
  setHex(t, e = Ve) {
    return (
      (t = Math.floor(t)),
      (this.r = ((t >> 16) & 255) / 255),
      (this.g = ((t >> 8) & 255) / 255),
      (this.b = (t & 255) / 255),
      $t.colorSpaceToWorking(this, e),
      this
    );
  }
  setRGB(t, e, n, s = $t.workingColorSpace) {
    return ((this.r = t), (this.g = e), (this.b = n), $t.colorSpaceToWorking(this, s), this);
  }
  setHSL(t, e, n, s = $t.workingColorSpace) {
    if (((t = Ya(t, 1)), (e = Bt(e, 0, 1)), (n = Bt(n, 0, 1)), e === 0))
      this.r = this.g = this.b = n;
    else {
      const r = n <= 0.5 ? n * (1 + e) : n + e - n * e,
        a = 2 * n - r;
      ((this.r = fr(a, r, t + 1 / 3)), (this.g = fr(a, r, t)), (this.b = fr(a, r, t - 1 / 3)));
    }
    return ($t.colorSpaceToWorking(this, s), this);
  }
  setStyle(t, e = Ve) {
    function n(r) {
      r !== void 0 &&
        parseFloat(r) < 1 &&
        Ft('Color: Alpha component of ' + t + ' will be ignored.');
    }
    let s;
    if ((s = /^(\w+)\(([^\)]*)\)/.exec(t))) {
      let r;
      const a = s[1],
        o = s[2];
      switch (a) {
        case 'rgb':
        case 'rgba':
          if ((r = /^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o)))
            return (
              n(r[4]),
              this.setRGB(
                Math.min(255, parseInt(r[1], 10)) / 255,
                Math.min(255, parseInt(r[2], 10)) / 255,
                Math.min(255, parseInt(r[3], 10)) / 255,
                e
              )
            );
          if ((r = /^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o)))
            return (
              n(r[4]),
              this.setRGB(
                Math.min(100, parseInt(r[1], 10)) / 100,
                Math.min(100, parseInt(r[2], 10)) / 100,
                Math.min(100, parseInt(r[3], 10)) / 100,
                e
              )
            );
          break;
        case 'hsl':
        case 'hsla':
          if (
            (r =
              /^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(
                o
              ))
          )
            return (
              n(r[4]),
              this.setHSL(parseFloat(r[1]) / 360, parseFloat(r[2]) / 100, parseFloat(r[3]) / 100, e)
            );
          break;
        default:
          Ft('Color: Unknown color model ' + t);
      }
    } else if ((s = /^\#([A-Fa-f\d]+)$/.exec(t))) {
      const r = s[1],
        a = r.length;
      if (a === 3)
        return this.setRGB(
          parseInt(r.charAt(0), 16) / 15,
          parseInt(r.charAt(1), 16) / 15,
          parseInt(r.charAt(2), 16) / 15,
          e
        );
      if (a === 6) return this.setHex(parseInt(r, 16), e);
      Ft('Color: Invalid hex color ' + t);
    } else if (t && t.length > 0) return this.setColorName(t, e);
    return this;
  }
  setColorName(t, e = Ve) {
    const n = zl[t.toLowerCase()];
    return (n !== void 0 ? this.setHex(n, e) : Ft('Color: Unknown color ' + t), this);
  }
  clone() {
    return new this.constructor(this.r, this.g, this.b);
  }
  copy(t) {
    return ((this.r = t.r), (this.g = t.g), (this.b = t.b), this);
  }
  copySRGBToLinear(t) {
    return ((this.r = Mn(t.r)), (this.g = Mn(t.g)), (this.b = Mn(t.b)), this);
  }
  copyLinearToSRGB(t) {
    return ((this.r = Mi(t.r)), (this.g = Mi(t.g)), (this.b = Mi(t.b)), this);
  }
  convertSRGBToLinear() {
    return (this.copySRGBToLinear(this), this);
  }
  convertLinearToSRGB() {
    return (this.copyLinearToSRGB(this), this);
  }
  getHex(t = Ve) {
    return (
      $t.workingToColorSpace(Te.copy(this), t),
      Math.round(Bt(Te.r * 255, 0, 255)) * 65536 +
        Math.round(Bt(Te.g * 255, 0, 255)) * 256 +
        Math.round(Bt(Te.b * 255, 0, 255))
    );
  }
  getHexString(t = Ve) {
    return ('000000' + this.getHex(t).toString(16)).slice(-6);
  }
  getHSL(t, e = $t.workingColorSpace) {
    $t.workingToColorSpace(Te.copy(this), e);
    const n = Te.r,
      s = Te.g,
      r = Te.b,
      a = Math.max(n, s, r),
      o = Math.min(n, s, r);
    let l, c;
    const h = (o + a) / 2;
    if (o === a) ((l = 0), (c = 0));
    else {
      const f = a - o;
      switch (((c = h <= 0.5 ? f / (a + o) : f / (2 - a - o)), a)) {
        case n:
          l = (s - r) / f + (s < r ? 6 : 0);
          break;
        case s:
          l = (r - n) / f + 2;
          break;
        case r:
          l = (n - s) / f + 4;
          break;
      }
      l /= 6;
    }
    return ((t.h = l), (t.s = c), (t.l = h), t);
  }
  getRGB(t, e = $t.workingColorSpace) {
    return ($t.workingToColorSpace(Te.copy(this), e), (t.r = Te.r), (t.g = Te.g), (t.b = Te.b), t);
  }
  getStyle(t = Ve) {
    $t.workingToColorSpace(Te.copy(this), t);
    const e = Te.r,
      n = Te.g,
      s = Te.b;
    return t !== Ve
      ? `color(${t} ${e.toFixed(3)} ${n.toFixed(3)} ${s.toFixed(3)})`
      : `rgb(${Math.round(e * 255)},${Math.round(n * 255)},${Math.round(s * 255)})`;
  }
  offsetHSL(t, e, n) {
    return (this.getHSL(wn), this.setHSL(wn.h + t, wn.s + e, wn.l + n));
  }
  add(t) {
    return ((this.r += t.r), (this.g += t.g), (this.b += t.b), this);
  }
  addColors(t, e) {
    return ((this.r = t.r + e.r), (this.g = t.g + e.g), (this.b = t.b + e.b), this);
  }
  addScalar(t) {
    return ((this.r += t), (this.g += t), (this.b += t), this);
  }
  sub(t) {
    return (
      (this.r = Math.max(0, this.r - t.r)),
      (this.g = Math.max(0, this.g - t.g)),
      (this.b = Math.max(0, this.b - t.b)),
      this
    );
  }
  multiply(t) {
    return ((this.r *= t.r), (this.g *= t.g), (this.b *= t.b), this);
  }
  multiplyScalar(t) {
    return ((this.r *= t), (this.g *= t), (this.b *= t), this);
  }
  lerp(t, e) {
    return (
      (this.r += (t.r - this.r) * e),
      (this.g += (t.g - this.g) * e),
      (this.b += (t.b - this.b) * e),
      this
    );
  }
  lerpColors(t, e, n) {
    return (
      (this.r = t.r + (e.r - t.r) * n),
      (this.g = t.g + (e.g - t.g) * n),
      (this.b = t.b + (e.b - t.b) * n),
      this
    );
  }
  lerpHSL(t, e) {
    (this.getHSL(wn), t.getHSL(os));
    const n = Gi(wn.h, os.h, e),
      s = Gi(wn.s, os.s, e),
      r = Gi(wn.l, os.l, e);
    return (this.setHSL(n, s, r), this);
  }
  setFromVector3(t) {
    return ((this.r = t.x), (this.g = t.y), (this.b = t.z), this);
  }
  applyMatrix3(t) {
    const e = this.r,
      n = this.g,
      s = this.b,
      r = t.elements;
    return (
      (this.r = r[0] * e + r[3] * n + r[6] * s),
      (this.g = r[1] * e + r[4] * n + r[7] * s),
      (this.b = r[2] * e + r[5] * n + r[8] * s),
      this
    );
  }
  equals(t) {
    return t.r === this.r && t.g === this.g && t.b === this.b;
  }
  fromArray(t, e = 0) {
    return ((this.r = t[e]), (this.g = t[e + 1]), (this.b = t[e + 2]), this);
  }
  toArray(t = [], e = 0) {
    return ((t[e] = this.r), (t[e + 1] = this.g), (t[e + 2] = this.b), t);
  }
  fromBufferAttribute(t, e) {
    return ((this.r = t.getX(e)), (this.g = t.getY(e)), (this.b = t.getZ(e)), this);
  }
  toJSON() {
    return this.getHex();
  }
  *[Symbol.iterator]() {
    (yield this.r, yield this.g, yield this.b);
  }
}
const Te = new zt();
zt.NAMES = zl;
class v0 extends de {
  constructor() {
    (super(),
      (this.isScene = !0),
      (this.type = 'Scene'),
      (this.background = null),
      (this.environment = null),
      (this.fog = null),
      (this.backgroundBlurriness = 0),
      (this.backgroundIntensity = 1),
      (this.backgroundRotation = new Ge()),
      (this.environmentIntensity = 1),
      (this.environmentRotation = new Ge()),
      (this.overrideMaterial = null),
      typeof __THREE_DEVTOOLS__ < 'u' &&
        __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent('observe', { detail: this })));
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      t.background !== null && (this.background = t.background.clone()),
      t.environment !== null && (this.environment = t.environment.clone()),
      t.fog !== null && (this.fog = t.fog.clone()),
      (this.backgroundBlurriness = t.backgroundBlurriness),
      (this.backgroundIntensity = t.backgroundIntensity),
      this.backgroundRotation.copy(t.backgroundRotation),
      (this.environmentIntensity = t.environmentIntensity),
      this.environmentRotation.copy(t.environmentRotation),
      t.overrideMaterial !== null && (this.overrideMaterial = t.overrideMaterial.clone()),
      (this.matrixAutoUpdate = t.matrixAutoUpdate),
      this
    );
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return (
      this.fog !== null && (e.object.fog = this.fog.toJSON()),
      this.backgroundBlurriness > 0 && (e.object.backgroundBlurriness = this.backgroundBlurriness),
      this.backgroundIntensity !== 1 && (e.object.backgroundIntensity = this.backgroundIntensity),
      (e.object.backgroundRotation = this.backgroundRotation.toArray()),
      this.environmentIntensity !== 1 &&
        (e.object.environmentIntensity = this.environmentIntensity),
      (e.object.environmentRotation = this.environmentRotation.toArray()),
      e
    );
  }
}
const We = new L(),
  fn = new L(),
  dr = new L(),
  dn = new L(),
  oi = new L(),
  li = new L(),
  Co = new L(),
  pr = new L(),
  mr = new L(),
  gr = new L(),
  _r = new ue(),
  xr = new ue(),
  vr = new ue();
class qe {
  constructor(t = new L(), e = new L(), n = new L()) {
    ((this.a = t), (this.b = e), (this.c = n));
  }
  static getNormal(t, e, n, s) {
    (s.subVectors(n, e), We.subVectors(t, e), s.cross(We));
    const r = s.lengthSq();
    return r > 0 ? s.multiplyScalar(1 / Math.sqrt(r)) : s.set(0, 0, 0);
  }
  static getBarycoord(t, e, n, s, r) {
    (We.subVectors(s, e), fn.subVectors(n, e), dr.subVectors(t, e));
    const a = We.dot(We),
      o = We.dot(fn),
      l = We.dot(dr),
      c = fn.dot(fn),
      h = fn.dot(dr),
      f = a * c - o * o;
    if (f === 0) return (r.set(0, 0, 0), null);
    const u = 1 / f,
      p = (c * l - o * h) * u,
      g = (a * h - o * l) * u;
    return r.set(1 - p - g, g, p);
  }
  static containsPoint(t, e, n, s) {
    return this.getBarycoord(t, e, n, s, dn) === null
      ? !1
      : dn.x >= 0 && dn.y >= 0 && dn.x + dn.y <= 1;
  }
  static getInterpolation(t, e, n, s, r, a, o, l) {
    return this.getBarycoord(t, e, n, s, dn) === null
      ? ((l.x = 0), (l.y = 0), 'z' in l && (l.z = 0), 'w' in l && (l.w = 0), null)
      : (l.setScalar(0),
        l.addScaledVector(r, dn.x),
        l.addScaledVector(a, dn.y),
        l.addScaledVector(o, dn.z),
        l);
  }
  static getInterpolatedAttribute(t, e, n, s, r, a) {
    return (
      _r.setScalar(0),
      xr.setScalar(0),
      vr.setScalar(0),
      _r.fromBufferAttribute(t, e),
      xr.fromBufferAttribute(t, n),
      vr.fromBufferAttribute(t, s),
      a.setScalar(0),
      a.addScaledVector(_r, r.x),
      a.addScaledVector(xr, r.y),
      a.addScaledVector(vr, r.z),
      a
    );
  }
  static isFrontFacing(t, e, n, s) {
    return (We.subVectors(n, e), fn.subVectors(t, e), We.cross(fn).dot(s) < 0);
  }
  set(t, e, n) {
    return (this.a.copy(t), this.b.copy(e), this.c.copy(n), this);
  }
  setFromPointsAndIndices(t, e, n, s) {
    return (this.a.copy(t[e]), this.b.copy(t[n]), this.c.copy(t[s]), this);
  }
  setFromAttributeAndIndices(t, e, n, s) {
    return (
      this.a.fromBufferAttribute(t, e),
      this.b.fromBufferAttribute(t, n),
      this.c.fromBufferAttribute(t, s),
      this
    );
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    return (this.a.copy(t.a), this.b.copy(t.b), this.c.copy(t.c), this);
  }
  getArea() {
    return (
      We.subVectors(this.c, this.b),
      fn.subVectors(this.a, this.b),
      We.cross(fn).length() * 0.5
    );
  }
  getMidpoint(t) {
    return t
      .addVectors(this.a, this.b)
      .add(this.c)
      .multiplyScalar(1 / 3);
  }
  getNormal(t) {
    return qe.getNormal(this.a, this.b, this.c, t);
  }
  getPlane(t) {
    return t.setFromCoplanarPoints(this.a, this.b, this.c);
  }
  getBarycoord(t, e) {
    return qe.getBarycoord(t, this.a, this.b, this.c, e);
  }
  getInterpolation(t, e, n, s, r) {
    return qe.getInterpolation(t, this.a, this.b, this.c, e, n, s, r);
  }
  containsPoint(t) {
    return qe.containsPoint(t, this.a, this.b, this.c);
  }
  isFrontFacing(t) {
    return qe.isFrontFacing(this.a, this.b, this.c, t);
  }
  intersectsBox(t) {
    return t.intersectsTriangle(this);
  }
  closestPointToPoint(t, e) {
    const n = this.a,
      s = this.b,
      r = this.c;
    let a, o;
    (oi.subVectors(s, n), li.subVectors(r, n), pr.subVectors(t, n));
    const l = oi.dot(pr),
      c = li.dot(pr);
    if (l <= 0 && c <= 0) return e.copy(n);
    mr.subVectors(t, s);
    const h = oi.dot(mr),
      f = li.dot(mr);
    if (h >= 0 && f <= h) return e.copy(s);
    const u = l * f - h * c;
    if (u <= 0 && l >= 0 && h <= 0) return ((a = l / (l - h)), e.copy(n).addScaledVector(oi, a));
    gr.subVectors(t, r);
    const p = oi.dot(gr),
      g = li.dot(gr);
    if (g >= 0 && p <= g) return e.copy(r);
    const M = p * c - l * g;
    if (M <= 0 && c >= 0 && g <= 0) return ((o = c / (c - g)), e.copy(n).addScaledVector(li, o));
    const m = h * g - p * f;
    if (m <= 0 && f - h >= 0 && p - g >= 0)
      return (
        Co.subVectors(r, s),
        (o = (f - h) / (f - h + (p - g))),
        e.copy(s).addScaledVector(Co, o)
      );
    const d = 1 / (m + M + u);
    return ((a = M * d), (o = u * d), e.copy(n).addScaledVector(oi, a).addScaledVector(li, o));
  }
  equals(t) {
    return t.a.equals(this.a) && t.b.equals(this.b) && t.c.equals(this.c);
  }
}
class ji {
  constructor(t = new L(1 / 0, 1 / 0, 1 / 0), e = new L(-1 / 0, -1 / 0, -1 / 0)) {
    ((this.isBox3 = !0), (this.min = t), (this.max = e));
  }
  set(t, e) {
    return (this.min.copy(t), this.max.copy(e), this);
  }
  setFromArray(t) {
    this.makeEmpty();
    for (let e = 0, n = t.length; e < n; e += 3) this.expandByPoint(Xe.fromArray(t, e));
    return this;
  }
  setFromBufferAttribute(t) {
    this.makeEmpty();
    for (let e = 0, n = t.count; e < n; e++) this.expandByPoint(Xe.fromBufferAttribute(t, e));
    return this;
  }
  setFromPoints(t) {
    this.makeEmpty();
    for (let e = 0, n = t.length; e < n; e++) this.expandByPoint(t[e]);
    return this;
  }
  setFromCenterAndSize(t, e) {
    const n = Xe.copy(e).multiplyScalar(0.5);
    return (this.min.copy(t).sub(n), this.max.copy(t).add(n), this);
  }
  setFromObject(t, e = !1) {
    return (this.makeEmpty(), this.expandByObject(t, e));
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    return (this.min.copy(t.min), this.max.copy(t.max), this);
  }
  makeEmpty() {
    return (
      (this.min.x = this.min.y = this.min.z = 1 / 0),
      (this.max.x = this.max.y = this.max.z = -1 / 0),
      this
    );
  }
  isEmpty() {
    return this.max.x < this.min.x || this.max.y < this.min.y || this.max.z < this.min.z;
  }
  getCenter(t) {
    return this.isEmpty() ? t.set(0, 0, 0) : t.addVectors(this.min, this.max).multiplyScalar(0.5);
  }
  getSize(t) {
    return this.isEmpty() ? t.set(0, 0, 0) : t.subVectors(this.max, this.min);
  }
  expandByPoint(t) {
    return (this.min.min(t), this.max.max(t), this);
  }
  expandByVector(t) {
    return (this.min.sub(t), this.max.add(t), this);
  }
  expandByScalar(t) {
    return (this.min.addScalar(-t), this.max.addScalar(t), this);
  }
  expandByObject(t, e = !1) {
    t.updateWorldMatrix(!1, !1);
    const n = t.geometry;
    if (n !== void 0) {
      const r = n.getAttribute('position');
      if (e === !0 && r !== void 0 && t.isInstancedMesh !== !0)
        for (let a = 0, o = r.count; a < o; a++)
          (t.isMesh === !0 ? t.getVertexPosition(a, Xe) : Xe.fromBufferAttribute(r, a),
            Xe.applyMatrix4(t.matrixWorld),
            this.expandByPoint(Xe));
      else
        (t.boundingBox !== void 0
          ? (t.boundingBox === null && t.computeBoundingBox(), ls.copy(t.boundingBox))
          : (n.boundingBox === null && n.computeBoundingBox(), ls.copy(n.boundingBox)),
          ls.applyMatrix4(t.matrixWorld),
          this.union(ls));
    }
    const s = t.children;
    for (let r = 0, a = s.length; r < a; r++) this.expandByObject(s[r], e);
    return this;
  }
  containsPoint(t) {
    return (
      t.x >= this.min.x &&
      t.x <= this.max.x &&
      t.y >= this.min.y &&
      t.y <= this.max.y &&
      t.z >= this.min.z &&
      t.z <= this.max.z
    );
  }
  containsBox(t) {
    return (
      this.min.x <= t.min.x &&
      t.max.x <= this.max.x &&
      this.min.y <= t.min.y &&
      t.max.y <= this.max.y &&
      this.min.z <= t.min.z &&
      t.max.z <= this.max.z
    );
  }
  getParameter(t, e) {
    return e.set(
      (t.x - this.min.x) / (this.max.x - this.min.x),
      (t.y - this.min.y) / (this.max.y - this.min.y),
      (t.z - this.min.z) / (this.max.z - this.min.z)
    );
  }
  intersectsBox(t) {
    return (
      t.max.x >= this.min.x &&
      t.min.x <= this.max.x &&
      t.max.y >= this.min.y &&
      t.min.y <= this.max.y &&
      t.max.z >= this.min.z &&
      t.min.z <= this.max.z
    );
  }
  intersectsSphere(t) {
    return (this.clampPoint(t.center, Xe), Xe.distanceToSquared(t.center) <= t.radius * t.radius);
  }
  intersectsPlane(t) {
    let e, n;
    return (
      t.normal.x > 0
        ? ((e = t.normal.x * this.min.x), (n = t.normal.x * this.max.x))
        : ((e = t.normal.x * this.max.x), (n = t.normal.x * this.min.x)),
      t.normal.y > 0
        ? ((e += t.normal.y * this.min.y), (n += t.normal.y * this.max.y))
        : ((e += t.normal.y * this.max.y), (n += t.normal.y * this.min.y)),
      t.normal.z > 0
        ? ((e += t.normal.z * this.min.z), (n += t.normal.z * this.max.z))
        : ((e += t.normal.z * this.max.z), (n += t.normal.z * this.min.z)),
      e <= -t.constant && n >= -t.constant
    );
  }
  intersectsTriangle(t) {
    if (this.isEmpty()) return !1;
    (this.getCenter(Li),
      cs.subVectors(this.max, Li),
      ci.subVectors(t.a, Li),
      hi.subVectors(t.b, Li),
      ui.subVectors(t.c, Li),
      Rn.subVectors(hi, ci),
      Cn.subVectors(ui, hi),
      On.subVectors(ci, ui));
    let e = [
      0,
      -Rn.z,
      Rn.y,
      0,
      -Cn.z,
      Cn.y,
      0,
      -On.z,
      On.y,
      Rn.z,
      0,
      -Rn.x,
      Cn.z,
      0,
      -Cn.x,
      On.z,
      0,
      -On.x,
      -Rn.y,
      Rn.x,
      0,
      -Cn.y,
      Cn.x,
      0,
      -On.y,
      On.x,
      0,
    ];
    return !Mr(e, ci, hi, ui, cs) || ((e = [1, 0, 0, 0, 1, 0, 0, 0, 1]), !Mr(e, ci, hi, ui, cs))
      ? !1
      : (hs.crossVectors(Rn, Cn), (e = [hs.x, hs.y, hs.z]), Mr(e, ci, hi, ui, cs));
  }
  clampPoint(t, e) {
    return e.copy(t).clamp(this.min, this.max);
  }
  distanceToPoint(t) {
    return this.clampPoint(t, Xe).distanceTo(t);
  }
  getBoundingSphere(t) {
    return (
      this.isEmpty()
        ? t.makeEmpty()
        : (this.getCenter(t.center), (t.radius = this.getSize(Xe).length() * 0.5)),
      t
    );
  }
  intersect(t) {
    return (this.min.max(t.min), this.max.min(t.max), this.isEmpty() && this.makeEmpty(), this);
  }
  union(t) {
    return (this.min.min(t.min), this.max.max(t.max), this);
  }
  applyMatrix4(t) {
    return this.isEmpty()
      ? this
      : (pn[0].set(this.min.x, this.min.y, this.min.z).applyMatrix4(t),
        pn[1].set(this.min.x, this.min.y, this.max.z).applyMatrix4(t),
        pn[2].set(this.min.x, this.max.y, this.min.z).applyMatrix4(t),
        pn[3].set(this.min.x, this.max.y, this.max.z).applyMatrix4(t),
        pn[4].set(this.max.x, this.min.y, this.min.z).applyMatrix4(t),
        pn[5].set(this.max.x, this.min.y, this.max.z).applyMatrix4(t),
        pn[6].set(this.max.x, this.max.y, this.min.z).applyMatrix4(t),
        pn[7].set(this.max.x, this.max.y, this.max.z).applyMatrix4(t),
        this.setFromPoints(pn),
        this);
  }
  translate(t) {
    return (this.min.add(t), this.max.add(t), this);
  }
  equals(t) {
    return t.min.equals(this.min) && t.max.equals(this.max);
  }
  toJSON() {
    return { min: this.min.toArray(), max: this.max.toArray() };
  }
  fromJSON(t) {
    return (this.min.fromArray(t.min), this.max.fromArray(t.max), this);
  }
}
const pn = [new L(), new L(), new L(), new L(), new L(), new L(), new L(), new L()],
  Xe = new L(),
  ls = new ji(),
  ci = new L(),
  hi = new L(),
  ui = new L(),
  Rn = new L(),
  Cn = new L(),
  On = new L(),
  Li = new L(),
  cs = new L(),
  hs = new L(),
  Bn = new L();
function Mr(i, t, e, n, s) {
  for (let r = 0, a = i.length - 3; r <= a; r += 3) {
    Bn.fromArray(i, r);
    const o = s.x * Math.abs(Bn.x) + s.y * Math.abs(Bn.y) + s.z * Math.abs(Bn.z),
      l = t.dot(Bn),
      c = e.dot(Bn),
      h = n.dot(Bn);
    if (Math.max(-Math.max(l, c, h), Math.min(l, c, h)) > o) return !1;
  }
  return !0;
}
const _n = Fh();
function Fh() {
  const i = new ArrayBuffer(4),
    t = new Float32Array(i),
    e = new Uint32Array(i),
    n = new Uint32Array(512),
    s = new Uint32Array(512);
  for (let l = 0; l < 256; ++l) {
    const c = l - 127;
    c < -27
      ? ((n[l] = 0), (n[l | 256] = 32768), (s[l] = 24), (s[l | 256] = 24))
      : c < -14
        ? ((n[l] = 1024 >> (-c - 14)),
          (n[l | 256] = (1024 >> (-c - 14)) | 32768),
          (s[l] = -c - 1),
          (s[l | 256] = -c - 1))
        : c <= 15
          ? ((n[l] = (c + 15) << 10),
            (n[l | 256] = ((c + 15) << 10) | 32768),
            (s[l] = 13),
            (s[l | 256] = 13))
          : c < 128
            ? ((n[l] = 31744), (n[l | 256] = 64512), (s[l] = 24), (s[l | 256] = 24))
            : ((n[l] = 31744), (n[l | 256] = 64512), (s[l] = 13), (s[l | 256] = 13));
  }
  const r = new Uint32Array(2048),
    a = new Uint32Array(64),
    o = new Uint32Array(64);
  for (let l = 1; l < 1024; ++l) {
    let c = l << 13,
      h = 0;
    for (; !(c & 8388608); ) ((c <<= 1), (h -= 8388608));
    ((c &= -8388609), (h += 947912704), (r[l] = c | h));
  }
  for (let l = 1024; l < 2048; ++l) r[l] = 939524096 + ((l - 1024) << 13);
  for (let l = 1; l < 31; ++l) a[l] = l << 23;
  ((a[31] = 1199570944), (a[32] = 2147483648));
  for (let l = 33; l < 63; ++l) a[l] = 2147483648 + ((l - 32) << 23);
  a[63] = 3347054592;
  for (let l = 1; l < 64; ++l) l !== 32 && (o[l] = 1024);
  return {
    floatView: t,
    uint32View: e,
    baseTable: n,
    shiftTable: s,
    mantissaTable: r,
    exponentTable: a,
    offsetTable: o,
  };
}
function Ue(i) {
  (Math.abs(i) > 65504 && Ft('DataUtils.toHalfFloat(): Value out of range.'),
    (i = Bt(i, -65504, 65504)),
    (_n.floatView[0] = i));
  const t = _n.uint32View[0],
    e = (t >> 23) & 511;
  return _n.baseTable[e] + ((t & 8388607) >> _n.shiftTable[e]);
}
function us(i) {
  const t = i >> 10;
  return (
    (_n.uint32View[0] = _n.mantissaTable[_n.offsetTable[t] + (i & 1023)] + _n.exponentTable[t]),
    _n.floatView[0]
  );
}
const pe = new L(),
  fs = new ct();
let Oh = 0;
class Be {
  constructor(t, e, n = !1) {
    if (Array.isArray(t))
      throw new TypeError('THREE.BufferAttribute: array should be a Typed Array.');
    ((this.isBufferAttribute = !0),
      Object.defineProperty(this, 'id', { value: Oh++ }),
      (this.name = ''),
      (this.array = t),
      (this.itemSize = e),
      (this.count = t !== void 0 ? t.length / e : 0),
      (this.normalized = n),
      (this.usage = Pa),
      (this.updateRanges = []),
      (this.gpuType = en),
      (this.version = 0));
  }
  onUploadCallback() {}
  set needsUpdate(t) {
    t === !0 && this.version++;
  }
  setUsage(t) {
    return ((this.usage = t), this);
  }
  addUpdateRange(t, e) {
    this.updateRanges.push({ start: t, count: e });
  }
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  copy(t) {
    return (
      (this.name = t.name),
      (this.array = new t.array.constructor(t.array)),
      (this.itemSize = t.itemSize),
      (this.count = t.count),
      (this.normalized = t.normalized),
      (this.usage = t.usage),
      (this.gpuType = t.gpuType),
      this
    );
  }
  copyAt(t, e, n) {
    ((t *= this.itemSize), (n *= e.itemSize));
    for (let s = 0, r = this.itemSize; s < r; s++) this.array[t + s] = e.array[n + s];
    return this;
  }
  copyArray(t) {
    return (this.array.set(t), this);
  }
  applyMatrix3(t) {
    if (this.itemSize === 2)
      for (let e = 0, n = this.count; e < n; e++)
        (fs.fromBufferAttribute(this, e), fs.applyMatrix3(t), this.setXY(e, fs.x, fs.y));
    else if (this.itemSize === 3)
      for (let e = 0, n = this.count; e < n; e++)
        (pe.fromBufferAttribute(this, e), pe.applyMatrix3(t), this.setXYZ(e, pe.x, pe.y, pe.z));
    return this;
  }
  applyMatrix4(t) {
    for (let e = 0, n = this.count; e < n; e++)
      (pe.fromBufferAttribute(this, e), pe.applyMatrix4(t), this.setXYZ(e, pe.x, pe.y, pe.z));
    return this;
  }
  applyNormalMatrix(t) {
    for (let e = 0, n = this.count; e < n; e++)
      (pe.fromBufferAttribute(this, e), pe.applyNormalMatrix(t), this.setXYZ(e, pe.x, pe.y, pe.z));
    return this;
  }
  transformDirection(t) {
    for (let e = 0, n = this.count; e < n; e++)
      (pe.fromBufferAttribute(this, e), pe.transformDirection(t), this.setXYZ(e, pe.x, pe.y, pe.z));
    return this;
  }
  set(t, e = 0) {
    return (this.array.set(t, e), this);
  }
  getComponent(t, e) {
    let n = this.array[t * this.itemSize + e];
    return (this.normalized && (n = Ce(n, this.array)), n);
  }
  setComponent(t, e, n) {
    return (
      this.normalized && (n = Wt(n, this.array)),
      (this.array[t * this.itemSize + e] = n),
      this
    );
  }
  getX(t) {
    let e = this.array[t * this.itemSize];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setX(t, e) {
    return (this.normalized && (e = Wt(e, this.array)), (this.array[t * this.itemSize] = e), this);
  }
  getY(t) {
    let e = this.array[t * this.itemSize + 1];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setY(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize + 1] = e),
      this
    );
  }
  getZ(t) {
    let e = this.array[t * this.itemSize + 2];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setZ(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize + 2] = e),
      this
    );
  }
  getW(t) {
    let e = this.array[t * this.itemSize + 3];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setW(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize + 3] = e),
      this
    );
  }
  setXY(t, e, n) {
    return (
      (t *= this.itemSize),
      this.normalized && ((e = Wt(e, this.array)), (n = Wt(n, this.array))),
      (this.array[t + 0] = e),
      (this.array[t + 1] = n),
      this
    );
  }
  setXYZ(t, e, n, s) {
    return (
      (t *= this.itemSize),
      this.normalized &&
        ((e = Wt(e, this.array)), (n = Wt(n, this.array)), (s = Wt(s, this.array))),
      (this.array[t + 0] = e),
      (this.array[t + 1] = n),
      (this.array[t + 2] = s),
      this
    );
  }
  setXYZW(t, e, n, s, r) {
    return (
      (t *= this.itemSize),
      this.normalized &&
        ((e = Wt(e, this.array)),
        (n = Wt(n, this.array)),
        (s = Wt(s, this.array)),
        (r = Wt(r, this.array))),
      (this.array[t + 0] = e),
      (this.array[t + 1] = n),
      (this.array[t + 2] = s),
      (this.array[t + 3] = r),
      this
    );
  }
  onUpload(t) {
    return ((this.onUploadCallback = t), this);
  }
  clone() {
    return new this.constructor(this.array, this.itemSize).copy(this);
  }
  toJSON() {
    const t = {
      itemSize: this.itemSize,
      type: this.array.constructor.name,
      array: Array.from(this.array),
      normalized: this.normalized,
    };
    return (
      this.name !== '' && (t.name = this.name),
      this.usage !== Pa && (t.usage = this.usage),
      t
    );
  }
}
class Vl extends Be {
  constructor(t, e, n) {
    super(new Uint16Array(t), e, n);
  }
}
class Gl extends Be {
  constructor(t, e, n) {
    super(new Uint32Array(t), e, n);
  }
}
class M0 extends Be {
  constructor(t, e, n) {
    (super(new Uint16Array(t), e, n), (this.isFloat16BufferAttribute = !0));
  }
  getX(t) {
    let e = us(this.array[t * this.itemSize]);
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setX(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize] = Ue(e)),
      this
    );
  }
  getY(t) {
    let e = us(this.array[t * this.itemSize + 1]);
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setY(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize + 1] = Ue(e)),
      this
    );
  }
  getZ(t) {
    let e = us(this.array[t * this.itemSize + 2]);
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setZ(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize + 2] = Ue(e)),
      this
    );
  }
  getW(t) {
    let e = us(this.array[t * this.itemSize + 3]);
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setW(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.array[t * this.itemSize + 3] = Ue(e)),
      this
    );
  }
  setXY(t, e, n) {
    return (
      (t *= this.itemSize),
      this.normalized && ((e = Wt(e, this.array)), (n = Wt(n, this.array))),
      (this.array[t + 0] = Ue(e)),
      (this.array[t + 1] = Ue(n)),
      this
    );
  }
  setXYZ(t, e, n, s) {
    return (
      (t *= this.itemSize),
      this.normalized &&
        ((e = Wt(e, this.array)), (n = Wt(n, this.array)), (s = Wt(s, this.array))),
      (this.array[t + 0] = Ue(e)),
      (this.array[t + 1] = Ue(n)),
      (this.array[t + 2] = Ue(s)),
      this
    );
  }
  setXYZW(t, e, n, s, r) {
    return (
      (t *= this.itemSize),
      this.normalized &&
        ((e = Wt(e, this.array)),
        (n = Wt(n, this.array)),
        (s = Wt(s, this.array)),
        (r = Wt(r, this.array))),
      (this.array[t + 0] = Ue(e)),
      (this.array[t + 1] = Ue(n)),
      (this.array[t + 2] = Ue(s)),
      (this.array[t + 3] = Ue(r)),
      this
    );
  }
}
class ee extends Be {
  constructor(t, e, n) {
    super(new Float32Array(t), e, n);
  }
}
const Bh = new ji(),
  Di = new L(),
  Sr = new L();
class Qi {
  constructor(t = new L(), e = -1) {
    ((this.isSphere = !0), (this.center = t), (this.radius = e));
  }
  set(t, e) {
    return (this.center.copy(t), (this.radius = e), this);
  }
  setFromPoints(t, e) {
    const n = this.center;
    e !== void 0 ? n.copy(e) : Bh.setFromPoints(t).getCenter(n);
    let s = 0;
    for (let r = 0, a = t.length; r < a; r++) s = Math.max(s, n.distanceToSquared(t[r]));
    return ((this.radius = Math.sqrt(s)), this);
  }
  copy(t) {
    return (this.center.copy(t.center), (this.radius = t.radius), this);
  }
  isEmpty() {
    return this.radius < 0;
  }
  makeEmpty() {
    return (this.center.set(0, 0, 0), (this.radius = -1), this);
  }
  containsPoint(t) {
    return t.distanceToSquared(this.center) <= this.radius * this.radius;
  }
  distanceToPoint(t) {
    return t.distanceTo(this.center) - this.radius;
  }
  intersectsSphere(t) {
    const e = this.radius + t.radius;
    return t.center.distanceToSquared(this.center) <= e * e;
  }
  intersectsBox(t) {
    return t.intersectsSphere(this);
  }
  intersectsPlane(t) {
    return Math.abs(t.distanceToPoint(this.center)) <= this.radius;
  }
  clampPoint(t, e) {
    const n = this.center.distanceToSquared(t);
    return (
      e.copy(t),
      n > this.radius * this.radius &&
        (e.sub(this.center).normalize(), e.multiplyScalar(this.radius).add(this.center)),
      e
    );
  }
  getBoundingBox(t) {
    return this.isEmpty()
      ? (t.makeEmpty(), t)
      : (t.set(this.center, this.center), t.expandByScalar(this.radius), t);
  }
  applyMatrix4(t) {
    return (this.center.applyMatrix4(t), (this.radius = this.radius * t.getMaxScaleOnAxis()), this);
  }
  translate(t) {
    return (this.center.add(t), this);
  }
  expandByPoint(t) {
    if (this.isEmpty()) return (this.center.copy(t), (this.radius = 0), this);
    Di.subVectors(t, this.center);
    const e = Di.lengthSq();
    if (e > this.radius * this.radius) {
      const n = Math.sqrt(e),
        s = (n - this.radius) * 0.5;
      (this.center.addScaledVector(Di, s / n), (this.radius += s));
    }
    return this;
  }
  union(t) {
    return t.isEmpty()
      ? this
      : this.isEmpty()
        ? (this.copy(t), this)
        : (this.center.equals(t.center) === !0
            ? (this.radius = Math.max(this.radius, t.radius))
            : (Sr.subVectors(t.center, this.center).setLength(t.radius),
              this.expandByPoint(Di.copy(t.center).add(Sr)),
              this.expandByPoint(Di.copy(t.center).sub(Sr))),
          this);
  }
  equals(t) {
    return t.center.equals(this.center) && t.radius === this.radius;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  toJSON() {
    return { radius: this.radius, center: this.center.toArray() };
  }
  fromJSON(t) {
    return ((this.radius = t.radius), this.center.fromArray(t.center), this);
  }
}
let zh = 0;
const ze = new oe(),
  yr = new de(),
  fi = new L(),
  Ne = new ji(),
  Ii = new ji(),
  Me = new L();
class xe extends jn {
  constructor() {
    (super(),
      (this.isBufferGeometry = !0),
      Object.defineProperty(this, 'id', { value: zh++ }),
      (this.uuid = sn()),
      (this.name = ''),
      (this.type = 'BufferGeometry'),
      (this.index = null),
      (this.indirect = null),
      (this.indirectOffset = 0),
      (this.attributes = {}),
      (this.morphAttributes = {}),
      (this.morphTargetsRelative = !1),
      (this.groups = []),
      (this.boundingBox = null),
      (this.boundingSphere = null),
      (this.drawRange = { start: 0, count: 1 / 0 }),
      (this.userData = {}));
  }
  getIndex() {
    return this.index;
  }
  setIndex(t) {
    return (Array.isArray(t) ? (this.index = new (ih(t) ? Gl : Vl)(t, 1)) : (this.index = t), this);
  }
  setIndirect(t, e = 0) {
    return ((this.indirect = t), (this.indirectOffset = e), this);
  }
  getIndirect() {
    return this.indirect;
  }
  getAttribute(t) {
    return this.attributes[t];
  }
  setAttribute(t, e) {
    return ((this.attributes[t] = e), this);
  }
  deleteAttribute(t) {
    return (delete this.attributes[t], this);
  }
  hasAttribute(t) {
    return this.attributes[t] !== void 0;
  }
  addGroup(t, e, n = 0) {
    this.groups.push({ start: t, count: e, materialIndex: n });
  }
  clearGroups() {
    this.groups = [];
  }
  setDrawRange(t, e) {
    ((this.drawRange.start = t), (this.drawRange.count = e));
  }
  applyMatrix4(t) {
    const e = this.attributes.position;
    e !== void 0 && (e.applyMatrix4(t), (e.needsUpdate = !0));
    const n = this.attributes.normal;
    if (n !== void 0) {
      const r = new Xt().getNormalMatrix(t);
      (n.applyNormalMatrix(r), (n.needsUpdate = !0));
    }
    const s = this.attributes.tangent;
    return (
      s !== void 0 && (s.transformDirection(t), (s.needsUpdate = !0)),
      this.boundingBox !== null && this.computeBoundingBox(),
      this.boundingSphere !== null && this.computeBoundingSphere(),
      this
    );
  }
  applyQuaternion(t) {
    return (ze.makeRotationFromQuaternion(t), this.applyMatrix4(ze), this);
  }
  rotateX(t) {
    return (ze.makeRotationX(t), this.applyMatrix4(ze), this);
  }
  rotateY(t) {
    return (ze.makeRotationY(t), this.applyMatrix4(ze), this);
  }
  rotateZ(t) {
    return (ze.makeRotationZ(t), this.applyMatrix4(ze), this);
  }
  translate(t, e, n) {
    return (ze.makeTranslation(t, e, n), this.applyMatrix4(ze), this);
  }
  scale(t, e, n) {
    return (ze.makeScale(t, e, n), this.applyMatrix4(ze), this);
  }
  lookAt(t) {
    return (yr.lookAt(t), yr.updateMatrix(), this.applyMatrix4(yr.matrix), this);
  }
  center() {
    return (
      this.computeBoundingBox(),
      this.boundingBox.getCenter(fi).negate(),
      this.translate(fi.x, fi.y, fi.z),
      this
    );
  }
  setFromPoints(t) {
    const e = this.getAttribute('position');
    if (e === void 0) {
      const n = [];
      for (let s = 0, r = t.length; s < r; s++) {
        const a = t[s];
        n.push(a.x, a.y, a.z || 0);
      }
      this.setAttribute('position', new ee(n, 3));
    } else {
      const n = Math.min(t.length, e.count);
      for (let s = 0; s < n; s++) {
        const r = t[s];
        e.setXYZ(s, r.x, r.y, r.z || 0);
      }
      (t.length > e.count &&
        Ft(
          'BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry.'
        ),
        (e.needsUpdate = !0));
    }
    return this;
  }
  computeBoundingBox() {
    this.boundingBox === null && (this.boundingBox = new ji());
    const t = this.attributes.position,
      e = this.morphAttributes.position;
    if (t && t.isGLBufferAttribute) {
      (Jt(
        'BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.',
        this
      ),
        this.boundingBox.set(new L(-1 / 0, -1 / 0, -1 / 0), new L(1 / 0, 1 / 0, 1 / 0)));
      return;
    }
    if (t !== void 0) {
      if ((this.boundingBox.setFromBufferAttribute(t), e))
        for (let n = 0, s = e.length; n < s; n++) {
          const r = e[n];
          (Ne.setFromBufferAttribute(r),
            this.morphTargetsRelative
              ? (Me.addVectors(this.boundingBox.min, Ne.min),
                this.boundingBox.expandByPoint(Me),
                Me.addVectors(this.boundingBox.max, Ne.max),
                this.boundingBox.expandByPoint(Me))
              : (this.boundingBox.expandByPoint(Ne.min), this.boundingBox.expandByPoint(Ne.max)));
        }
    } else this.boundingBox.makeEmpty();
    (isNaN(this.boundingBox.min.x) ||
      isNaN(this.boundingBox.min.y) ||
      isNaN(this.boundingBox.min.z)) &&
      Jt(
        'BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',
        this
      );
  }
  computeBoundingSphere() {
    this.boundingSphere === null && (this.boundingSphere = new Qi());
    const t = this.attributes.position,
      e = this.morphAttributes.position;
    if (t && t.isGLBufferAttribute) {
      (Jt(
        'BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.',
        this
      ),
        this.boundingSphere.set(new L(), 1 / 0));
      return;
    }
    if (t) {
      const n = this.boundingSphere.center;
      if ((Ne.setFromBufferAttribute(t), e))
        for (let r = 0, a = e.length; r < a; r++) {
          const o = e[r];
          (Ii.setFromBufferAttribute(o),
            this.morphTargetsRelative
              ? (Me.addVectors(Ne.min, Ii.min),
                Ne.expandByPoint(Me),
                Me.addVectors(Ne.max, Ii.max),
                Ne.expandByPoint(Me))
              : (Ne.expandByPoint(Ii.min), Ne.expandByPoint(Ii.max)));
        }
      Ne.getCenter(n);
      let s = 0;
      for (let r = 0, a = t.count; r < a; r++)
        (Me.fromBufferAttribute(t, r), (s = Math.max(s, n.distanceToSquared(Me))));
      if (e)
        for (let r = 0, a = e.length; r < a; r++) {
          const o = e[r],
            l = this.morphTargetsRelative;
          for (let c = 0, h = o.count; c < h; c++)
            (Me.fromBufferAttribute(o, c),
              l && (fi.fromBufferAttribute(t, c), Me.add(fi)),
              (s = Math.max(s, n.distanceToSquared(Me))));
        }
      ((this.boundingSphere.radius = Math.sqrt(s)),
        isNaN(this.boundingSphere.radius) &&
          Jt(
            'BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',
            this
          ));
    }
  }
  computeTangents() {
    const t = this.index,
      e = this.attributes;
    if (t === null || e.position === void 0 || e.normal === void 0 || e.uv === void 0) {
      Jt(
        'BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)'
      );
      return;
    }
    const n = e.position,
      s = e.normal,
      r = e.uv;
    this.hasAttribute('tangent') === !1 &&
      this.setAttribute('tangent', new Be(new Float32Array(4 * n.count), 4));
    const a = this.getAttribute('tangent'),
      o = [],
      l = [];
    for (let x = 0; x < n.count; x++) ((o[x] = new L()), (l[x] = new L()));
    const c = new L(),
      h = new L(),
      f = new L(),
      u = new ct(),
      p = new ct(),
      g = new ct(),
      M = new L(),
      m = new L();
    function d(x, b, H) {
      (c.fromBufferAttribute(n, x),
        h.fromBufferAttribute(n, b),
        f.fromBufferAttribute(n, H),
        u.fromBufferAttribute(r, x),
        p.fromBufferAttribute(r, b),
        g.fromBufferAttribute(r, H),
        h.sub(c),
        f.sub(c),
        p.sub(u),
        g.sub(u));
      const C = 1 / (p.x * g.y - g.x * p.y);
      isFinite(C) &&
        (M.copy(h).multiplyScalar(g.y).addScaledVector(f, -p.y).multiplyScalar(C),
        m.copy(f).multiplyScalar(p.x).addScaledVector(h, -g.x).multiplyScalar(C),
        o[x].add(M),
        o[b].add(M),
        o[H].add(M),
        l[x].add(m),
        l[b].add(m),
        l[H].add(m));
    }
    let E = this.groups;
    E.length === 0 && (E = [{ start: 0, count: t.count }]);
    for (let x = 0, b = E.length; x < b; ++x) {
      const H = E[x],
        C = H.start,
        N = H.count;
      for (let z = C, k = C + N; z < k; z += 3) d(t.getX(z + 0), t.getX(z + 1), t.getX(z + 2));
    }
    const y = new L(),
      S = new L(),
      R = new L(),
      w = new L();
    function P(x) {
      (R.fromBufferAttribute(s, x), w.copy(R));
      const b = o[x];
      (y.copy(b), y.sub(R.multiplyScalar(R.dot(b))).normalize(), S.crossVectors(w, b));
      const C = S.dot(l[x]) < 0 ? -1 : 1;
      a.setXYZW(x, y.x, y.y, y.z, C);
    }
    for (let x = 0, b = E.length; x < b; ++x) {
      const H = E[x],
        C = H.start,
        N = H.count;
      for (let z = C, k = C + N; z < k; z += 3)
        (P(t.getX(z + 0)), P(t.getX(z + 1)), P(t.getX(z + 2)));
    }
  }
  computeVertexNormals() {
    const t = this.index,
      e = this.getAttribute('position');
    if (e !== void 0) {
      let n = this.getAttribute('normal');
      if (n === void 0)
        ((n = new Be(new Float32Array(e.count * 3), 3)), this.setAttribute('normal', n));
      else for (let u = 0, p = n.count; u < p; u++) n.setXYZ(u, 0, 0, 0);
      const s = new L(),
        r = new L(),
        a = new L(),
        o = new L(),
        l = new L(),
        c = new L(),
        h = new L(),
        f = new L();
      if (t)
        for (let u = 0, p = t.count; u < p; u += 3) {
          const g = t.getX(u + 0),
            M = t.getX(u + 1),
            m = t.getX(u + 2);
          (s.fromBufferAttribute(e, g),
            r.fromBufferAttribute(e, M),
            a.fromBufferAttribute(e, m),
            h.subVectors(a, r),
            f.subVectors(s, r),
            h.cross(f),
            o.fromBufferAttribute(n, g),
            l.fromBufferAttribute(n, M),
            c.fromBufferAttribute(n, m),
            o.add(h),
            l.add(h),
            c.add(h),
            n.setXYZ(g, o.x, o.y, o.z),
            n.setXYZ(M, l.x, l.y, l.z),
            n.setXYZ(m, c.x, c.y, c.z));
        }
      else
        for (let u = 0, p = e.count; u < p; u += 3)
          (s.fromBufferAttribute(e, u + 0),
            r.fromBufferAttribute(e, u + 1),
            a.fromBufferAttribute(e, u + 2),
            h.subVectors(a, r),
            f.subVectors(s, r),
            h.cross(f),
            n.setXYZ(u + 0, h.x, h.y, h.z),
            n.setXYZ(u + 1, h.x, h.y, h.z),
            n.setXYZ(u + 2, h.x, h.y, h.z));
      (this.normalizeNormals(), (n.needsUpdate = !0));
    }
  }
  normalizeNormals() {
    const t = this.attributes.normal;
    for (let e = 0, n = t.count; e < n; e++)
      (Me.fromBufferAttribute(t, e), Me.normalize(), t.setXYZ(e, Me.x, Me.y, Me.z));
  }
  toNonIndexed() {
    function t(o, l) {
      const c = o.array,
        h = o.itemSize,
        f = o.normalized,
        u = new c.constructor(l.length * h);
      let p = 0,
        g = 0;
      for (let M = 0, m = l.length; M < m; M++) {
        o.isInterleavedBufferAttribute ? (p = l[M] * o.data.stride + o.offset) : (p = l[M] * h);
        for (let d = 0; d < h; d++) u[g++] = c[p++];
      }
      return new Be(u, h, f);
    }
    if (this.index === null)
      return (Ft('BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed.'), this);
    const e = new xe(),
      n = this.index.array,
      s = this.attributes;
    for (const o in s) {
      const l = s[o],
        c = t(l, n);
      e.setAttribute(o, c);
    }
    const r = this.morphAttributes;
    for (const o in r) {
      const l = [],
        c = r[o];
      for (let h = 0, f = c.length; h < f; h++) {
        const u = c[h],
          p = t(u, n);
        l.push(p);
      }
      e.morphAttributes[o] = l;
    }
    e.morphTargetsRelative = this.morphTargetsRelative;
    const a = this.groups;
    for (let o = 0, l = a.length; o < l; o++) {
      const c = a[o];
      e.addGroup(c.start, c.count, c.materialIndex);
    }
    return e;
  }
  toJSON() {
    const t = {
      metadata: { version: 4.7, type: 'BufferGeometry', generator: 'BufferGeometry.toJSON' },
    };
    if (
      ((t.uuid = this.uuid),
      (t.type = this.type),
      this.name !== '' && (t.name = this.name),
      Object.keys(this.userData).length > 0 && (t.userData = this.userData),
      this.parameters !== void 0)
    ) {
      const l = this.parameters;
      for (const c in l) l[c] !== void 0 && (t[c] = l[c]);
      return t;
    }
    t.data = { attributes: {} };
    const e = this.index;
    e !== null &&
      (t.data.index = {
        type: e.array.constructor.name,
        array: Array.prototype.slice.call(e.array),
      });
    const n = this.attributes;
    for (const l in n) {
      const c = n[l];
      t.data.attributes[l] = c.toJSON(t.data);
    }
    const s = {};
    let r = !1;
    for (const l in this.morphAttributes) {
      const c = this.morphAttributes[l],
        h = [];
      for (let f = 0, u = c.length; f < u; f++) {
        const p = c[f];
        h.push(p.toJSON(t.data));
      }
      h.length > 0 && ((s[l] = h), (r = !0));
    }
    r && ((t.data.morphAttributes = s), (t.data.morphTargetsRelative = this.morphTargetsRelative));
    const a = this.groups;
    a.length > 0 && (t.data.groups = JSON.parse(JSON.stringify(a)));
    const o = this.boundingSphere;
    return (o !== null && (t.data.boundingSphere = o.toJSON()), t);
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    ((this.index = null),
      (this.attributes = {}),
      (this.morphAttributes = {}),
      (this.groups = []),
      (this.boundingBox = null),
      (this.boundingSphere = null));
    const e = {};
    this.name = t.name;
    const n = t.index;
    n !== null && this.setIndex(n.clone());
    const s = t.attributes;
    for (const c in s) {
      const h = s[c];
      this.setAttribute(c, h.clone(e));
    }
    const r = t.morphAttributes;
    for (const c in r) {
      const h = [],
        f = r[c];
      for (let u = 0, p = f.length; u < p; u++) h.push(f[u].clone(e));
      this.morphAttributes[c] = h;
    }
    this.morphTargetsRelative = t.morphTargetsRelative;
    const a = t.groups;
    for (let c = 0, h = a.length; c < h; c++) {
      const f = a[c];
      this.addGroup(f.start, f.count, f.materialIndex);
    }
    const o = t.boundingBox;
    o !== null && (this.boundingBox = o.clone());
    const l = t.boundingSphere;
    return (
      l !== null && (this.boundingSphere = l.clone()),
      (this.drawRange.start = t.drawRange.start),
      (this.drawRange.count = t.drawRange.count),
      (this.userData = t.userData),
      this
    );
  }
  dispose() {
    this.dispatchEvent({ type: 'dispose' });
  }
}
class Vh {
  constructor(t, e) {
    ((this.isInterleavedBuffer = !0),
      (this.array = t),
      (this.stride = e),
      (this.count = t !== void 0 ? t.length / e : 0),
      (this.usage = Pa),
      (this.updateRanges = []),
      (this.version = 0),
      (this.uuid = sn()));
  }
  onUploadCallback() {}
  set needsUpdate(t) {
    t === !0 && this.version++;
  }
  setUsage(t) {
    return ((this.usage = t), this);
  }
  addUpdateRange(t, e) {
    this.updateRanges.push({ start: t, count: e });
  }
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  copy(t) {
    return (
      (this.array = new t.array.constructor(t.array)),
      (this.count = t.count),
      (this.stride = t.stride),
      (this.usage = t.usage),
      this
    );
  }
  copyAt(t, e, n) {
    ((t *= this.stride), (n *= e.stride));
    for (let s = 0, r = this.stride; s < r; s++) this.array[t + s] = e.array[n + s];
    return this;
  }
  set(t, e = 0) {
    return (this.array.set(t, e), this);
  }
  clone(t) {
    (t.arrayBuffers === void 0 && (t.arrayBuffers = {}),
      this.array.buffer._uuid === void 0 && (this.array.buffer._uuid = sn()),
      t.arrayBuffers[this.array.buffer._uuid] === void 0 &&
        (t.arrayBuffers[this.array.buffer._uuid] = this.array.slice(0).buffer));
    const e = new this.array.constructor(t.arrayBuffers[this.array.buffer._uuid]),
      n = new this.constructor(e, this.stride);
    return (n.setUsage(this.usage), n);
  }
  onUpload(t) {
    return ((this.onUploadCallback = t), this);
  }
  toJSON(t) {
    return (
      t.arrayBuffers === void 0 && (t.arrayBuffers = {}),
      this.array.buffer._uuid === void 0 && (this.array.buffer._uuid = sn()),
      t.arrayBuffers[this.array.buffer._uuid] === void 0 &&
        (t.arrayBuffers[this.array.buffer._uuid] = Array.from(new Uint32Array(this.array.buffer))),
      {
        uuid: this.uuid,
        buffer: this.array.buffer._uuid,
        type: this.array.constructor.name,
        stride: this.stride,
      }
    );
  }
}
const we = new L();
class Hl {
  constructor(t, e, n, s = !1) {
    ((this.isInterleavedBufferAttribute = !0),
      (this.name = ''),
      (this.data = t),
      (this.itemSize = e),
      (this.offset = n),
      (this.normalized = s));
  }
  get count() {
    return this.data.count;
  }
  get array() {
    return this.data.array;
  }
  set needsUpdate(t) {
    this.data.needsUpdate = t;
  }
  applyMatrix4(t) {
    for (let e = 0, n = this.data.count; e < n; e++)
      (we.fromBufferAttribute(this, e), we.applyMatrix4(t), this.setXYZ(e, we.x, we.y, we.z));
    return this;
  }
  applyNormalMatrix(t) {
    for (let e = 0, n = this.count; e < n; e++)
      (we.fromBufferAttribute(this, e), we.applyNormalMatrix(t), this.setXYZ(e, we.x, we.y, we.z));
    return this;
  }
  transformDirection(t) {
    for (let e = 0, n = this.count; e < n; e++)
      (we.fromBufferAttribute(this, e), we.transformDirection(t), this.setXYZ(e, we.x, we.y, we.z));
    return this;
  }
  getComponent(t, e) {
    let n = this.array[t * this.data.stride + this.offset + e];
    return (this.normalized && (n = Ce(n, this.array)), n);
  }
  setComponent(t, e, n) {
    return (
      this.normalized && (n = Wt(n, this.array)),
      (this.data.array[t * this.data.stride + this.offset + e] = n),
      this
    );
  }
  setX(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.data.array[t * this.data.stride + this.offset] = e),
      this
    );
  }
  setY(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.data.array[t * this.data.stride + this.offset + 1] = e),
      this
    );
  }
  setZ(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.data.array[t * this.data.stride + this.offset + 2] = e),
      this
    );
  }
  setW(t, e) {
    return (
      this.normalized && (e = Wt(e, this.array)),
      (this.data.array[t * this.data.stride + this.offset + 3] = e),
      this
    );
  }
  getX(t) {
    let e = this.data.array[t * this.data.stride + this.offset];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  getY(t) {
    let e = this.data.array[t * this.data.stride + this.offset + 1];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  getZ(t) {
    let e = this.data.array[t * this.data.stride + this.offset + 2];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  getW(t) {
    let e = this.data.array[t * this.data.stride + this.offset + 3];
    return (this.normalized && (e = Ce(e, this.array)), e);
  }
  setXY(t, e, n) {
    return (
      (t = t * this.data.stride + this.offset),
      this.normalized && ((e = Wt(e, this.array)), (n = Wt(n, this.array))),
      (this.data.array[t + 0] = e),
      (this.data.array[t + 1] = n),
      this
    );
  }
  setXYZ(t, e, n, s) {
    return (
      (t = t * this.data.stride + this.offset),
      this.normalized &&
        ((e = Wt(e, this.array)), (n = Wt(n, this.array)), (s = Wt(s, this.array))),
      (this.data.array[t + 0] = e),
      (this.data.array[t + 1] = n),
      (this.data.array[t + 2] = s),
      this
    );
  }
  setXYZW(t, e, n, s, r) {
    return (
      (t = t * this.data.stride + this.offset),
      this.normalized &&
        ((e = Wt(e, this.array)),
        (n = Wt(n, this.array)),
        (s = Wt(s, this.array)),
        (r = Wt(r, this.array))),
      (this.data.array[t + 0] = e),
      (this.data.array[t + 1] = n),
      (this.data.array[t + 2] = s),
      (this.data.array[t + 3] = r),
      this
    );
  }
  clone(t) {
    if (t === void 0) {
      ks(
        'InterleavedBufferAttribute.clone(): Cloning an interleaved buffer attribute will de-interleave buffer data.'
      );
      const e = [];
      for (let n = 0; n < this.count; n++) {
        const s = n * this.data.stride + this.offset;
        for (let r = 0; r < this.itemSize; r++) e.push(this.data.array[s + r]);
      }
      return new Be(new this.array.constructor(e), this.itemSize, this.normalized);
    } else
      return (
        t.interleavedBuffers === void 0 && (t.interleavedBuffers = {}),
        t.interleavedBuffers[this.data.uuid] === void 0 &&
          (t.interleavedBuffers[this.data.uuid] = this.data.clone(t)),
        new Hl(t.interleavedBuffers[this.data.uuid], this.itemSize, this.offset, this.normalized)
      );
  }
  toJSON(t) {
    if (t === void 0) {
      ks(
        'InterleavedBufferAttribute.toJSON(): Serializing an interleaved buffer attribute will de-interleave buffer data.'
      );
      const e = [];
      for (let n = 0; n < this.count; n++) {
        const s = n * this.data.stride + this.offset;
        for (let r = 0; r < this.itemSize; r++) e.push(this.data.array[s + r]);
      }
      return {
        itemSize: this.itemSize,
        type: this.array.constructor.name,
        array: e,
        normalized: this.normalized,
      };
    } else
      return (
        t.interleavedBuffers === void 0 && (t.interleavedBuffers = {}),
        t.interleavedBuffers[this.data.uuid] === void 0 &&
          (t.interleavedBuffers[this.data.uuid] = this.data.toJSON(t)),
        {
          isInterleavedBufferAttribute: !0,
          itemSize: this.itemSize,
          data: this.data.uuid,
          offset: this.offset,
          normalized: this.normalized,
        }
      );
  }
}
let Gh = 0;
class Le extends jn {
  constructor() {
    (super(),
      (this.isMaterial = !0),
      Object.defineProperty(this, 'id', { value: Gh++ }),
      (this.uuid = sn()),
      (this.name = ''),
      (this.type = 'Material'),
      (this.blending = vi),
      (this.side = Un),
      (this.vertexColors = !1),
      (this.opacity = 1),
      (this.transparent = !1),
      (this.alphaHash = !1),
      (this.blendSrc = Gr),
      (this.blendDst = Hr),
      (this.blendEquation = Wn),
      (this.blendSrcAlpha = null),
      (this.blendDstAlpha = null),
      (this.blendEquationAlpha = null),
      (this.blendColor = new zt(0, 0, 0)),
      (this.blendAlpha = 0),
      (this.depthFunc = Si),
      (this.depthTest = !0),
      (this.depthWrite = !0),
      (this.stencilWriteMask = 255),
      (this.stencilFunc = mo),
      (this.stencilRef = 0),
      (this.stencilFuncMask = 255),
      (this.stencilFail = ni),
      (this.stencilZFail = ni),
      (this.stencilZPass = ni),
      (this.stencilWrite = !1),
      (this.clippingPlanes = null),
      (this.clipIntersection = !1),
      (this.clipShadows = !1),
      (this.shadowSide = null),
      (this.colorWrite = !0),
      (this.precision = null),
      (this.polygonOffset = !1),
      (this.polygonOffsetFactor = 0),
      (this.polygonOffsetUnits = 0),
      (this.dithering = !1),
      (this.alphaToCoverage = !1),
      (this.premultipliedAlpha = !1),
      (this.forceSinglePass = !1),
      (this.allowOverride = !0),
      (this.visible = !0),
      (this.toneMapped = !0),
      (this.userData = {}),
      (this.version = 0),
      (this._alphaTest = 0));
  }
  get alphaTest() {
    return this._alphaTest;
  }
  set alphaTest(t) {
    (this._alphaTest > 0 != t > 0 && this.version++, (this._alphaTest = t));
  }
  onBeforeRender() {}
  onBeforeCompile() {}
  customProgramCacheKey() {
    return this.onBeforeCompile.toString();
  }
  setValues(t) {
    if (t !== void 0)
      for (const e in t) {
        const n = t[e];
        if (n === void 0) {
          Ft(`Material: parameter '${e}' has value of undefined.`);
          continue;
        }
        const s = this[e];
        if (s === void 0) {
          Ft(`Material: '${e}' is not a property of THREE.${this.type}.`);
          continue;
        }
        s && s.isColor
          ? s.set(n)
          : s && s.isVector3 && n && n.isVector3
            ? s.copy(n)
            : (this[e] = n);
      }
  }
  toJSON(t) {
    const e = t === void 0 || typeof t == 'string';
    e && (t = { textures: {}, images: {} });
    const n = { metadata: { version: 4.7, type: 'Material', generator: 'Material.toJSON' } };
    ((n.uuid = this.uuid),
      (n.type = this.type),
      this.name !== '' && (n.name = this.name),
      this.color && this.color.isColor && (n.color = this.color.getHex()),
      this.roughness !== void 0 && (n.roughness = this.roughness),
      this.metalness !== void 0 && (n.metalness = this.metalness),
      this.sheen !== void 0 && (n.sheen = this.sheen),
      this.sheenColor && this.sheenColor.isColor && (n.sheenColor = this.sheenColor.getHex()),
      this.sheenRoughness !== void 0 && (n.sheenRoughness = this.sheenRoughness),
      this.emissive && this.emissive.isColor && (n.emissive = this.emissive.getHex()),
      this.emissiveIntensity !== void 0 &&
        this.emissiveIntensity !== 1 &&
        (n.emissiveIntensity = this.emissiveIntensity),
      this.specular && this.specular.isColor && (n.specular = this.specular.getHex()),
      this.specularIntensity !== void 0 && (n.specularIntensity = this.specularIntensity),
      this.specularColor &&
        this.specularColor.isColor &&
        (n.specularColor = this.specularColor.getHex()),
      this.shininess !== void 0 && (n.shininess = this.shininess),
      this.clearcoat !== void 0 && (n.clearcoat = this.clearcoat),
      this.clearcoatRoughness !== void 0 && (n.clearcoatRoughness = this.clearcoatRoughness),
      this.clearcoatMap &&
        this.clearcoatMap.isTexture &&
        (n.clearcoatMap = this.clearcoatMap.toJSON(t).uuid),
      this.clearcoatRoughnessMap &&
        this.clearcoatRoughnessMap.isTexture &&
        (n.clearcoatRoughnessMap = this.clearcoatRoughnessMap.toJSON(t).uuid),
      this.clearcoatNormalMap &&
        this.clearcoatNormalMap.isTexture &&
        ((n.clearcoatNormalMap = this.clearcoatNormalMap.toJSON(t).uuid),
        (n.clearcoatNormalScale = this.clearcoatNormalScale.toArray())),
      this.sheenColorMap &&
        this.sheenColorMap.isTexture &&
        (n.sheenColorMap = this.sheenColorMap.toJSON(t).uuid),
      this.sheenRoughnessMap &&
        this.sheenRoughnessMap.isTexture &&
        (n.sheenRoughnessMap = this.sheenRoughnessMap.toJSON(t).uuid),
      this.dispersion !== void 0 && (n.dispersion = this.dispersion),
      this.iridescence !== void 0 && (n.iridescence = this.iridescence),
      this.iridescenceIOR !== void 0 && (n.iridescenceIOR = this.iridescenceIOR),
      this.iridescenceThicknessRange !== void 0 &&
        (n.iridescenceThicknessRange = this.iridescenceThicknessRange),
      this.iridescenceMap &&
        this.iridescenceMap.isTexture &&
        (n.iridescenceMap = this.iridescenceMap.toJSON(t).uuid),
      this.iridescenceThicknessMap &&
        this.iridescenceThicknessMap.isTexture &&
        (n.iridescenceThicknessMap = this.iridescenceThicknessMap.toJSON(t).uuid),
      this.anisotropy !== void 0 && (n.anisotropy = this.anisotropy),
      this.anisotropyRotation !== void 0 && (n.anisotropyRotation = this.anisotropyRotation),
      this.anisotropyMap &&
        this.anisotropyMap.isTexture &&
        (n.anisotropyMap = this.anisotropyMap.toJSON(t).uuid),
      this.map && this.map.isTexture && (n.map = this.map.toJSON(t).uuid),
      this.matcap && this.matcap.isTexture && (n.matcap = this.matcap.toJSON(t).uuid),
      this.alphaMap && this.alphaMap.isTexture && (n.alphaMap = this.alphaMap.toJSON(t).uuid),
      this.lightMap &&
        this.lightMap.isTexture &&
        ((n.lightMap = this.lightMap.toJSON(t).uuid),
        (n.lightMapIntensity = this.lightMapIntensity)),
      this.aoMap &&
        this.aoMap.isTexture &&
        ((n.aoMap = this.aoMap.toJSON(t).uuid), (n.aoMapIntensity = this.aoMapIntensity)),
      this.bumpMap &&
        this.bumpMap.isTexture &&
        ((n.bumpMap = this.bumpMap.toJSON(t).uuid), (n.bumpScale = this.bumpScale)),
      this.normalMap &&
        this.normalMap.isTexture &&
        ((n.normalMap = this.normalMap.toJSON(t).uuid),
        (n.normalMapType = this.normalMapType),
        (n.normalScale = this.normalScale.toArray())),
      this.displacementMap &&
        this.displacementMap.isTexture &&
        ((n.displacementMap = this.displacementMap.toJSON(t).uuid),
        (n.displacementScale = this.displacementScale),
        (n.displacementBias = this.displacementBias)),
      this.roughnessMap &&
        this.roughnessMap.isTexture &&
        (n.roughnessMap = this.roughnessMap.toJSON(t).uuid),
      this.metalnessMap &&
        this.metalnessMap.isTexture &&
        (n.metalnessMap = this.metalnessMap.toJSON(t).uuid),
      this.emissiveMap &&
        this.emissiveMap.isTexture &&
        (n.emissiveMap = this.emissiveMap.toJSON(t).uuid),
      this.specularMap &&
        this.specularMap.isTexture &&
        (n.specularMap = this.specularMap.toJSON(t).uuid),
      this.specularIntensityMap &&
        this.specularIntensityMap.isTexture &&
        (n.specularIntensityMap = this.specularIntensityMap.toJSON(t).uuid),
      this.specularColorMap &&
        this.specularColorMap.isTexture &&
        (n.specularColorMap = this.specularColorMap.toJSON(t).uuid),
      this.envMap &&
        this.envMap.isTexture &&
        ((n.envMap = this.envMap.toJSON(t).uuid),
        this.combine !== void 0 && (n.combine = this.combine)),
      this.envMapRotation !== void 0 && (n.envMapRotation = this.envMapRotation.toArray()),
      this.envMapIntensity !== void 0 && (n.envMapIntensity = this.envMapIntensity),
      this.reflectivity !== void 0 && (n.reflectivity = this.reflectivity),
      this.refractionRatio !== void 0 && (n.refractionRatio = this.refractionRatio),
      this.gradientMap &&
        this.gradientMap.isTexture &&
        (n.gradientMap = this.gradientMap.toJSON(t).uuid),
      this.transmission !== void 0 && (n.transmission = this.transmission),
      this.transmissionMap &&
        this.transmissionMap.isTexture &&
        (n.transmissionMap = this.transmissionMap.toJSON(t).uuid),
      this.thickness !== void 0 && (n.thickness = this.thickness),
      this.thicknessMap &&
        this.thicknessMap.isTexture &&
        (n.thicknessMap = this.thicknessMap.toJSON(t).uuid),
      this.attenuationDistance !== void 0 &&
        this.attenuationDistance !== 1 / 0 &&
        (n.attenuationDistance = this.attenuationDistance),
      this.attenuationColor !== void 0 && (n.attenuationColor = this.attenuationColor.getHex()),
      this.size !== void 0 && (n.size = this.size),
      this.shadowSide !== null && (n.shadowSide = this.shadowSide),
      this.sizeAttenuation !== void 0 && (n.sizeAttenuation = this.sizeAttenuation),
      this.blending !== vi && (n.blending = this.blending),
      this.side !== Un && (n.side = this.side),
      this.vertexColors === !0 && (n.vertexColors = !0),
      this.opacity < 1 && (n.opacity = this.opacity),
      this.transparent === !0 && (n.transparent = !0),
      this.blendSrc !== Gr && (n.blendSrc = this.blendSrc),
      this.blendDst !== Hr && (n.blendDst = this.blendDst),
      this.blendEquation !== Wn && (n.blendEquation = this.blendEquation),
      this.blendSrcAlpha !== null && (n.blendSrcAlpha = this.blendSrcAlpha),
      this.blendDstAlpha !== null && (n.blendDstAlpha = this.blendDstAlpha),
      this.blendEquationAlpha !== null && (n.blendEquationAlpha = this.blendEquationAlpha),
      this.blendColor && this.blendColor.isColor && (n.blendColor = this.blendColor.getHex()),
      this.blendAlpha !== 0 && (n.blendAlpha = this.blendAlpha),
      this.depthFunc !== Si && (n.depthFunc = this.depthFunc),
      this.depthTest === !1 && (n.depthTest = this.depthTest),
      this.depthWrite === !1 && (n.depthWrite = this.depthWrite),
      this.colorWrite === !1 && (n.colorWrite = this.colorWrite),
      this.stencilWriteMask !== 255 && (n.stencilWriteMask = this.stencilWriteMask),
      this.stencilFunc !== mo && (n.stencilFunc = this.stencilFunc),
      this.stencilRef !== 0 && (n.stencilRef = this.stencilRef),
      this.stencilFuncMask !== 255 && (n.stencilFuncMask = this.stencilFuncMask),
      this.stencilFail !== ni && (n.stencilFail = this.stencilFail),
      this.stencilZFail !== ni && (n.stencilZFail = this.stencilZFail),
      this.stencilZPass !== ni && (n.stencilZPass = this.stencilZPass),
      this.stencilWrite === !0 && (n.stencilWrite = this.stencilWrite),
      this.rotation !== void 0 && this.rotation !== 0 && (n.rotation = this.rotation),
      this.polygonOffset === !0 && (n.polygonOffset = !0),
      this.polygonOffsetFactor !== 0 && (n.polygonOffsetFactor = this.polygonOffsetFactor),
      this.polygonOffsetUnits !== 0 && (n.polygonOffsetUnits = this.polygonOffsetUnits),
      this.linewidth !== void 0 && this.linewidth !== 1 && (n.linewidth = this.linewidth),
      this.dashSize !== void 0 && (n.dashSize = this.dashSize),
      this.gapSize !== void 0 && (n.gapSize = this.gapSize),
      this.scale !== void 0 && (n.scale = this.scale),
      this.dithering === !0 && (n.dithering = !0),
      this.alphaTest > 0 && (n.alphaTest = this.alphaTest),
      this.alphaHash === !0 && (n.alphaHash = !0),
      this.alphaToCoverage === !0 && (n.alphaToCoverage = !0),
      this.premultipliedAlpha === !0 && (n.premultipliedAlpha = !0),
      this.forceSinglePass === !0 && (n.forceSinglePass = !0),
      this.allowOverride === !1 && (n.allowOverride = !1),
      this.wireframe === !0 && (n.wireframe = !0),
      this.wireframeLinewidth > 1 && (n.wireframeLinewidth = this.wireframeLinewidth),
      this.wireframeLinecap !== 'round' && (n.wireframeLinecap = this.wireframeLinecap),
      this.wireframeLinejoin !== 'round' && (n.wireframeLinejoin = this.wireframeLinejoin),
      this.flatShading === !0 && (n.flatShading = !0),
      this.visible === !1 && (n.visible = !1),
      this.toneMapped === !1 && (n.toneMapped = !1),
      this.fog === !1 && (n.fog = !1),
      Object.keys(this.userData).length > 0 && (n.userData = this.userData));
    function s(r) {
      const a = [];
      for (const o in r) {
        const l = r[o];
        (delete l.metadata, a.push(l));
      }
      return a;
    }
    if (e) {
      const r = s(t.textures),
        a = s(t.images);
      (r.length > 0 && (n.textures = r), a.length > 0 && (n.images = a));
    }
    return n;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    ((this.name = t.name),
      (this.blending = t.blending),
      (this.side = t.side),
      (this.vertexColors = t.vertexColors),
      (this.opacity = t.opacity),
      (this.transparent = t.transparent),
      (this.blendSrc = t.blendSrc),
      (this.blendDst = t.blendDst),
      (this.blendEquation = t.blendEquation),
      (this.blendSrcAlpha = t.blendSrcAlpha),
      (this.blendDstAlpha = t.blendDstAlpha),
      (this.blendEquationAlpha = t.blendEquationAlpha),
      this.blendColor.copy(t.blendColor),
      (this.blendAlpha = t.blendAlpha),
      (this.depthFunc = t.depthFunc),
      (this.depthTest = t.depthTest),
      (this.depthWrite = t.depthWrite),
      (this.stencilWriteMask = t.stencilWriteMask),
      (this.stencilFunc = t.stencilFunc),
      (this.stencilRef = t.stencilRef),
      (this.stencilFuncMask = t.stencilFuncMask),
      (this.stencilFail = t.stencilFail),
      (this.stencilZFail = t.stencilZFail),
      (this.stencilZPass = t.stencilZPass),
      (this.stencilWrite = t.stencilWrite));
    const e = t.clippingPlanes;
    let n = null;
    if (e !== null) {
      const s = e.length;
      n = new Array(s);
      for (let r = 0; r !== s; ++r) n[r] = e[r].clone();
    }
    return (
      (this.clippingPlanes = n),
      (this.clipIntersection = t.clipIntersection),
      (this.clipShadows = t.clipShadows),
      (this.shadowSide = t.shadowSide),
      (this.colorWrite = t.colorWrite),
      (this.precision = t.precision),
      (this.polygonOffset = t.polygonOffset),
      (this.polygonOffsetFactor = t.polygonOffsetFactor),
      (this.polygonOffsetUnits = t.polygonOffsetUnits),
      (this.dithering = t.dithering),
      (this.alphaTest = t.alphaTest),
      (this.alphaHash = t.alphaHash),
      (this.alphaToCoverage = t.alphaToCoverage),
      (this.premultipliedAlpha = t.premultipliedAlpha),
      (this.forceSinglePass = t.forceSinglePass),
      (this.allowOverride = t.allowOverride),
      (this.visible = t.visible),
      (this.toneMapped = t.toneMapped),
      (this.userData = JSON.parse(JSON.stringify(t.userData))),
      this
    );
  }
  dispose() {
    this.dispatchEvent({ type: 'dispose' });
  }
  set needsUpdate(t) {
    t === !0 && this.version++;
  }
}
class S0 extends Le {
  constructor(t) {
    (super(),
      (this.isSpriteMaterial = !0),
      (this.type = 'SpriteMaterial'),
      (this.color = new zt(16777215)),
      (this.map = null),
      (this.alphaMap = null),
      (this.rotation = 0),
      (this.sizeAttenuation = !0),
      (this.transparent = !0),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      (this.map = t.map),
      (this.alphaMap = t.alphaMap),
      (this.rotation = t.rotation),
      (this.sizeAttenuation = t.sizeAttenuation),
      (this.fog = t.fog),
      this
    );
  }
}
const mn = new L(),
  Er = new L(),
  ds = new L(),
  Pn = new L(),
  br = new L(),
  ps = new L(),
  Tr = new L();
class $s {
  constructor(t = new L(), e = new L(0, 0, -1)) {
    ((this.origin = t), (this.direction = e));
  }
  set(t, e) {
    return (this.origin.copy(t), this.direction.copy(e), this);
  }
  copy(t) {
    return (this.origin.copy(t.origin), this.direction.copy(t.direction), this);
  }
  at(t, e) {
    return e.copy(this.origin).addScaledVector(this.direction, t);
  }
  lookAt(t) {
    return (this.direction.copy(t).sub(this.origin).normalize(), this);
  }
  recast(t) {
    return (this.origin.copy(this.at(t, mn)), this);
  }
  closestPointToPoint(t, e) {
    e.subVectors(t, this.origin);
    const n = e.dot(this.direction);
    return n < 0 ? e.copy(this.origin) : e.copy(this.origin).addScaledVector(this.direction, n);
  }
  distanceToPoint(t) {
    return Math.sqrt(this.distanceSqToPoint(t));
  }
  distanceSqToPoint(t) {
    const e = mn.subVectors(t, this.origin).dot(this.direction);
    return e < 0
      ? this.origin.distanceToSquared(t)
      : (mn.copy(this.origin).addScaledVector(this.direction, e), mn.distanceToSquared(t));
  }
  distanceSqToSegment(t, e, n, s) {
    (Er.copy(t).add(e).multiplyScalar(0.5),
      ds.copy(e).sub(t).normalize(),
      Pn.copy(this.origin).sub(Er));
    const r = t.distanceTo(e) * 0.5,
      a = -this.direction.dot(ds),
      o = Pn.dot(this.direction),
      l = -Pn.dot(ds),
      c = Pn.lengthSq(),
      h = Math.abs(1 - a * a);
    let f, u, p, g;
    if (h > 0)
      if (((f = a * l - o), (u = a * o - l), (g = r * h), f >= 0))
        if (u >= -g)
          if (u <= g) {
            const M = 1 / h;
            ((f *= M), (u *= M), (p = f * (f + a * u + 2 * o) + u * (a * f + u + 2 * l) + c));
          } else ((u = r), (f = Math.max(0, -(a * u + o))), (p = -f * f + u * (u + 2 * l) + c));
        else ((u = -r), (f = Math.max(0, -(a * u + o))), (p = -f * f + u * (u + 2 * l) + c));
      else
        u <= -g
          ? ((f = Math.max(0, -(-a * r + o))),
            (u = f > 0 ? -r : Math.min(Math.max(-r, -l), r)),
            (p = -f * f + u * (u + 2 * l) + c))
          : u <= g
            ? ((f = 0), (u = Math.min(Math.max(-r, -l), r)), (p = u * (u + 2 * l) + c))
            : ((f = Math.max(0, -(a * r + o))),
              (u = f > 0 ? r : Math.min(Math.max(-r, -l), r)),
              (p = -f * f + u * (u + 2 * l) + c));
    else
      ((u = a > 0 ? -r : r), (f = Math.max(0, -(a * u + o))), (p = -f * f + u * (u + 2 * l) + c));
    return (
      n && n.copy(this.origin).addScaledVector(this.direction, f),
      s && s.copy(Er).addScaledVector(ds, u),
      p
    );
  }
  intersectSphere(t, e) {
    mn.subVectors(t.center, this.origin);
    const n = mn.dot(this.direction),
      s = mn.dot(mn) - n * n,
      r = t.radius * t.radius;
    if (s > r) return null;
    const a = Math.sqrt(r - s),
      o = n - a,
      l = n + a;
    return l < 0 ? null : o < 0 ? this.at(l, e) : this.at(o, e);
  }
  intersectsSphere(t) {
    return t.radius < 0 ? !1 : this.distanceSqToPoint(t.center) <= t.radius * t.radius;
  }
  distanceToPlane(t) {
    const e = t.normal.dot(this.direction);
    if (e === 0) return t.distanceToPoint(this.origin) === 0 ? 0 : null;
    const n = -(this.origin.dot(t.normal) + t.constant) / e;
    return n >= 0 ? n : null;
  }
  intersectPlane(t, e) {
    const n = this.distanceToPlane(t);
    return n === null ? null : this.at(n, e);
  }
  intersectsPlane(t) {
    const e = t.distanceToPoint(this.origin);
    return e === 0 || t.normal.dot(this.direction) * e < 0;
  }
  intersectBox(t, e) {
    let n, s, r, a, o, l;
    const c = 1 / this.direction.x,
      h = 1 / this.direction.y,
      f = 1 / this.direction.z,
      u = this.origin;
    return (
      c >= 0
        ? ((n = (t.min.x - u.x) * c), (s = (t.max.x - u.x) * c))
        : ((n = (t.max.x - u.x) * c), (s = (t.min.x - u.x) * c)),
      h >= 0
        ? ((r = (t.min.y - u.y) * h), (a = (t.max.y - u.y) * h))
        : ((r = (t.max.y - u.y) * h), (a = (t.min.y - u.y) * h)),
      n > a ||
      r > s ||
      ((r > n || isNaN(n)) && (n = r),
      (a < s || isNaN(s)) && (s = a),
      f >= 0
        ? ((o = (t.min.z - u.z) * f), (l = (t.max.z - u.z) * f))
        : ((o = (t.max.z - u.z) * f), (l = (t.min.z - u.z) * f)),
      n > l || o > s) ||
      ((o > n || n !== n) && (n = o), (l < s || s !== s) && (s = l), s < 0)
        ? null
        : this.at(n >= 0 ? n : s, e)
    );
  }
  intersectsBox(t) {
    return this.intersectBox(t, mn) !== null;
  }
  intersectTriangle(t, e, n, s, r) {
    (br.subVectors(e, t), ps.subVectors(n, t), Tr.crossVectors(br, ps));
    let a = this.direction.dot(Tr),
      o;
    if (a > 0) {
      if (s) return null;
      o = 1;
    } else if (a < 0) ((o = -1), (a = -a));
    else return null;
    Pn.subVectors(this.origin, t);
    const l = o * this.direction.dot(ps.crossVectors(Pn, ps));
    if (l < 0) return null;
    const c = o * this.direction.dot(br.cross(Pn));
    if (c < 0 || l + c > a) return null;
    const h = -o * Pn.dot(Tr);
    return h < 0 ? null : this.at(h / a, r);
  }
  applyMatrix4(t) {
    return (this.origin.applyMatrix4(t), this.direction.transformDirection(t), this);
  }
  equals(t) {
    return t.origin.equals(this.origin) && t.direction.equals(this.direction);
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
class kl extends Le {
  constructor(t) {
    (super(),
      (this.isMeshBasicMaterial = !0),
      (this.type = 'MeshBasicMaterial'),
      (this.color = new zt(16777215)),
      (this.map = null),
      (this.lightMap = null),
      (this.lightMapIntensity = 1),
      (this.aoMap = null),
      (this.aoMapIntensity = 1),
      (this.specularMap = null),
      (this.alphaMap = null),
      (this.envMap = null),
      (this.envMapRotation = new Ge()),
      (this.combine = Zs),
      (this.reflectivity = 1),
      (this.refractionRatio = 0.98),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.wireframeLinecap = 'round'),
      (this.wireframeLinejoin = 'round'),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      (this.map = t.map),
      (this.lightMap = t.lightMap),
      (this.lightMapIntensity = t.lightMapIntensity),
      (this.aoMap = t.aoMap),
      (this.aoMapIntensity = t.aoMapIntensity),
      (this.specularMap = t.specularMap),
      (this.alphaMap = t.alphaMap),
      (this.envMap = t.envMap),
      this.envMapRotation.copy(t.envMapRotation),
      (this.combine = t.combine),
      (this.reflectivity = t.reflectivity),
      (this.refractionRatio = t.refractionRatio),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.wireframeLinecap = t.wireframeLinecap),
      (this.wireframeLinejoin = t.wireframeLinejoin),
      (this.fog = t.fog),
      this
    );
  }
}
const Po = new oe(),
  zn = new $s(),
  ms = new Qi(),
  Lo = new L(),
  gs = new L(),
  _s = new L(),
  xs = new L(),
  Ar = new L(),
  vs = new L(),
  Do = new L(),
  Ms = new L();
class En extends de {
  constructor(t = new xe(), e = new kl()) {
    (super(),
      (this.isMesh = !0),
      (this.type = 'Mesh'),
      (this.geometry = t),
      (this.material = e),
      (this.morphTargetDictionary = void 0),
      (this.morphTargetInfluences = void 0),
      (this.count = 1),
      this.updateMorphTargets());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      t.morphTargetInfluences !== void 0 &&
        (this.morphTargetInfluences = t.morphTargetInfluences.slice()),
      t.morphTargetDictionary !== void 0 &&
        (this.morphTargetDictionary = Object.assign({}, t.morphTargetDictionary)),
      (this.material = Array.isArray(t.material) ? t.material.slice() : t.material),
      (this.geometry = t.geometry),
      this
    );
  }
  updateMorphTargets() {
    const e = this.geometry.morphAttributes,
      n = Object.keys(e);
    if (n.length > 0) {
      const s = e[n[0]];
      if (s !== void 0) {
        ((this.morphTargetInfluences = []), (this.morphTargetDictionary = {}));
        for (let r = 0, a = s.length; r < a; r++) {
          const o = s[r].name || String(r);
          (this.morphTargetInfluences.push(0), (this.morphTargetDictionary[o] = r));
        }
      }
    }
  }
  getVertexPosition(t, e) {
    const n = this.geometry,
      s = n.attributes.position,
      r = n.morphAttributes.position,
      a = n.morphTargetsRelative;
    e.fromBufferAttribute(s, t);
    const o = this.morphTargetInfluences;
    if (r && o) {
      vs.set(0, 0, 0);
      for (let l = 0, c = r.length; l < c; l++) {
        const h = o[l],
          f = r[l];
        h !== 0 &&
          (Ar.fromBufferAttribute(f, t),
          a ? vs.addScaledVector(Ar, h) : vs.addScaledVector(Ar.sub(e), h));
      }
      e.add(vs);
    }
    return e;
  }
  raycast(t, e) {
    const n = this.geometry,
      s = this.material,
      r = this.matrixWorld;
    s !== void 0 &&
      (n.boundingSphere === null && n.computeBoundingSphere(),
      ms.copy(n.boundingSphere),
      ms.applyMatrix4(r),
      zn.copy(t.ray).recast(t.near),
      !(
        ms.containsPoint(zn.origin) === !1 &&
        (zn.intersectSphere(ms, Lo) === null ||
          zn.origin.distanceToSquared(Lo) > (t.far - t.near) ** 2)
      ) &&
        (Po.copy(r).invert(),
        zn.copy(t.ray).applyMatrix4(Po),
        !(n.boundingBox !== null && zn.intersectsBox(n.boundingBox) === !1) &&
          this._computeIntersections(t, e, zn)));
  }
  _computeIntersections(t, e, n) {
    let s;
    const r = this.geometry,
      a = this.material,
      o = r.index,
      l = r.attributes.position,
      c = r.attributes.uv,
      h = r.attributes.uv1,
      f = r.attributes.normal,
      u = r.groups,
      p = r.drawRange;
    if (o !== null)
      if (Array.isArray(a))
        for (let g = 0, M = u.length; g < M; g++) {
          const m = u[g],
            d = a[m.materialIndex],
            E = Math.max(m.start, p.start),
            y = Math.min(o.count, Math.min(m.start + m.count, p.start + p.count));
          for (let S = E, R = y; S < R; S += 3) {
            const w = o.getX(S),
              P = o.getX(S + 1),
              x = o.getX(S + 2);
            ((s = Ss(this, d, t, n, c, h, f, w, P, x)),
              s &&
                ((s.faceIndex = Math.floor(S / 3)),
                (s.face.materialIndex = m.materialIndex),
                e.push(s)));
          }
        }
      else {
        const g = Math.max(0, p.start),
          M = Math.min(o.count, p.start + p.count);
        for (let m = g, d = M; m < d; m += 3) {
          const E = o.getX(m),
            y = o.getX(m + 1),
            S = o.getX(m + 2);
          ((s = Ss(this, a, t, n, c, h, f, E, y, S)),
            s && ((s.faceIndex = Math.floor(m / 3)), e.push(s)));
        }
      }
    else if (l !== void 0)
      if (Array.isArray(a))
        for (let g = 0, M = u.length; g < M; g++) {
          const m = u[g],
            d = a[m.materialIndex],
            E = Math.max(m.start, p.start),
            y = Math.min(l.count, Math.min(m.start + m.count, p.start + p.count));
          for (let S = E, R = y; S < R; S += 3) {
            const w = S,
              P = S + 1,
              x = S + 2;
            ((s = Ss(this, d, t, n, c, h, f, w, P, x)),
              s &&
                ((s.faceIndex = Math.floor(S / 3)),
                (s.face.materialIndex = m.materialIndex),
                e.push(s)));
          }
        }
      else {
        const g = Math.max(0, p.start),
          M = Math.min(l.count, p.start + p.count);
        for (let m = g, d = M; m < d; m += 3) {
          const E = m,
            y = m + 1,
            S = m + 2;
          ((s = Ss(this, a, t, n, c, h, f, E, y, S)),
            s && ((s.faceIndex = Math.floor(m / 3)), e.push(s)));
        }
      }
  }
}
function Hh(i, t, e, n, s, r, a, o) {
  let l;
  if (
    (t.side === Pe
      ? (l = n.intersectTriangle(a, r, s, !0, o))
      : (l = n.intersectTriangle(s, r, a, t.side === Un, o)),
    l === null)
  )
    return null;
  (Ms.copy(o), Ms.applyMatrix4(i.matrixWorld));
  const c = e.ray.origin.distanceTo(Ms);
  return c < e.near || c > e.far ? null : { distance: c, point: Ms.clone(), object: i };
}
function Ss(i, t, e, n, s, r, a, o, l, c) {
  (i.getVertexPosition(o, gs), i.getVertexPosition(l, _s), i.getVertexPosition(c, xs));
  const h = Hh(i, t, e, n, gs, _s, xs, Do);
  if (h) {
    const f = new L();
    (qe.getBarycoord(Do, gs, _s, xs, f),
      s && (h.uv = qe.getInterpolatedAttribute(s, o, l, c, f, new ct())),
      r && (h.uv1 = qe.getInterpolatedAttribute(r, o, l, c, f, new ct())),
      a &&
        ((h.normal = qe.getInterpolatedAttribute(a, o, l, c, f, new L())),
        h.normal.dot(n.direction) > 0 && h.normal.multiplyScalar(-1)));
    const u = { a: o, b: l, c, normal: new L(), materialIndex: 0 };
    (qe.getNormal(gs, _s, xs, u.normal), (h.face = u), (h.barycoord = f));
  }
  return h;
}
class kh extends ye {
  constructor(t = null, e = 1, n = 1, s, r, a, o, l, c = me, h = me, f, u) {
    (super(null, a, o, l, c, h, s, r, f, u),
      (this.isDataTexture = !0),
      (this.image = { data: t, width: e, height: n }),
      (this.generateMipmaps = !1),
      (this.flipY = !1),
      (this.unpackAlignment = 1));
  }
}
class y0 extends Be {
  constructor(t, e, n, s = 1) {
    (super(t, e, n), (this.isInstancedBufferAttribute = !0), (this.meshPerAttribute = s));
  }
  copy(t) {
    return (super.copy(t), (this.meshPerAttribute = t.meshPerAttribute), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.meshPerAttribute = this.meshPerAttribute), (t.isInstancedBufferAttribute = !0), t);
  }
}
const wr = new L(),
  Wh = new L(),
  Xh = new Xt();
class kn {
  constructor(t = new L(1, 0, 0), e = 0) {
    ((this.isPlane = !0), (this.normal = t), (this.constant = e));
  }
  set(t, e) {
    return (this.normal.copy(t), (this.constant = e), this);
  }
  setComponents(t, e, n, s) {
    return (this.normal.set(t, e, n), (this.constant = s), this);
  }
  setFromNormalAndCoplanarPoint(t, e) {
    return (this.normal.copy(t), (this.constant = -e.dot(this.normal)), this);
  }
  setFromCoplanarPoints(t, e, n) {
    const s = wr.subVectors(n, e).cross(Wh.subVectors(t, e)).normalize();
    return (this.setFromNormalAndCoplanarPoint(s, t), this);
  }
  copy(t) {
    return (this.normal.copy(t.normal), (this.constant = t.constant), this);
  }
  normalize() {
    const t = 1 / this.normal.length();
    return (this.normal.multiplyScalar(t), (this.constant *= t), this);
  }
  negate() {
    return ((this.constant *= -1), this.normal.negate(), this);
  }
  distanceToPoint(t) {
    return this.normal.dot(t) + this.constant;
  }
  distanceToSphere(t) {
    return this.distanceToPoint(t.center) - t.radius;
  }
  projectPoint(t, e) {
    return e.copy(t).addScaledVector(this.normal, -this.distanceToPoint(t));
  }
  intersectLine(t, e) {
    const n = t.delta(wr),
      s = this.normal.dot(n);
    if (s === 0) return this.distanceToPoint(t.start) === 0 ? e.copy(t.start) : null;
    const r = -(t.start.dot(this.normal) + this.constant) / s;
    return r < 0 || r > 1 ? null : e.copy(t.start).addScaledVector(n, r);
  }
  intersectsLine(t) {
    const e = this.distanceToPoint(t.start),
      n = this.distanceToPoint(t.end);
    return (e < 0 && n > 0) || (n < 0 && e > 0);
  }
  intersectsBox(t) {
    return t.intersectsPlane(this);
  }
  intersectsSphere(t) {
    return t.intersectsPlane(this);
  }
  coplanarPoint(t) {
    return t.copy(this.normal).multiplyScalar(-this.constant);
  }
  applyMatrix4(t, e) {
    const n = e || Xh.getNormalMatrix(t),
      s = this.coplanarPoint(wr).applyMatrix4(t),
      r = this.normal.applyMatrix3(n).normalize();
    return ((this.constant = -s.dot(r)), this);
  }
  translate(t) {
    return ((this.constant -= t.dot(this.normal)), this);
  }
  equals(t) {
    return t.normal.equals(this.normal) && t.constant === this.constant;
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
const Vn = new Qi(),
  qh = new ct(0.5, 0.5),
  ys = new L();
class Ks {
  constructor(t = new kn(), e = new kn(), n = new kn(), s = new kn(), r = new kn(), a = new kn()) {
    this.planes = [t, e, n, s, r, a];
  }
  set(t, e, n, s, r, a) {
    const o = this.planes;
    return (
      o[0].copy(t),
      o[1].copy(e),
      o[2].copy(n),
      o[3].copy(s),
      o[4].copy(r),
      o[5].copy(a),
      this
    );
  }
  copy(t) {
    const e = this.planes;
    for (let n = 0; n < 6; n++) e[n].copy(t.planes[n]);
    return this;
  }
  setFromProjectionMatrix(t, e = Ze, n = !1) {
    const s = this.planes,
      r = t.elements,
      a = r[0],
      o = r[1],
      l = r[2],
      c = r[3],
      h = r[4],
      f = r[5],
      u = r[6],
      p = r[7],
      g = r[8],
      M = r[9],
      m = r[10],
      d = r[11],
      E = r[12],
      y = r[13],
      S = r[14],
      R = r[15];
    if (
      (s[0].setComponents(c - a, p - h, d - g, R - E).normalize(),
      s[1].setComponents(c + a, p + h, d + g, R + E).normalize(),
      s[2].setComponents(c + o, p + f, d + M, R + y).normalize(),
      s[3].setComponents(c - o, p - f, d - M, R - y).normalize(),
      n)
    )
      (s[4].setComponents(l, u, m, S).normalize(),
        s[5].setComponents(c - l, p - u, d - m, R - S).normalize());
    else if ((s[4].setComponents(c - l, p - u, d - m, R - S).normalize(), e === Ze))
      s[5].setComponents(c + l, p + u, d + m, R + S).normalize();
    else if (e === qi) s[5].setComponents(l, u, m, S).normalize();
    else
      throw new Error('THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: ' + e);
    return this;
  }
  intersectsObject(t) {
    if (t.boundingSphere !== void 0)
      (t.boundingSphere === null && t.computeBoundingSphere(),
        Vn.copy(t.boundingSphere).applyMatrix4(t.matrixWorld));
    else {
      const e = t.geometry;
      (e.boundingSphere === null && e.computeBoundingSphere(),
        Vn.copy(e.boundingSphere).applyMatrix4(t.matrixWorld));
    }
    return this.intersectsSphere(Vn);
  }
  intersectsSprite(t) {
    Vn.center.set(0, 0, 0);
    const e = qh.distanceTo(t.center);
    return (
      (Vn.radius = 0.7071067811865476 + e),
      Vn.applyMatrix4(t.matrixWorld),
      this.intersectsSphere(Vn)
    );
  }
  intersectsSphere(t) {
    const e = this.planes,
      n = t.center,
      s = -t.radius;
    for (let r = 0; r < 6; r++) if (e[r].distanceToPoint(n) < s) return !1;
    return !0;
  }
  intersectsBox(t) {
    const e = this.planes;
    for (let n = 0; n < 6; n++) {
      const s = e[n];
      if (
        ((ys.x = s.normal.x > 0 ? t.max.x : t.min.x),
        (ys.y = s.normal.y > 0 ? t.max.y : t.min.y),
        (ys.z = s.normal.z > 0 ? t.max.z : t.min.z),
        s.distanceToPoint(ys) < 0)
      )
        return !1;
    }
    return !0;
  }
  containsPoint(t) {
    const e = this.planes;
    for (let n = 0; n < 6; n++) if (e[n].distanceToPoint(t) < 0) return !1;
    return !0;
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
const $e = new oe(),
  Ke = new Ks();
class Wl {
  constructor() {
    this.coordinateSystem = Ze;
  }
  intersectsObject(t, e) {
    if (!e.isArrayCamera || e.cameras.length === 0) return !1;
    for (let n = 0; n < e.cameras.length; n++) {
      const s = e.cameras[n];
      if (
        ($e.multiplyMatrices(s.projectionMatrix, s.matrixWorldInverse),
        Ke.setFromProjectionMatrix($e, s.coordinateSystem, s.reversedDepth),
        Ke.intersectsObject(t))
      )
        return !0;
    }
    return !1;
  }
  intersectsSprite(t, e) {
    if (!e || !e.cameras || e.cameras.length === 0) return !1;
    for (let n = 0; n < e.cameras.length; n++) {
      const s = e.cameras[n];
      if (
        ($e.multiplyMatrices(s.projectionMatrix, s.matrixWorldInverse),
        Ke.setFromProjectionMatrix($e, s.coordinateSystem, s.reversedDepth),
        Ke.intersectsSprite(t))
      )
        return !0;
    }
    return !1;
  }
  intersectsSphere(t, e) {
    if (!e || !e.cameras || e.cameras.length === 0) return !1;
    for (let n = 0; n < e.cameras.length; n++) {
      const s = e.cameras[n];
      if (
        ($e.multiplyMatrices(s.projectionMatrix, s.matrixWorldInverse),
        Ke.setFromProjectionMatrix($e, s.coordinateSystem, s.reversedDepth),
        Ke.intersectsSphere(t))
      )
        return !0;
    }
    return !1;
  }
  intersectsBox(t, e) {
    if (!e || !e.cameras || e.cameras.length === 0) return !1;
    for (let n = 0; n < e.cameras.length; n++) {
      const s = e.cameras[n];
      if (
        ($e.multiplyMatrices(s.projectionMatrix, s.matrixWorldInverse),
        Ke.setFromProjectionMatrix($e, s.coordinateSystem, s.reversedDepth),
        Ke.intersectsBox(t))
      )
        return !0;
    }
    return !1;
  }
  containsPoint(t, e) {
    if (!e || !e.cameras || e.cameras.length === 0) return !1;
    for (let n = 0; n < e.cameras.length; n++) {
      const s = e.cameras[n];
      if (
        ($e.multiplyMatrices(s.projectionMatrix, s.matrixWorldInverse),
        Ke.setFromProjectionMatrix($e, s.coordinateSystem, s.reversedDepth),
        Ke.containsPoint(t))
      )
        return !0;
    }
    return !1;
  }
  clone() {
    return new Wl();
  }
}
class Xl extends Le {
  constructor(t) {
    (super(),
      (this.isLineBasicMaterial = !0),
      (this.type = 'LineBasicMaterial'),
      (this.color = new zt(16777215)),
      (this.map = null),
      (this.linewidth = 1),
      (this.linecap = 'round'),
      (this.linejoin = 'round'),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      (this.map = t.map),
      (this.linewidth = t.linewidth),
      (this.linecap = t.linecap),
      (this.linejoin = t.linejoin),
      (this.fog = t.fog),
      this
    );
  }
}
const Xs = new L(),
  qs = new L(),
  Io = new oe(),
  Ui = new $s(),
  Es = new Qi(),
  Rr = new L(),
  Uo = new L();
class Yh extends de {
  constructor(t = new xe(), e = new Xl()) {
    (super(),
      (this.isLine = !0),
      (this.type = 'Line'),
      (this.geometry = t),
      (this.material = e),
      (this.morphTargetDictionary = void 0),
      (this.morphTargetInfluences = void 0),
      this.updateMorphTargets());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      (this.material = Array.isArray(t.material) ? t.material.slice() : t.material),
      (this.geometry = t.geometry),
      this
    );
  }
  computeLineDistances() {
    const t = this.geometry;
    if (t.index === null) {
      const e = t.attributes.position,
        n = [0];
      for (let s = 1, r = e.count; s < r; s++)
        (Xs.fromBufferAttribute(e, s - 1),
          qs.fromBufferAttribute(e, s),
          (n[s] = n[s - 1]),
          (n[s] += Xs.distanceTo(qs)));
      t.setAttribute('lineDistance', new ee(n, 1));
    } else
      Ft('Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.');
    return this;
  }
  raycast(t, e) {
    const n = this.geometry,
      s = this.matrixWorld,
      r = t.params.Line.threshold,
      a = n.drawRange;
    if (
      (n.boundingSphere === null && n.computeBoundingSphere(),
      Es.copy(n.boundingSphere),
      Es.applyMatrix4(s),
      (Es.radius += r),
      t.ray.intersectsSphere(Es) === !1)
    )
      return;
    (Io.copy(s).invert(), Ui.copy(t.ray).applyMatrix4(Io));
    const o = r / ((this.scale.x + this.scale.y + this.scale.z) / 3),
      l = o * o,
      c = this.isLineSegments ? 2 : 1,
      h = n.index,
      u = n.attributes.position;
    if (h !== null) {
      const p = Math.max(0, a.start),
        g = Math.min(h.count, a.start + a.count);
      for (let M = p, m = g - 1; M < m; M += c) {
        const d = h.getX(M),
          E = h.getX(M + 1),
          y = bs(this, t, Ui, l, d, E, M);
        y && e.push(y);
      }
      if (this.isLineLoop) {
        const M = h.getX(g - 1),
          m = h.getX(p),
          d = bs(this, t, Ui, l, M, m, g - 1);
        d && e.push(d);
      }
    } else {
      const p = Math.max(0, a.start),
        g = Math.min(u.count, a.start + a.count);
      for (let M = p, m = g - 1; M < m; M += c) {
        const d = bs(this, t, Ui, l, M, M + 1, M);
        d && e.push(d);
      }
      if (this.isLineLoop) {
        const M = bs(this, t, Ui, l, g - 1, p, g - 1);
        M && e.push(M);
      }
    }
  }
  updateMorphTargets() {
    const e = this.geometry.morphAttributes,
      n = Object.keys(e);
    if (n.length > 0) {
      const s = e[n[0]];
      if (s !== void 0) {
        ((this.morphTargetInfluences = []), (this.morphTargetDictionary = {}));
        for (let r = 0, a = s.length; r < a; r++) {
          const o = s[r].name || String(r);
          (this.morphTargetInfluences.push(0), (this.morphTargetDictionary[o] = r));
        }
      }
    }
  }
}
function bs(i, t, e, n, s, r, a) {
  const o = i.geometry.attributes.position;
  if (
    (Xs.fromBufferAttribute(o, s),
    qs.fromBufferAttribute(o, r),
    e.distanceSqToSegment(Xs, qs, Rr, Uo) > n)
  )
    return;
  Rr.applyMatrix4(i.matrixWorld);
  const c = t.ray.origin.distanceTo(Rr);
  if (!(c < t.near || c > t.far))
    return {
      distance: c,
      point: Uo.clone().applyMatrix4(i.matrixWorld),
      index: a,
      face: null,
      faceIndex: null,
      barycoord: null,
      object: i,
    };
}
const No = new L(),
  Fo = new L();
class E0 extends Yh {
  constructor(t, e) {
    (super(t, e), (this.isLineSegments = !0), (this.type = 'LineSegments'));
  }
  computeLineDistances() {
    const t = this.geometry;
    if (t.index === null) {
      const e = t.attributes.position,
        n = [];
      for (let s = 0, r = e.count; s < r; s += 2)
        (No.fromBufferAttribute(e, s),
          Fo.fromBufferAttribute(e, s + 1),
          (n[s] = s === 0 ? 0 : n[s - 1]),
          (n[s + 1] = n[s] + No.distanceTo(Fo)));
      t.setAttribute('lineDistance', new ee(n, 1));
    } else
      Ft(
        'LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.'
      );
    return this;
  }
}
class Zh extends Le {
  constructor(t) {
    (super(),
      (this.isPointsMaterial = !0),
      (this.type = 'PointsMaterial'),
      (this.color = new zt(16777215)),
      (this.map = null),
      (this.alphaMap = null),
      (this.size = 1),
      (this.sizeAttenuation = !0),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      (this.map = t.map),
      (this.alphaMap = t.alphaMap),
      (this.size = t.size),
      (this.sizeAttenuation = t.sizeAttenuation),
      (this.fog = t.fog),
      this
    );
  }
}
const Oo = new oe(),
  La = new $s(),
  Ts = new Qi(),
  As = new L();
class b0 extends de {
  constructor(t = new xe(), e = new Zh()) {
    (super(),
      (this.isPoints = !0),
      (this.type = 'Points'),
      (this.geometry = t),
      (this.material = e),
      (this.morphTargetDictionary = void 0),
      (this.morphTargetInfluences = void 0),
      this.updateMorphTargets());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      (this.material = Array.isArray(t.material) ? t.material.slice() : t.material),
      (this.geometry = t.geometry),
      this
    );
  }
  raycast(t, e) {
    const n = this.geometry,
      s = this.matrixWorld,
      r = t.params.Points.threshold,
      a = n.drawRange;
    if (
      (n.boundingSphere === null && n.computeBoundingSphere(),
      Ts.copy(n.boundingSphere),
      Ts.applyMatrix4(s),
      (Ts.radius += r),
      t.ray.intersectsSphere(Ts) === !1)
    )
      return;
    (Oo.copy(s).invert(), La.copy(t.ray).applyMatrix4(Oo));
    const o = r / ((this.scale.x + this.scale.y + this.scale.z) / 3),
      l = o * o,
      c = n.index,
      f = n.attributes.position;
    if (c !== null) {
      const u = Math.max(0, a.start),
        p = Math.min(c.count, a.start + a.count);
      for (let g = u, M = p; g < M; g++) {
        const m = c.getX(g);
        (As.fromBufferAttribute(f, m), Bo(As, m, l, s, t, e, this));
      }
    } else {
      const u = Math.max(0, a.start),
        p = Math.min(f.count, a.start + a.count);
      for (let g = u, M = p; g < M; g++)
        (As.fromBufferAttribute(f, g), Bo(As, g, l, s, t, e, this));
    }
  }
  updateMorphTargets() {
    const e = this.geometry.morphAttributes,
      n = Object.keys(e);
    if (n.length > 0) {
      const s = e[n[0]];
      if (s !== void 0) {
        ((this.morphTargetInfluences = []), (this.morphTargetDictionary = {}));
        for (let r = 0, a = s.length; r < a; r++) {
          const o = s[r].name || String(r);
          (this.morphTargetInfluences.push(0), (this.morphTargetDictionary[o] = r));
        }
      }
    }
  }
}
function Bo(i, t, e, n, s, r, a) {
  const o = La.distanceSqToPoint(i);
  if (o < e) {
    const l = new L();
    (La.closestPointToPoint(i, l), l.applyMatrix4(n));
    const c = s.ray.origin.distanceTo(l);
    if (c < s.near || c > s.far) return;
    r.push({
      distance: c,
      distanceToRay: Math.sqrt(o),
      point: l,
      index: t,
      face: null,
      faceIndex: null,
      barycoord: null,
      object: a,
    });
  }
}
class T0 extends ye {
  constructor(t, e) {
    (super({ width: t, height: e }),
      (this.isFramebufferTexture = !0),
      (this.magFilter = me),
      (this.minFilter = me),
      (this.generateMipmaps = !1),
      (this.needsUpdate = !0));
  }
}
class ql extends ye {
  constructor(t = [], e = Jn, n, s, r, a, o, l, c, h) {
    (super(t, e, n, s, r, a, o, l, c, h), (this.isCubeTexture = !0), (this.flipY = !1));
  }
  get images() {
    return this.image;
  }
  set images(t) {
    this.image = t;
  }
}
class Zi extends ye {
  constructor(t, e, n = an, s, r, a, o = me, l = me, c, h = yn, f = 1) {
    if (h !== yn && h !== Yn)
      throw new Error(
        'DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat'
      );
    const u = { width: t, height: e, depth: f };
    (super(u, s, r, a, o, l, h, n, c),
      (this.isDepthTexture = !0),
      (this.flipY = !1),
      (this.generateMipmaps = !1),
      (this.compareFunction = null));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.source = new Za(Object.assign({}, t.image))),
      (this.compareFunction = t.compareFunction),
      this
    );
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return (this.compareFunction !== null && (e.compareFunction = this.compareFunction), e);
  }
}
class Jh extends Zi {
  constructor(t, e = an, n = Jn, s, r, a = me, o = me, l, c = yn) {
    const h = { width: t, height: t, depth: 1 },
      f = [h, h, h, h, h, h];
    (super(t, t, e, n, s, r, a, o, l, c),
      (this.image = f),
      (this.isCubeDepthTexture = !0),
      (this.isCubeTexture = !0));
  }
  get images() {
    return this.image;
  }
  set images(t) {
    this.image = t;
  }
}
class Yl extends ye {
  constructor(t = null) {
    (super(), (this.sourceTexture = t), (this.isExternalTexture = !0));
  }
  copy(t) {
    return (super.copy(t), (this.sourceTexture = t.sourceTexture), this);
  }
}
class ts extends xe {
  constructor(t = 1, e = 1, n = 1, s = 1, r = 1, a = 1) {
    (super(),
      (this.type = 'BoxGeometry'),
      (this.parameters = {
        width: t,
        height: e,
        depth: n,
        widthSegments: s,
        heightSegments: r,
        depthSegments: a,
      }));
    const o = this;
    ((s = Math.floor(s)), (r = Math.floor(r)), (a = Math.floor(a)));
    const l = [],
      c = [],
      h = [],
      f = [];
    let u = 0,
      p = 0;
    (g('z', 'y', 'x', -1, -1, n, e, t, a, r, 0),
      g('z', 'y', 'x', 1, -1, n, e, -t, a, r, 1),
      g('x', 'z', 'y', 1, 1, t, n, e, s, a, 2),
      g('x', 'z', 'y', 1, -1, t, n, -e, s, a, 3),
      g('x', 'y', 'z', 1, -1, t, e, n, s, r, 4),
      g('x', 'y', 'z', -1, -1, t, e, -n, s, r, 5),
      this.setIndex(l),
      this.setAttribute('position', new ee(c, 3)),
      this.setAttribute('normal', new ee(h, 3)),
      this.setAttribute('uv', new ee(f, 2)));
    function g(M, m, d, E, y, S, R, w, P, x, b) {
      const H = S / P,
        C = R / x,
        N = S / 2,
        z = R / 2,
        k = w / 2,
        F = P + 1,
        O = x + 1;
      let B = 0,
        nt = 0;
      const j = new L();
      for (let mt = 0; mt < O; mt++) {
        const _t = mt * C - z;
        for (let gt = 0; gt < F; gt++) {
          const Ot = gt * H - N;
          ((j[M] = Ot * E),
            (j[m] = _t * y),
            (j[d] = k),
            c.push(j.x, j.y, j.z),
            (j[M] = 0),
            (j[m] = 0),
            (j[d] = w > 0 ? 1 : -1),
            h.push(j.x, j.y, j.z),
            f.push(gt / P),
            f.push(1 - mt / x),
            (B += 1));
        }
      }
      for (let mt = 0; mt < x; mt++)
        for (let _t = 0; _t < P; _t++) {
          const gt = u + _t + F * mt,
            Ot = u + _t + F * (mt + 1),
            jt = u + (_t + 1) + F * (mt + 1),
            ne = u + (_t + 1) + F * mt;
          (l.push(gt, Ot, ne), l.push(Ot, jt, ne), (nt += 6));
        }
      (o.addGroup(p, nt, b), (p += nt), (u += B));
    }
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  static fromJSON(t) {
    return new ts(t.width, t.height, t.depth, t.widthSegments, t.heightSegments, t.depthSegments);
  }
}
class Zl extends xe {
  constructor(t = 1, e = 32, n = 0, s = Math.PI * 2) {
    (super(),
      (this.type = 'CircleGeometry'),
      (this.parameters = { radius: t, segments: e, thetaStart: n, thetaLength: s }),
      (e = Math.max(3, e)));
    const r = [],
      a = [],
      o = [],
      l = [],
      c = new L(),
      h = new ct();
    (a.push(0, 0, 0), o.push(0, 0, 1), l.push(0.5, 0.5));
    for (let f = 0, u = 3; f <= e; f++, u += 3) {
      const p = n + (f / e) * s;
      ((c.x = t * Math.cos(p)),
        (c.y = t * Math.sin(p)),
        a.push(c.x, c.y, c.z),
        o.push(0, 0, 1),
        (h.x = (a[u] / t + 1) / 2),
        (h.y = (a[u + 1] / t + 1) / 2),
        l.push(h.x, h.y));
    }
    for (let f = 1; f <= e; f++) r.push(f, f + 1, 0);
    (this.setIndex(r),
      this.setAttribute('position', new ee(a, 3)),
      this.setAttribute('normal', new ee(o, 3)),
      this.setAttribute('uv', new ee(l, 2)));
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  static fromJSON(t) {
    return new Zl(t.radius, t.segments, t.thetaStart, t.thetaLength);
  }
}
class Jl extends xe {
  constructor(t = 1, e = 1, n = 1, s = 32, r = 1, a = !1, o = 0, l = Math.PI * 2) {
    (super(),
      (this.type = 'CylinderGeometry'),
      (this.parameters = {
        radiusTop: t,
        radiusBottom: e,
        height: n,
        radialSegments: s,
        heightSegments: r,
        openEnded: a,
        thetaStart: o,
        thetaLength: l,
      }));
    const c = this;
    ((s = Math.floor(s)), (r = Math.floor(r)));
    const h = [],
      f = [],
      u = [],
      p = [];
    let g = 0;
    const M = [],
      m = n / 2;
    let d = 0;
    (E(),
      a === !1 && (t > 0 && y(!0), e > 0 && y(!1)),
      this.setIndex(h),
      this.setAttribute('position', new ee(f, 3)),
      this.setAttribute('normal', new ee(u, 3)),
      this.setAttribute('uv', new ee(p, 2)));
    function E() {
      const S = new L(),
        R = new L();
      let w = 0;
      const P = (e - t) / n;
      for (let x = 0; x <= r; x++) {
        const b = [],
          H = x / r,
          C = H * (e - t) + t;
        for (let N = 0; N <= s; N++) {
          const z = N / s,
            k = z * l + o,
            F = Math.sin(k),
            O = Math.cos(k);
          ((R.x = C * F),
            (R.y = -H * n + m),
            (R.z = C * O),
            f.push(R.x, R.y, R.z),
            S.set(F, P, O).normalize(),
            u.push(S.x, S.y, S.z),
            p.push(z, 1 - H),
            b.push(g++));
        }
        M.push(b);
      }
      for (let x = 0; x < s; x++)
        for (let b = 0; b < r; b++) {
          const H = M[b][x],
            C = M[b + 1][x],
            N = M[b + 1][x + 1],
            z = M[b][x + 1];
          ((t > 0 || b !== 0) && (h.push(H, C, z), (w += 3)),
            (e > 0 || b !== r - 1) && (h.push(C, N, z), (w += 3)));
        }
      (c.addGroup(d, w, 0), (d += w));
    }
    function y(S) {
      const R = g,
        w = new ct(),
        P = new L();
      let x = 0;
      const b = S === !0 ? t : e,
        H = S === !0 ? 1 : -1;
      for (let N = 1; N <= s; N++) (f.push(0, m * H, 0), u.push(0, H, 0), p.push(0.5, 0.5), g++);
      const C = g;
      for (let N = 0; N <= s; N++) {
        const k = (N / s) * l + o,
          F = Math.cos(k),
          O = Math.sin(k);
        ((P.x = b * O),
          (P.y = m * H),
          (P.z = b * F),
          f.push(P.x, P.y, P.z),
          u.push(0, H, 0),
          (w.x = F * 0.5 + 0.5),
          (w.y = O * 0.5 * H + 0.5),
          p.push(w.x, w.y),
          g++);
      }
      for (let N = 0; N < s; N++) {
        const z = R + N,
          k = C + N;
        (S === !0 ? h.push(k, k + 1, z) : h.push(k + 1, k, z), (x += 3));
      }
      (c.addGroup(d, x, S === !0 ? 1 : 2), (d += x));
    }
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  static fromJSON(t) {
    return new Jl(
      t.radiusTop,
      t.radiusBottom,
      t.height,
      t.radialSegments,
      t.heightSegments,
      t.openEnded,
      t.thetaStart,
      t.thetaLength
    );
  }
}
class ln {
  constructor() {
    ((this.type = 'Curve'),
      (this.arcLengthDivisions = 200),
      (this.needsUpdate = !1),
      (this.cacheArcLengths = null));
  }
  getPoint() {
    Ft('Curve: .getPoint() not implemented.');
  }
  getPointAt(t, e) {
    const n = this.getUtoTmapping(t);
    return this.getPoint(n, e);
  }
  getPoints(t = 5) {
    const e = [];
    for (let n = 0; n <= t; n++) e.push(this.getPoint(n / t));
    return e;
  }
  getSpacedPoints(t = 5) {
    const e = [];
    for (let n = 0; n <= t; n++) e.push(this.getPointAt(n / t));
    return e;
  }
  getLength() {
    const t = this.getLengths();
    return t[t.length - 1];
  }
  getLengths(t = this.arcLengthDivisions) {
    if (this.cacheArcLengths && this.cacheArcLengths.length === t + 1 && !this.needsUpdate)
      return this.cacheArcLengths;
    this.needsUpdate = !1;
    const e = [];
    let n,
      s = this.getPoint(0),
      r = 0;
    e.push(0);
    for (let a = 1; a <= t; a++)
      ((n = this.getPoint(a / t)), (r += n.distanceTo(s)), e.push(r), (s = n));
    return ((this.cacheArcLengths = e), e);
  }
  updateArcLengths() {
    ((this.needsUpdate = !0), this.getLengths());
  }
  getUtoTmapping(t, e = null) {
    const n = this.getLengths();
    let s = 0;
    const r = n.length;
    let a;
    e ? (a = e) : (a = t * n[r - 1]);
    let o = 0,
      l = r - 1,
      c;
    for (; o <= l; )
      if (((s = Math.floor(o + (l - o) / 2)), (c = n[s] - a), c < 0)) o = s + 1;
      else if (c > 0) l = s - 1;
      else {
        l = s;
        break;
      }
    if (((s = l), n[s] === a)) return s / (r - 1);
    const h = n[s],
      u = n[s + 1] - h,
      p = (a - h) / u;
    return (s + p) / (r - 1);
  }
  getTangent(t, e) {
    let s = t - 1e-4,
      r = t + 1e-4;
    (s < 0 && (s = 0), r > 1 && (r = 1));
    const a = this.getPoint(s),
      o = this.getPoint(r),
      l = e || (a.isVector2 ? new ct() : new L());
    return (l.copy(o).sub(a).normalize(), l);
  }
  getTangentAt(t, e) {
    const n = this.getUtoTmapping(t);
    return this.getTangent(n, e);
  }
  computeFrenetFrames(t, e = !1) {
    const n = new L(),
      s = [],
      r = [],
      a = [],
      o = new L(),
      l = new oe();
    for (let p = 0; p <= t; p++) {
      const g = p / t;
      s[p] = this.getTangentAt(g, new L());
    }
    ((r[0] = new L()), (a[0] = new L()));
    let c = Number.MAX_VALUE;
    const h = Math.abs(s[0].x),
      f = Math.abs(s[0].y),
      u = Math.abs(s[0].z);
    (h <= c && ((c = h), n.set(1, 0, 0)),
      f <= c && ((c = f), n.set(0, 1, 0)),
      u <= c && n.set(0, 0, 1),
      o.crossVectors(s[0], n).normalize(),
      r[0].crossVectors(s[0], o),
      a[0].crossVectors(s[0], r[0]));
    for (let p = 1; p <= t; p++) {
      if (
        ((r[p] = r[p - 1].clone()),
        (a[p] = a[p - 1].clone()),
        o.crossVectors(s[p - 1], s[p]),
        o.length() > Number.EPSILON)
      ) {
        o.normalize();
        const g = Math.acos(Bt(s[p - 1].dot(s[p]), -1, 1));
        r[p].applyMatrix4(l.makeRotationAxis(o, g));
      }
      a[p].crossVectors(s[p], r[p]);
    }
    if (e === !0) {
      let p = Math.acos(Bt(r[0].dot(r[t]), -1, 1));
      ((p /= t), s[0].dot(o.crossVectors(r[0], r[t])) > 0 && (p = -p));
      for (let g = 1; g <= t; g++)
        (r[g].applyMatrix4(l.makeRotationAxis(s[g], p * g)), a[g].crossVectors(s[g], r[g]));
    }
    return { tangents: s, normals: r, binormals: a };
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t) {
    return ((this.arcLengthDivisions = t.arcLengthDivisions), this);
  }
  toJSON() {
    const t = { metadata: { version: 4.7, type: 'Curve', generator: 'Curve.toJSON' } };
    return ((t.arcLengthDivisions = this.arcLengthDivisions), (t.type = this.type), t);
  }
  fromJSON(t) {
    return ((this.arcLengthDivisions = t.arcLengthDivisions), this);
  }
}
class $a extends ln {
  constructor(t = 0, e = 0, n = 1, s = 1, r = 0, a = Math.PI * 2, o = !1, l = 0) {
    (super(),
      (this.isEllipseCurve = !0),
      (this.type = 'EllipseCurve'),
      (this.aX = t),
      (this.aY = e),
      (this.xRadius = n),
      (this.yRadius = s),
      (this.aStartAngle = r),
      (this.aEndAngle = a),
      (this.aClockwise = o),
      (this.aRotation = l));
  }
  getPoint(t, e = new ct()) {
    const n = e,
      s = Math.PI * 2;
    let r = this.aEndAngle - this.aStartAngle;
    const a = Math.abs(r) < Number.EPSILON;
    for (; r < 0; ) r += s;
    for (; r > s; ) r -= s;
    (r < Number.EPSILON && (a ? (r = 0) : (r = s)),
      this.aClockwise === !0 && !a && (r === s ? (r = -s) : (r = r - s)));
    const o = this.aStartAngle + t * r;
    let l = this.aX + this.xRadius * Math.cos(o),
      c = this.aY + this.yRadius * Math.sin(o);
    if (this.aRotation !== 0) {
      const h = Math.cos(this.aRotation),
        f = Math.sin(this.aRotation),
        u = l - this.aX,
        p = c - this.aY;
      ((l = u * h - p * f + this.aX), (c = u * f + p * h + this.aY));
    }
    return n.set(l, c);
  }
  copy(t) {
    return (
      super.copy(t),
      (this.aX = t.aX),
      (this.aY = t.aY),
      (this.xRadius = t.xRadius),
      (this.yRadius = t.yRadius),
      (this.aStartAngle = t.aStartAngle),
      (this.aEndAngle = t.aEndAngle),
      (this.aClockwise = t.aClockwise),
      (this.aRotation = t.aRotation),
      this
    );
  }
  toJSON() {
    const t = super.toJSON();
    return (
      (t.aX = this.aX),
      (t.aY = this.aY),
      (t.xRadius = this.xRadius),
      (t.yRadius = this.yRadius),
      (t.aStartAngle = this.aStartAngle),
      (t.aEndAngle = this.aEndAngle),
      (t.aClockwise = this.aClockwise),
      (t.aRotation = this.aRotation),
      t
    );
  }
  fromJSON(t) {
    return (
      super.fromJSON(t),
      (this.aX = t.aX),
      (this.aY = t.aY),
      (this.xRadius = t.xRadius),
      (this.yRadius = t.yRadius),
      (this.aStartAngle = t.aStartAngle),
      (this.aEndAngle = t.aEndAngle),
      (this.aClockwise = t.aClockwise),
      (this.aRotation = t.aRotation),
      this
    );
  }
}
class $h extends $a {
  constructor(t, e, n, s, r, a) {
    (super(t, e, n, n, s, r, a), (this.isArcCurve = !0), (this.type = 'ArcCurve'));
  }
}
function Ka() {
  let i = 0,
    t = 0,
    e = 0,
    n = 0;
  function s(r, a, o, l) {
    ((i = r), (t = o), (e = -3 * r + 3 * a - 2 * o - l), (n = 2 * r - 2 * a + o + l));
  }
  return {
    initCatmullRom: function (r, a, o, l, c) {
      s(a, o, c * (o - r), c * (l - a));
    },
    initNonuniformCatmullRom: function (r, a, o, l, c, h, f) {
      let u = (a - r) / c - (o - r) / (c + h) + (o - a) / h,
        p = (o - a) / h - (l - a) / (h + f) + (l - o) / f;
      ((u *= h), (p *= h), s(a, o, u, p));
    },
    calc: function (r) {
      const a = r * r,
        o = a * r;
      return i + t * r + e * a + n * o;
    },
  };
}
const ws = new L(),
  Cr = new Ka(),
  Pr = new Ka(),
  Lr = new Ka();
class Kh extends ln {
  constructor(t = [], e = !1, n = 'centripetal', s = 0.5) {
    (super(),
      (this.isCatmullRomCurve3 = !0),
      (this.type = 'CatmullRomCurve3'),
      (this.points = t),
      (this.closed = e),
      (this.curveType = n),
      (this.tension = s));
  }
  getPoint(t, e = new L()) {
    const n = e,
      s = this.points,
      r = s.length,
      a = (r - (this.closed ? 0 : 1)) * t;
    let o = Math.floor(a),
      l = a - o;
    this.closed
      ? (o += o > 0 ? 0 : (Math.floor(Math.abs(o) / r) + 1) * r)
      : l === 0 && o === r - 1 && ((o = r - 2), (l = 1));
    let c, h;
    this.closed || o > 0 ? (c = s[(o - 1) % r]) : (ws.subVectors(s[0], s[1]).add(s[0]), (c = ws));
    const f = s[o % r],
      u = s[(o + 1) % r];
    if (
      (this.closed || o + 2 < r
        ? (h = s[(o + 2) % r])
        : (ws.subVectors(s[r - 1], s[r - 2]).add(s[r - 1]), (h = ws)),
      this.curveType === 'centripetal' || this.curveType === 'chordal')
    ) {
      const p = this.curveType === 'chordal' ? 0.5 : 0.25;
      let g = Math.pow(c.distanceToSquared(f), p),
        M = Math.pow(f.distanceToSquared(u), p),
        m = Math.pow(u.distanceToSquared(h), p);
      (M < 1e-4 && (M = 1),
        g < 1e-4 && (g = M),
        m < 1e-4 && (m = M),
        Cr.initNonuniformCatmullRom(c.x, f.x, u.x, h.x, g, M, m),
        Pr.initNonuniformCatmullRom(c.y, f.y, u.y, h.y, g, M, m),
        Lr.initNonuniformCatmullRom(c.z, f.z, u.z, h.z, g, M, m));
    } else
      this.curveType === 'catmullrom' &&
        (Cr.initCatmullRom(c.x, f.x, u.x, h.x, this.tension),
        Pr.initCatmullRom(c.y, f.y, u.y, h.y, this.tension),
        Lr.initCatmullRom(c.z, f.z, u.z, h.z, this.tension));
    return (n.set(Cr.calc(l), Pr.calc(l), Lr.calc(l)), n);
  }
  copy(t) {
    (super.copy(t), (this.points = []));
    for (let e = 0, n = t.points.length; e < n; e++) {
      const s = t.points[e];
      this.points.push(s.clone());
    }
    return (
      (this.closed = t.closed),
      (this.curveType = t.curveType),
      (this.tension = t.tension),
      this
    );
  }
  toJSON() {
    const t = super.toJSON();
    t.points = [];
    for (let e = 0, n = this.points.length; e < n; e++) {
      const s = this.points[e];
      t.points.push(s.toArray());
    }
    return (
      (t.closed = this.closed),
      (t.curveType = this.curveType),
      (t.tension = this.tension),
      t
    );
  }
  fromJSON(t) {
    (super.fromJSON(t), (this.points = []));
    for (let e = 0, n = t.points.length; e < n; e++) {
      const s = t.points[e];
      this.points.push(new L().fromArray(s));
    }
    return (
      (this.closed = t.closed),
      (this.curveType = t.curveType),
      (this.tension = t.tension),
      this
    );
  }
}
function zo(i, t, e, n, s) {
  const r = (n - t) * 0.5,
    a = (s - e) * 0.5,
    o = i * i,
    l = i * o;
  return (2 * e - 2 * n + r + a) * l + (-3 * e + 3 * n - 2 * r - a) * o + r * i + e;
}
function jh(i, t) {
  const e = 1 - i;
  return e * e * t;
}
function Qh(i, t) {
  return 2 * (1 - i) * i * t;
}
function tu(i, t) {
  return i * i * t;
}
function Hi(i, t, e, n) {
  return jh(i, t) + Qh(i, e) + tu(i, n);
}
function eu(i, t) {
  const e = 1 - i;
  return e * e * e * t;
}
function nu(i, t) {
  const e = 1 - i;
  return 3 * e * e * i * t;
}
function iu(i, t) {
  return 3 * (1 - i) * i * i * t;
}
function su(i, t) {
  return i * i * i * t;
}
function ki(i, t, e, n, s) {
  return eu(i, t) + nu(i, e) + iu(i, n) + su(i, s);
}
class $l extends ln {
  constructor(t = new ct(), e = new ct(), n = new ct(), s = new ct()) {
    (super(),
      (this.isCubicBezierCurve = !0),
      (this.type = 'CubicBezierCurve'),
      (this.v0 = t),
      (this.v1 = e),
      (this.v2 = n),
      (this.v3 = s));
  }
  getPoint(t, e = new ct()) {
    const n = e,
      s = this.v0,
      r = this.v1,
      a = this.v2,
      o = this.v3;
    return (n.set(ki(t, s.x, r.x, a.x, o.x), ki(t, s.y, r.y, a.y, o.y)), n);
  }
  copy(t) {
    return (
      super.copy(t),
      this.v0.copy(t.v0),
      this.v1.copy(t.v1),
      this.v2.copy(t.v2),
      this.v3.copy(t.v3),
      this
    );
  }
  toJSON() {
    const t = super.toJSON();
    return (
      (t.v0 = this.v0.toArray()),
      (t.v1 = this.v1.toArray()),
      (t.v2 = this.v2.toArray()),
      (t.v3 = this.v3.toArray()),
      t
    );
  }
  fromJSON(t) {
    return (
      super.fromJSON(t),
      this.v0.fromArray(t.v0),
      this.v1.fromArray(t.v1),
      this.v2.fromArray(t.v2),
      this.v3.fromArray(t.v3),
      this
    );
  }
}
class ru extends ln {
  constructor(t = new L(), e = new L(), n = new L(), s = new L()) {
    (super(),
      (this.isCubicBezierCurve3 = !0),
      (this.type = 'CubicBezierCurve3'),
      (this.v0 = t),
      (this.v1 = e),
      (this.v2 = n),
      (this.v3 = s));
  }
  getPoint(t, e = new L()) {
    const n = e,
      s = this.v0,
      r = this.v1,
      a = this.v2,
      o = this.v3;
    return (
      n.set(ki(t, s.x, r.x, a.x, o.x), ki(t, s.y, r.y, a.y, o.y), ki(t, s.z, r.z, a.z, o.z)),
      n
    );
  }
  copy(t) {
    return (
      super.copy(t),
      this.v0.copy(t.v0),
      this.v1.copy(t.v1),
      this.v2.copy(t.v2),
      this.v3.copy(t.v3),
      this
    );
  }
  toJSON() {
    const t = super.toJSON();
    return (
      (t.v0 = this.v0.toArray()),
      (t.v1 = this.v1.toArray()),
      (t.v2 = this.v2.toArray()),
      (t.v3 = this.v3.toArray()),
      t
    );
  }
  fromJSON(t) {
    return (
      super.fromJSON(t),
      this.v0.fromArray(t.v0),
      this.v1.fromArray(t.v1),
      this.v2.fromArray(t.v2),
      this.v3.fromArray(t.v3),
      this
    );
  }
}
class Kl extends ln {
  constructor(t = new ct(), e = new ct()) {
    (super(), (this.isLineCurve = !0), (this.type = 'LineCurve'), (this.v1 = t), (this.v2 = e));
  }
  getPoint(t, e = new ct()) {
    const n = e;
    return (
      t === 1 ? n.copy(this.v2) : (n.copy(this.v2).sub(this.v1), n.multiplyScalar(t).add(this.v1)),
      n
    );
  }
  getPointAt(t, e) {
    return this.getPoint(t, e);
  }
  getTangent(t, e = new ct()) {
    return e.subVectors(this.v2, this.v1).normalize();
  }
  getTangentAt(t, e) {
    return this.getTangent(t, e);
  }
  copy(t) {
    return (super.copy(t), this.v1.copy(t.v1), this.v2.copy(t.v2), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.v1 = this.v1.toArray()), (t.v2 = this.v2.toArray()), t);
  }
  fromJSON(t) {
    return (super.fromJSON(t), this.v1.fromArray(t.v1), this.v2.fromArray(t.v2), this);
  }
}
class au extends ln {
  constructor(t = new L(), e = new L()) {
    (super(), (this.isLineCurve3 = !0), (this.type = 'LineCurve3'), (this.v1 = t), (this.v2 = e));
  }
  getPoint(t, e = new L()) {
    const n = e;
    return (
      t === 1 ? n.copy(this.v2) : (n.copy(this.v2).sub(this.v1), n.multiplyScalar(t).add(this.v1)),
      n
    );
  }
  getPointAt(t, e) {
    return this.getPoint(t, e);
  }
  getTangent(t, e = new L()) {
    return e.subVectors(this.v2, this.v1).normalize();
  }
  getTangentAt(t, e) {
    return this.getTangent(t, e);
  }
  copy(t) {
    return (super.copy(t), this.v1.copy(t.v1), this.v2.copy(t.v2), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.v1 = this.v1.toArray()), (t.v2 = this.v2.toArray()), t);
  }
  fromJSON(t) {
    return (super.fromJSON(t), this.v1.fromArray(t.v1), this.v2.fromArray(t.v2), this);
  }
}
class jl extends ln {
  constructor(t = new ct(), e = new ct(), n = new ct()) {
    (super(),
      (this.isQuadraticBezierCurve = !0),
      (this.type = 'QuadraticBezierCurve'),
      (this.v0 = t),
      (this.v1 = e),
      (this.v2 = n));
  }
  getPoint(t, e = new ct()) {
    const n = e,
      s = this.v0,
      r = this.v1,
      a = this.v2;
    return (n.set(Hi(t, s.x, r.x, a.x), Hi(t, s.y, r.y, a.y)), n);
  }
  copy(t) {
    return (super.copy(t), this.v0.copy(t.v0), this.v1.copy(t.v1), this.v2.copy(t.v2), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.v0 = this.v0.toArray()), (t.v1 = this.v1.toArray()), (t.v2 = this.v2.toArray()), t);
  }
  fromJSON(t) {
    return (
      super.fromJSON(t),
      this.v0.fromArray(t.v0),
      this.v1.fromArray(t.v1),
      this.v2.fromArray(t.v2),
      this
    );
  }
}
class Ql extends ln {
  constructor(t = new L(), e = new L(), n = new L()) {
    (super(),
      (this.isQuadraticBezierCurve3 = !0),
      (this.type = 'QuadraticBezierCurve3'),
      (this.v0 = t),
      (this.v1 = e),
      (this.v2 = n));
  }
  getPoint(t, e = new L()) {
    const n = e,
      s = this.v0,
      r = this.v1,
      a = this.v2;
    return (n.set(Hi(t, s.x, r.x, a.x), Hi(t, s.y, r.y, a.y), Hi(t, s.z, r.z, a.z)), n);
  }
  copy(t) {
    return (super.copy(t), this.v0.copy(t.v0), this.v1.copy(t.v1), this.v2.copy(t.v2), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.v0 = this.v0.toArray()), (t.v1 = this.v1.toArray()), (t.v2 = this.v2.toArray()), t);
  }
  fromJSON(t) {
    return (
      super.fromJSON(t),
      this.v0.fromArray(t.v0),
      this.v1.fromArray(t.v1),
      this.v2.fromArray(t.v2),
      this
    );
  }
}
class tc extends ln {
  constructor(t = []) {
    (super(), (this.isSplineCurve = !0), (this.type = 'SplineCurve'), (this.points = t));
  }
  getPoint(t, e = new ct()) {
    const n = e,
      s = this.points,
      r = (s.length - 1) * t,
      a = Math.floor(r),
      o = r - a,
      l = s[a === 0 ? a : a - 1],
      c = s[a],
      h = s[a > s.length - 2 ? s.length - 1 : a + 1],
      f = s[a > s.length - 3 ? s.length - 1 : a + 2];
    return (n.set(zo(o, l.x, c.x, h.x, f.x), zo(o, l.y, c.y, h.y, f.y)), n);
  }
  copy(t) {
    (super.copy(t), (this.points = []));
    for (let e = 0, n = t.points.length; e < n; e++) {
      const s = t.points[e];
      this.points.push(s.clone());
    }
    return this;
  }
  toJSON() {
    const t = super.toJSON();
    t.points = [];
    for (let e = 0, n = this.points.length; e < n; e++) {
      const s = this.points[e];
      t.points.push(s.toArray());
    }
    return t;
  }
  fromJSON(t) {
    (super.fromJSON(t), (this.points = []));
    for (let e = 0, n = t.points.length; e < n; e++) {
      const s = t.points[e];
      this.points.push(new ct().fromArray(s));
    }
    return this;
  }
}
var Ys = Object.freeze({
  __proto__: null,
  ArcCurve: $h,
  CatmullRomCurve3: Kh,
  CubicBezierCurve: $l,
  CubicBezierCurve3: ru,
  EllipseCurve: $a,
  LineCurve: Kl,
  LineCurve3: au,
  QuadraticBezierCurve: jl,
  QuadraticBezierCurve3: Ql,
  SplineCurve: tc,
});
class ou extends ln {
  constructor() {
    (super(), (this.type = 'CurvePath'), (this.curves = []), (this.autoClose = !1));
  }
  add(t) {
    this.curves.push(t);
  }
  closePath() {
    const t = this.curves[0].getPoint(0),
      e = this.curves[this.curves.length - 1].getPoint(1);
    if (!t.equals(e)) {
      const n = t.isVector2 === !0 ? 'LineCurve' : 'LineCurve3';
      this.curves.push(new Ys[n](e, t));
    }
    return this;
  }
  getPoint(t, e) {
    const n = t * this.getLength(),
      s = this.getCurveLengths();
    let r = 0;
    for (; r < s.length; ) {
      if (s[r] >= n) {
        const a = s[r] - n,
          o = this.curves[r],
          l = o.getLength(),
          c = l === 0 ? 0 : 1 - a / l;
        return o.getPointAt(c, e);
      }
      r++;
    }
    return null;
  }
  getLength() {
    const t = this.getCurveLengths();
    return t[t.length - 1];
  }
  updateArcLengths() {
    ((this.needsUpdate = !0), (this.cacheLengths = null), this.getCurveLengths());
  }
  getCurveLengths() {
    if (this.cacheLengths && this.cacheLengths.length === this.curves.length)
      return this.cacheLengths;
    const t = [];
    let e = 0;
    for (let n = 0, s = this.curves.length; n < s; n++)
      ((e += this.curves[n].getLength()), t.push(e));
    return ((this.cacheLengths = t), t);
  }
  getSpacedPoints(t = 40) {
    const e = [];
    for (let n = 0; n <= t; n++) e.push(this.getPoint(n / t));
    return (this.autoClose && e.push(e[0]), e);
  }
  getPoints(t = 12) {
    const e = [];
    let n;
    for (let s = 0, r = this.curves; s < r.length; s++) {
      const a = r[s],
        o = a.isEllipseCurve
          ? t * 2
          : a.isLineCurve || a.isLineCurve3
            ? 1
            : a.isSplineCurve
              ? t * a.points.length
              : t,
        l = a.getPoints(o);
      for (let c = 0; c < l.length; c++) {
        const h = l[c];
        (n && n.equals(h)) || (e.push(h), (n = h));
      }
    }
    return (this.autoClose && e.length > 1 && !e[e.length - 1].equals(e[0]) && e.push(e[0]), e);
  }
  copy(t) {
    (super.copy(t), (this.curves = []));
    for (let e = 0, n = t.curves.length; e < n; e++) {
      const s = t.curves[e];
      this.curves.push(s.clone());
    }
    return ((this.autoClose = t.autoClose), this);
  }
  toJSON() {
    const t = super.toJSON();
    ((t.autoClose = this.autoClose), (t.curves = []));
    for (let e = 0, n = this.curves.length; e < n; e++) {
      const s = this.curves[e];
      t.curves.push(s.toJSON());
    }
    return t;
  }
  fromJSON(t) {
    (super.fromJSON(t), (this.autoClose = t.autoClose), (this.curves = []));
    for (let e = 0, n = t.curves.length; e < n; e++) {
      const s = t.curves[e];
      this.curves.push(new Ys[s.type]().fromJSON(s));
    }
    return this;
  }
}
class Da extends ou {
  constructor(t) {
    (super(), (this.type = 'Path'), (this.currentPoint = new ct()), t && this.setFromPoints(t));
  }
  setFromPoints(t) {
    this.moveTo(t[0].x, t[0].y);
    for (let e = 1, n = t.length; e < n; e++) this.lineTo(t[e].x, t[e].y);
    return this;
  }
  moveTo(t, e) {
    return (this.currentPoint.set(t, e), this);
  }
  lineTo(t, e) {
    const n = new Kl(this.currentPoint.clone(), new ct(t, e));
    return (this.curves.push(n), this.currentPoint.set(t, e), this);
  }
  quadraticCurveTo(t, e, n, s) {
    const r = new jl(this.currentPoint.clone(), new ct(t, e), new ct(n, s));
    return (this.curves.push(r), this.currentPoint.set(n, s), this);
  }
  bezierCurveTo(t, e, n, s, r, a) {
    const o = new $l(this.currentPoint.clone(), new ct(t, e), new ct(n, s), new ct(r, a));
    return (this.curves.push(o), this.currentPoint.set(r, a), this);
  }
  splineThru(t) {
    const e = [this.currentPoint.clone()].concat(t),
      n = new tc(e);
    return (this.curves.push(n), this.currentPoint.copy(t[t.length - 1]), this);
  }
  arc(t, e, n, s, r, a) {
    const o = this.currentPoint.x,
      l = this.currentPoint.y;
    return (this.absarc(t + o, e + l, n, s, r, a), this);
  }
  absarc(t, e, n, s, r, a) {
    return (this.absellipse(t, e, n, n, s, r, a), this);
  }
  ellipse(t, e, n, s, r, a, o, l) {
    const c = this.currentPoint.x,
      h = this.currentPoint.y;
    return (this.absellipse(t + c, e + h, n, s, r, a, o, l), this);
  }
  absellipse(t, e, n, s, r, a, o, l) {
    const c = new $a(t, e, n, s, r, a, o, l);
    if (this.curves.length > 0) {
      const f = c.getPoint(0);
      f.equals(this.currentPoint) || this.lineTo(f.x, f.y);
    }
    this.curves.push(c);
    const h = c.getPoint(1);
    return (this.currentPoint.copy(h), this);
  }
  copy(t) {
    return (super.copy(t), this.currentPoint.copy(t.currentPoint), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.currentPoint = this.currentPoint.toArray()), t);
  }
  fromJSON(t) {
    return (super.fromJSON(t), this.currentPoint.fromArray(t.currentPoint), this);
  }
}
class Vs extends Da {
  constructor(t) {
    (super(t), (this.uuid = sn()), (this.type = 'Shape'), (this.holes = []));
  }
  getPointsHoles(t) {
    const e = [];
    for (let n = 0, s = this.holes.length; n < s; n++) e[n] = this.holes[n].getPoints(t);
    return e;
  }
  extractPoints(t) {
    return { shape: this.getPoints(t), holes: this.getPointsHoles(t) };
  }
  copy(t) {
    (super.copy(t), (this.holes = []));
    for (let e = 0, n = t.holes.length; e < n; e++) {
      const s = t.holes[e];
      this.holes.push(s.clone());
    }
    return this;
  }
  toJSON() {
    const t = super.toJSON();
    ((t.uuid = this.uuid), (t.holes = []));
    for (let e = 0, n = this.holes.length; e < n; e++) {
      const s = this.holes[e];
      t.holes.push(s.toJSON());
    }
    return t;
  }
  fromJSON(t) {
    (super.fromJSON(t), (this.uuid = t.uuid), (this.holes = []));
    for (let e = 0, n = t.holes.length; e < n; e++) {
      const s = t.holes[e];
      this.holes.push(new Da().fromJSON(s));
    }
    return this;
  }
}
function lu(i, t, e = 2) {
  const n = t && t.length,
    s = n ? t[0] * e : i.length;
  let r = ec(i, 0, s, e, !0);
  const a = [];
  if (!r || r.next === r.prev) return a;
  let o, l, c;
  if ((n && (r = du(i, t, r, e)), i.length > 80 * e)) {
    ((o = i[0]), (l = i[1]));
    let h = o,
      f = l;
    for (let u = e; u < s; u += e) {
      const p = i[u],
        g = i[u + 1];
      (p < o && (o = p), g < l && (l = g), p > h && (h = p), g > f && (f = g));
    }
    ((c = Math.max(h - o, f - l)), (c = c !== 0 ? 32767 / c : 0));
  }
  return (Ji(r, a, e, o, l, c, 0), a);
}
function ec(i, t, e, n, s) {
  let r;
  if (s === bu(i, t, e, n) > 0)
    for (let a = t; a < e; a += n) r = Vo((a / n) | 0, i[a], i[a + 1], r);
  else for (let a = e - n; a >= t; a -= n) r = Vo((a / n) | 0, i[a], i[a + 1], r);
  return (r && Ai(r, r.next) && (Ki(r), (r = r.next)), r);
}
function $n(i, t) {
  if (!i) return i;
  t || (t = i);
  let e = i,
    n;
  do
    if (((n = !1), !e.steiner && (Ai(e, e.next) || ce(e.prev, e, e.next) === 0))) {
      if ((Ki(e), (e = t = e.prev), e === e.next)) break;
      n = !0;
    } else e = e.next;
  while (n || e !== t);
  return t;
}
function Ji(i, t, e, n, s, r, a) {
  if (!i) return;
  !a && r && xu(i, n, s, r);
  let o = i;
  for (; i.prev !== i.next; ) {
    const l = i.prev,
      c = i.next;
    if (r ? hu(i, n, s, r) : cu(i)) {
      (t.push(l.i, i.i, c.i), Ki(i), (i = c.next), (o = c.next));
      continue;
    }
    if (((i = c), i === o)) {
      a
        ? a === 1
          ? ((i = uu($n(i), t)), Ji(i, t, e, n, s, r, 2))
          : a === 2 && fu(i, t, e, n, s, r)
        : Ji($n(i), t, e, n, s, r, 1);
      break;
    }
  }
}
function cu(i) {
  const t = i.prev,
    e = i,
    n = i.next;
  if (ce(t, e, n) >= 0) return !1;
  const s = t.x,
    r = e.x,
    a = n.x,
    o = t.y,
    l = e.y,
    c = n.y,
    h = Math.min(s, r, a),
    f = Math.min(o, l, c),
    u = Math.max(s, r, a),
    p = Math.max(o, l, c);
  let g = n.next;
  for (; g !== t; ) {
    if (
      g.x >= h &&
      g.x <= u &&
      g.y >= f &&
      g.y <= p &&
      Bi(s, o, r, l, a, c, g.x, g.y) &&
      ce(g.prev, g, g.next) >= 0
    )
      return !1;
    g = g.next;
  }
  return !0;
}
function hu(i, t, e, n) {
  const s = i.prev,
    r = i,
    a = i.next;
  if (ce(s, r, a) >= 0) return !1;
  const o = s.x,
    l = r.x,
    c = a.x,
    h = s.y,
    f = r.y,
    u = a.y,
    p = Math.min(o, l, c),
    g = Math.min(h, f, u),
    M = Math.max(o, l, c),
    m = Math.max(h, f, u),
    d = Ia(p, g, t, e, n),
    E = Ia(M, m, t, e, n);
  let y = i.prevZ,
    S = i.nextZ;
  for (; y && y.z >= d && S && S.z <= E; ) {
    if (
      (y.x >= p &&
        y.x <= M &&
        y.y >= g &&
        y.y <= m &&
        y !== s &&
        y !== a &&
        Bi(o, h, l, f, c, u, y.x, y.y) &&
        ce(y.prev, y, y.next) >= 0) ||
      ((y = y.prevZ),
      S.x >= p &&
        S.x <= M &&
        S.y >= g &&
        S.y <= m &&
        S !== s &&
        S !== a &&
        Bi(o, h, l, f, c, u, S.x, S.y) &&
        ce(S.prev, S, S.next) >= 0)
    )
      return !1;
    S = S.nextZ;
  }
  for (; y && y.z >= d; ) {
    if (
      y.x >= p &&
      y.x <= M &&
      y.y >= g &&
      y.y <= m &&
      y !== s &&
      y !== a &&
      Bi(o, h, l, f, c, u, y.x, y.y) &&
      ce(y.prev, y, y.next) >= 0
    )
      return !1;
    y = y.prevZ;
  }
  for (; S && S.z <= E; ) {
    if (
      S.x >= p &&
      S.x <= M &&
      S.y >= g &&
      S.y <= m &&
      S !== s &&
      S !== a &&
      Bi(o, h, l, f, c, u, S.x, S.y) &&
      ce(S.prev, S, S.next) >= 0
    )
      return !1;
    S = S.nextZ;
  }
  return !0;
}
function uu(i, t) {
  let e = i;
  do {
    const n = e.prev,
      s = e.next.next;
    (!Ai(n, s) &&
      ic(n, e, e.next, s) &&
      $i(n, s) &&
      $i(s, n) &&
      (t.push(n.i, e.i, s.i), Ki(e), Ki(e.next), (e = i = s)),
      (e = e.next));
  } while (e !== i);
  return $n(e);
}
function fu(i, t, e, n, s, r) {
  let a = i;
  do {
    let o = a.next.next;
    for (; o !== a.prev; ) {
      if (a.i !== o.i && Su(a, o)) {
        let l = sc(a, o);
        ((a = $n(a, a.next)),
          (l = $n(l, l.next)),
          Ji(a, t, e, n, s, r, 0),
          Ji(l, t, e, n, s, r, 0));
        return;
      }
      o = o.next;
    }
    a = a.next;
  } while (a !== i);
}
function du(i, t, e, n) {
  const s = [];
  for (let r = 0, a = t.length; r < a; r++) {
    const o = t[r] * n,
      l = r < a - 1 ? t[r + 1] * n : i.length,
      c = ec(i, o, l, n, !1);
    (c === c.next && (c.steiner = !0), s.push(Mu(c)));
  }
  s.sort(pu);
  for (let r = 0; r < s.length; r++) e = mu(s[r], e);
  return e;
}
function pu(i, t) {
  let e = i.x - t.x;
  if (e === 0 && ((e = i.y - t.y), e === 0)) {
    const n = (i.next.y - i.y) / (i.next.x - i.x),
      s = (t.next.y - t.y) / (t.next.x - t.x);
    e = n - s;
  }
  return e;
}
function mu(i, t) {
  const e = gu(i, t);
  if (!e) return t;
  const n = sc(e, i);
  return ($n(n, n.next), $n(e, e.next));
}
function gu(i, t) {
  let e = t;
  const n = i.x,
    s = i.y;
  let r = -1 / 0,
    a;
  if (Ai(i, e)) return e;
  do {
    if (Ai(i, e.next)) return e.next;
    if (s <= e.y && s >= e.next.y && e.next.y !== e.y) {
      const f = e.x + ((s - e.y) * (e.next.x - e.x)) / (e.next.y - e.y);
      if (f <= n && f > r && ((r = f), (a = e.x < e.next.x ? e : e.next), f === n)) return a;
    }
    e = e.next;
  } while (e !== t);
  if (!a) return null;
  const o = a,
    l = a.x,
    c = a.y;
  let h = 1 / 0;
  e = a;
  do {
    if (
      n >= e.x &&
      e.x >= l &&
      n !== e.x &&
      nc(s < c ? n : r, s, l, c, s < c ? r : n, s, e.x, e.y)
    ) {
      const f = Math.abs(s - e.y) / (n - e.x);
      $i(e, i) &&
        (f < h || (f === h && (e.x > a.x || (e.x === a.x && _u(a, e))))) &&
        ((a = e), (h = f));
    }
    e = e.next;
  } while (e !== o);
  return a;
}
function _u(i, t) {
  return ce(i.prev, i, t.prev) < 0 && ce(t.next, i, i.next) < 0;
}
function xu(i, t, e, n) {
  let s = i;
  do
    (s.z === 0 && (s.z = Ia(s.x, s.y, t, e, n)),
      (s.prevZ = s.prev),
      (s.nextZ = s.next),
      (s = s.next));
  while (s !== i);
  ((s.prevZ.nextZ = null), (s.prevZ = null), vu(s));
}
function vu(i) {
  let t,
    e = 1;
  do {
    let n = i,
      s;
    i = null;
    let r = null;
    for (t = 0; n; ) {
      t++;
      let a = n,
        o = 0;
      for (let c = 0; c < e && (o++, (a = a.nextZ), !!a); c++);
      let l = e;
      for (; o > 0 || (l > 0 && a); )
        (o !== 0 && (l === 0 || !a || n.z <= a.z)
          ? ((s = n), (n = n.nextZ), o--)
          : ((s = a), (a = a.nextZ), l--),
          r ? (r.nextZ = s) : (i = s),
          (s.prevZ = r),
          (r = s));
      n = a;
    }
    ((r.nextZ = null), (e *= 2));
  } while (t > 1);
  return i;
}
function Ia(i, t, e, n, s) {
  return (
    (i = ((i - e) * s) | 0),
    (t = ((t - n) * s) | 0),
    (i = (i | (i << 8)) & 16711935),
    (i = (i | (i << 4)) & 252645135),
    (i = (i | (i << 2)) & 858993459),
    (i = (i | (i << 1)) & 1431655765),
    (t = (t | (t << 8)) & 16711935),
    (t = (t | (t << 4)) & 252645135),
    (t = (t | (t << 2)) & 858993459),
    (t = (t | (t << 1)) & 1431655765),
    i | (t << 1)
  );
}
function Mu(i) {
  let t = i,
    e = i;
  do ((t.x < e.x || (t.x === e.x && t.y < e.y)) && (e = t), (t = t.next));
  while (t !== i);
  return e;
}
function nc(i, t, e, n, s, r, a, o) {
  return (
    (s - a) * (t - o) >= (i - a) * (r - o) &&
    (i - a) * (n - o) >= (e - a) * (t - o) &&
    (e - a) * (r - o) >= (s - a) * (n - o)
  );
}
function Bi(i, t, e, n, s, r, a, o) {
  return !(i === a && t === o) && nc(i, t, e, n, s, r, a, o);
}
function Su(i, t) {
  return (
    i.next.i !== t.i &&
    i.prev.i !== t.i &&
    !yu(i, t) &&
    (($i(i, t) && $i(t, i) && Eu(i, t) && (ce(i.prev, i, t.prev) || ce(i, t.prev, t))) ||
      (Ai(i, t) && ce(i.prev, i, i.next) > 0 && ce(t.prev, t, t.next) > 0))
  );
}
function ce(i, t, e) {
  return (t.y - i.y) * (e.x - t.x) - (t.x - i.x) * (e.y - t.y);
}
function Ai(i, t) {
  return i.x === t.x && i.y === t.y;
}
function ic(i, t, e, n) {
  const s = Cs(ce(i, t, e)),
    r = Cs(ce(i, t, n)),
    a = Cs(ce(e, n, i)),
    o = Cs(ce(e, n, t));
  return !!(
    (s !== r && a !== o) ||
    (s === 0 && Rs(i, e, t)) ||
    (r === 0 && Rs(i, n, t)) ||
    (a === 0 && Rs(e, i, n)) ||
    (o === 0 && Rs(e, t, n))
  );
}
function Rs(i, t, e) {
  return (
    t.x <= Math.max(i.x, e.x) &&
    t.x >= Math.min(i.x, e.x) &&
    t.y <= Math.max(i.y, e.y) &&
    t.y >= Math.min(i.y, e.y)
  );
}
function Cs(i) {
  return i > 0 ? 1 : i < 0 ? -1 : 0;
}
function yu(i, t) {
  let e = i;
  do {
    if (e.i !== i.i && e.next.i !== i.i && e.i !== t.i && e.next.i !== t.i && ic(e, e.next, i, t))
      return !0;
    e = e.next;
  } while (e !== i);
  return !1;
}
function $i(i, t) {
  return ce(i.prev, i, i.next) < 0
    ? ce(i, t, i.next) >= 0 && ce(i, i.prev, t) >= 0
    : ce(i, t, i.prev) < 0 || ce(i, i.next, t) < 0;
}
function Eu(i, t) {
  let e = i,
    n = !1;
  const s = (i.x + t.x) / 2,
    r = (i.y + t.y) / 2;
  do
    (e.y > r != e.next.y > r &&
      e.next.y !== e.y &&
      s < ((e.next.x - e.x) * (r - e.y)) / (e.next.y - e.y) + e.x &&
      (n = !n),
      (e = e.next));
  while (e !== i);
  return n;
}
function sc(i, t) {
  const e = Ua(i.i, i.x, i.y),
    n = Ua(t.i, t.x, t.y),
    s = i.next,
    r = t.prev;
  return (
    (i.next = t),
    (t.prev = i),
    (e.next = s),
    (s.prev = e),
    (n.next = e),
    (e.prev = n),
    (r.next = n),
    (n.prev = r),
    n
  );
}
function Vo(i, t, e, n) {
  const s = Ua(i, t, e);
  return (
    n
      ? ((s.next = n.next), (s.prev = n), (n.next.prev = s), (n.next = s))
      : ((s.prev = s), (s.next = s)),
    s
  );
}
function Ki(i) {
  ((i.next.prev = i.prev),
    (i.prev.next = i.next),
    i.prevZ && (i.prevZ.nextZ = i.nextZ),
    i.nextZ && (i.nextZ.prevZ = i.prevZ));
}
function Ua(i, t, e) {
  return { i, x: t, y: e, prev: null, next: null, z: 0, prevZ: null, nextZ: null, steiner: !1 };
}
function bu(i, t, e, n) {
  let s = 0;
  for (let r = t, a = e - n; r < e; r += n) ((s += (i[a] - i[r]) * (i[r + 1] + i[a + 1])), (a = r));
  return s;
}
class Tu {
  static triangulate(t, e, n = 2) {
    return lu(t, e, n);
  }
}
class Zn {
  static area(t) {
    const e = t.length;
    let n = 0;
    for (let s = e - 1, r = 0; r < e; s = r++) n += t[s].x * t[r].y - t[r].x * t[s].y;
    return n * 0.5;
  }
  static isClockWise(t) {
    return Zn.area(t) < 0;
  }
  static triangulateShape(t, e) {
    const n = [],
      s = [],
      r = [];
    (Go(t), Ho(n, t));
    let a = t.length;
    e.forEach(Go);
    for (let l = 0; l < e.length; l++) (s.push(a), (a += e[l].length), Ho(n, e[l]));
    const o = Tu.triangulate(n, s);
    for (let l = 0; l < o.length; l += 3) r.push(o.slice(l, l + 3));
    return r;
  }
}
function Go(i) {
  const t = i.length;
  t > 2 && i[t - 1].equals(i[0]) && i.pop();
}
function Ho(i, t) {
  for (let e = 0; e < t.length; e++) (i.push(t[e].x), i.push(t[e].y));
}
class rc extends xe {
  constructor(
    t = new Vs([new ct(0.5, 0.5), new ct(-0.5, 0.5), new ct(-0.5, -0.5), new ct(0.5, -0.5)]),
    e = {}
  ) {
    (super(),
      (this.type = 'ExtrudeGeometry'),
      (this.parameters = { shapes: t, options: e }),
      (t = Array.isArray(t) ? t : [t]));
    const n = this,
      s = [],
      r = [];
    for (let o = 0, l = t.length; o < l; o++) {
      const c = t[o];
      a(c);
    }
    (this.setAttribute('position', new ee(s, 3)),
      this.setAttribute('uv', new ee(r, 2)),
      this.computeVertexNormals());
    function a(o) {
      const l = [],
        c = e.curveSegments !== void 0 ? e.curveSegments : 12,
        h = e.steps !== void 0 ? e.steps : 1,
        f = e.depth !== void 0 ? e.depth : 1;
      let u = e.bevelEnabled !== void 0 ? e.bevelEnabled : !0,
        p = e.bevelThickness !== void 0 ? e.bevelThickness : 0.2,
        g = e.bevelSize !== void 0 ? e.bevelSize : p - 0.1,
        M = e.bevelOffset !== void 0 ? e.bevelOffset : 0,
        m = e.bevelSegments !== void 0 ? e.bevelSegments : 3;
      const d = e.extrudePath,
        E = e.UVGenerator !== void 0 ? e.UVGenerator : Au;
      let y,
        S = !1,
        R,
        w,
        P,
        x;
      if (d) {
        ((y = d.getSpacedPoints(h)), (S = !0), (u = !1));
        const $ = d.isCatmullRomCurve3 ? d.closed : !1;
        ((R = d.computeFrenetFrames(h, $)), (w = new L()), (P = new L()), (x = new L()));
      }
      u || ((m = 0), (p = 0), (g = 0), (M = 0));
      const b = o.extractPoints(c);
      let H = b.shape;
      const C = b.holes;
      if (!Zn.isClockWise(H)) {
        H = H.reverse();
        for (let $ = 0, tt = C.length; $ < tt; $++) {
          const K = C[$];
          Zn.isClockWise(K) && (C[$] = K.reverse());
        }
      }
      function z($) {
        const K = 10000000000000001e-36;
        let ut = $[0];
        for (let A = 1; A <= $.length; A++) {
          const Dt = A % $.length,
            xt = $[Dt],
            Ut = xt.x - ut.x,
            ot = xt.y - ut.y,
            T = Ut * Ut + ot * ot,
            _ = Math.max(Math.abs(xt.x), Math.abs(xt.y), Math.abs(ut.x), Math.abs(ut.y)),
            I = K * _ * _;
          if (T <= I) {
            ($.splice(Dt, 1), A--);
            continue;
          }
          ut = xt;
        }
      }
      (z(H), C.forEach(z));
      const k = C.length,
        F = H;
      for (let $ = 0; $ < k; $++) {
        const tt = C[$];
        H = H.concat(tt);
      }
      function O($, tt, K) {
        return (tt || Jt('ExtrudeGeometry: vec does not exist'), $.clone().addScaledVector(tt, K));
      }
      const B = H.length;
      function nt($, tt, K) {
        let ut, A, Dt;
        const xt = $.x - tt.x,
          Ut = $.y - tt.y,
          ot = K.x - $.x,
          T = K.y - $.y,
          _ = xt * xt + Ut * Ut,
          I = xt * T - Ut * ot;
        if (Math.abs(I) > Number.EPSILON) {
          const X = Math.sqrt(_),
            J = Math.sqrt(ot * ot + T * T),
            q = tt.x - Ut / X,
            yt = tt.y + xt / X,
            lt = K.x - T / J,
            Ct = K.y + ot / J,
            Nt = ((lt - q) * T - (Ct - yt) * ot) / (xt * T - Ut * ot);
          ((ut = q + xt * Nt - $.x), (A = yt + Ut * Nt - $.y));
          const Q = ut * ut + A * A;
          if (Q <= 2) return new ct(ut, A);
          Dt = Math.sqrt(Q / 2);
        } else {
          let X = !1;
          (xt > Number.EPSILON
            ? ot > Number.EPSILON && (X = !0)
            : xt < -Number.EPSILON
              ? ot < -Number.EPSILON && (X = !0)
              : Math.sign(Ut) === Math.sign(T) && (X = !0),
            X
              ? ((ut = -Ut), (A = xt), (Dt = Math.sqrt(_)))
              : ((ut = xt), (A = Ut), (Dt = Math.sqrt(_ / 2))));
        }
        return new ct(ut / Dt, A / Dt);
      }
      const j = [];
      for (let $ = 0, tt = F.length, K = tt - 1, ut = $ + 1; $ < tt; $++, K++, ut++)
        (K === tt && (K = 0), ut === tt && (ut = 0), (j[$] = nt(F[$], F[K], F[ut])));
      const mt = [];
      let _t,
        gt = j.concat();
      for (let $ = 0, tt = k; $ < tt; $++) {
        const K = C[$];
        _t = [];
        for (let ut = 0, A = K.length, Dt = A - 1, xt = ut + 1; ut < A; ut++, Dt++, xt++)
          (Dt === A && (Dt = 0), xt === A && (xt = 0), (_t[ut] = nt(K[ut], K[Dt], K[xt])));
        (mt.push(_t), (gt = gt.concat(_t)));
      }
      let Ot;
      if (m === 0) Ot = Zn.triangulateShape(F, C);
      else {
        const $ = [],
          tt = [];
        for (let K = 0; K < m; K++) {
          const ut = K / m,
            A = p * Math.cos((ut * Math.PI) / 2),
            Dt = g * Math.sin((ut * Math.PI) / 2) + M;
          for (let xt = 0, Ut = F.length; xt < Ut; xt++) {
            const ot = O(F[xt], j[xt], Dt);
            (It(ot.x, ot.y, -A), ut === 0 && $.push(ot));
          }
          for (let xt = 0, Ut = k; xt < Ut; xt++) {
            const ot = C[xt];
            _t = mt[xt];
            const T = [];
            for (let _ = 0, I = ot.length; _ < I; _++) {
              const X = O(ot[_], _t[_], Dt);
              (It(X.x, X.y, -A), ut === 0 && T.push(X));
            }
            ut === 0 && tt.push(T);
          }
        }
        Ot = Zn.triangulateShape($, tt);
      }
      const jt = Ot.length,
        ne = g + M;
      for (let $ = 0; $ < B; $++) {
        const tt = u ? O(H[$], gt[$], ne) : H[$];
        S
          ? (P.copy(R.normals[0]).multiplyScalar(tt.x),
            w.copy(R.binormals[0]).multiplyScalar(tt.y),
            x.copy(y[0]).add(P).add(w),
            It(x.x, x.y, x.z))
          : It(tt.x, tt.y, 0);
      }
      for (let $ = 1; $ <= h; $++)
        for (let tt = 0; tt < B; tt++) {
          const K = u ? O(H[tt], gt[tt], ne) : H[tt];
          S
            ? (P.copy(R.normals[$]).multiplyScalar(K.x),
              w.copy(R.binormals[$]).multiplyScalar(K.y),
              x.copy(y[$]).add(P).add(w),
              It(x.x, x.y, x.z))
            : It(K.x, K.y, (f / h) * $);
        }
      for (let $ = m - 1; $ >= 0; $--) {
        const tt = $ / m,
          K = p * Math.cos((tt * Math.PI) / 2),
          ut = g * Math.sin((tt * Math.PI) / 2) + M;
        for (let A = 0, Dt = F.length; A < Dt; A++) {
          const xt = O(F[A], j[A], ut);
          It(xt.x, xt.y, f + K);
        }
        for (let A = 0, Dt = C.length; A < Dt; A++) {
          const xt = C[A];
          _t = mt[A];
          for (let Ut = 0, ot = xt.length; Ut < ot; Ut++) {
            const T = O(xt[Ut], _t[Ut], ut);
            S ? It(T.x, T.y + y[h - 1].y, y[h - 1].x + K) : It(T.x, T.y, f + K);
          }
        }
      }
      (Z(), rt());
      function Z() {
        const $ = s.length / 3;
        if (u) {
          let tt = 0,
            K = B * tt;
          for (let ut = 0; ut < jt; ut++) {
            const A = Ot[ut];
            Lt(A[2] + K, A[1] + K, A[0] + K);
          }
          ((tt = h + m * 2), (K = B * tt));
          for (let ut = 0; ut < jt; ut++) {
            const A = Ot[ut];
            Lt(A[0] + K, A[1] + K, A[2] + K);
          }
        } else {
          for (let tt = 0; tt < jt; tt++) {
            const K = Ot[tt];
            Lt(K[2], K[1], K[0]);
          }
          for (let tt = 0; tt < jt; tt++) {
            const K = Ot[tt];
            Lt(K[0] + B * h, K[1] + B * h, K[2] + B * h);
          }
        }
        n.addGroup($, s.length / 3 - $, 0);
      }
      function rt() {
        const $ = s.length / 3;
        let tt = 0;
        (at(F, tt), (tt += F.length));
        for (let K = 0, ut = C.length; K < ut; K++) {
          const A = C[K];
          (at(A, tt), (tt += A.length));
        }
        n.addGroup($, s.length / 3 - $, 1);
      }
      function at($, tt) {
        let K = $.length;
        for (; --K >= 0; ) {
          const ut = K;
          let A = K - 1;
          A < 0 && (A = $.length - 1);
          for (let Dt = 0, xt = h + m * 2; Dt < xt; Dt++) {
            const Ut = B * Dt,
              ot = B * (Dt + 1),
              T = tt + ut + Ut,
              _ = tt + A + Ut,
              I = tt + A + ot,
              X = tt + ut + ot;
            Vt(T, _, I, X);
          }
        }
      }
      function It($, tt, K) {
        (l.push($), l.push(tt), l.push(K));
      }
      function Lt($, tt, K) {
        (ie($), ie(tt), ie(K));
        const ut = s.length / 3,
          A = E.generateTopUV(n, s, ut - 3, ut - 2, ut - 1);
        (Ht(A[0]), Ht(A[1]), Ht(A[2]));
      }
      function Vt($, tt, K, ut) {
        (ie($), ie(tt), ie(ut), ie(tt), ie(K), ie(ut));
        const A = s.length / 3,
          Dt = E.generateSideWallUV(n, s, A - 6, A - 3, A - 2, A - 1);
        (Ht(Dt[0]), Ht(Dt[1]), Ht(Dt[3]), Ht(Dt[1]), Ht(Dt[2]), Ht(Dt[3]));
      }
      function ie($) {
        (s.push(l[$ * 3 + 0]), s.push(l[$ * 3 + 1]), s.push(l[$ * 3 + 2]));
      }
      function Ht($) {
        (r.push($.x), r.push($.y));
      }
    }
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  toJSON() {
    const t = super.toJSON(),
      e = this.parameters.shapes,
      n = this.parameters.options;
    return wu(e, n, t);
  }
  static fromJSON(t, e) {
    const n = [];
    for (let r = 0, a = t.shapes.length; r < a; r++) {
      const o = e[t.shapes[r]];
      n.push(o);
    }
    const s = t.options.extrudePath;
    return (
      s !== void 0 && (t.options.extrudePath = new Ys[s.type]().fromJSON(s)),
      new rc(n, t.options)
    );
  }
}
const Au = {
  generateTopUV: function (i, t, e, n, s) {
    const r = t[e * 3],
      a = t[e * 3 + 1],
      o = t[n * 3],
      l = t[n * 3 + 1],
      c = t[s * 3],
      h = t[s * 3 + 1];
    return [new ct(r, a), new ct(o, l), new ct(c, h)];
  },
  generateSideWallUV: function (i, t, e, n, s, r) {
    const a = t[e * 3],
      o = t[e * 3 + 1],
      l = t[e * 3 + 2],
      c = t[n * 3],
      h = t[n * 3 + 1],
      f = t[n * 3 + 2],
      u = t[s * 3],
      p = t[s * 3 + 1],
      g = t[s * 3 + 2],
      M = t[r * 3],
      m = t[r * 3 + 1],
      d = t[r * 3 + 2];
    return Math.abs(o - h) < Math.abs(a - c)
      ? [new ct(a, 1 - l), new ct(c, 1 - f), new ct(u, 1 - g), new ct(M, 1 - d)]
      : [new ct(o, 1 - l), new ct(h, 1 - f), new ct(p, 1 - g), new ct(m, 1 - d)];
  },
};
function wu(i, t, e) {
  if (((e.shapes = []), Array.isArray(i)))
    for (let n = 0, s = i.length; n < s; n++) {
      const r = i[n];
      e.shapes.push(r.uuid);
    }
  else e.shapes.push(i.uuid);
  return (
    (e.options = Object.assign({}, t)),
    t.extrudePath !== void 0 && (e.options.extrudePath = t.extrudePath.toJSON()),
    e
  );
}
class js extends xe {
  constructor(t = 1, e = 1, n = 1, s = 1) {
    (super(),
      (this.type = 'PlaneGeometry'),
      (this.parameters = { width: t, height: e, widthSegments: n, heightSegments: s }));
    const r = t / 2,
      a = e / 2,
      o = Math.floor(n),
      l = Math.floor(s),
      c = o + 1,
      h = l + 1,
      f = t / o,
      u = e / l,
      p = [],
      g = [],
      M = [],
      m = [];
    for (let d = 0; d < h; d++) {
      const E = d * u - a;
      for (let y = 0; y < c; y++) {
        const S = y * f - r;
        (g.push(S, -E, 0), M.push(0, 0, 1), m.push(y / o), m.push(1 - d / l));
      }
    }
    for (let d = 0; d < l; d++)
      for (let E = 0; E < o; E++) {
        const y = E + c * d,
          S = E + c * (d + 1),
          R = E + 1 + c * (d + 1),
          w = E + 1 + c * d;
        (p.push(y, S, w), p.push(S, R, w));
      }
    (this.setIndex(p),
      this.setAttribute('position', new ee(g, 3)),
      this.setAttribute('normal', new ee(M, 3)),
      this.setAttribute('uv', new ee(m, 2)));
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  static fromJSON(t) {
    return new js(t.width, t.height, t.widthSegments, t.heightSegments);
  }
}
class ac extends xe {
  constructor(t = 0.5, e = 1, n = 32, s = 1, r = 0, a = Math.PI * 2) {
    (super(),
      (this.type = 'RingGeometry'),
      (this.parameters = {
        innerRadius: t,
        outerRadius: e,
        thetaSegments: n,
        phiSegments: s,
        thetaStart: r,
        thetaLength: a,
      }),
      (n = Math.max(3, n)),
      (s = Math.max(1, s)));
    const o = [],
      l = [],
      c = [],
      h = [];
    let f = t;
    const u = (e - t) / s,
      p = new L(),
      g = new ct();
    for (let M = 0; M <= s; M++) {
      for (let m = 0; m <= n; m++) {
        const d = r + (m / n) * a;
        ((p.x = f * Math.cos(d)),
          (p.y = f * Math.sin(d)),
          l.push(p.x, p.y, p.z),
          c.push(0, 0, 1),
          (g.x = (p.x / e + 1) / 2),
          (g.y = (p.y / e + 1) / 2),
          h.push(g.x, g.y));
      }
      f += u;
    }
    for (let M = 0; M < s; M++) {
      const m = M * (n + 1);
      for (let d = 0; d < n; d++) {
        const E = d + m,
          y = E,
          S = E + n + 1,
          R = E + n + 2,
          w = E + 1;
        (o.push(y, S, w), o.push(S, R, w));
      }
    }
    (this.setIndex(o),
      this.setAttribute('position', new ee(l, 3)),
      this.setAttribute('normal', new ee(c, 3)),
      this.setAttribute('uv', new ee(h, 2)));
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  static fromJSON(t) {
    return new ac(
      t.innerRadius,
      t.outerRadius,
      t.thetaSegments,
      t.phiSegments,
      t.thetaStart,
      t.thetaLength
    );
  }
}
class oc extends xe {
  constructor(t = 1, e = 32, n = 16, s = 0, r = Math.PI * 2, a = 0, o = Math.PI) {
    (super(),
      (this.type = 'SphereGeometry'),
      (this.parameters = {
        radius: t,
        widthSegments: e,
        heightSegments: n,
        phiStart: s,
        phiLength: r,
        thetaStart: a,
        thetaLength: o,
      }),
      (e = Math.max(3, Math.floor(e))),
      (n = Math.max(2, Math.floor(n))));
    const l = Math.min(a + o, Math.PI);
    let c = 0;
    const h = [],
      f = new L(),
      u = new L(),
      p = [],
      g = [],
      M = [],
      m = [];
    for (let d = 0; d <= n; d++) {
      const E = [],
        y = d / n;
      let S = 0;
      d === 0 && a === 0 ? (S = 0.5 / e) : d === n && l === Math.PI && (S = -0.5 / e);
      for (let R = 0; R <= e; R++) {
        const w = R / e;
        ((f.x = -t * Math.cos(s + w * r) * Math.sin(a + y * o)),
          (f.y = t * Math.cos(a + y * o)),
          (f.z = t * Math.sin(s + w * r) * Math.sin(a + y * o)),
          g.push(f.x, f.y, f.z),
          u.copy(f).normalize(),
          M.push(u.x, u.y, u.z),
          m.push(w + S, 1 - y),
          E.push(c++));
      }
      h.push(E);
    }
    for (let d = 0; d < n; d++)
      for (let E = 0; E < e; E++) {
        const y = h[d][E + 1],
          S = h[d][E],
          R = h[d + 1][E],
          w = h[d + 1][E + 1];
        ((d !== 0 || a > 0) && p.push(y, S, w), (d !== n - 1 || l < Math.PI) && p.push(S, R, w));
      }
    (this.setIndex(p),
      this.setAttribute('position', new ee(g, 3)),
      this.setAttribute('normal', new ee(M, 3)),
      this.setAttribute('uv', new ee(m, 2)));
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  static fromJSON(t) {
    return new oc(
      t.radius,
      t.widthSegments,
      t.heightSegments,
      t.phiStart,
      t.phiLength,
      t.thetaStart,
      t.thetaLength
    );
  }
}
class lc extends xe {
  constructor(
    t = new Ql(new L(-1, -1, 0), new L(-1, 1, 0), new L(1, 1, 0)),
    e = 64,
    n = 1,
    s = 8,
    r = !1
  ) {
    (super(),
      (this.type = 'TubeGeometry'),
      (this.parameters = { path: t, tubularSegments: e, radius: n, radialSegments: s, closed: r }));
    const a = t.computeFrenetFrames(e, r);
    ((this.tangents = a.tangents), (this.normals = a.normals), (this.binormals = a.binormals));
    const o = new L(),
      l = new L(),
      c = new ct();
    let h = new L();
    const f = [],
      u = [],
      p = [],
      g = [];
    (M(),
      this.setIndex(g),
      this.setAttribute('position', new ee(f, 3)),
      this.setAttribute('normal', new ee(u, 3)),
      this.setAttribute('uv', new ee(p, 2)));
    function M() {
      for (let y = 0; y < e; y++) m(y);
      (m(r === !1 ? e : 0), E(), d());
    }
    function m(y) {
      h = t.getPointAt(y / e, h);
      const S = a.normals[y],
        R = a.binormals[y];
      for (let w = 0; w <= s; w++) {
        const P = (w / s) * Math.PI * 2,
          x = Math.sin(P),
          b = -Math.cos(P);
        ((l.x = b * S.x + x * R.x),
          (l.y = b * S.y + x * R.y),
          (l.z = b * S.z + x * R.z),
          l.normalize(),
          u.push(l.x, l.y, l.z),
          (o.x = h.x + n * l.x),
          (o.y = h.y + n * l.y),
          (o.z = h.z + n * l.z),
          f.push(o.x, o.y, o.z));
      }
    }
    function d() {
      for (let y = 1; y <= e; y++)
        for (let S = 1; S <= s; S++) {
          const R = (s + 1) * (y - 1) + (S - 1),
            w = (s + 1) * y + (S - 1),
            P = (s + 1) * y + S,
            x = (s + 1) * (y - 1) + S;
          (g.push(R, w, x), g.push(w, P, x));
        }
    }
    function E() {
      for (let y = 0; y <= e; y++)
        for (let S = 0; S <= s; S++) ((c.x = y / e), (c.y = S / s), p.push(c.x, c.y));
    }
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.path = this.parameters.path.toJSON()), t);
  }
  static fromJSON(t) {
    return new lc(
      new Ys[t.path.type]().fromJSON(t.path),
      t.tubularSegments,
      t.radius,
      t.radialSegments,
      t.closed
    );
  }
}
class A0 extends xe {
  constructor(t = null) {
    if (
      (super(), (this.type = 'WireframeGeometry'), (this.parameters = { geometry: t }), t !== null)
    ) {
      const e = [],
        n = new Set(),
        s = new L(),
        r = new L();
      if (t.index !== null) {
        const a = t.attributes.position,
          o = t.index;
        let l = t.groups;
        l.length === 0 && (l = [{ start: 0, count: o.count, materialIndex: 0 }]);
        for (let c = 0, h = l.length; c < h; ++c) {
          const f = l[c],
            u = f.start,
            p = f.count;
          for (let g = u, M = u + p; g < M; g += 3)
            for (let m = 0; m < 3; m++) {
              const d = o.getX(g + m),
                E = o.getX(g + ((m + 1) % 3));
              (s.fromBufferAttribute(a, d),
                r.fromBufferAttribute(a, E),
                ko(s, r, n) === !0 && (e.push(s.x, s.y, s.z), e.push(r.x, r.y, r.z)));
            }
        }
      } else {
        const a = t.attributes.position;
        for (let o = 0, l = a.count / 3; o < l; o++)
          for (let c = 0; c < 3; c++) {
            const h = 3 * o + c,
              f = 3 * o + ((c + 1) % 3);
            (s.fromBufferAttribute(a, h),
              r.fromBufferAttribute(a, f),
              ko(s, r, n) === !0 && (e.push(s.x, s.y, s.z), e.push(r.x, r.y, r.z)));
          }
      }
      this.setAttribute('position', new ee(e, 3));
    }
  }
  copy(t) {
    return (super.copy(t), (this.parameters = Object.assign({}, t.parameters)), this);
  }
}
function ko(i, t, e) {
  const n = `${i.x},${i.y},${i.z}-${t.x},${t.y},${t.z}`,
    s = `${t.x},${t.y},${t.z}-${i.x},${i.y},${i.z}`;
  return e.has(n) === !0 || e.has(s) === !0 ? !1 : (e.add(n), e.add(s), !0);
}
class w0 extends Le {
  constructor(t) {
    (super(),
      (this.isShadowMaterial = !0),
      (this.type = 'ShadowMaterial'),
      (this.color = new zt(0)),
      (this.transparent = !0),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (super.copy(t), this.color.copy(t.color), (this.fog = t.fog), this);
  }
}
function wi(i) {
  const t = {};
  for (const e in i) {
    t[e] = {};
    for (const n in i[e]) {
      const s = i[e][n];
      s &&
      (s.isColor ||
        s.isMatrix3 ||
        s.isMatrix4 ||
        s.isVector2 ||
        s.isVector3 ||
        s.isVector4 ||
        s.isTexture ||
        s.isQuaternion)
        ? s.isRenderTargetTexture
          ? (Ft(
              'UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms().'
            ),
            (t[e][n] = null))
          : (t[e][n] = s.clone())
        : Array.isArray(s)
          ? (t[e][n] = s.slice())
          : (t[e][n] = s);
    }
  }
  return t;
}
function Re(i) {
  const t = {};
  for (let e = 0; e < i.length; e++) {
    const n = wi(i[e]);
    for (const s in n) t[s] = n[s];
  }
  return t;
}
function Ru(i) {
  const t = [];
  for (let e = 0; e < i.length; e++) t.push(i[e].clone());
  return t;
}
function cc(i) {
  const t = i.getRenderTarget();
  return t === null
    ? i.outputColorSpace
    : t.isXRRenderTarget === !0
      ? t.texture.colorSpace
      : $t.workingColorSpace;
}
const Cu = { clone: wi, merge: Re };
var Pu = `void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,
  Lu = `void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;
class on extends Le {
  constructor(t) {
    (super(),
      (this.isShaderMaterial = !0),
      (this.type = 'ShaderMaterial'),
      (this.defines = {}),
      (this.uniforms = {}),
      (this.uniformsGroups = []),
      (this.vertexShader = Pu),
      (this.fragmentShader = Lu),
      (this.linewidth = 1),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.fog = !1),
      (this.lights = !1),
      (this.clipping = !1),
      (this.forceSinglePass = !0),
      (this.extensions = { clipCullDistance: !1, multiDraw: !1 }),
      (this.defaultAttributeValues = { color: [1, 1, 1], uv: [0, 0], uv1: [0, 0] }),
      (this.index0AttributeName = void 0),
      (this.uniformsNeedUpdate = !1),
      (this.glslVersion = null),
      t !== void 0 && this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.fragmentShader = t.fragmentShader),
      (this.vertexShader = t.vertexShader),
      (this.uniforms = wi(t.uniforms)),
      (this.uniformsGroups = Ru(t.uniformsGroups)),
      (this.defines = Object.assign({}, t.defines)),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.fog = t.fog),
      (this.lights = t.lights),
      (this.clipping = t.clipping),
      (this.extensions = Object.assign({}, t.extensions)),
      (this.glslVersion = t.glslVersion),
      (this.defaultAttributeValues = Object.assign({}, t.defaultAttributeValues)),
      (this.index0AttributeName = t.index0AttributeName),
      (this.uniformsNeedUpdate = t.uniformsNeedUpdate),
      this
    );
  }
  toJSON(t) {
    const e = super.toJSON(t);
    ((e.glslVersion = this.glslVersion), (e.uniforms = {}));
    for (const s in this.uniforms) {
      const a = this.uniforms[s].value;
      a && a.isTexture
        ? (e.uniforms[s] = { type: 't', value: a.toJSON(t).uuid })
        : a && a.isColor
          ? (e.uniforms[s] = { type: 'c', value: a.getHex() })
          : a && a.isVector2
            ? (e.uniforms[s] = { type: 'v2', value: a.toArray() })
            : a && a.isVector3
              ? (e.uniforms[s] = { type: 'v3', value: a.toArray() })
              : a && a.isVector4
                ? (e.uniforms[s] = { type: 'v4', value: a.toArray() })
                : a && a.isMatrix3
                  ? (e.uniforms[s] = { type: 'm3', value: a.toArray() })
                  : a && a.isMatrix4
                    ? (e.uniforms[s] = { type: 'm4', value: a.toArray() })
                    : (e.uniforms[s] = { value: a });
    }
    (Object.keys(this.defines).length > 0 && (e.defines = this.defines),
      (e.vertexShader = this.vertexShader),
      (e.fragmentShader = this.fragmentShader),
      (e.lights = this.lights),
      (e.clipping = this.clipping));
    const n = {};
    for (const s in this.extensions) this.extensions[s] === !0 && (n[s] = !0);
    return (Object.keys(n).length > 0 && (e.extensions = n), e);
  }
}
class Du extends on {
  constructor(t) {
    (super(t), (this.isRawShaderMaterial = !0), (this.type = 'RawShaderMaterial'));
  }
}
class Iu extends Le {
  constructor(t) {
    (super(),
      (this.isMeshStandardMaterial = !0),
      (this.type = 'MeshStandardMaterial'),
      (this.defines = { STANDARD: '' }),
      (this.color = new zt(16777215)),
      (this.roughness = 1),
      (this.metalness = 0),
      (this.map = null),
      (this.lightMap = null),
      (this.lightMapIntensity = 1),
      (this.aoMap = null),
      (this.aoMapIntensity = 1),
      (this.emissive = new zt(0)),
      (this.emissiveIntensity = 1),
      (this.emissiveMap = null),
      (this.bumpMap = null),
      (this.bumpScale = 1),
      (this.normalMap = null),
      (this.normalMapType = Kn),
      (this.normalScale = new ct(1, 1)),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.roughnessMap = null),
      (this.metalnessMap = null),
      (this.alphaMap = null),
      (this.envMap = null),
      (this.envMapRotation = new Ge()),
      (this.envMapIntensity = 1),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.wireframeLinecap = 'round'),
      (this.wireframeLinejoin = 'round'),
      (this.flatShading = !1),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.defines = { STANDARD: '' }),
      this.color.copy(t.color),
      (this.roughness = t.roughness),
      (this.metalness = t.metalness),
      (this.map = t.map),
      (this.lightMap = t.lightMap),
      (this.lightMapIntensity = t.lightMapIntensity),
      (this.aoMap = t.aoMap),
      (this.aoMapIntensity = t.aoMapIntensity),
      this.emissive.copy(t.emissive),
      (this.emissiveMap = t.emissiveMap),
      (this.emissiveIntensity = t.emissiveIntensity),
      (this.bumpMap = t.bumpMap),
      (this.bumpScale = t.bumpScale),
      (this.normalMap = t.normalMap),
      (this.normalMapType = t.normalMapType),
      this.normalScale.copy(t.normalScale),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.roughnessMap = t.roughnessMap),
      (this.metalnessMap = t.metalnessMap),
      (this.alphaMap = t.alphaMap),
      (this.envMap = t.envMap),
      this.envMapRotation.copy(t.envMapRotation),
      (this.envMapIntensity = t.envMapIntensity),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.wireframeLinecap = t.wireframeLinecap),
      (this.wireframeLinejoin = t.wireframeLinejoin),
      (this.flatShading = t.flatShading),
      (this.fog = t.fog),
      this
    );
  }
}
class R0 extends Iu {
  constructor(t) {
    (super(),
      (this.isMeshPhysicalMaterial = !0),
      (this.defines = { STANDARD: '', PHYSICAL: '' }),
      (this.type = 'MeshPhysicalMaterial'),
      (this.anisotropyRotation = 0),
      (this.anisotropyMap = null),
      (this.clearcoatMap = null),
      (this.clearcoatRoughness = 0),
      (this.clearcoatRoughnessMap = null),
      (this.clearcoatNormalScale = new ct(1, 1)),
      (this.clearcoatNormalMap = null),
      (this.ior = 1.5),
      Object.defineProperty(this, 'reflectivity', {
        get: function () {
          return Bt((2.5 * (this.ior - 1)) / (this.ior + 1), 0, 1);
        },
        set: function (e) {
          this.ior = (1 + 0.4 * e) / (1 - 0.4 * e);
        },
      }),
      (this.iridescenceMap = null),
      (this.iridescenceIOR = 1.3),
      (this.iridescenceThicknessRange = [100, 400]),
      (this.iridescenceThicknessMap = null),
      (this.sheenColor = new zt(0)),
      (this.sheenColorMap = null),
      (this.sheenRoughness = 1),
      (this.sheenRoughnessMap = null),
      (this.transmissionMap = null),
      (this.thickness = 0),
      (this.thicknessMap = null),
      (this.attenuationDistance = 1 / 0),
      (this.attenuationColor = new zt(1, 1, 1)),
      (this.specularIntensity = 1),
      (this.specularIntensityMap = null),
      (this.specularColor = new zt(1, 1, 1)),
      (this.specularColorMap = null),
      (this._anisotropy = 0),
      (this._clearcoat = 0),
      (this._dispersion = 0),
      (this._iridescence = 0),
      (this._sheen = 0),
      (this._transmission = 0),
      this.setValues(t));
  }
  get anisotropy() {
    return this._anisotropy;
  }
  set anisotropy(t) {
    (this._anisotropy > 0 != t > 0 && this.version++, (this._anisotropy = t));
  }
  get clearcoat() {
    return this._clearcoat;
  }
  set clearcoat(t) {
    (this._clearcoat > 0 != t > 0 && this.version++, (this._clearcoat = t));
  }
  get iridescence() {
    return this._iridescence;
  }
  set iridescence(t) {
    (this._iridescence > 0 != t > 0 && this.version++, (this._iridescence = t));
  }
  get dispersion() {
    return this._dispersion;
  }
  set dispersion(t) {
    (this._dispersion > 0 != t > 0 && this.version++, (this._dispersion = t));
  }
  get sheen() {
    return this._sheen;
  }
  set sheen(t) {
    (this._sheen > 0 != t > 0 && this.version++, (this._sheen = t));
  }
  get transmission() {
    return this._transmission;
  }
  set transmission(t) {
    (this._transmission > 0 != t > 0 && this.version++, (this._transmission = t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.defines = { STANDARD: '', PHYSICAL: '' }),
      (this.anisotropy = t.anisotropy),
      (this.anisotropyRotation = t.anisotropyRotation),
      (this.anisotropyMap = t.anisotropyMap),
      (this.clearcoat = t.clearcoat),
      (this.clearcoatMap = t.clearcoatMap),
      (this.clearcoatRoughness = t.clearcoatRoughness),
      (this.clearcoatRoughnessMap = t.clearcoatRoughnessMap),
      (this.clearcoatNormalMap = t.clearcoatNormalMap),
      this.clearcoatNormalScale.copy(t.clearcoatNormalScale),
      (this.dispersion = t.dispersion),
      (this.ior = t.ior),
      (this.iridescence = t.iridescence),
      (this.iridescenceMap = t.iridescenceMap),
      (this.iridescenceIOR = t.iridescenceIOR),
      (this.iridescenceThicknessRange = [...t.iridescenceThicknessRange]),
      (this.iridescenceThicknessMap = t.iridescenceThicknessMap),
      (this.sheen = t.sheen),
      this.sheenColor.copy(t.sheenColor),
      (this.sheenColorMap = t.sheenColorMap),
      (this.sheenRoughness = t.sheenRoughness),
      (this.sheenRoughnessMap = t.sheenRoughnessMap),
      (this.transmission = t.transmission),
      (this.transmissionMap = t.transmissionMap),
      (this.thickness = t.thickness),
      (this.thicknessMap = t.thicknessMap),
      (this.attenuationDistance = t.attenuationDistance),
      this.attenuationColor.copy(t.attenuationColor),
      (this.specularIntensity = t.specularIntensity),
      (this.specularIntensityMap = t.specularIntensityMap),
      this.specularColor.copy(t.specularColor),
      (this.specularColorMap = t.specularColorMap),
      this
    );
  }
}
class C0 extends Le {
  constructor(t) {
    (super(),
      (this.isMeshPhongMaterial = !0),
      (this.type = 'MeshPhongMaterial'),
      (this.color = new zt(16777215)),
      (this.specular = new zt(1118481)),
      (this.shininess = 30),
      (this.map = null),
      (this.lightMap = null),
      (this.lightMapIntensity = 1),
      (this.aoMap = null),
      (this.aoMapIntensity = 1),
      (this.emissive = new zt(0)),
      (this.emissiveIntensity = 1),
      (this.emissiveMap = null),
      (this.bumpMap = null),
      (this.bumpScale = 1),
      (this.normalMap = null),
      (this.normalMapType = Kn),
      (this.normalScale = new ct(1, 1)),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.specularMap = null),
      (this.alphaMap = null),
      (this.envMap = null),
      (this.envMapRotation = new Ge()),
      (this.combine = Zs),
      (this.reflectivity = 1),
      (this.envMapIntensity = 1),
      (this.refractionRatio = 0.98),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.wireframeLinecap = 'round'),
      (this.wireframeLinejoin = 'round'),
      (this.flatShading = !1),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      this.specular.copy(t.specular),
      (this.shininess = t.shininess),
      (this.map = t.map),
      (this.lightMap = t.lightMap),
      (this.lightMapIntensity = t.lightMapIntensity),
      (this.aoMap = t.aoMap),
      (this.aoMapIntensity = t.aoMapIntensity),
      this.emissive.copy(t.emissive),
      (this.emissiveMap = t.emissiveMap),
      (this.emissiveIntensity = t.emissiveIntensity),
      (this.bumpMap = t.bumpMap),
      (this.bumpScale = t.bumpScale),
      (this.normalMap = t.normalMap),
      (this.normalMapType = t.normalMapType),
      this.normalScale.copy(t.normalScale),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.specularMap = t.specularMap),
      (this.alphaMap = t.alphaMap),
      (this.envMap = t.envMap),
      this.envMapRotation.copy(t.envMapRotation),
      (this.combine = t.combine),
      (this.reflectivity = t.reflectivity),
      (this.envMapIntensity = t.envMapIntensity),
      (this.refractionRatio = t.refractionRatio),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.wireframeLinecap = t.wireframeLinecap),
      (this.wireframeLinejoin = t.wireframeLinejoin),
      (this.flatShading = t.flatShading),
      (this.fog = t.fog),
      this
    );
  }
}
class P0 extends Le {
  constructor(t) {
    (super(),
      (this.isMeshToonMaterial = !0),
      (this.defines = { TOON: '' }),
      (this.type = 'MeshToonMaterial'),
      (this.color = new zt(16777215)),
      (this.map = null),
      (this.gradientMap = null),
      (this.lightMap = null),
      (this.lightMapIntensity = 1),
      (this.aoMap = null),
      (this.aoMapIntensity = 1),
      (this.emissive = new zt(0)),
      (this.emissiveIntensity = 1),
      (this.emissiveMap = null),
      (this.bumpMap = null),
      (this.bumpScale = 1),
      (this.normalMap = null),
      (this.normalMapType = Kn),
      (this.normalScale = new ct(1, 1)),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.alphaMap = null),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.wireframeLinecap = 'round'),
      (this.wireframeLinejoin = 'round'),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      (this.map = t.map),
      (this.gradientMap = t.gradientMap),
      (this.lightMap = t.lightMap),
      (this.lightMapIntensity = t.lightMapIntensity),
      (this.aoMap = t.aoMap),
      (this.aoMapIntensity = t.aoMapIntensity),
      this.emissive.copy(t.emissive),
      (this.emissiveMap = t.emissiveMap),
      (this.emissiveIntensity = t.emissiveIntensity),
      (this.bumpMap = t.bumpMap),
      (this.bumpScale = t.bumpScale),
      (this.normalMap = t.normalMap),
      (this.normalMapType = t.normalMapType),
      this.normalScale.copy(t.normalScale),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.alphaMap = t.alphaMap),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.wireframeLinecap = t.wireframeLinecap),
      (this.wireframeLinejoin = t.wireframeLinejoin),
      (this.fog = t.fog),
      this
    );
  }
}
class L0 extends Le {
  constructor(t) {
    (super(),
      (this.isMeshNormalMaterial = !0),
      (this.type = 'MeshNormalMaterial'),
      (this.bumpMap = null),
      (this.bumpScale = 1),
      (this.normalMap = null),
      (this.normalMapType = Kn),
      (this.normalScale = new ct(1, 1)),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.flatShading = !1),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.bumpMap = t.bumpMap),
      (this.bumpScale = t.bumpScale),
      (this.normalMap = t.normalMap),
      (this.normalMapType = t.normalMapType),
      this.normalScale.copy(t.normalScale),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.flatShading = t.flatShading),
      this
    );
  }
}
class D0 extends Le {
  constructor(t) {
    (super(),
      (this.isMeshLambertMaterial = !0),
      (this.type = 'MeshLambertMaterial'),
      (this.color = new zt(16777215)),
      (this.map = null),
      (this.lightMap = null),
      (this.lightMapIntensity = 1),
      (this.aoMap = null),
      (this.aoMapIntensity = 1),
      (this.emissive = new zt(0)),
      (this.emissiveIntensity = 1),
      (this.emissiveMap = null),
      (this.bumpMap = null),
      (this.bumpScale = 1),
      (this.normalMap = null),
      (this.normalMapType = Kn),
      (this.normalScale = new ct(1, 1)),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.specularMap = null),
      (this.alphaMap = null),
      (this.envMap = null),
      (this.envMapRotation = new Ge()),
      (this.combine = Zs),
      (this.reflectivity = 1),
      (this.envMapIntensity = 1),
      (this.refractionRatio = 0.98),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.wireframeLinecap = 'round'),
      (this.wireframeLinejoin = 'round'),
      (this.flatShading = !1),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      this.color.copy(t.color),
      (this.map = t.map),
      (this.lightMap = t.lightMap),
      (this.lightMapIntensity = t.lightMapIntensity),
      (this.aoMap = t.aoMap),
      (this.aoMapIntensity = t.aoMapIntensity),
      this.emissive.copy(t.emissive),
      (this.emissiveMap = t.emissiveMap),
      (this.emissiveIntensity = t.emissiveIntensity),
      (this.bumpMap = t.bumpMap),
      (this.bumpScale = t.bumpScale),
      (this.normalMap = t.normalMap),
      (this.normalMapType = t.normalMapType),
      this.normalScale.copy(t.normalScale),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.specularMap = t.specularMap),
      (this.alphaMap = t.alphaMap),
      (this.envMap = t.envMap),
      this.envMapRotation.copy(t.envMapRotation),
      (this.combine = t.combine),
      (this.reflectivity = t.reflectivity),
      (this.envMapIntensity = t.envMapIntensity),
      (this.refractionRatio = t.refractionRatio),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.wireframeLinecap = t.wireframeLinecap),
      (this.wireframeLinejoin = t.wireframeLinejoin),
      (this.flatShading = t.flatShading),
      (this.fog = t.fog),
      this
    );
  }
}
class Uu extends Le {
  constructor(t) {
    (super(),
      (this.isMeshDepthMaterial = !0),
      (this.type = 'MeshDepthMaterial'),
      (this.depthPacking = Jc),
      (this.map = null),
      (this.alphaMap = null),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.depthPacking = t.depthPacking),
      (this.map = t.map),
      (this.alphaMap = t.alphaMap),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      this
    );
  }
}
class Nu extends Le {
  constructor(t) {
    (super(),
      (this.isMeshDistanceMaterial = !0),
      (this.type = 'MeshDistanceMaterial'),
      (this.map = null),
      (this.alphaMap = null),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.map = t.map),
      (this.alphaMap = t.alphaMap),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      this
    );
  }
}
class I0 extends Le {
  constructor(t) {
    (super(),
      (this.isMeshMatcapMaterial = !0),
      (this.defines = { MATCAP: '' }),
      (this.type = 'MeshMatcapMaterial'),
      (this.color = new zt(16777215)),
      (this.matcap = null),
      (this.map = null),
      (this.bumpMap = null),
      (this.bumpScale = 1),
      (this.normalMap = null),
      (this.normalMapType = Kn),
      (this.normalScale = new ct(1, 1)),
      (this.displacementMap = null),
      (this.displacementScale = 1),
      (this.displacementBias = 0),
      (this.alphaMap = null),
      (this.wireframe = !1),
      (this.wireframeLinewidth = 1),
      (this.flatShading = !1),
      (this.fog = !0),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.defines = { MATCAP: '' }),
      this.color.copy(t.color),
      (this.matcap = t.matcap),
      (this.map = t.map),
      (this.bumpMap = t.bumpMap),
      (this.bumpScale = t.bumpScale),
      (this.normalMap = t.normalMap),
      (this.normalMapType = t.normalMapType),
      this.normalScale.copy(t.normalScale),
      (this.displacementMap = t.displacementMap),
      (this.displacementScale = t.displacementScale),
      (this.displacementBias = t.displacementBias),
      (this.alphaMap = t.alphaMap),
      (this.wireframe = t.wireframe),
      (this.wireframeLinewidth = t.wireframeLinewidth),
      (this.flatShading = t.flatShading),
      (this.fog = t.fog),
      this
    );
  }
}
class U0 extends Xl {
  constructor(t) {
    (super(),
      (this.isLineDashedMaterial = !0),
      (this.type = 'LineDashedMaterial'),
      (this.scale = 1),
      (this.dashSize = 3),
      (this.gapSize = 1),
      this.setValues(t));
  }
  copy(t) {
    return (
      super.copy(t),
      (this.scale = t.scale),
      (this.dashSize = t.dashSize),
      (this.gapSize = t.gapSize),
      this
    );
  }
}
const Dr = {
  enabled: !1,
  files: {},
  add: function (i, t) {
    this.enabled !== !1 && (Wo(i) || (this.files[i] = t));
  },
  get: function (i) {
    if (this.enabled !== !1 && !Wo(i)) return this.files[i];
  },
  remove: function (i) {
    delete this.files[i];
  },
  clear: function () {
    this.files = {};
  },
};
function Wo(i) {
  try {
    const t = i.slice(i.indexOf(':') + 1);
    return new URL(t).protocol === 'blob:';
  } catch {
    return !1;
  }
}
class Fu {
  constructor(t, e, n) {
    const s = this;
    let r = !1,
      a = 0,
      o = 0,
      l;
    const c = [];
    ((this.onStart = void 0),
      (this.onLoad = t),
      (this.onProgress = e),
      (this.onError = n),
      (this._abortController = null),
      (this.itemStart = function (h) {
        (o++, r === !1 && s.onStart !== void 0 && s.onStart(h, a, o), (r = !0));
      }),
      (this.itemEnd = function (h) {
        (a++,
          s.onProgress !== void 0 && s.onProgress(h, a, o),
          a === o && ((r = !1), s.onLoad !== void 0 && s.onLoad()));
      }),
      (this.itemError = function (h) {
        s.onError !== void 0 && s.onError(h);
      }),
      (this.resolveURL = function (h) {
        return l ? l(h) : h;
      }),
      (this.setURLModifier = function (h) {
        return ((l = h), this);
      }),
      (this.addHandler = function (h, f) {
        return (c.push(h, f), this);
      }),
      (this.removeHandler = function (h) {
        const f = c.indexOf(h);
        return (f !== -1 && c.splice(f, 2), this);
      }),
      (this.getHandler = function (h) {
        for (let f = 0, u = c.length; f < u; f += 2) {
          const p = c[f],
            g = c[f + 1];
          if ((p.global && (p.lastIndex = 0), p.test(h))) return g;
        }
        return null;
      }),
      (this.abort = function () {
        return (this.abortController.abort(), (this._abortController = null), this);
      }));
  }
  get abortController() {
    return (
      this._abortController || (this._abortController = new AbortController()),
      this._abortController
    );
  }
}
const Ou = new Fu();
class ja {
  constructor(t) {
    ((this.manager = t !== void 0 ? t : Ou),
      (this.crossOrigin = 'anonymous'),
      (this.withCredentials = !1),
      (this.path = ''),
      (this.resourcePath = ''),
      (this.requestHeader = {}),
      typeof __THREE_DEVTOOLS__ < 'u' &&
        __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent('observe', { detail: this })));
  }
  load() {}
  loadAsync(t, e) {
    const n = this;
    return new Promise(function (s, r) {
      n.load(t, s, e, r);
    });
  }
  parse() {}
  setCrossOrigin(t) {
    return ((this.crossOrigin = t), this);
  }
  setWithCredentials(t) {
    return ((this.withCredentials = t), this);
  }
  setPath(t) {
    return ((this.path = t), this);
  }
  setResourcePath(t) {
    return ((this.resourcePath = t), this);
  }
  setRequestHeader(t) {
    return ((this.requestHeader = t), this);
  }
  abort() {
    return this;
  }
}
ja.DEFAULT_MATERIAL_NAME = '__DEFAULT';
const di = new WeakMap();
class Bu extends ja {
  constructor(t) {
    super(t);
  }
  load(t, e, n, s) {
    (this.path !== void 0 && (t = this.path + t), (t = this.manager.resolveURL(t)));
    const r = this,
      a = Dr.get(`image:${t}`);
    if (a !== void 0) {
      if (a.complete === !0)
        (r.manager.itemStart(t),
          setTimeout(function () {
            (e && e(a), r.manager.itemEnd(t));
          }, 0));
      else {
        let f = di.get(a);
        (f === void 0 && ((f = []), di.set(a, f)), f.push({ onLoad: e, onError: s }));
      }
      return a;
    }
    const o = Yi('img');
    function l() {
      (h(), e && e(this));
      const f = di.get(this) || [];
      for (let u = 0; u < f.length; u++) {
        const p = f[u];
        p.onLoad && p.onLoad(this);
      }
      (di.delete(this), r.manager.itemEnd(t));
    }
    function c(f) {
      (h(), s && s(f), Dr.remove(`image:${t}`));
      const u = di.get(this) || [];
      for (let p = 0; p < u.length; p++) {
        const g = u[p];
        g.onError && g.onError(f);
      }
      (di.delete(this), r.manager.itemError(t), r.manager.itemEnd(t));
    }
    function h() {
      (o.removeEventListener('load', l, !1), o.removeEventListener('error', c, !1));
    }
    return (
      o.addEventListener('load', l, !1),
      o.addEventListener('error', c, !1),
      t.slice(0, 5) !== 'data:' &&
        this.crossOrigin !== void 0 &&
        (o.crossOrigin = this.crossOrigin),
      Dr.add(`image:${t}`, o),
      r.manager.itemStart(t),
      (o.src = t),
      o
    );
  }
}
class N0 extends ja {
  constructor(t) {
    super(t);
  }
  load(t, e, n, s) {
    const r = new ye(),
      a = new Bu(this.manager);
    return (
      a.setCrossOrigin(this.crossOrigin),
      a.setPath(this.path),
      a.load(
        t,
        function (o) {
          ((r.image = o), (r.needsUpdate = !0), e !== void 0 && e(r));
        },
        n,
        s
      ),
      r
    );
  }
}
class Qn extends de {
  constructor(t, e = 1) {
    (super(),
      (this.isLight = !0),
      (this.type = 'Light'),
      (this.color = new zt(t)),
      (this.intensity = e));
  }
  dispose() {
    this.dispatchEvent({ type: 'dispose' });
  }
  copy(t, e) {
    return (super.copy(t, e), this.color.copy(t.color), (this.intensity = t.intensity), this);
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return ((e.object.color = this.color.getHex()), (e.object.intensity = this.intensity), e);
  }
}
class F0 extends Qn {
  constructor(t, e, n) {
    (super(t, n),
      (this.isHemisphereLight = !0),
      (this.type = 'HemisphereLight'),
      this.position.copy(de.DEFAULT_UP),
      this.updateMatrix(),
      (this.groundColor = new zt(e)));
  }
  copy(t, e) {
    return (super.copy(t, e), this.groundColor.copy(t.groundColor), this);
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return ((e.object.groundColor = this.groundColor.getHex()), e);
  }
}
const Ir = new oe(),
  Xo = new L(),
  qo = new L();
class Qa {
  constructor(t) {
    ((this.camera = t),
      (this.intensity = 1),
      (this.bias = 0),
      (this.biasNode = null),
      (this.normalBias = 0),
      (this.radius = 1),
      (this.blurSamples = 8),
      (this.mapSize = new ct(512, 512)),
      (this.mapType = Oe),
      (this.map = null),
      (this.mapPass = null),
      (this.matrix = new oe()),
      (this.autoUpdate = !0),
      (this.needsUpdate = !1),
      (this._frustum = new Ks()),
      (this._frameExtents = new ct(1, 1)),
      (this._viewportCount = 1),
      (this._viewports = [new ue(0, 0, 1, 1)]));
  }
  getViewportCount() {
    return this._viewportCount;
  }
  getFrustum() {
    return this._frustum;
  }
  updateMatrices(t) {
    const e = this.camera,
      n = this.matrix;
    (Xo.setFromMatrixPosition(t.matrixWorld),
      e.position.copy(Xo),
      qo.setFromMatrixPosition(t.target.matrixWorld),
      e.lookAt(qo),
      e.updateMatrixWorld(),
      Ir.multiplyMatrices(e.projectionMatrix, e.matrixWorldInverse),
      this._frustum.setFromProjectionMatrix(Ir, e.coordinateSystem, e.reversedDepth),
      e.coordinateSystem === qi || e.reversedDepth
        ? n.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 1, 0, 0, 0, 0, 1)
        : n.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1),
      n.multiply(Ir));
  }
  getViewport(t) {
    return this._viewports[t];
  }
  getFrameExtents() {
    return this._frameExtents;
  }
  dispose() {
    (this.map && this.map.dispose(), this.mapPass && this.mapPass.dispose());
  }
  copy(t) {
    return (
      (this.camera = t.camera.clone()),
      (this.intensity = t.intensity),
      (this.bias = t.bias),
      (this.radius = t.radius),
      (this.autoUpdate = t.autoUpdate),
      (this.needsUpdate = t.needsUpdate),
      (this.normalBias = t.normalBias),
      (this.blurSamples = t.blurSamples),
      this.mapSize.copy(t.mapSize),
      (this.biasNode = t.biasNode),
      this
    );
  }
  clone() {
    return new this.constructor().copy(this);
  }
  toJSON() {
    const t = {};
    return (
      this.intensity !== 1 && (t.intensity = this.intensity),
      this.bias !== 0 && (t.bias = this.bias),
      this.normalBias !== 0 && (t.normalBias = this.normalBias),
      this.radius !== 1 && (t.radius = this.radius),
      (this.mapSize.x !== 512 || this.mapSize.y !== 512) && (t.mapSize = this.mapSize.toArray()),
      (t.camera = this.camera.toJSON(!1).object),
      delete t.camera.matrix,
      t
    );
  }
}
const Ps = new L(),
  Ls = new Ri(),
  je = new L();
class hc extends de {
  constructor() {
    (super(),
      (this.isCamera = !0),
      (this.type = 'Camera'),
      (this.matrixWorldInverse = new oe()),
      (this.projectionMatrix = new oe()),
      (this.projectionMatrixInverse = new oe()),
      (this.coordinateSystem = Ze),
      (this._reversedDepth = !1));
  }
  get reversedDepth() {
    return this._reversedDepth;
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      this.matrixWorldInverse.copy(t.matrixWorldInverse),
      this.projectionMatrix.copy(t.projectionMatrix),
      this.projectionMatrixInverse.copy(t.projectionMatrixInverse),
      (this.coordinateSystem = t.coordinateSystem),
      this
    );
  }
  getWorldDirection(t) {
    return super.getWorldDirection(t).negate();
  }
  updateMatrixWorld(t) {
    (super.updateMatrixWorld(t),
      this.matrixWorld.decompose(Ps, Ls, je),
      je.x === 1 && je.y === 1 && je.z === 1
        ? this.matrixWorldInverse.copy(this.matrixWorld).invert()
        : this.matrixWorldInverse.compose(Ps, Ls, je.set(1, 1, 1)).invert());
  }
  updateWorldMatrix(t, e) {
    (super.updateWorldMatrix(t, e),
      this.matrixWorld.decompose(Ps, Ls, je),
      je.x === 1 && je.y === 1 && je.z === 1
        ? this.matrixWorldInverse.copy(this.matrixWorld).invert()
        : this.matrixWorldInverse.compose(Ps, Ls, je.set(1, 1, 1)).invert());
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
const Ln = new L(),
  Yo = new ct(),
  Zo = new ct();
class Fe extends hc {
  constructor(t = 50, e = 1, n = 0.1, s = 2e3) {
    (super(),
      (this.isPerspectiveCamera = !0),
      (this.type = 'PerspectiveCamera'),
      (this.fov = t),
      (this.zoom = 1),
      (this.near = n),
      (this.far = s),
      (this.focus = 10),
      (this.aspect = e),
      (this.view = null),
      (this.filmGauge = 35),
      (this.filmOffset = 0),
      this.updateProjectionMatrix());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      (this.fov = t.fov),
      (this.zoom = t.zoom),
      (this.near = t.near),
      (this.far = t.far),
      (this.focus = t.focus),
      (this.aspect = t.aspect),
      (this.view = t.view === null ? null : Object.assign({}, t.view)),
      (this.filmGauge = t.filmGauge),
      (this.filmOffset = t.filmOffset),
      this
    );
  }
  setFocalLength(t) {
    const e = (0.5 * this.getFilmHeight()) / t;
    ((this.fov = Ti * 2 * Math.atan(e)), this.updateProjectionMatrix());
  }
  getFocalLength() {
    const t = Math.tan(Vi * 0.5 * this.fov);
    return (0.5 * this.getFilmHeight()) / t;
  }
  getEffectiveFOV() {
    return Ti * 2 * Math.atan(Math.tan(Vi * 0.5 * this.fov) / this.zoom);
  }
  getFilmWidth() {
    return this.filmGauge * Math.min(this.aspect, 1);
  }
  getFilmHeight() {
    return this.filmGauge / Math.max(this.aspect, 1);
  }
  getViewBounds(t, e, n) {
    (Ln.set(-1, -1, 0.5).applyMatrix4(this.projectionMatrixInverse),
      e.set(Ln.x, Ln.y).multiplyScalar(-t / Ln.z),
      Ln.set(1, 1, 0.5).applyMatrix4(this.projectionMatrixInverse),
      n.set(Ln.x, Ln.y).multiplyScalar(-t / Ln.z));
  }
  getViewSize(t, e) {
    return (this.getViewBounds(t, Yo, Zo), e.subVectors(Zo, Yo));
  }
  setViewOffset(t, e, n, s, r, a) {
    ((this.aspect = t / e),
      this.view === null &&
        (this.view = {
          enabled: !0,
          fullWidth: 1,
          fullHeight: 1,
          offsetX: 0,
          offsetY: 0,
          width: 1,
          height: 1,
        }),
      (this.view.enabled = !0),
      (this.view.fullWidth = t),
      (this.view.fullHeight = e),
      (this.view.offsetX = n),
      (this.view.offsetY = s),
      (this.view.width = r),
      (this.view.height = a),
      this.updateProjectionMatrix());
  }
  clearViewOffset() {
    (this.view !== null && (this.view.enabled = !1), this.updateProjectionMatrix());
  }
  updateProjectionMatrix() {
    const t = this.near;
    let e = (t * Math.tan(Vi * 0.5 * this.fov)) / this.zoom,
      n = 2 * e,
      s = this.aspect * n,
      r = -0.5 * s;
    const a = this.view;
    if (this.view !== null && this.view.enabled) {
      const l = a.fullWidth,
        c = a.fullHeight;
      ((r += (a.offsetX * s) / l),
        (e -= (a.offsetY * n) / c),
        (s *= a.width / l),
        (n *= a.height / c));
    }
    const o = this.filmOffset;
    (o !== 0 && (r += (t * o) / this.getFilmWidth()),
      this.projectionMatrix.makePerspective(
        r,
        r + s,
        e,
        e - n,
        t,
        this.far,
        this.coordinateSystem,
        this.reversedDepth
      ),
      this.projectionMatrixInverse.copy(this.projectionMatrix).invert());
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return (
      (e.object.fov = this.fov),
      (e.object.zoom = this.zoom),
      (e.object.near = this.near),
      (e.object.far = this.far),
      (e.object.focus = this.focus),
      (e.object.aspect = this.aspect),
      this.view !== null && (e.object.view = Object.assign({}, this.view)),
      (e.object.filmGauge = this.filmGauge),
      (e.object.filmOffset = this.filmOffset),
      e
    );
  }
}
class zu extends Qa {
  constructor() {
    (super(new Fe(50, 1, 0.5, 500)),
      (this.isSpotLightShadow = !0),
      (this.focus = 1),
      (this.aspect = 1));
  }
  updateMatrices(t) {
    const e = this.camera,
      n = Ti * 2 * t.angle * this.focus,
      s = (this.mapSize.width / this.mapSize.height) * this.aspect,
      r = t.distance || e.far;
    ((n !== e.fov || s !== e.aspect || r !== e.far) &&
      ((e.fov = n), (e.aspect = s), (e.far = r), e.updateProjectionMatrix()),
      super.updateMatrices(t));
  }
  copy(t) {
    return (super.copy(t), (this.focus = t.focus), this);
  }
}
class O0 extends Qn {
  constructor(t, e, n = 0, s = Math.PI / 3, r = 0, a = 2) {
    (super(t, e),
      (this.isSpotLight = !0),
      (this.type = 'SpotLight'),
      this.position.copy(de.DEFAULT_UP),
      this.updateMatrix(),
      (this.target = new de()),
      (this.distance = n),
      (this.angle = s),
      (this.penumbra = r),
      (this.decay = a),
      (this.map = null),
      (this.shadow = new zu()));
  }
  get power() {
    return this.intensity * Math.PI;
  }
  set power(t) {
    this.intensity = t / Math.PI;
  }
  dispose() {
    (super.dispose(), this.shadow.dispose());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      (this.distance = t.distance),
      (this.angle = t.angle),
      (this.penumbra = t.penumbra),
      (this.decay = t.decay),
      (this.target = t.target.clone()),
      (this.map = t.map),
      (this.shadow = t.shadow.clone()),
      this
    );
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return (
      (e.object.distance = this.distance),
      (e.object.angle = this.angle),
      (e.object.decay = this.decay),
      (e.object.penumbra = this.penumbra),
      (e.object.target = this.target.uuid),
      this.map && this.map.isTexture && (e.object.map = this.map.toJSON(t).uuid),
      (e.object.shadow = this.shadow.toJSON()),
      e
    );
  }
}
class Vu extends Qa {
  constructor() {
    (super(new Fe(90, 1, 0.5, 500)), (this.isPointLightShadow = !0));
  }
}
class B0 extends Qn {
  constructor(t, e, n = 0, s = 2) {
    (super(t, e),
      (this.isPointLight = !0),
      (this.type = 'PointLight'),
      (this.distance = n),
      (this.decay = s),
      (this.shadow = new Vu()));
  }
  get power() {
    return this.intensity * 4 * Math.PI;
  }
  set power(t) {
    this.intensity = t / (4 * Math.PI);
  }
  dispose() {
    (super.dispose(), this.shadow.dispose());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      (this.distance = t.distance),
      (this.decay = t.decay),
      (this.shadow = t.shadow.clone()),
      this
    );
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return (
      (e.object.distance = this.distance),
      (e.object.decay = this.decay),
      (e.object.shadow = this.shadow.toJSON()),
      e
    );
  }
}
class to extends hc {
  constructor(t = -1, e = 1, n = 1, s = -1, r = 0.1, a = 2e3) {
    (super(),
      (this.isOrthographicCamera = !0),
      (this.type = 'OrthographicCamera'),
      (this.zoom = 1),
      (this.view = null),
      (this.left = t),
      (this.right = e),
      (this.top = n),
      (this.bottom = s),
      (this.near = r),
      (this.far = a),
      this.updateProjectionMatrix());
  }
  copy(t, e) {
    return (
      super.copy(t, e),
      (this.left = t.left),
      (this.right = t.right),
      (this.top = t.top),
      (this.bottom = t.bottom),
      (this.near = t.near),
      (this.far = t.far),
      (this.zoom = t.zoom),
      (this.view = t.view === null ? null : Object.assign({}, t.view)),
      this
    );
  }
  setViewOffset(t, e, n, s, r, a) {
    (this.view === null &&
      (this.view = {
        enabled: !0,
        fullWidth: 1,
        fullHeight: 1,
        offsetX: 0,
        offsetY: 0,
        width: 1,
        height: 1,
      }),
      (this.view.enabled = !0),
      (this.view.fullWidth = t),
      (this.view.fullHeight = e),
      (this.view.offsetX = n),
      (this.view.offsetY = s),
      (this.view.width = r),
      (this.view.height = a),
      this.updateProjectionMatrix());
  }
  clearViewOffset() {
    (this.view !== null && (this.view.enabled = !1), this.updateProjectionMatrix());
  }
  updateProjectionMatrix() {
    const t = (this.right - this.left) / (2 * this.zoom),
      e = (this.top - this.bottom) / (2 * this.zoom),
      n = (this.right + this.left) / 2,
      s = (this.top + this.bottom) / 2;
    let r = n - t,
      a = n + t,
      o = s + e,
      l = s - e;
    if (this.view !== null && this.view.enabled) {
      const c = (this.right - this.left) / this.view.fullWidth / this.zoom,
        h = (this.top - this.bottom) / this.view.fullHeight / this.zoom;
      ((r += c * this.view.offsetX),
        (a = r + c * this.view.width),
        (o -= h * this.view.offsetY),
        (l = o - h * this.view.height));
    }
    (this.projectionMatrix.makeOrthographic(
      r,
      a,
      o,
      l,
      this.near,
      this.far,
      this.coordinateSystem,
      this.reversedDepth
    ),
      this.projectionMatrixInverse.copy(this.projectionMatrix).invert());
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return (
      (e.object.zoom = this.zoom),
      (e.object.left = this.left),
      (e.object.right = this.right),
      (e.object.top = this.top),
      (e.object.bottom = this.bottom),
      (e.object.near = this.near),
      (e.object.far = this.far),
      this.view !== null && (e.object.view = Object.assign({}, this.view)),
      e
    );
  }
}
class Gu extends Qa {
  constructor() {
    (super(new to(-5, 5, 5, -5, 0.5, 500)), (this.isDirectionalLightShadow = !0));
  }
}
class z0 extends Qn {
  constructor(t, e) {
    (super(t, e),
      (this.isDirectionalLight = !0),
      (this.type = 'DirectionalLight'),
      this.position.copy(de.DEFAULT_UP),
      this.updateMatrix(),
      (this.target = new de()),
      (this.shadow = new Gu()));
  }
  dispose() {
    (super.dispose(), this.shadow.dispose());
  }
  copy(t) {
    return (
      super.copy(t),
      (this.target = t.target.clone()),
      (this.shadow = t.shadow.clone()),
      this
    );
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return ((e.object.shadow = this.shadow.toJSON()), (e.object.target = this.target.uuid), e);
  }
}
class V0 extends Qn {
  constructor(t, e) {
    (super(t, e), (this.isAmbientLight = !0), (this.type = 'AmbientLight'));
  }
}
class G0 extends Qn {
  constructor(t, e, n = 10, s = 10) {
    (super(t, e),
      (this.isRectAreaLight = !0),
      (this.type = 'RectAreaLight'),
      (this.width = n),
      (this.height = s));
  }
  get power() {
    return this.intensity * this.width * this.height * Math.PI;
  }
  set power(t) {
    this.intensity = t / (this.width * this.height * Math.PI);
  }
  copy(t) {
    return (super.copy(t), (this.width = t.width), (this.height = t.height), this);
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return ((e.object.width = this.width), (e.object.height = this.height), e);
  }
}
class Hu {
  constructor() {
    ((this.isSphericalHarmonics3 = !0), (this.coefficients = []));
    for (let t = 0; t < 9; t++) this.coefficients.push(new L());
  }
  set(t) {
    for (let e = 0; e < 9; e++) this.coefficients[e].copy(t[e]);
    return this;
  }
  zero() {
    for (let t = 0; t < 9; t++) this.coefficients[t].set(0, 0, 0);
    return this;
  }
  getAt(t, e) {
    const n = t.x,
      s = t.y,
      r = t.z,
      a = this.coefficients;
    return (
      e.copy(a[0]).multiplyScalar(0.282095),
      e.addScaledVector(a[1], 0.488603 * s),
      e.addScaledVector(a[2], 0.488603 * r),
      e.addScaledVector(a[3], 0.488603 * n),
      e.addScaledVector(a[4], 1.092548 * (n * s)),
      e.addScaledVector(a[5], 1.092548 * (s * r)),
      e.addScaledVector(a[6], 0.315392 * (3 * r * r - 1)),
      e.addScaledVector(a[7], 1.092548 * (n * r)),
      e.addScaledVector(a[8], 0.546274 * (n * n - s * s)),
      e
    );
  }
  getIrradianceAt(t, e) {
    const n = t.x,
      s = t.y,
      r = t.z,
      a = this.coefficients;
    return (
      e.copy(a[0]).multiplyScalar(0.886227),
      e.addScaledVector(a[1], 2 * 0.511664 * s),
      e.addScaledVector(a[2], 2 * 0.511664 * r),
      e.addScaledVector(a[3], 2 * 0.511664 * n),
      e.addScaledVector(a[4], 2 * 0.429043 * n * s),
      e.addScaledVector(a[5], 2 * 0.429043 * s * r),
      e.addScaledVector(a[6], 0.743125 * r * r - 0.247708),
      e.addScaledVector(a[7], 2 * 0.429043 * n * r),
      e.addScaledVector(a[8], 0.429043 * (n * n - s * s)),
      e
    );
  }
  add(t) {
    for (let e = 0; e < 9; e++) this.coefficients[e].add(t.coefficients[e]);
    return this;
  }
  addScaledSH(t, e) {
    for (let n = 0; n < 9; n++) this.coefficients[n].addScaledVector(t.coefficients[n], e);
    return this;
  }
  scale(t) {
    for (let e = 0; e < 9; e++) this.coefficients[e].multiplyScalar(t);
    return this;
  }
  lerp(t, e) {
    for (let n = 0; n < 9; n++) this.coefficients[n].lerp(t.coefficients[n], e);
    return this;
  }
  equals(t) {
    for (let e = 0; e < 9; e++) if (!this.coefficients[e].equals(t.coefficients[e])) return !1;
    return !0;
  }
  copy(t) {
    return this.set(t.coefficients);
  }
  clone() {
    return new this.constructor().copy(this);
  }
  fromArray(t, e = 0) {
    const n = this.coefficients;
    for (let s = 0; s < 9; s++) n[s].fromArray(t, e + s * 3);
    return this;
  }
  toArray(t = [], e = 0) {
    const n = this.coefficients;
    for (let s = 0; s < 9; s++) n[s].toArray(t, e + s * 3);
    return t;
  }
  static getBasisAt(t, e) {
    const n = t.x,
      s = t.y,
      r = t.z;
    ((e[0] = 0.282095),
      (e[1] = 0.488603 * s),
      (e[2] = 0.488603 * r),
      (e[3] = 0.488603 * n),
      (e[4] = 1.092548 * n * s),
      (e[5] = 1.092548 * s * r),
      (e[6] = 0.315392 * (3 * r * r - 1)),
      (e[7] = 1.092548 * n * r),
      (e[8] = 0.546274 * (n * n - s * s)));
  }
}
class H0 extends Qn {
  constructor(t = new Hu(), e = 1) {
    (super(void 0, e), (this.isLightProbe = !0), (this.sh = t));
  }
  copy(t) {
    return (super.copy(t), this.sh.copy(t.sh), this);
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return ((e.object.sh = this.sh.toArray()), e);
  }
}
class k0 extends xe {
  constructor() {
    (super(),
      (this.isInstancedBufferGeometry = !0),
      (this.type = 'InstancedBufferGeometry'),
      (this.instanceCount = 1 / 0));
  }
  copy(t) {
    return (super.copy(t), (this.instanceCount = t.instanceCount), this);
  }
  toJSON() {
    const t = super.toJSON();
    return ((t.instanceCount = this.instanceCount), (t.isInstancedBufferGeometry = !0), t);
  }
}
const pi = -90,
  mi = 1;
class ku extends de {
  constructor(t, e, n) {
    (super(),
      (this.type = 'CubeCamera'),
      (this.renderTarget = n),
      (this.coordinateSystem = null),
      (this.activeMipmapLevel = 0));
    const s = new Fe(pi, mi, t, e);
    ((s.layers = this.layers), this.add(s));
    const r = new Fe(pi, mi, t, e);
    ((r.layers = this.layers), this.add(r));
    const a = new Fe(pi, mi, t, e);
    ((a.layers = this.layers), this.add(a));
    const o = new Fe(pi, mi, t, e);
    ((o.layers = this.layers), this.add(o));
    const l = new Fe(pi, mi, t, e);
    ((l.layers = this.layers), this.add(l));
    const c = new Fe(pi, mi, t, e);
    ((c.layers = this.layers), this.add(c));
  }
  updateCoordinateSystem() {
    const t = this.coordinateSystem,
      e = this.children.concat(),
      [n, s, r, a, o, l] = e;
    for (const c of e) this.remove(c);
    if (t === Ze)
      (n.up.set(0, 1, 0),
        n.lookAt(1, 0, 0),
        s.up.set(0, 1, 0),
        s.lookAt(-1, 0, 0),
        r.up.set(0, 0, -1),
        r.lookAt(0, 1, 0),
        a.up.set(0, 0, 1),
        a.lookAt(0, -1, 0),
        o.up.set(0, 1, 0),
        o.lookAt(0, 0, 1),
        l.up.set(0, 1, 0),
        l.lookAt(0, 0, -1));
    else if (t === qi)
      (n.up.set(0, -1, 0),
        n.lookAt(-1, 0, 0),
        s.up.set(0, -1, 0),
        s.lookAt(1, 0, 0),
        r.up.set(0, 0, 1),
        r.lookAt(0, 1, 0),
        a.up.set(0, 0, -1),
        a.lookAt(0, -1, 0),
        o.up.set(0, -1, 0),
        o.lookAt(0, 0, 1),
        l.up.set(0, -1, 0),
        l.lookAt(0, 0, -1));
    else
      throw new Error('THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: ' + t);
    for (const c of e) (this.add(c), c.updateMatrixWorld());
  }
  update(t, e) {
    this.parent === null && this.updateMatrixWorld();
    const { renderTarget: n, activeMipmapLevel: s } = this;
    this.coordinateSystem !== t.coordinateSystem &&
      ((this.coordinateSystem = t.coordinateSystem), this.updateCoordinateSystem());
    const [r, a, o, l, c, h] = this.children,
      f = t.getRenderTarget(),
      u = t.getActiveCubeFace(),
      p = t.getActiveMipmapLevel(),
      g = t.xr.enabled;
    t.xr.enabled = !1;
    const M = n.texture.generateMipmaps;
    n.texture.generateMipmaps = !1;
    let m = !1;
    (t.isWebGLRenderer === !0
      ? (m = t.state.buffers.depth.getReversed())
      : (m = t.reversedDepthBuffer),
      t.setRenderTarget(n, 0, s),
      m && t.autoClear === !1 && t.clearDepth(),
      t.render(e, r),
      t.setRenderTarget(n, 1, s),
      m && t.autoClear === !1 && t.clearDepth(),
      t.render(e, a),
      t.setRenderTarget(n, 2, s),
      m && t.autoClear === !1 && t.clearDepth(),
      t.render(e, o),
      t.setRenderTarget(n, 3, s),
      m && t.autoClear === !1 && t.clearDepth(),
      t.render(e, l),
      t.setRenderTarget(n, 4, s),
      m && t.autoClear === !1 && t.clearDepth(),
      t.render(e, c),
      (n.texture.generateMipmaps = M),
      t.setRenderTarget(n, 5, s),
      m && t.autoClear === !1 && t.clearDepth(),
      t.render(e, h),
      t.setRenderTarget(f, u, p),
      (t.xr.enabled = g),
      (n.texture.needsPMREMUpdate = !0));
  }
}
class Wu extends Fe {
  constructor(t = []) {
    (super(), (this.isArrayCamera = !0), (this.isMultiViewCamera = !1), (this.cameras = t));
  }
}
class W0 {
  constructor() {
    ((this._previousTime = 0),
      (this._currentTime = 0),
      (this._startTime = performance.now()),
      (this._delta = 0),
      (this._elapsed = 0),
      (this._timescale = 1),
      (this._document = null),
      (this._pageVisibilityHandler = null));
  }
  connect(t) {
    ((this._document = t),
      t.hidden !== void 0 &&
        ((this._pageVisibilityHandler = Xu.bind(this)),
        t.addEventListener('visibilitychange', this._pageVisibilityHandler, !1)));
  }
  disconnect() {
    (this._pageVisibilityHandler !== null &&
      (this._document.removeEventListener('visibilitychange', this._pageVisibilityHandler),
      (this._pageVisibilityHandler = null)),
      (this._document = null));
  }
  getDelta() {
    return this._delta / 1e3;
  }
  getElapsed() {
    return this._elapsed / 1e3;
  }
  getTimescale() {
    return this._timescale;
  }
  setTimescale(t) {
    return ((this._timescale = t), this);
  }
  reset() {
    return ((this._currentTime = performance.now() - this._startTime), this);
  }
  dispose() {
    this.disconnect();
  }
  update(t) {
    return (
      this._pageVisibilityHandler !== null && this._document.hidden === !0
        ? (this._delta = 0)
        : ((this._previousTime = this._currentTime),
          (this._currentTime = (t !== void 0 ? t : performance.now()) - this._startTime),
          (this._delta = (this._currentTime - this._previousTime) * this._timescale),
          (this._elapsed += this._delta)),
      this
    );
  }
}
function Xu() {
  this._document.hidden === !1 && this.reset();
}
class X0 extends Vh {
  constructor(t, e, n = 1) {
    (super(t, e), (this.isInstancedInterleavedBuffer = !0), (this.meshPerAttribute = n));
  }
  copy(t) {
    return (super.copy(t), (this.meshPerAttribute = t.meshPerAttribute), this);
  }
  clone(t) {
    const e = super.clone(t);
    return ((e.meshPerAttribute = this.meshPerAttribute), e);
  }
  toJSON(t) {
    const e = super.toJSON(t);
    return ((e.isInstancedInterleavedBuffer = !0), (e.meshPerAttribute = this.meshPerAttribute), e);
  }
}
const Jo = new oe();
class q0 {
  constructor(t, e, n = 0, s = 1 / 0) {
    ((this.ray = new $s(t, e)),
      (this.near = n),
      (this.far = s),
      (this.camera = null),
      (this.layers = new Ja()),
      (this.params = {
        Mesh: {},
        Line: { threshold: 1 },
        LOD: {},
        Points: { threshold: 1 },
        Sprite: {},
      }));
  }
  set(t, e) {
    this.ray.set(t, e);
  }
  setFromCamera(t, e) {
    e.isPerspectiveCamera
      ? (this.ray.origin.setFromMatrixPosition(e.matrixWorld),
        this.ray.direction.set(t.x, t.y, 0.5).unproject(e).sub(this.ray.origin).normalize(),
        (this.camera = e))
      : e.isOrthographicCamera
        ? (this.ray.origin.set(t.x, t.y, (e.near + e.far) / (e.near - e.far)).unproject(e),
          this.ray.direction.set(0, 0, -1).transformDirection(e.matrixWorld),
          (this.camera = e))
        : Jt('Raycaster: Unsupported camera type: ' + e.type);
  }
  setFromXRController(t) {
    return (
      Jo.identity().extractRotation(t.matrixWorld),
      this.ray.origin.setFromMatrixPosition(t.matrixWorld),
      this.ray.direction.set(0, 0, -1).applyMatrix4(Jo),
      this
    );
  }
  intersectObject(t, e = !0, n = []) {
    return (Na(t, this, n, e), n.sort($o), n);
  }
  intersectObjects(t, e = !0, n = []) {
    for (let s = 0, r = t.length; s < r; s++) Na(t[s], this, n, e);
    return (n.sort($o), n);
  }
}
function $o(i, t) {
  return i.distance - t.distance;
}
function Na(i, t, e, n) {
  let s = !0;
  if ((i.layers.test(t.layers) && i.raycast(t, e) === !1 && (s = !1), s === !0 && n === !0)) {
    const r = i.children;
    for (let a = 0, o = r.length; a < o; a++) Na(r[a], t, e, !0);
  }
}
class Y0 {
  constructor(t = !0) {
    ((this.autoStart = t),
      (this.startTime = 0),
      (this.oldTime = 0),
      (this.elapsedTime = 0),
      (this.running = !1),
      Ft('THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.'));
  }
  start() {
    ((this.startTime = performance.now()),
      (this.oldTime = this.startTime),
      (this.elapsedTime = 0),
      (this.running = !0));
  }
  stop() {
    (this.getElapsedTime(), (this.running = !1), (this.autoStart = !1));
  }
  getElapsedTime() {
    return (this.getDelta(), this.elapsedTime);
  }
  getDelta() {
    let t = 0;
    if (this.autoStart && !this.running) return (this.start(), 0);
    if (this.running) {
      const e = performance.now();
      ((t = (e - this.oldTime) / 1e3), (this.oldTime = e), (this.elapsedTime += t));
    }
    return t;
  }
}
class Z0 {
  constructor(t = 1, e = 0, n = 0) {
    ((this.radius = t), (this.phi = e), (this.theta = n));
  }
  set(t, e, n) {
    return ((this.radius = t), (this.phi = e), (this.theta = n), this);
  }
  copy(t) {
    return ((this.radius = t.radius), (this.phi = t.phi), (this.theta = t.theta), this);
  }
  makeSafe() {
    return ((this.phi = Bt(this.phi, 1e-6, Math.PI - 1e-6)), this);
  }
  setFromVector3(t) {
    return this.setFromCartesianCoords(t.x, t.y, t.z);
  }
  setFromCartesianCoords(t, e, n) {
    return (
      (this.radius = Math.sqrt(t * t + e * e + n * n)),
      this.radius === 0
        ? ((this.theta = 0), (this.phi = 0))
        : ((this.theta = Math.atan2(t, n)), (this.phi = Math.acos(Bt(e / this.radius, -1, 1)))),
      this
    );
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
class uc {
  constructor(t, e, n, s) {
    ((uc.prototype.isMatrix2 = !0),
      (this.elements = [1, 0, 0, 1]),
      t !== void 0 && this.set(t, e, n, s));
  }
  identity() {
    return (this.set(1, 0, 0, 1), this);
  }
  fromArray(t, e = 0) {
    for (let n = 0; n < 4; n++) this.elements[n] = t[n + e];
    return this;
  }
  set(t, e, n, s) {
    const r = this.elements;
    return ((r[0] = t), (r[2] = e), (r[1] = n), (r[3] = s), this);
  }
}
const Ko = new L(),
  Ds = new L(),
  gi = new L(),
  _i = new L(),
  Ur = new L(),
  qu = new L(),
  Yu = new L();
class J0 {
  constructor(t = new L(), e = new L()) {
    ((this.start = t), (this.end = e));
  }
  set(t, e) {
    return (this.start.copy(t), this.end.copy(e), this);
  }
  copy(t) {
    return (this.start.copy(t.start), this.end.copy(t.end), this);
  }
  getCenter(t) {
    return t.addVectors(this.start, this.end).multiplyScalar(0.5);
  }
  delta(t) {
    return t.subVectors(this.end, this.start);
  }
  distanceSq() {
    return this.start.distanceToSquared(this.end);
  }
  distance() {
    return this.start.distanceTo(this.end);
  }
  at(t, e) {
    return this.delta(e).multiplyScalar(t).add(this.start);
  }
  closestPointToPointParameter(t, e) {
    (Ko.subVectors(t, this.start), Ds.subVectors(this.end, this.start));
    const n = Ds.dot(Ds);
    let r = Ds.dot(Ko) / n;
    return (e && (r = Bt(r, 0, 1)), r);
  }
  closestPointToPoint(t, e, n) {
    const s = this.closestPointToPointParameter(t, e);
    return this.delta(n).multiplyScalar(s).add(this.start);
  }
  distanceSqToLine3(t, e = qu, n = Yu) {
    const s = 10000000000000001e-32;
    let r, a;
    const o = this.start,
      l = t.start,
      c = this.end,
      h = t.end;
    (gi.subVectors(c, o), _i.subVectors(h, l), Ur.subVectors(o, l));
    const f = gi.dot(gi),
      u = _i.dot(_i),
      p = _i.dot(Ur);
    if (f <= s && u <= s) return (e.copy(o), n.copy(l), e.sub(n), e.dot(e));
    if (f <= s) ((r = 0), (a = p / u), (a = Bt(a, 0, 1)));
    else {
      const g = gi.dot(Ur);
      if (u <= s) ((a = 0), (r = Bt(-g / f, 0, 1)));
      else {
        const M = gi.dot(_i),
          m = f * u - M * M;
        (m !== 0 ? (r = Bt((M * p - g * u) / m, 0, 1)) : (r = 0),
          (a = (M * r + p) / u),
          a < 0
            ? ((a = 0), (r = Bt(-g / f, 0, 1)))
            : a > 1 && ((a = 1), (r = Bt((M - g) / f, 0, 1))));
      }
    }
    return (
      e.copy(o).addScaledVector(gi, r),
      n.copy(l).addScaledVector(_i, a),
      e.distanceToSquared(n)
    );
  }
  applyMatrix4(t) {
    return (this.start.applyMatrix4(t), this.end.applyMatrix4(t), this);
  }
  equals(t) {
    return t.start.equals(this.start) && t.end.equals(this.end);
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
class $0 {
  constructor() {
    ((this.type = 'ShapePath'),
      (this.color = new zt()),
      (this.subPaths = []),
      (this.currentPath = null));
  }
  moveTo(t, e) {
    return (
      (this.currentPath = new Da()),
      this.subPaths.push(this.currentPath),
      this.currentPath.moveTo(t, e),
      this
    );
  }
  lineTo(t, e) {
    return (this.currentPath.lineTo(t, e), this);
  }
  quadraticCurveTo(t, e, n, s) {
    return (this.currentPath.quadraticCurveTo(t, e, n, s), this);
  }
  bezierCurveTo(t, e, n, s, r, a) {
    return (this.currentPath.bezierCurveTo(t, e, n, s, r, a), this);
  }
  splineThru(t) {
    return (this.currentPath.splineThru(t), this);
  }
  toShapes(t) {
    function e(d) {
      const E = [];
      for (let y = 0, S = d.length; y < S; y++) {
        const R = d[y],
          w = new Vs();
        ((w.curves = R.curves), E.push(w));
      }
      return E;
    }
    function n(d, E) {
      const y = E.length;
      let S = !1;
      for (let R = y - 1, w = 0; w < y; R = w++) {
        let P = E[R],
          x = E[w],
          b = x.x - P.x,
          H = x.y - P.y;
        if (Math.abs(H) > Number.EPSILON) {
          if ((H < 0 && ((P = E[w]), (b = -b), (x = E[R]), (H = -H)), d.y < P.y || d.y > x.y))
            continue;
          if (d.y === P.y) {
            if (d.x === P.x) return !0;
          } else {
            const C = H * (d.x - P.x) - b * (d.y - P.y);
            if (C === 0) return !0;
            if (C < 0) continue;
            S = !S;
          }
        } else {
          if (d.y !== P.y) continue;
          if ((x.x <= d.x && d.x <= P.x) || (P.x <= d.x && d.x <= x.x)) return !0;
        }
      }
      return S;
    }
    const s = Zn.isClockWise,
      r = this.subPaths;
    if (r.length === 0) return [];
    let a, o, l;
    const c = [];
    if (r.length === 1) return ((o = r[0]), (l = new Vs()), (l.curves = o.curves), c.push(l), c);
    let h = !s(r[0].getPoints());
    h = t ? !h : h;
    const f = [],
      u = [];
    let p = [],
      g = 0,
      M;
    ((u[g] = void 0), (p[g] = []));
    for (let d = 0, E = r.length; d < E; d++)
      ((o = r[d]),
        (M = o.getPoints()),
        (a = s(M)),
        (a = t ? !a : a),
        a
          ? (!h && u[g] && g++,
            (u[g] = { s: new Vs(), p: M }),
            (u[g].s.curves = o.curves),
            h && g++,
            (p[g] = []))
          : p[g].push({ h: o, p: M[0] }));
    if (!u[0]) return e(r);
    if (u.length > 1) {
      let d = !1,
        E = 0;
      for (let y = 0, S = u.length; y < S; y++) f[y] = [];
      for (let y = 0, S = u.length; y < S; y++) {
        const R = p[y];
        for (let w = 0; w < R.length; w++) {
          const P = R[w];
          let x = !0;
          for (let b = 0; b < u.length; b++)
            n(P.p, u[b].p) && (y !== b && E++, x ? ((x = !1), f[b].push(P)) : (d = !0));
          x && f[y].push(P);
        }
      }
      E > 0 && d === !1 && (p = f);
    }
    let m;
    for (let d = 0, E = u.length; d < E; d++) {
      ((l = u[d].s), c.push(l), (m = p[d]));
      for (let y = 0, S = m.length; y < S; y++) l.holes.push(m[y].h);
    }
    return c;
  }
}
class K0 extends jn {
  constructor(t, e = null) {
    (super(),
      (this.object = t),
      (this.domElement = e),
      (this.enabled = !0),
      (this.state = -1),
      (this.keys = {}),
      (this.mouseButtons = { LEFT: null, MIDDLE: null, RIGHT: null }),
      (this.touches = { ONE: null, TWO: null }));
  }
  connect(t) {
    if (t === void 0) {
      Ft('Controls: connect() now requires an element.');
      return;
    }
    (this.domElement !== null && this.disconnect(), (this.domElement = t));
  }
  disconnect() {}
  dispose() {}
  update() {}
}
function jo(i, t, e, n) {
  const s = Zu(n);
  switch (e) {
    case Ul:
      return i * t;
    case Fl:
      return ((i * t) / s.components) * s.byteLength;
    case Ha:
      return ((i * t) / s.components) * s.byteLength;
    case Ei:
      return ((i * t * 2) / s.components) * s.byteLength;
    case ka:
      return ((i * t * 2) / s.components) * s.byteLength;
    case Nl:
      return ((i * t * 3) / s.components) * s.byteLength;
    case Ye:
      return ((i * t * 4) / s.components) * s.byteLength;
    case Wa:
      return ((i * t * 4) / s.components) * s.byteLength;
    case Fs:
    case Os:
      return Math.floor((i + 3) / 4) * Math.floor((t + 3) / 4) * 8;
    case Bs:
    case zs:
      return Math.floor((i + 3) / 4) * Math.floor((t + 3) / 4) * 16;
    case Qr:
    case ea:
      return (Math.max(i, 16) * Math.max(t, 8)) / 4;
    case jr:
    case ta:
      return (Math.max(i, 8) * Math.max(t, 8)) / 2;
    case na:
    case ia:
    case ra:
    case aa:
      return Math.floor((i + 3) / 4) * Math.floor((t + 3) / 4) * 8;
    case sa:
    case oa:
    case la:
      return Math.floor((i + 3) / 4) * Math.floor((t + 3) / 4) * 16;
    case ca:
      return Math.floor((i + 3) / 4) * Math.floor((t + 3) / 4) * 16;
    case ha:
      return Math.floor((i + 4) / 5) * Math.floor((t + 3) / 4) * 16;
    case ua:
      return Math.floor((i + 4) / 5) * Math.floor((t + 4) / 5) * 16;
    case fa:
      return Math.floor((i + 5) / 6) * Math.floor((t + 4) / 5) * 16;
    case da:
      return Math.floor((i + 5) / 6) * Math.floor((t + 5) / 6) * 16;
    case pa:
      return Math.floor((i + 7) / 8) * Math.floor((t + 4) / 5) * 16;
    case ma:
      return Math.floor((i + 7) / 8) * Math.floor((t + 5) / 6) * 16;
    case ga:
      return Math.floor((i + 7) / 8) * Math.floor((t + 7) / 8) * 16;
    case _a:
      return Math.floor((i + 9) / 10) * Math.floor((t + 4) / 5) * 16;
    case xa:
      return Math.floor((i + 9) / 10) * Math.floor((t + 5) / 6) * 16;
    case va:
      return Math.floor((i + 9) / 10) * Math.floor((t + 7) / 8) * 16;
    case Ma:
      return Math.floor((i + 9) / 10) * Math.floor((t + 9) / 10) * 16;
    case Sa:
      return Math.floor((i + 11) / 12) * Math.floor((t + 9) / 10) * 16;
    case ya:
      return Math.floor((i + 11) / 12) * Math.floor((t + 11) / 12) * 16;
    case Ea:
    case ba:
    case Ta:
      return Math.ceil(i / 4) * Math.ceil(t / 4) * 16;
    case Aa:
    case wa:
      return Math.ceil(i / 4) * Math.ceil(t / 4) * 8;
    case Ra:
    case Ca:
      return Math.ceil(i / 4) * Math.ceil(t / 4) * 16;
  }
  throw new Error(`Unable to determine texture byte length for ${e} format.`);
}
function Zu(i) {
  switch (i) {
    case Oe:
    case Pl:
      return { byteLength: 1, components: 1 };
    case Wi:
    case Ll:
    case Sn:
      return { byteLength: 2, components: 1 };
    case Va:
    case Ga:
      return { byteLength: 2, components: 4 };
    case an:
    case za:
    case en:
      return { byteLength: 4, components: 1 };
    case Dl:
    case Il:
      return { byteLength: 4, components: 3 };
  }
  throw new Error(`Unknown texture type ${i}.`);
}
typeof __THREE_DEVTOOLS__ < 'u' &&
  __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent('register', { detail: { revision: Ba } }));
typeof window < 'u' &&
  (window.__THREE__
    ? Ft('WARNING: Multiple instances of Three.js being imported.')
    : (window.__THREE__ = Ba));
/**
 * @license
 * Copyright 2010-2026 Three.js Authors
 * SPDX-License-Identifier: MIT
 */ function fc() {
  let i = null,
    t = !1,
    e = null,
    n = null;
  function s(r, a) {
    (e(r, a), (n = i.requestAnimationFrame(s)));
  }
  return {
    start: function () {
      t !== !0 && e !== null && ((n = i.requestAnimationFrame(s)), (t = !0));
    },
    stop: function () {
      (i.cancelAnimationFrame(n), (t = !1));
    },
    setAnimationLoop: function (r) {
      e = r;
    },
    setContext: function (r) {
      i = r;
    },
  };
}
function Ju(i) {
  const t = new WeakMap();
  function e(o, l) {
    const c = o.array,
      h = o.usage,
      f = c.byteLength,
      u = i.createBuffer();
    (i.bindBuffer(l, u), i.bufferData(l, c, h), o.onUploadCallback());
    let p;
    if (c instanceof Float32Array) p = i.FLOAT;
    else if (typeof Float16Array < 'u' && c instanceof Float16Array) p = i.HALF_FLOAT;
    else if (c instanceof Uint16Array)
      o.isFloat16BufferAttribute ? (p = i.HALF_FLOAT) : (p = i.UNSIGNED_SHORT);
    else if (c instanceof Int16Array) p = i.SHORT;
    else if (c instanceof Uint32Array) p = i.UNSIGNED_INT;
    else if (c instanceof Int32Array) p = i.INT;
    else if (c instanceof Int8Array) p = i.BYTE;
    else if (c instanceof Uint8Array) p = i.UNSIGNED_BYTE;
    else if (c instanceof Uint8ClampedArray) p = i.UNSIGNED_BYTE;
    else throw new Error('THREE.WebGLAttributes: Unsupported buffer data format: ' + c);
    return {
      buffer: u,
      type: p,
      bytesPerElement: c.BYTES_PER_ELEMENT,
      version: o.version,
      size: f,
    };
  }
  function n(o, l, c) {
    const h = l.array,
      f = l.updateRanges;
    if ((i.bindBuffer(c, o), f.length === 0)) i.bufferSubData(c, 0, h);
    else {
      f.sort((p, g) => p.start - g.start);
      let u = 0;
      for (let p = 1; p < f.length; p++) {
        const g = f[u],
          M = f[p];
        M.start <= g.start + g.count + 1
          ? (g.count = Math.max(g.count, M.start + M.count - g.start))
          : (++u, (f[u] = M));
      }
      f.length = u + 1;
      for (let p = 0, g = f.length; p < g; p++) {
        const M = f[p];
        i.bufferSubData(c, M.start * h.BYTES_PER_ELEMENT, h, M.start, M.count);
      }
      l.clearUpdateRanges();
    }
    l.onUploadCallback();
  }
  function s(o) {
    return (o.isInterleavedBufferAttribute && (o = o.data), t.get(o));
  }
  function r(o) {
    o.isInterleavedBufferAttribute && (o = o.data);
    const l = t.get(o);
    l && (i.deleteBuffer(l.buffer), t.delete(o));
  }
  function a(o, l) {
    if ((o.isInterleavedBufferAttribute && (o = o.data), o.isGLBufferAttribute)) {
      const h = t.get(o);
      (!h || h.version < o.version) &&
        t.set(o, {
          buffer: o.buffer,
          type: o.type,
          bytesPerElement: o.elementSize,
          version: o.version,
        });
      return;
    }
    const c = t.get(o);
    if (c === void 0) t.set(o, e(o, l));
    else if (c.version < o.version) {
      if (c.size !== o.array.byteLength)
        throw new Error(
          "THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported."
        );
      (n(c.buffer, o, l), (c.version = o.version));
    }
  }
  return { get: s, remove: r, update: a };
}
var $u = `#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,
  Ku = `#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,
  ju = `#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,
  Qu = `#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,
  tf = `#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,
  ef = `#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,
  nf = `#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,
  sf = `#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,
  rf = `#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec4 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 );
	}
#endif`,
  af = `#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,
  of = `vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,
  lf = `vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,
  cf = `float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,
  hf = `#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,
  uf = `#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,
  ff = `#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,
  df = `#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,
  pf = `#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,
  mf = `#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,
  gf = `#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#endif`,
  _f = `#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#endif`,
  xf = `#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec4 vColor;
#endif`,
  vf = `#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec4( 1.0 );
#endif
#ifdef USE_COLOR_ALPHA
	vColor *= color;
#elif defined( USE_COLOR )
	vColor.rgb *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.rgb *= instanceColor.rgb;
#endif
#ifdef USE_BATCHING_COLOR
	vColor *= getBatchingColor( getIndirectIndex( gl_DrawID ) );
#endif`,
  Mf = `#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,
  Sf = `#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,
  yf = `vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,
  Ef = `#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,
  bf = `#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,
  Tf = `#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,
  Af = `#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,
  wf = 'gl_FragColor = linearToOutputTexel( gl_FragColor );',
  Rf = `vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,
  Cf = `#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
		#ifdef ENVMAP_BLENDING_MULTIPLY
			outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
		#elif defined( ENVMAP_BLENDING_MIX )
			outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
		#elif defined( ENVMAP_BLENDING_ADD )
			outgoingLight += envColor.xyz * specularStrength * reflectivity;
		#endif
	#endif
#endif`,
  Pf = `#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
#endif`,
  Lf = `#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,
  Df = `#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,
  If = `#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,
  Uf = `#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,
  Nf = `#ifdef USE_FOG
	varying float vFogDepth;
#endif`,
  Ff = `#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,
  Of = `#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,
  Bf = `#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,
  zf = `#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,
  Vf = `LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,
  Gf = `varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,
  Hf = `uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,
  kf = `#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, pow4( roughness ) ) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,
  Wf = `ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,
  Xf = `varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,
  qf = `BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,
  Yf = `varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,
  Zf = `PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.diffuseContribution = diffuseColor.rgb * ( 1.0 - metalnessFactor );
material.metalness = metalnessFactor;
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor;
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = vec3( 0.04 );
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.0001, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,
  Jf = `uniform sampler2D dfgLUT;
struct PhysicalMaterial {
	vec3 diffuseColor;
	vec3 diffuseContribution;
	vec3 specularColor;
	vec3 specularColorBlended;
	float roughness;
	float metalness;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
		vec3 iridescenceFresnelDielectric;
		vec3 iridescenceFresnelMetallic;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return v;
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColorBlended;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transpose( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float rInv = 1.0 / ( roughness + 0.1 );
	float a = -1.9362 + 1.0678 * roughness + 0.4573 * r2 - 0.8469 * rInv;
	float b = -0.6014 + 0.5538 * roughness - 0.4670 * r2 - 0.1255 * rInv;
	float DG = exp( a * dotNV + b );
	return saturate( DG );
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
vec3 BRDF_GGX_Multiscatter( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 singleScatter = BRDF_GGX( lightDir, viewDir, normal, material );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 dfgV = texture2D( dfgLUT, vec2( material.roughness, dotNV ) ).rg;
	vec2 dfgL = texture2D( dfgLUT, vec2( material.roughness, dotNL ) ).rg;
	vec3 FssEss_V = material.specularColorBlended * dfgV.x + material.specularF90 * dfgV.y;
	vec3 FssEss_L = material.specularColorBlended * dfgL.x + material.specularF90 * dfgL.y;
	float Ess_V = dfgV.x + dfgV.y;
	float Ess_L = dfgL.x + dfgL.y;
	float Ems_V = 1.0 - Ess_V;
	float Ems_L = 1.0 - Ess_L;
	vec3 Favg = material.specularColorBlended + ( 1.0 - material.specularColorBlended ) * 0.047619;
	vec3 Fms = FssEss_V * FssEss_L * Favg / ( 1.0 - Ems_V * Ems_L * Favg + EPSILON );
	float compensationFactor = Ems_V * Ems_L;
	vec3 multiScatter = Fms * compensationFactor;
	return singleScatter + multiScatter;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColorBlended * t2.x + ( material.specularF90 - material.specularColorBlended ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseContribution * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
		#ifdef USE_CLEARCOAT
			vec3 Ncc = geometryClearcoatNormal;
			vec2 uvClearcoat = LTC_Uv( Ncc, viewDir, material.clearcoatRoughness );
			vec4 t1Clearcoat = texture2D( ltc_1, uvClearcoat );
			vec4 t2Clearcoat = texture2D( ltc_2, uvClearcoat );
			mat3 mInvClearcoat = mat3(
				vec3( t1Clearcoat.x, 0, t1Clearcoat.y ),
				vec3(             0, 1,             0 ),
				vec3( t1Clearcoat.z, 0, t1Clearcoat.w )
			);
			vec3 fresnelClearcoat = material.clearcoatF0 * t2Clearcoat.x + ( material.clearcoatF90 - material.clearcoatF0 ) * t2Clearcoat.y;
			clearcoatSpecularDirect += lightColor * fresnelClearcoat * LTC_Evaluate( Ncc, viewDir, position, mInvClearcoat, rectCoords );
		#endif
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
 
 		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
 
 		float sheenAlbedoV = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
 		float sheenAlbedoL = IBLSheenBRDF( geometryNormal, directLight.direction, material.sheenRoughness );
 
 		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * max( sheenAlbedoV, sheenAlbedoL );
 
 		irradiance *= sheenEnergyComp;
 
 	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX_Multiscatter( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 diffuse = irradiance * BRDF_Lambert( material.diffuseContribution );
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		diffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectDiffuse += diffuse;
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness ) * RECIPROCAL_PI;
 	#endif
	vec3 singleScatteringDielectric = vec3( 0.0 );
	vec3 multiScatteringDielectric = vec3( 0.0 );
	vec3 singleScatteringMetallic = vec3( 0.0 );
	vec3 multiScatteringMetallic = vec3( 0.0 );
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnelDielectric, material.roughness, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.diffuseColor, material.specularF90, material.iridescence, material.iridescenceFresnelMetallic, material.roughness, singleScatteringMetallic, multiScatteringMetallic );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscattering( geometryNormal, geometryViewDir, material.diffuseColor, material.specularF90, material.roughness, singleScatteringMetallic, multiScatteringMetallic );
	#endif
	vec3 singleScattering = mix( singleScatteringDielectric, singleScatteringMetallic, material.metalness );
	vec3 multiScattering = mix( multiScatteringDielectric, multiScatteringMetallic, material.metalness );
	vec3 totalScatteringDielectric = singleScatteringDielectric + multiScatteringDielectric;
	vec3 diffuse = material.diffuseContribution * ( 1.0 - totalScatteringDielectric );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	vec3 indirectSpecular = radiance * singleScattering;
	indirectSpecular += multiScattering * cosineWeightedIrradiance;
	vec3 indirectDiffuse = diffuse * cosineWeightedIrradiance;
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		indirectSpecular *= sheenEnergyComp;
		indirectDiffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectSpecular += indirectSpecular;
	reflectedLight.indirectDiffuse += indirectDiffuse;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,
  $f = `
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnelDielectric = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceFresnelMetallic = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.diffuseColor );
		material.iridescenceFresnel = mix( material.iridescenceFresnelDielectric, material.iridescenceFresnelMetallic, material.metalness );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,
  Kf = `#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )
		#if defined( STANDARD ) || defined( LAMBERT ) || defined( PHONG )
			iblIrradiance += getIBLIrradiance( geometryNormal );
		#endif
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,
  jf = `#if defined( RE_IndirectDiffuse )
	#if defined( LAMBERT ) || defined( PHONG )
		irradiance += iblIrradiance;
	#endif
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,
  Qf = `#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,
  td = `#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,
  ed = `#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,
  nd = `#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,
  id = `#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,
  sd = `#ifdef USE_MAP
	uniform sampler2D map;
#endif`,
  rd = `#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,
  ad = `#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,
  od = `float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,
  ld = `#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,
  cd = `#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,
  hd = `#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,
  ud = `#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,
  fd = `#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,
  dd = `#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,
  pd = `float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,
  md = `#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,
  gd = `#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,
  _d = `#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,
  xd = `#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,
  vd = `#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,
  Md = `#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,
  Sd = `#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,
  yd = `#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,
  Ed = `#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,
  bd = `#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,
  Td = `vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	#ifdef USE_REVERSED_DEPTH_BUFFER
	
		return depth * ( far - near ) - far;
	#else
		return depth * ( near - far ) - near;
	#endif
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	
	#ifdef USE_REVERSED_DEPTH_BUFFER
		return ( near * far ) / ( ( near - far ) * depth - near );
	#else
		return ( near * far ) / ( ( far - near ) * depth - far );
	#endif
}`,
  Ad = `#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,
  wd = `vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,
  Rd = `#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,
  Cd = `#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,
  Pd = `float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,
  Ld = `#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,
  Dd = `#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#else
			uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#endif
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#else
			uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#endif
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform samplerCubeShadow pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#elif defined( SHADOWMAP_TYPE_BASIC )
			uniform samplerCube pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#endif
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float interleavedGradientNoise( vec2 position ) {
			return fract( 52.9829189 * fract( dot( position, vec2( 0.06711056, 0.00583715 ) ) ) );
		}
		vec2 vogelDiskSample( int sampleIndex, int samplesCount, float phi ) {
			const float goldenAngle = 2.399963229728653;
			float r = sqrt( ( float( sampleIndex ) + 0.5 ) / float( samplesCount ) );
			float theta = float( sampleIndex ) * goldenAngle + phi;
			return vec2( cos( theta ), sin( theta ) ) * r;
		}
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float getShadow( sampler2DShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
				float radius = shadowRadius * texelSize.x;
				float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;
				shadow = (
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 0, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 1, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 2, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 3, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 4, 5, phi ) * radius, shadowCoord.z ) )
				) * 0.2;
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#elif defined( SHADOWMAP_TYPE_VSM )
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadowCoord.z -= shadowBias;
			#else
				shadowCoord.z += shadowBias;
			#endif
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 distribution = texture2D( shadowMap, shadowCoord.xy ).rg;
				float mean = distribution.x;
				float variance = distribution.y * distribution.y;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					float hard_shadow = step( mean, shadowCoord.z );
				#else
					float hard_shadow = step( shadowCoord.z, mean );
				#endif
				
				if ( hard_shadow == 1.0 ) {
					shadow = 1.0;
				} else {
					variance = max( variance, 0.0000001 );
					float d = shadowCoord.z - mean;
					float p_max = variance / ( variance + d * d );
					p_max = clamp( ( p_max - 0.3 ) / 0.65, 0.0, 1.0 );
					shadow = max( hard_shadow, p_max );
				}
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#else
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadowCoord.z -= shadowBias;
			#else
				shadowCoord.z += shadowBias;
			#endif
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				float depth = texture2D( shadowMap, shadowCoord.xy ).r;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					shadow = step( depth, shadowCoord.z );
				#else
					shadow = step( shadowCoord.z, depth );
				#endif
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	#if defined( SHADOWMAP_TYPE_PCF )
	float getPointShadow( samplerCubeShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 bd3D = normalize( lightToPosition );
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			#ifdef USE_REVERSED_DEPTH_BUFFER
				float dp = ( shadowCameraNear * ( shadowCameraFar - viewSpaceZ ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp -= shadowBias;
			#else
				float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp += shadowBias;
			#endif
			float texelSize = shadowRadius / shadowMapSize.x;
			vec3 absDir = abs( bd3D );
			vec3 tangent = absDir.x > absDir.z ? vec3( 0.0, 1.0, 0.0 ) : vec3( 1.0, 0.0, 0.0 );
			tangent = normalize( cross( bd3D, tangent ) );
			vec3 bitangent = cross( bd3D, tangent );
			float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;
			vec2 sample0 = vogelDiskSample( 0, 5, phi );
			vec2 sample1 = vogelDiskSample( 1, 5, phi );
			vec2 sample2 = vogelDiskSample( 2, 5, phi );
			vec2 sample3 = vogelDiskSample( 3, 5, phi );
			vec2 sample4 = vogelDiskSample( 4, 5, phi );
			shadow = (
				texture( shadowMap, vec4( bd3D + ( tangent * sample0.x + bitangent * sample0.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample1.x + bitangent * sample1.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample2.x + bitangent * sample2.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample3.x + bitangent * sample3.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample4.x + bitangent * sample4.y ) * texelSize, dp ) )
			) * 0.2;
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#elif defined( SHADOWMAP_TYPE_BASIC )
	float getPointShadow( samplerCube shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			float depth = textureCube( shadowMap, bd3D ).r;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				depth = 1.0 - depth;
			#endif
			shadow = step( dp, depth );
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#endif
	#endif
#endif`,
  Id = `#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,
  Ud = `#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,
  Nd = `float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0 && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,
  Fd = `#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,
  Od = `#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,
  Bd = `#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,
  zd = `#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,
  Vd = `float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,
  Gd = `#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,
  Hd = `#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,
  kd = `#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,
  Wd = `#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseContribution, material.specularColorBlended, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,
  Xd = `#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,
  qd = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,
  Yd = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,
  Zd = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,
  Jd = `#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;
const $d = `varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,
  Kd = `uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,
  jd = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,
  Qd = `#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,
  tp = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,
  ep = `uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,
  np = `#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,
  ip = `#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,
  sp = `#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,
  rp = `#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = vec4( dist, 0.0, 0.0, 1.0 );
}`,
  ap = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,
  op = `uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,
  lp = `uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,
  cp = `uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,
  hp = `#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,
  up = `uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,
  fp = `#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,
  dp = `#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,
  pp = `#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,
  mp = `#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,
  gp = `#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,
  _p = `#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( normalize( normal ) * 0.5 + 0.5, diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,
  xp = `#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,
  vp = `#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,
  Mp = `#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,
  Sp = `#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
 
		outgoingLight = outgoingLight + sheenSpecularDirect + sheenSpecularIndirect;
 
 	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,
  yp = `#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,
  Ep = `#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,
  bp = `uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,
  Tp = `uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,
  Ap = `#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,
  wp = `uniform vec3 color;
uniform float opacity;
#include <common>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,
  Rp = `uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,
  Cp = `uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,
  qt = {
    alphahash_fragment: $u,
    alphahash_pars_fragment: Ku,
    alphamap_fragment: ju,
    alphamap_pars_fragment: Qu,
    alphatest_fragment: tf,
    alphatest_pars_fragment: ef,
    aomap_fragment: nf,
    aomap_pars_fragment: sf,
    batching_pars_vertex: rf,
    batching_vertex: af,
    begin_vertex: of,
    beginnormal_vertex: lf,
    bsdfs: cf,
    iridescence_fragment: hf,
    bumpmap_pars_fragment: uf,
    clipping_planes_fragment: ff,
    clipping_planes_pars_fragment: df,
    clipping_planes_pars_vertex: pf,
    clipping_planes_vertex: mf,
    color_fragment: gf,
    color_pars_fragment: _f,
    color_pars_vertex: xf,
    color_vertex: vf,
    common: Mf,
    cube_uv_reflection_fragment: Sf,
    defaultnormal_vertex: yf,
    displacementmap_pars_vertex: Ef,
    displacementmap_vertex: bf,
    emissivemap_fragment: Tf,
    emissivemap_pars_fragment: Af,
    colorspace_fragment: wf,
    colorspace_pars_fragment: Rf,
    envmap_fragment: Cf,
    envmap_common_pars_fragment: Pf,
    envmap_pars_fragment: Lf,
    envmap_pars_vertex: Df,
    envmap_physical_pars_fragment: kf,
    envmap_vertex: If,
    fog_vertex: Uf,
    fog_pars_vertex: Nf,
    fog_fragment: Ff,
    fog_pars_fragment: Of,
    gradientmap_pars_fragment: Bf,
    lightmap_pars_fragment: zf,
    lights_lambert_fragment: Vf,
    lights_lambert_pars_fragment: Gf,
    lights_pars_begin: Hf,
    lights_toon_fragment: Wf,
    lights_toon_pars_fragment: Xf,
    lights_phong_fragment: qf,
    lights_phong_pars_fragment: Yf,
    lights_physical_fragment: Zf,
    lights_physical_pars_fragment: Jf,
    lights_fragment_begin: $f,
    lights_fragment_maps: Kf,
    lights_fragment_end: jf,
    logdepthbuf_fragment: Qf,
    logdepthbuf_pars_fragment: td,
    logdepthbuf_pars_vertex: ed,
    logdepthbuf_vertex: nd,
    map_fragment: id,
    map_pars_fragment: sd,
    map_particle_fragment: rd,
    map_particle_pars_fragment: ad,
    metalnessmap_fragment: od,
    metalnessmap_pars_fragment: ld,
    morphinstance_vertex: cd,
    morphcolor_vertex: hd,
    morphnormal_vertex: ud,
    morphtarget_pars_vertex: fd,
    morphtarget_vertex: dd,
    normal_fragment_begin: pd,
    normal_fragment_maps: md,
    normal_pars_fragment: gd,
    normal_pars_vertex: _d,
    normal_vertex: xd,
    normalmap_pars_fragment: vd,
    clearcoat_normal_fragment_begin: Md,
    clearcoat_normal_fragment_maps: Sd,
    clearcoat_pars_fragment: yd,
    iridescence_pars_fragment: Ed,
    opaque_fragment: bd,
    packing: Td,
    premultiplied_alpha_fragment: Ad,
    project_vertex: wd,
    dithering_fragment: Rd,
    dithering_pars_fragment: Cd,
    roughnessmap_fragment: Pd,
    roughnessmap_pars_fragment: Ld,
    shadowmap_pars_fragment: Dd,
    shadowmap_pars_vertex: Id,
    shadowmap_vertex: Ud,
    shadowmask_pars_fragment: Nd,
    skinbase_vertex: Fd,
    skinning_pars_vertex: Od,
    skinning_vertex: Bd,
    skinnormal_vertex: zd,
    specularmap_fragment: Vd,
    specularmap_pars_fragment: Gd,
    tonemapping_fragment: Hd,
    tonemapping_pars_fragment: kd,
    transmission_fragment: Wd,
    transmission_pars_fragment: Xd,
    uv_pars_fragment: qd,
    uv_pars_vertex: Yd,
    uv_vertex: Zd,
    worldpos_vertex: Jd,
    background_vert: $d,
    background_frag: Kd,
    backgroundCube_vert: jd,
    backgroundCube_frag: Qd,
    cube_vert: tp,
    cube_frag: ep,
    depth_vert: np,
    depth_frag: ip,
    distance_vert: sp,
    distance_frag: rp,
    equirect_vert: ap,
    equirect_frag: op,
    linedashed_vert: lp,
    linedashed_frag: cp,
    meshbasic_vert: hp,
    meshbasic_frag: up,
    meshlambert_vert: fp,
    meshlambert_frag: dp,
    meshmatcap_vert: pp,
    meshmatcap_frag: mp,
    meshnormal_vert: gp,
    meshnormal_frag: _p,
    meshphong_vert: xp,
    meshphong_frag: vp,
    meshphysical_vert: Mp,
    meshphysical_frag: Sp,
    meshtoon_vert: yp,
    meshtoon_frag: Ep,
    points_vert: bp,
    points_frag: Tp,
    shadow_vert: Ap,
    shadow_frag: wp,
    sprite_vert: Rp,
    sprite_frag: Cp,
  },
  ft = {
    common: {
      diffuse: { value: new zt(16777215) },
      opacity: { value: 1 },
      map: { value: null },
      mapTransform: { value: new Xt() },
      alphaMap: { value: null },
      alphaMapTransform: { value: new Xt() },
      alphaTest: { value: 0 },
    },
    specularmap: { specularMap: { value: null }, specularMapTransform: { value: new Xt() } },
    envmap: {
      envMap: { value: null },
      envMapRotation: { value: new Xt() },
      flipEnvMap: { value: -1 },
      reflectivity: { value: 1 },
      ior: { value: 1.5 },
      refractionRatio: { value: 0.98 },
      dfgLUT: { value: null },
    },
    aomap: {
      aoMap: { value: null },
      aoMapIntensity: { value: 1 },
      aoMapTransform: { value: new Xt() },
    },
    lightmap: {
      lightMap: { value: null },
      lightMapIntensity: { value: 1 },
      lightMapTransform: { value: new Xt() },
    },
    bumpmap: {
      bumpMap: { value: null },
      bumpMapTransform: { value: new Xt() },
      bumpScale: { value: 1 },
    },
    normalmap: {
      normalMap: { value: null },
      normalMapTransform: { value: new Xt() },
      normalScale: { value: new ct(1, 1) },
    },
    displacementmap: {
      displacementMap: { value: null },
      displacementMapTransform: { value: new Xt() },
      displacementScale: { value: 1 },
      displacementBias: { value: 0 },
    },
    emissivemap: { emissiveMap: { value: null }, emissiveMapTransform: { value: new Xt() } },
    metalnessmap: { metalnessMap: { value: null }, metalnessMapTransform: { value: new Xt() } },
    roughnessmap: { roughnessMap: { value: null }, roughnessMapTransform: { value: new Xt() } },
    gradientmap: { gradientMap: { value: null } },
    fog: {
      fogDensity: { value: 25e-5 },
      fogNear: { value: 1 },
      fogFar: { value: 2e3 },
      fogColor: { value: new zt(16777215) },
    },
    lights: {
      ambientLightColor: { value: [] },
      lightProbe: { value: [] },
      directionalLights: { value: [], properties: { direction: {}, color: {} } },
      directionalLightShadows: {
        value: [],
        properties: {
          shadowIntensity: 1,
          shadowBias: {},
          shadowNormalBias: {},
          shadowRadius: {},
          shadowMapSize: {},
        },
      },
      directionalShadowMatrix: { value: [] },
      spotLights: {
        value: [],
        properties: {
          color: {},
          position: {},
          direction: {},
          distance: {},
          coneCos: {},
          penumbraCos: {},
          decay: {},
        },
      },
      spotLightShadows: {
        value: [],
        properties: {
          shadowIntensity: 1,
          shadowBias: {},
          shadowNormalBias: {},
          shadowRadius: {},
          shadowMapSize: {},
        },
      },
      spotLightMap: { value: [] },
      spotLightMatrix: { value: [] },
      pointLights: { value: [], properties: { color: {}, position: {}, decay: {}, distance: {} } },
      pointLightShadows: {
        value: [],
        properties: {
          shadowIntensity: 1,
          shadowBias: {},
          shadowNormalBias: {},
          shadowRadius: {},
          shadowMapSize: {},
          shadowCameraNear: {},
          shadowCameraFar: {},
        },
      },
      pointShadowMatrix: { value: [] },
      hemisphereLights: { value: [], properties: { direction: {}, skyColor: {}, groundColor: {} } },
      rectAreaLights: { value: [], properties: { color: {}, position: {}, width: {}, height: {} } },
      ltc_1: { value: null },
      ltc_2: { value: null },
    },
    points: {
      diffuse: { value: new zt(16777215) },
      opacity: { value: 1 },
      size: { value: 1 },
      scale: { value: 1 },
      map: { value: null },
      alphaMap: { value: null },
      alphaMapTransform: { value: new Xt() },
      alphaTest: { value: 0 },
      uvTransform: { value: new Xt() },
    },
    sprite: {
      diffuse: { value: new zt(16777215) },
      opacity: { value: 1 },
      center: { value: new ct(0.5, 0.5) },
      rotation: { value: 0 },
      map: { value: null },
      mapTransform: { value: new Xt() },
      alphaMap: { value: null },
      alphaMapTransform: { value: new Xt() },
      alphaTest: { value: 0 },
    },
  },
  tn = {
    basic: {
      uniforms: Re([ft.common, ft.specularmap, ft.envmap, ft.aomap, ft.lightmap, ft.fog]),
      vertexShader: qt.meshbasic_vert,
      fragmentShader: qt.meshbasic_frag,
    },
    lambert: {
      uniforms: Re([
        ft.common,
        ft.specularmap,
        ft.envmap,
        ft.aomap,
        ft.lightmap,
        ft.emissivemap,
        ft.bumpmap,
        ft.normalmap,
        ft.displacementmap,
        ft.fog,
        ft.lights,
        { emissive: { value: new zt(0) }, envMapIntensity: { value: 1 } },
      ]),
      vertexShader: qt.meshlambert_vert,
      fragmentShader: qt.meshlambert_frag,
    },
    phong: {
      uniforms: Re([
        ft.common,
        ft.specularmap,
        ft.envmap,
        ft.aomap,
        ft.lightmap,
        ft.emissivemap,
        ft.bumpmap,
        ft.normalmap,
        ft.displacementmap,
        ft.fog,
        ft.lights,
        {
          emissive: { value: new zt(0) },
          specular: { value: new zt(1118481) },
          shininess: { value: 30 },
          envMapIntensity: { value: 1 },
        },
      ]),
      vertexShader: qt.meshphong_vert,
      fragmentShader: qt.meshphong_frag,
    },
    standard: {
      uniforms: Re([
        ft.common,
        ft.envmap,
        ft.aomap,
        ft.lightmap,
        ft.emissivemap,
        ft.bumpmap,
        ft.normalmap,
        ft.displacementmap,
        ft.roughnessmap,
        ft.metalnessmap,
        ft.fog,
        ft.lights,
        {
          emissive: { value: new zt(0) },
          roughness: { value: 1 },
          metalness: { value: 0 },
          envMapIntensity: { value: 1 },
        },
      ]),
      vertexShader: qt.meshphysical_vert,
      fragmentShader: qt.meshphysical_frag,
    },
    toon: {
      uniforms: Re([
        ft.common,
        ft.aomap,
        ft.lightmap,
        ft.emissivemap,
        ft.bumpmap,
        ft.normalmap,
        ft.displacementmap,
        ft.gradientmap,
        ft.fog,
        ft.lights,
        { emissive: { value: new zt(0) } },
      ]),
      vertexShader: qt.meshtoon_vert,
      fragmentShader: qt.meshtoon_frag,
    },
    matcap: {
      uniforms: Re([
        ft.common,
        ft.bumpmap,
        ft.normalmap,
        ft.displacementmap,
        ft.fog,
        { matcap: { value: null } },
      ]),
      vertexShader: qt.meshmatcap_vert,
      fragmentShader: qt.meshmatcap_frag,
    },
    points: {
      uniforms: Re([ft.points, ft.fog]),
      vertexShader: qt.points_vert,
      fragmentShader: qt.points_frag,
    },
    dashed: {
      uniforms: Re([
        ft.common,
        ft.fog,
        { scale: { value: 1 }, dashSize: { value: 1 }, totalSize: { value: 2 } },
      ]),
      vertexShader: qt.linedashed_vert,
      fragmentShader: qt.linedashed_frag,
    },
    depth: {
      uniforms: Re([ft.common, ft.displacementmap]),
      vertexShader: qt.depth_vert,
      fragmentShader: qt.depth_frag,
    },
    normal: {
      uniforms: Re([
        ft.common,
        ft.bumpmap,
        ft.normalmap,
        ft.displacementmap,
        { opacity: { value: 1 } },
      ]),
      vertexShader: qt.meshnormal_vert,
      fragmentShader: qt.meshnormal_frag,
    },
    sprite: {
      uniforms: Re([ft.sprite, ft.fog]),
      vertexShader: qt.sprite_vert,
      fragmentShader: qt.sprite_frag,
    },
    background: {
      uniforms: {
        uvTransform: { value: new Xt() },
        t2D: { value: null },
        backgroundIntensity: { value: 1 },
      },
      vertexShader: qt.background_vert,
      fragmentShader: qt.background_frag,
    },
    backgroundCube: {
      uniforms: {
        envMap: { value: null },
        flipEnvMap: { value: -1 },
        backgroundBlurriness: { value: 0 },
        backgroundIntensity: { value: 1 },
        backgroundRotation: { value: new Xt() },
      },
      vertexShader: qt.backgroundCube_vert,
      fragmentShader: qt.backgroundCube_frag,
    },
    cube: {
      uniforms: { tCube: { value: null }, tFlip: { value: -1 }, opacity: { value: 1 } },
      vertexShader: qt.cube_vert,
      fragmentShader: qt.cube_frag,
    },
    equirect: {
      uniforms: { tEquirect: { value: null } },
      vertexShader: qt.equirect_vert,
      fragmentShader: qt.equirect_frag,
    },
    distance: {
      uniforms: Re([
        ft.common,
        ft.displacementmap,
        {
          referencePosition: { value: new L() },
          nearDistance: { value: 1 },
          farDistance: { value: 1e3 },
        },
      ]),
      vertexShader: qt.distance_vert,
      fragmentShader: qt.distance_frag,
    },
    shadow: {
      uniforms: Re([ft.lights, ft.fog, { color: { value: new zt(0) }, opacity: { value: 1 } }]),
      vertexShader: qt.shadow_vert,
      fragmentShader: qt.shadow_frag,
    },
  };
tn.physical = {
  uniforms: Re([
    tn.standard.uniforms,
    {
      clearcoat: { value: 0 },
      clearcoatMap: { value: null },
      clearcoatMapTransform: { value: new Xt() },
      clearcoatNormalMap: { value: null },
      clearcoatNormalMapTransform: { value: new Xt() },
      clearcoatNormalScale: { value: new ct(1, 1) },
      clearcoatRoughness: { value: 0 },
      clearcoatRoughnessMap: { value: null },
      clearcoatRoughnessMapTransform: { value: new Xt() },
      dispersion: { value: 0 },
      iridescence: { value: 0 },
      iridescenceMap: { value: null },
      iridescenceMapTransform: { value: new Xt() },
      iridescenceIOR: { value: 1.3 },
      iridescenceThicknessMinimum: { value: 100 },
      iridescenceThicknessMaximum: { value: 400 },
      iridescenceThicknessMap: { value: null },
      iridescenceThicknessMapTransform: { value: new Xt() },
      sheen: { value: 0 },
      sheenColor: { value: new zt(0) },
      sheenColorMap: { value: null },
      sheenColorMapTransform: { value: new Xt() },
      sheenRoughness: { value: 1 },
      sheenRoughnessMap: { value: null },
      sheenRoughnessMapTransform: { value: new Xt() },
      transmission: { value: 0 },
      transmissionMap: { value: null },
      transmissionMapTransform: { value: new Xt() },
      transmissionSamplerSize: { value: new ct() },
      transmissionSamplerMap: { value: null },
      thickness: { value: 0 },
      thicknessMap: { value: null },
      thicknessMapTransform: { value: new Xt() },
      attenuationDistance: { value: 0 },
      attenuationColor: { value: new zt(0) },
      specularColor: { value: new zt(1, 1, 1) },
      specularColorMap: { value: null },
      specularColorMapTransform: { value: new Xt() },
      specularIntensity: { value: 1 },
      specularIntensityMap: { value: null },
      specularIntensityMapTransform: { value: new Xt() },
      anisotropyVector: { value: new ct() },
      anisotropyMap: { value: null },
      anisotropyMapTransform: { value: new Xt() },
    },
  ]),
  vertexShader: qt.meshphysical_vert,
  fragmentShader: qt.meshphysical_frag,
};
const Is = { r: 0, b: 0, g: 0 },
  Gn = new Ge(),
  Pp = new oe();
function Lp(i, t, e, n, s, r) {
  const a = new zt(0);
  let o = s === !0 ? 0 : 1,
    l,
    c,
    h = null,
    f = 0,
    u = null;
  function p(E) {
    let y = E.isScene === !0 ? E.background : null;
    if (y && y.isTexture) {
      const S = E.backgroundBlurriness > 0;
      y = t.get(y, S);
    }
    return y;
  }
  function g(E) {
    let y = !1;
    const S = p(E);
    S === null ? m(a, o) : S && S.isColor && (m(S, 1), (y = !0));
    const R = i.xr.getEnvironmentBlendMode();
    (R === 'additive'
      ? e.buffers.color.setClear(0, 0, 0, 1, r)
      : R === 'alpha-blend' && e.buffers.color.setClear(0, 0, 0, 0, r),
      (i.autoClear || y) &&
        (e.buffers.depth.setTest(!0),
        e.buffers.depth.setMask(!0),
        e.buffers.color.setMask(!0),
        i.clear(i.autoClearColor, i.autoClearDepth, i.autoClearStencil)));
  }
  function M(E, y) {
    const S = p(y);
    S && (S.isCubeTexture || S.mapping === Js)
      ? (c === void 0 &&
          ((c = new En(
            new ts(1, 1, 1),
            new on({
              name: 'BackgroundCubeMaterial',
              uniforms: wi(tn.backgroundCube.uniforms),
              vertexShader: tn.backgroundCube.vertexShader,
              fragmentShader: tn.backgroundCube.fragmentShader,
              side: Pe,
              depthTest: !1,
              depthWrite: !1,
              fog: !1,
              allowOverride: !1,
            })
          )),
          c.geometry.deleteAttribute('normal'),
          c.geometry.deleteAttribute('uv'),
          (c.onBeforeRender = function (R, w, P) {
            this.matrixWorld.copyPosition(P.matrixWorld);
          }),
          Object.defineProperty(c.material, 'envMap', {
            get: function () {
              return this.uniforms.envMap.value;
            },
          }),
          n.update(c)),
        Gn.copy(y.backgroundRotation),
        (Gn.x *= -1),
        (Gn.y *= -1),
        (Gn.z *= -1),
        S.isCubeTexture && S.isRenderTargetTexture === !1 && ((Gn.y *= -1), (Gn.z *= -1)),
        (c.material.uniforms.envMap.value = S),
        (c.material.uniforms.flipEnvMap.value =
          S.isCubeTexture && S.isRenderTargetTexture === !1 ? -1 : 1),
        (c.material.uniforms.backgroundBlurriness.value = y.backgroundBlurriness),
        (c.material.uniforms.backgroundIntensity.value = y.backgroundIntensity),
        c.material.uniforms.backgroundRotation.value.setFromMatrix4(Pp.makeRotationFromEuler(Gn)),
        (c.material.toneMapped = $t.getTransfer(S.colorSpace) !== te),
        (h !== S || f !== S.version || u !== i.toneMapping) &&
          ((c.material.needsUpdate = !0), (h = S), (f = S.version), (u = i.toneMapping)),
        c.layers.enableAll(),
        E.unshift(c, c.geometry, c.material, 0, 0, null))
      : S &&
        S.isTexture &&
        (l === void 0 &&
          ((l = new En(
            new js(2, 2),
            new on({
              name: 'BackgroundMaterial',
              uniforms: wi(tn.background.uniforms),
              vertexShader: tn.background.vertexShader,
              fragmentShader: tn.background.fragmentShader,
              side: Un,
              depthTest: !1,
              depthWrite: !1,
              fog: !1,
              allowOverride: !1,
            })
          )),
          l.geometry.deleteAttribute('normal'),
          Object.defineProperty(l.material, 'map', {
            get: function () {
              return this.uniforms.t2D.value;
            },
          }),
          n.update(l)),
        (l.material.uniforms.t2D.value = S),
        (l.material.uniforms.backgroundIntensity.value = y.backgroundIntensity),
        (l.material.toneMapped = $t.getTransfer(S.colorSpace) !== te),
        S.matrixAutoUpdate === !0 && S.updateMatrix(),
        l.material.uniforms.uvTransform.value.copy(S.matrix),
        (h !== S || f !== S.version || u !== i.toneMapping) &&
          ((l.material.needsUpdate = !0), (h = S), (f = S.version), (u = i.toneMapping)),
        l.layers.enableAll(),
        E.unshift(l, l.geometry, l.material, 0, 0, null));
  }
  function m(E, y) {
    (E.getRGB(Is, cc(i)), e.buffers.color.setClear(Is.r, Is.g, Is.b, y, r));
  }
  function d() {
    (c !== void 0 && (c.geometry.dispose(), c.material.dispose(), (c = void 0)),
      l !== void 0 && (l.geometry.dispose(), l.material.dispose(), (l = void 0)));
  }
  return {
    getClearColor: function () {
      return a;
    },
    setClearColor: function (E, y = 1) {
      (a.set(E), (o = y), m(a, o));
    },
    getClearAlpha: function () {
      return o;
    },
    setClearAlpha: function (E) {
      ((o = E), m(a, o));
    },
    render: g,
    addToRenderList: M,
    dispose: d,
  };
}
function Dp(i, t) {
  const e = i.getParameter(i.MAX_VERTEX_ATTRIBS),
    n = {},
    s = u(null);
  let r = s,
    a = !1;
  function o(C, N, z, k, F) {
    let O = !1;
    const B = f(C, k, z, N);
    (r !== B && ((r = B), c(r.object)),
      (O = p(C, k, z, F)),
      O && g(C, k, z, F),
      F !== null && t.update(F, i.ELEMENT_ARRAY_BUFFER),
      (O || a) &&
        ((a = !1),
        S(C, N, z, k),
        F !== null && i.bindBuffer(i.ELEMENT_ARRAY_BUFFER, t.get(F).buffer)));
  }
  function l() {
    return i.createVertexArray();
  }
  function c(C) {
    return i.bindVertexArray(C);
  }
  function h(C) {
    return i.deleteVertexArray(C);
  }
  function f(C, N, z, k) {
    const F = k.wireframe === !0;
    let O = n[N.id];
    O === void 0 && ((O = {}), (n[N.id] = O));
    const B = C.isInstancedMesh === !0 ? C.id : 0;
    let nt = O[B];
    nt === void 0 && ((nt = {}), (O[B] = nt));
    let j = nt[z.id];
    j === void 0 && ((j = {}), (nt[z.id] = j));
    let mt = j[F];
    return (mt === void 0 && ((mt = u(l())), (j[F] = mt)), mt);
  }
  function u(C) {
    const N = [],
      z = [],
      k = [];
    for (let F = 0; F < e; F++) ((N[F] = 0), (z[F] = 0), (k[F] = 0));
    return {
      geometry: null,
      program: null,
      wireframe: !1,
      newAttributes: N,
      enabledAttributes: z,
      attributeDivisors: k,
      object: C,
      attributes: {},
      index: null,
    };
  }
  function p(C, N, z, k) {
    const F = r.attributes,
      O = N.attributes;
    let B = 0;
    const nt = z.getAttributes();
    for (const j in nt)
      if (nt[j].location >= 0) {
        const _t = F[j];
        let gt = O[j];
        if (
          (gt === void 0 &&
            (j === 'instanceMatrix' && C.instanceMatrix && (gt = C.instanceMatrix),
            j === 'instanceColor' && C.instanceColor && (gt = C.instanceColor)),
          _t === void 0 || _t.attribute !== gt || (gt && _t.data !== gt.data))
        )
          return !0;
        B++;
      }
    return r.attributesNum !== B || r.index !== k;
  }
  function g(C, N, z, k) {
    const F = {},
      O = N.attributes;
    let B = 0;
    const nt = z.getAttributes();
    for (const j in nt)
      if (nt[j].location >= 0) {
        let _t = O[j];
        _t === void 0 &&
          (j === 'instanceMatrix' && C.instanceMatrix && (_t = C.instanceMatrix),
          j === 'instanceColor' && C.instanceColor && (_t = C.instanceColor));
        const gt = {};
        ((gt.attribute = _t), _t && _t.data && (gt.data = _t.data), (F[j] = gt), B++);
      }
    ((r.attributes = F), (r.attributesNum = B), (r.index = k));
  }
  function M() {
    const C = r.newAttributes;
    for (let N = 0, z = C.length; N < z; N++) C[N] = 0;
  }
  function m(C) {
    d(C, 0);
  }
  function d(C, N) {
    const z = r.newAttributes,
      k = r.enabledAttributes,
      F = r.attributeDivisors;
    ((z[C] = 1),
      k[C] === 0 && (i.enableVertexAttribArray(C), (k[C] = 1)),
      F[C] !== N && (i.vertexAttribDivisor(C, N), (F[C] = N)));
  }
  function E() {
    const C = r.newAttributes,
      N = r.enabledAttributes;
    for (let z = 0, k = N.length; z < k; z++)
      N[z] !== C[z] && (i.disableVertexAttribArray(z), (N[z] = 0));
  }
  function y(C, N, z, k, F, O, B) {
    B === !0 ? i.vertexAttribIPointer(C, N, z, F, O) : i.vertexAttribPointer(C, N, z, k, F, O);
  }
  function S(C, N, z, k) {
    M();
    const F = k.attributes,
      O = z.getAttributes(),
      B = N.defaultAttributeValues;
    for (const nt in O) {
      const j = O[nt];
      if (j.location >= 0) {
        let mt = F[nt];
        if (
          (mt === void 0 &&
            (nt === 'instanceMatrix' && C.instanceMatrix && (mt = C.instanceMatrix),
            nt === 'instanceColor' && C.instanceColor && (mt = C.instanceColor)),
          mt !== void 0)
        ) {
          const _t = mt.normalized,
            gt = mt.itemSize,
            Ot = t.get(mt);
          if (Ot === void 0) continue;
          const jt = Ot.buffer,
            ne = Ot.type,
            Z = Ot.bytesPerElement,
            rt = ne === i.INT || ne === i.UNSIGNED_INT || mt.gpuType === za;
          if (mt.isInterleavedBufferAttribute) {
            const at = mt.data,
              It = at.stride,
              Lt = mt.offset;
            if (at.isInstancedInterleavedBuffer) {
              for (let Vt = 0; Vt < j.locationSize; Vt++) d(j.location + Vt, at.meshPerAttribute);
              C.isInstancedMesh !== !0 &&
                k._maxInstanceCount === void 0 &&
                (k._maxInstanceCount = at.meshPerAttribute * at.count);
            } else for (let Vt = 0; Vt < j.locationSize; Vt++) m(j.location + Vt);
            i.bindBuffer(i.ARRAY_BUFFER, jt);
            for (let Vt = 0; Vt < j.locationSize; Vt++)
              y(
                j.location + Vt,
                gt / j.locationSize,
                ne,
                _t,
                It * Z,
                (Lt + (gt / j.locationSize) * Vt) * Z,
                rt
              );
          } else {
            if (mt.isInstancedBufferAttribute) {
              for (let at = 0; at < j.locationSize; at++) d(j.location + at, mt.meshPerAttribute);
              C.isInstancedMesh !== !0 &&
                k._maxInstanceCount === void 0 &&
                (k._maxInstanceCount = mt.meshPerAttribute * mt.count);
            } else for (let at = 0; at < j.locationSize; at++) m(j.location + at);
            i.bindBuffer(i.ARRAY_BUFFER, jt);
            for (let at = 0; at < j.locationSize; at++)
              y(
                j.location + at,
                gt / j.locationSize,
                ne,
                _t,
                gt * Z,
                (gt / j.locationSize) * at * Z,
                rt
              );
          }
        } else if (B !== void 0) {
          const _t = B[nt];
          if (_t !== void 0)
            switch (_t.length) {
              case 2:
                i.vertexAttrib2fv(j.location, _t);
                break;
              case 3:
                i.vertexAttrib3fv(j.location, _t);
                break;
              case 4:
                i.vertexAttrib4fv(j.location, _t);
                break;
              default:
                i.vertexAttrib1fv(j.location, _t);
            }
        }
      }
    }
    E();
  }
  function R() {
    b();
    for (const C in n) {
      const N = n[C];
      for (const z in N) {
        const k = N[z];
        for (const F in k) {
          const O = k[F];
          for (const B in O) (h(O[B].object), delete O[B]);
          delete k[F];
        }
      }
      delete n[C];
    }
  }
  function w(C) {
    if (n[C.id] === void 0) return;
    const N = n[C.id];
    for (const z in N) {
      const k = N[z];
      for (const F in k) {
        const O = k[F];
        for (const B in O) (h(O[B].object), delete O[B]);
        delete k[F];
      }
    }
    delete n[C.id];
  }
  function P(C) {
    for (const N in n) {
      const z = n[N];
      for (const k in z) {
        const F = z[k];
        if (F[C.id] === void 0) continue;
        const O = F[C.id];
        for (const B in O) (h(O[B].object), delete O[B]);
        delete F[C.id];
      }
    }
  }
  function x(C) {
    for (const N in n) {
      const z = n[N],
        k = C.isInstancedMesh === !0 ? C.id : 0,
        F = z[k];
      if (F !== void 0) {
        for (const O in F) {
          const B = F[O];
          for (const nt in B) (h(B[nt].object), delete B[nt]);
          delete F[O];
        }
        (delete z[k], Object.keys(z).length === 0 && delete n[N]);
      }
    }
  }
  function b() {
    (H(), (a = !0), r !== s && ((r = s), c(r.object)));
  }
  function H() {
    ((s.geometry = null), (s.program = null), (s.wireframe = !1));
  }
  return {
    setup: o,
    reset: b,
    resetDefaultState: H,
    dispose: R,
    releaseStatesOfGeometry: w,
    releaseStatesOfObject: x,
    releaseStatesOfProgram: P,
    initAttributes: M,
    enableAttribute: m,
    disableUnusedAttributes: E,
  };
}
function Ip(i, t, e) {
  let n;
  function s(c) {
    n = c;
  }
  function r(c, h) {
    (i.drawArrays(n, c, h), e.update(h, n, 1));
  }
  function a(c, h, f) {
    f !== 0 && (i.drawArraysInstanced(n, c, h, f), e.update(h, n, f));
  }
  function o(c, h, f) {
    if (f === 0) return;
    t.get('WEBGL_multi_draw').multiDrawArraysWEBGL(n, c, 0, h, 0, f);
    let p = 0;
    for (let g = 0; g < f; g++) p += h[g];
    e.update(p, n, 1);
  }
  function l(c, h, f, u) {
    if (f === 0) return;
    const p = t.get('WEBGL_multi_draw');
    if (p === null) for (let g = 0; g < c.length; g++) a(c[g], h[g], u[g]);
    else {
      p.multiDrawArraysInstancedWEBGL(n, c, 0, h, 0, u, 0, f);
      let g = 0;
      for (let M = 0; M < f; M++) g += h[M] * u[M];
      e.update(g, n, 1);
    }
  }
  ((this.setMode = s),
    (this.render = r),
    (this.renderInstances = a),
    (this.renderMultiDraw = o),
    (this.renderMultiDrawInstances = l));
}
function Up(i, t, e, n) {
  let s;
  function r() {
    if (s !== void 0) return s;
    if (t.has('EXT_texture_filter_anisotropic') === !0) {
      const P = t.get('EXT_texture_filter_anisotropic');
      s = i.getParameter(P.MAX_TEXTURE_MAX_ANISOTROPY_EXT);
    } else s = 0;
    return s;
  }
  function a(P) {
    return !(P !== Ye && n.convert(P) !== i.getParameter(i.IMPLEMENTATION_COLOR_READ_FORMAT));
  }
  function o(P) {
    const x = P === Sn && (t.has('EXT_color_buffer_half_float') || t.has('EXT_color_buffer_float'));
    return !(
      P !== Oe &&
      n.convert(P) !== i.getParameter(i.IMPLEMENTATION_COLOR_READ_TYPE) &&
      P !== en &&
      !x
    );
  }
  function l(P) {
    if (P === 'highp') {
      if (
        i.getShaderPrecisionFormat(i.VERTEX_SHADER, i.HIGH_FLOAT).precision > 0 &&
        i.getShaderPrecisionFormat(i.FRAGMENT_SHADER, i.HIGH_FLOAT).precision > 0
      )
        return 'highp';
      P = 'mediump';
    }
    return P === 'mediump' &&
      i.getShaderPrecisionFormat(i.VERTEX_SHADER, i.MEDIUM_FLOAT).precision > 0 &&
      i.getShaderPrecisionFormat(i.FRAGMENT_SHADER, i.MEDIUM_FLOAT).precision > 0
      ? 'mediump'
      : 'lowp';
  }
  let c = e.precision !== void 0 ? e.precision : 'highp';
  const h = l(c);
  h !== c && (Ft('WebGLRenderer:', c, 'not supported, using', h, 'instead.'), (c = h));
  const f = e.logarithmicDepthBuffer === !0,
    u = e.reversedDepthBuffer === !0 && t.has('EXT_clip_control'),
    p = i.getParameter(i.MAX_TEXTURE_IMAGE_UNITS),
    g = i.getParameter(i.MAX_VERTEX_TEXTURE_IMAGE_UNITS),
    M = i.getParameter(i.MAX_TEXTURE_SIZE),
    m = i.getParameter(i.MAX_CUBE_MAP_TEXTURE_SIZE),
    d = i.getParameter(i.MAX_VERTEX_ATTRIBS),
    E = i.getParameter(i.MAX_VERTEX_UNIFORM_VECTORS),
    y = i.getParameter(i.MAX_VARYING_VECTORS),
    S = i.getParameter(i.MAX_FRAGMENT_UNIFORM_VECTORS),
    R = i.getParameter(i.MAX_SAMPLES),
    w = i.getParameter(i.SAMPLES);
  return {
    isWebGL2: !0,
    getMaxAnisotropy: r,
    getMaxPrecision: l,
    textureFormatReadable: a,
    textureTypeReadable: o,
    precision: c,
    logarithmicDepthBuffer: f,
    reversedDepthBuffer: u,
    maxTextures: p,
    maxVertexTextures: g,
    maxTextureSize: M,
    maxCubemapSize: m,
    maxAttributes: d,
    maxVertexUniforms: E,
    maxVaryings: y,
    maxFragmentUniforms: S,
    maxSamples: R,
    samples: w,
  };
}
function Np(i) {
  const t = this;
  let e = null,
    n = 0,
    s = !1,
    r = !1;
  const a = new kn(),
    o = new Xt(),
    l = { value: null, needsUpdate: !1 };
  ((this.uniform = l),
    (this.numPlanes = 0),
    (this.numIntersection = 0),
    (this.init = function (f, u) {
      const p = f.length !== 0 || u || n !== 0 || s;
      return ((s = u), (n = f.length), p);
    }),
    (this.beginShadows = function () {
      ((r = !0), h(null));
    }),
    (this.endShadows = function () {
      r = !1;
    }),
    (this.setGlobalState = function (f, u) {
      e = h(f, u, 0);
    }),
    (this.setState = function (f, u, p) {
      const g = f.clippingPlanes,
        M = f.clipIntersection,
        m = f.clipShadows,
        d = i.get(f);
      if (!s || g === null || g.length === 0 || (r && !m)) r ? h(null) : c();
      else {
        const E = r ? 0 : n,
          y = E * 4;
        let S = d.clippingState || null;
        ((l.value = S), (S = h(g, u, y, p)));
        for (let R = 0; R !== y; ++R) S[R] = e[R];
        ((d.clippingState = S),
          (this.numIntersection = M ? this.numPlanes : 0),
          (this.numPlanes += E));
      }
    }));
  function c() {
    (l.value !== e && ((l.value = e), (l.needsUpdate = n > 0)),
      (t.numPlanes = n),
      (t.numIntersection = 0));
  }
  function h(f, u, p, g) {
    const M = f !== null ? f.length : 0;
    let m = null;
    if (M !== 0) {
      if (((m = l.value), g !== !0 || m === null)) {
        const d = p + M * 4,
          E = u.matrixWorldInverse;
        (o.getNormalMatrix(E), (m === null || m.length < d) && (m = new Float32Array(d)));
        for (let y = 0, S = p; y !== M; ++y, S += 4)
          (a.copy(f[y]).applyMatrix4(E, o), a.normal.toArray(m, S), (m[S + 3] = a.constant));
      }
      ((l.value = m), (l.needsUpdate = !0));
    }
    return ((t.numPlanes = M), (t.numIntersection = 0), m);
  }
}
const In = 4,
  Qo = [0.125, 0.215, 0.35, 0.446, 0.526, 0.582],
  Xn = 20,
  Fp = 256,
  Ni = new to(),
  tl = new zt();
let Nr = null,
  Fr = 0,
  Or = 0,
  Br = !1;
const Op = new L();
class el {
  constructor(t) {
    ((this._renderer = t),
      (this._pingPongRenderTarget = null),
      (this._lodMax = 0),
      (this._cubeSize = 0),
      (this._sizeLods = []),
      (this._sigmas = []),
      (this._lodMeshes = []),
      (this._backgroundBox = null),
      (this._cubemapMaterial = null),
      (this._equirectMaterial = null),
      (this._blurMaterial = null),
      (this._ggxMaterial = null));
  }
  fromScene(t, e = 0, n = 0.1, s = 100, r = {}) {
    const { size: a = 256, position: o = Op } = r;
    ((Nr = this._renderer.getRenderTarget()),
      (Fr = this._renderer.getActiveCubeFace()),
      (Or = this._renderer.getActiveMipmapLevel()),
      (Br = this._renderer.xr.enabled),
      (this._renderer.xr.enabled = !1),
      this._setSize(a));
    const l = this._allocateTargets();
    return (
      (l.depthBuffer = !0),
      this._sceneToCubeUV(t, n, s, l, o),
      e > 0 && this._blur(l, 0, 0, e),
      this._applyPMREM(l),
      this._cleanup(l),
      l
    );
  }
  fromEquirectangular(t, e = null) {
    return this._fromTexture(t, e);
  }
  fromCubemap(t, e = null) {
    return this._fromTexture(t, e);
  }
  compileCubemapShader() {
    this._cubemapMaterial === null &&
      ((this._cubemapMaterial = sl()), this._compileMaterial(this._cubemapMaterial));
  }
  compileEquirectangularShader() {
    this._equirectMaterial === null &&
      ((this._equirectMaterial = il()), this._compileMaterial(this._equirectMaterial));
  }
  dispose() {
    (this._dispose(),
      this._cubemapMaterial !== null && this._cubemapMaterial.dispose(),
      this._equirectMaterial !== null && this._equirectMaterial.dispose(),
      this._backgroundBox !== null &&
        (this._backgroundBox.geometry.dispose(), this._backgroundBox.material.dispose()));
  }
  _setSize(t) {
    ((this._lodMax = Math.floor(Math.log2(t))), (this._cubeSize = Math.pow(2, this._lodMax)));
  }
  _dispose() {
    (this._blurMaterial !== null && this._blurMaterial.dispose(),
      this._ggxMaterial !== null && this._ggxMaterial.dispose(),
      this._pingPongRenderTarget !== null && this._pingPongRenderTarget.dispose());
    for (let t = 0; t < this._lodMeshes.length; t++) this._lodMeshes[t].geometry.dispose();
  }
  _cleanup(t) {
    (this._renderer.setRenderTarget(Nr, Fr, Or),
      (this._renderer.xr.enabled = Br),
      (t.scissorTest = !1),
      xi(t, 0, 0, t.width, t.height));
  }
  _fromTexture(t, e) {
    (t.mapping === Jn || t.mapping === yi
      ? this._setSize(t.image.length === 0 ? 16 : t.image[0].width || t.image[0].image.width)
      : this._setSize(t.image.width / 4),
      (Nr = this._renderer.getRenderTarget()),
      (Fr = this._renderer.getActiveCubeFace()),
      (Or = this._renderer.getActiveMipmapLevel()),
      (Br = this._renderer.xr.enabled),
      (this._renderer.xr.enabled = !1));
    const n = e || this._allocateTargets();
    return (this._textureToCubeUV(t, n), this._applyPMREM(n), this._cleanup(n), n);
  }
  _allocateTargets() {
    const t = 3 * Math.max(this._cubeSize, 112),
      e = 4 * this._cubeSize,
      n = {
        magFilter: Ae,
        minFilter: Ae,
        generateMipmaps: !1,
        type: Sn,
        format: Ye,
        colorSpace: bi,
        depthBuffer: !1,
      },
      s = nl(t, e, n);
    if (
      this._pingPongRenderTarget === null ||
      this._pingPongRenderTarget.width !== t ||
      this._pingPongRenderTarget.height !== e
    ) {
      (this._pingPongRenderTarget !== null && this._dispose(),
        (this._pingPongRenderTarget = nl(t, e, n)));
      const { _lodMax: r } = this;
      (({ lodMeshes: this._lodMeshes, sizeLods: this._sizeLods, sigmas: this._sigmas } = Bp(r)),
        (this._blurMaterial = Vp(r, t, e)),
        (this._ggxMaterial = zp(r, t, e)));
    }
    return s;
  }
  _compileMaterial(t) {
    const e = new En(new xe(), t);
    this._renderer.compile(e, Ni);
  }
  _sceneToCubeUV(t, e, n, s, r) {
    const l = new Fe(90, 1, e, n),
      c = [1, -1, 1, 1, 1, 1],
      h = [1, 1, 1, -1, -1, -1],
      f = this._renderer,
      u = f.autoClear,
      p = f.toneMapping;
    (f.getClearColor(tl),
      (f.toneMapping = nn),
      (f.autoClear = !1),
      f.state.buffers.depth.getReversed() &&
        (f.setRenderTarget(s), f.clearDepth(), f.setRenderTarget(null)),
      this._backgroundBox === null &&
        (this._backgroundBox = new En(
          new ts(),
          new kl({ name: 'PMREM.Background', side: Pe, depthWrite: !1, depthTest: !1 })
        )));
    const M = this._backgroundBox,
      m = M.material;
    let d = !1;
    const E = t.background;
    E
      ? E.isColor && (m.color.copy(E), (t.background = null), (d = !0))
      : (m.color.copy(tl), (d = !0));
    for (let y = 0; y < 6; y++) {
      const S = y % 3;
      S === 0
        ? (l.up.set(0, c[y], 0), l.position.set(r.x, r.y, r.z), l.lookAt(r.x + h[y], r.y, r.z))
        : S === 1
          ? (l.up.set(0, 0, c[y]), l.position.set(r.x, r.y, r.z), l.lookAt(r.x, r.y + h[y], r.z))
          : (l.up.set(0, c[y], 0), l.position.set(r.x, r.y, r.z), l.lookAt(r.x, r.y, r.z + h[y]));
      const R = this._cubeSize;
      (xi(s, S * R, y > 2 ? R : 0, R, R),
        f.setRenderTarget(s),
        d && f.render(M, l),
        f.render(t, l));
    }
    ((f.toneMapping = p), (f.autoClear = u), (t.background = E));
  }
  _textureToCubeUV(t, e) {
    const n = this._renderer,
      s = t.mapping === Jn || t.mapping === yi;
    s
      ? (this._cubemapMaterial === null && (this._cubemapMaterial = sl()),
        (this._cubemapMaterial.uniforms.flipEnvMap.value = t.isRenderTargetTexture === !1 ? -1 : 1))
      : this._equirectMaterial === null && (this._equirectMaterial = il());
    const r = s ? this._cubemapMaterial : this._equirectMaterial,
      a = this._lodMeshes[0];
    a.material = r;
    const o = r.uniforms;
    o.envMap.value = t;
    const l = this._cubeSize;
    (xi(e, 0, 0, 3 * l, 2 * l), n.setRenderTarget(e), n.render(a, Ni));
  }
  _applyPMREM(t) {
    const e = this._renderer,
      n = e.autoClear;
    e.autoClear = !1;
    const s = this._lodMeshes.length;
    for (let r = 1; r < s; r++) this._applyGGXFilter(t, r - 1, r);
    e.autoClear = n;
  }
  _applyGGXFilter(t, e, n) {
    const s = this._renderer,
      r = this._pingPongRenderTarget,
      a = this._ggxMaterial,
      o = this._lodMeshes[n];
    o.material = a;
    const l = a.uniforms,
      c = n / (this._lodMeshes.length - 1),
      h = e / (this._lodMeshes.length - 1),
      f = Math.sqrt(c * c - h * h),
      u = 0 + c * 1.25,
      p = f * u,
      { _lodMax: g } = this,
      M = this._sizeLods[n],
      m = 3 * M * (n > g - In ? n - g + In : 0),
      d = 4 * (this._cubeSize - M);
    ((l.envMap.value = t.texture),
      (l.roughness.value = p),
      (l.mipInt.value = g - e),
      xi(r, m, d, 3 * M, 2 * M),
      s.setRenderTarget(r),
      s.render(o, Ni),
      (l.envMap.value = r.texture),
      (l.roughness.value = 0),
      (l.mipInt.value = g - n),
      xi(t, m, d, 3 * M, 2 * M),
      s.setRenderTarget(t),
      s.render(o, Ni));
  }
  _blur(t, e, n, s, r) {
    const a = this._pingPongRenderTarget;
    (this._halfBlur(t, a, e, n, s, 'latitudinal', r),
      this._halfBlur(a, t, n, n, s, 'longitudinal', r));
  }
  _halfBlur(t, e, n, s, r, a, o) {
    const l = this._renderer,
      c = this._blurMaterial;
    a !== 'latitudinal' &&
      a !== 'longitudinal' &&
      Jt('blur direction must be either latitudinal or longitudinal!');
    const h = 3,
      f = this._lodMeshes[s];
    f.material = c;
    const u = c.uniforms,
      p = this._sizeLods[n] - 1,
      g = isFinite(r) ? Math.PI / (2 * p) : (2 * Math.PI) / (2 * Xn - 1),
      M = r / g,
      m = isFinite(r) ? 1 + Math.floor(h * M) : Xn;
    m > Xn &&
      Ft(
        `sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${Xn}`
      );
    const d = [];
    let E = 0;
    for (let P = 0; P < Xn; ++P) {
      const x = P / M,
        b = Math.exp((-x * x) / 2);
      (d.push(b), P === 0 ? (E += b) : P < m && (E += 2 * b));
    }
    for (let P = 0; P < d.length; P++) d[P] = d[P] / E;
    ((u.envMap.value = t.texture),
      (u.samples.value = m),
      (u.weights.value = d),
      (u.latitudinal.value = a === 'latitudinal'),
      o && (u.poleAxis.value = o));
    const { _lodMax: y } = this;
    ((u.dTheta.value = g), (u.mipInt.value = y - n));
    const S = this._sizeLods[s],
      R = 3 * S * (s > y - In ? s - y + In : 0),
      w = 4 * (this._cubeSize - S);
    (xi(e, R, w, 3 * S, 2 * S), l.setRenderTarget(e), l.render(f, Ni));
  }
}
function Bp(i) {
  const t = [],
    e = [],
    n = [];
  let s = i;
  const r = i - In + 1 + Qo.length;
  for (let a = 0; a < r; a++) {
    const o = Math.pow(2, s);
    t.push(o);
    let l = 1 / o;
    (a > i - In ? (l = Qo[a - i + In - 1]) : a === 0 && (l = 0), e.push(l));
    const c = 1 / (o - 2),
      h = -c,
      f = 1 + c,
      u = [h, h, f, h, f, f, h, h, f, f, h, f],
      p = 6,
      g = 6,
      M = 3,
      m = 2,
      d = 1,
      E = new Float32Array(M * g * p),
      y = new Float32Array(m * g * p),
      S = new Float32Array(d * g * p);
    for (let w = 0; w < p; w++) {
      const P = ((w % 3) * 2) / 3 - 1,
        x = w > 2 ? 0 : -1,
        b = [
          P,
          x,
          0,
          P + 2 / 3,
          x,
          0,
          P + 2 / 3,
          x + 1,
          0,
          P,
          x,
          0,
          P + 2 / 3,
          x + 1,
          0,
          P,
          x + 1,
          0,
        ];
      (E.set(b, M * g * w), y.set(u, m * g * w));
      const H = [w, w, w, w, w, w];
      S.set(H, d * g * w);
    }
    const R = new xe();
    (R.setAttribute('position', new Be(E, M)),
      R.setAttribute('uv', new Be(y, m)),
      R.setAttribute('faceIndex', new Be(S, d)),
      n.push(new En(R, null)),
      s > In && s--);
  }
  return { lodMeshes: n, sizeLods: t, sigmas: e };
}
function nl(i, t, e) {
  const n = new rn(i, t, e);
  return ((n.texture.mapping = Js), (n.texture.name = 'PMREM.cubeUv'), (n.scissorTest = !0), n);
}
function xi(i, t, e, n, s) {
  (i.viewport.set(t, e, n, s), i.scissor.set(t, e, n, s));
}
function zp(i, t, e) {
  return new on({
    name: 'PMREMGGXConvolution',
    defines: {
      GGX_SAMPLES: Fp,
      CUBEUV_TEXEL_WIDTH: 1 / t,
      CUBEUV_TEXEL_HEIGHT: 1 / e,
      CUBEUV_MAX_MIP: `${i}.0`,
    },
    uniforms: { envMap: { value: null }, roughness: { value: 0 }, mipInt: { value: 0 } },
    vertexShader: Qs(),
    fragmentShader: `

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float roughness;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359

			// Van der Corput radical inverse
			float radicalInverse_VdC(uint bits) {
				bits = (bits << 16u) | (bits >> 16u);
				bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
				bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
				bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
				bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
				return float(bits) * 2.3283064365386963e-10; // / 0x100000000
			}

			// Hammersley sequence
			vec2 hammersley(uint i, uint N) {
				return vec2(float(i) / float(N), radicalInverse_VdC(i));
			}

			// GGX VNDF importance sampling (Eric Heitz 2018)
			// "Sampling the GGX Distribution of Visible Normals"
			// https://jcgt.org/published/0007/04/01/
			vec3 importanceSampleGGX_VNDF(vec2 Xi, vec3 V, float roughness) {
				float alpha = roughness * roughness;

				// Section 4.1: Orthonormal basis
				vec3 T1 = vec3(1.0, 0.0, 0.0);
				vec3 T2 = cross(V, T1);

				// Section 4.2: Parameterization of projected area
				float r = sqrt(Xi.x);
				float phi = 2.0 * PI * Xi.y;
				float t1 = r * cos(phi);
				float t2 = r * sin(phi);
				float s = 0.5 * (1.0 + V.z);
				t2 = (1.0 - s) * sqrt(1.0 - t1 * t1) + s * t2;

				// Section 4.3: Reprojection onto hemisphere
				vec3 Nh = t1 * T1 + t2 * T2 + sqrt(max(0.0, 1.0 - t1 * t1 - t2 * t2)) * V;

				// Section 3.4: Transform back to ellipsoid configuration
				return normalize(vec3(alpha * Nh.x, alpha * Nh.y, max(0.0, Nh.z)));
			}

			void main() {
				vec3 N = normalize(vOutputDirection);
				vec3 V = N; // Assume view direction equals normal for pre-filtering

				vec3 prefilteredColor = vec3(0.0);
				float totalWeight = 0.0;

				// For very low roughness, just sample the environment directly
				if (roughness < 0.001) {
					gl_FragColor = vec4(bilinearCubeUV(envMap, N, mipInt), 1.0);
					return;
				}

				// Tangent space basis for VNDF sampling
				vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
				vec3 tangent = normalize(cross(up, N));
				vec3 bitangent = cross(N, tangent);

				for(uint i = 0u; i < uint(GGX_SAMPLES); i++) {
					vec2 Xi = hammersley(i, uint(GGX_SAMPLES));

					// For PMREM, V = N, so in tangent space V is always (0, 0, 1)
					vec3 H_tangent = importanceSampleGGX_VNDF(Xi, vec3(0.0, 0.0, 1.0), roughness);

					// Transform H back to world space
					vec3 H = normalize(tangent * H_tangent.x + bitangent * H_tangent.y + N * H_tangent.z);
					vec3 L = normalize(2.0 * dot(V, H) * H - V);

					float NdotL = max(dot(N, L), 0.0);

					if(NdotL > 0.0) {
						// Sample environment at fixed mip level
						// VNDF importance sampling handles the distribution filtering
						vec3 sampleColor = bilinearCubeUV(envMap, L, mipInt);

						// Weight by NdotL for the split-sum approximation
						// VNDF PDF naturally accounts for the visible microfacet distribution
						prefilteredColor += sampleColor * NdotL;
						totalWeight += NdotL;
					}
				}

				if (totalWeight > 0.0) {
					prefilteredColor = prefilteredColor / totalWeight;
				}

				gl_FragColor = vec4(prefilteredColor, 1.0);
			}
		`,
    blending: vn,
    depthTest: !1,
    depthWrite: !1,
  });
}
function Vp(i, t, e) {
  const n = new Float32Array(Xn),
    s = new L(0, 1, 0);
  return new on({
    name: 'SphericalGaussianBlur',
    defines: {
      n: Xn,
      CUBEUV_TEXEL_WIDTH: 1 / t,
      CUBEUV_TEXEL_HEIGHT: 1 / e,
      CUBEUV_MAX_MIP: `${i}.0`,
    },
    uniforms: {
      envMap: { value: null },
      samples: { value: 1 },
      weights: { value: n },
      latitudinal: { value: !1 },
      dTheta: { value: 0 },
      mipInt: { value: 0 },
      poleAxis: { value: s },
    },
    vertexShader: Qs(),
    fragmentShader: `

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,
    blending: vn,
    depthTest: !1,
    depthWrite: !1,
  });
}
function il() {
  return new on({
    name: 'EquirectangularToCubeUV',
    uniforms: { envMap: { value: null } },
    vertexShader: Qs(),
    fragmentShader: `

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,
    blending: vn,
    depthTest: !1,
    depthWrite: !1,
  });
}
function sl() {
  return new on({
    name: 'CubemapToCubeUV',
    uniforms: { envMap: { value: null }, flipEnvMap: { value: -1 } },
    vertexShader: Qs(),
    fragmentShader: `

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,
    blending: vn,
    depthTest: !1,
    depthWrite: !1,
  });
}
function Qs() {
  return `

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`;
}
class dc extends rn {
  constructor(t = 1, e = {}) {
    (super(t, t, e), (this.isWebGLCubeRenderTarget = !0));
    const n = { width: t, height: t, depth: 1 },
      s = [n, n, n, n, n, n];
    ((this.texture = new ql(s)),
      this._setTextureOptions(e),
      (this.texture.isRenderTargetTexture = !0));
  }
  fromEquirectangularTexture(t, e) {
    ((this.texture.type = e.type),
      (this.texture.colorSpace = e.colorSpace),
      (this.texture.generateMipmaps = e.generateMipmaps),
      (this.texture.minFilter = e.minFilter),
      (this.texture.magFilter = e.magFilter));
    const n = {
        uniforms: { tEquirect: { value: null } },
        vertexShader: `

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,
        fragmentShader: `

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`,
      },
      s = new ts(5, 5, 5),
      r = new on({
        name: 'CubemapFromEquirect',
        uniforms: wi(n.uniforms),
        vertexShader: n.vertexShader,
        fragmentShader: n.fragmentShader,
        side: Pe,
        blending: vn,
      });
    r.uniforms.tEquirect.value = e;
    const a = new En(s, r),
      o = e.minFilter;
    return (
      e.minFilter === qn && (e.minFilter = Ae),
      new ku(1, 10, this).update(t, a),
      (e.minFilter = o),
      a.geometry.dispose(),
      a.material.dispose(),
      this
    );
  }
  clear(t, e = !0, n = !0, s = !0) {
    const r = t.getRenderTarget();
    for (let a = 0; a < 6; a++) (t.setRenderTarget(this, a), t.clear(e, n, s));
    t.setRenderTarget(r);
  }
}
function Gp(i) {
  let t = new WeakMap(),
    e = new WeakMap(),
    n = null;
  function s(u, p = !1) {
    return u == null ? null : p ? a(u) : r(u);
  }
  function r(u) {
    if (u && u.isTexture) {
      const p = u.mapping;
      if (p === ir || p === sr)
        if (t.has(u)) {
          const g = t.get(u).texture;
          return o(g, u.mapping);
        } else {
          const g = u.image;
          if (g && g.height > 0) {
            const M = new dc(g.height);
            return (
              M.fromEquirectangularTexture(i, u),
              t.set(u, M),
              u.addEventListener('dispose', c),
              o(M.texture, u.mapping)
            );
          } else return null;
        }
    }
    return u;
  }
  function a(u) {
    if (u && u.isTexture) {
      const p = u.mapping,
        g = p === ir || p === sr,
        M = p === Jn || p === yi;
      if (g || M) {
        let m = e.get(u);
        const d = m !== void 0 ? m.texture.pmremVersion : 0;
        if (u.isRenderTargetTexture && u.pmremVersion !== d)
          return (
            n === null && (n = new el(i)),
            (m = g ? n.fromEquirectangular(u, m) : n.fromCubemap(u, m)),
            (m.texture.pmremVersion = u.pmremVersion),
            e.set(u, m),
            m.texture
          );
        if (m !== void 0) return m.texture;
        {
          const E = u.image;
          return (g && E && E.height > 0) || (M && E && l(E))
            ? (n === null && (n = new el(i)),
              (m = g ? n.fromEquirectangular(u) : n.fromCubemap(u)),
              (m.texture.pmremVersion = u.pmremVersion),
              e.set(u, m),
              u.addEventListener('dispose', h),
              m.texture)
            : null;
        }
      }
    }
    return u;
  }
  function o(u, p) {
    return (p === ir ? (u.mapping = Jn) : p === sr && (u.mapping = yi), u);
  }
  function l(u) {
    let p = 0;
    const g = 6;
    for (let M = 0; M < g; M++) u[M] !== void 0 && p++;
    return p === g;
  }
  function c(u) {
    const p = u.target;
    p.removeEventListener('dispose', c);
    const g = t.get(p);
    g !== void 0 && (t.delete(p), g.dispose());
  }
  function h(u) {
    const p = u.target;
    p.removeEventListener('dispose', h);
    const g = e.get(p);
    g !== void 0 && (e.delete(p), g.dispose());
  }
  function f() {
    ((t = new WeakMap()), (e = new WeakMap()), n !== null && (n.dispose(), (n = null)));
  }
  return { get: s, dispose: f };
}
function Hp(i) {
  const t = {};
  function e(n) {
    if (t[n] !== void 0) return t[n];
    const s = i.getExtension(n);
    return ((t[n] = s), s);
  }
  return {
    has: function (n) {
      return e(n) !== null;
    },
    init: function () {
      (e('EXT_color_buffer_float'),
        e('WEBGL_clip_cull_distance'),
        e('OES_texture_float_linear'),
        e('EXT_color_buffer_half_float'),
        e('WEBGL_multisampled_render_to_texture'),
        e('WEBGL_render_shared_exponent'));
    },
    get: function (n) {
      const s = e(n);
      return (s === null && Ws('WebGLRenderer: ' + n + ' extension not supported.'), s);
    },
  };
}
function kp(i, t, e, n) {
  const s = {},
    r = new WeakMap();
  function a(f) {
    const u = f.target;
    u.index !== null && t.remove(u.index);
    for (const g in u.attributes) t.remove(u.attributes[g]);
    (u.removeEventListener('dispose', a), delete s[u.id]);
    const p = r.get(u);
    (p && (t.remove(p), r.delete(u)),
      n.releaseStatesOfGeometry(u),
      u.isInstancedBufferGeometry === !0 && delete u._maxInstanceCount,
      e.memory.geometries--);
  }
  function o(f, u) {
    return (
      s[u.id] === !0 || (u.addEventListener('dispose', a), (s[u.id] = !0), e.memory.geometries++),
      u
    );
  }
  function l(f) {
    const u = f.attributes;
    for (const p in u) t.update(u[p], i.ARRAY_BUFFER);
  }
  function c(f) {
    const u = [],
      p = f.index,
      g = f.attributes.position;
    let M = 0;
    if (g === void 0) return;
    if (p !== null) {
      const E = p.array;
      M = p.version;
      for (let y = 0, S = E.length; y < S; y += 3) {
        const R = E[y + 0],
          w = E[y + 1],
          P = E[y + 2];
        u.push(R, w, w, P, P, R);
      }
    } else {
      const E = g.array;
      M = g.version;
      for (let y = 0, S = E.length / 3 - 1; y < S; y += 3) {
        const R = y + 0,
          w = y + 1,
          P = y + 2;
        u.push(R, w, w, P, P, R);
      }
    }
    const m = new (g.count >= 65535 ? Gl : Vl)(u, 1);
    m.version = M;
    const d = r.get(f);
    (d && t.remove(d), r.set(f, m));
  }
  function h(f) {
    const u = r.get(f);
    if (u) {
      const p = f.index;
      p !== null && u.version < p.version && c(f);
    } else c(f);
    return r.get(f);
  }
  return { get: o, update: l, getWireframeAttribute: h };
}
function Wp(i, t, e) {
  let n;
  function s(u) {
    n = u;
  }
  let r, a;
  function o(u) {
    ((r = u.type), (a = u.bytesPerElement));
  }
  function l(u, p) {
    (i.drawElements(n, p, r, u * a), e.update(p, n, 1));
  }
  function c(u, p, g) {
    g !== 0 && (i.drawElementsInstanced(n, p, r, u * a, g), e.update(p, n, g));
  }
  function h(u, p, g) {
    if (g === 0) return;
    t.get('WEBGL_multi_draw').multiDrawElementsWEBGL(n, p, 0, r, u, 0, g);
    let m = 0;
    for (let d = 0; d < g; d++) m += p[d];
    e.update(m, n, 1);
  }
  function f(u, p, g, M) {
    if (g === 0) return;
    const m = t.get('WEBGL_multi_draw');
    if (m === null) for (let d = 0; d < u.length; d++) c(u[d] / a, p[d], M[d]);
    else {
      m.multiDrawElementsInstancedWEBGL(n, p, 0, r, u, 0, M, 0, g);
      let d = 0;
      for (let E = 0; E < g; E++) d += p[E] * M[E];
      e.update(d, n, 1);
    }
  }
  ((this.setMode = s),
    (this.setIndex = o),
    (this.render = l),
    (this.renderInstances = c),
    (this.renderMultiDraw = h),
    (this.renderMultiDrawInstances = f));
}
function Xp(i) {
  const t = { geometries: 0, textures: 0 },
    e = { frame: 0, calls: 0, triangles: 0, points: 0, lines: 0 };
  function n(r, a, o) {
    switch ((e.calls++, a)) {
      case i.TRIANGLES:
        e.triangles += o * (r / 3);
        break;
      case i.LINES:
        e.lines += o * (r / 2);
        break;
      case i.LINE_STRIP:
        e.lines += o * (r - 1);
        break;
      case i.LINE_LOOP:
        e.lines += o * r;
        break;
      case i.POINTS:
        e.points += o * r;
        break;
      default:
        Jt('WebGLInfo: Unknown draw mode:', a);
        break;
    }
  }
  function s() {
    ((e.calls = 0), (e.triangles = 0), (e.points = 0), (e.lines = 0));
  }
  return { memory: t, render: e, programs: null, autoReset: !0, reset: s, update: n };
}
function qp(i, t, e) {
  const n = new WeakMap(),
    s = new ue();
  function r(a, o, l) {
    const c = a.morphTargetInfluences,
      h = o.morphAttributes.position || o.morphAttributes.normal || o.morphAttributes.color,
      f = h !== void 0 ? h.length : 0;
    let u = n.get(o);
    if (u === void 0 || u.count !== f) {
      let b = function () {
        (P.dispose(), n.delete(o), o.removeEventListener('dispose', b));
      };
      u !== void 0 && u.texture.dispose();
      const p = o.morphAttributes.position !== void 0,
        g = o.morphAttributes.normal !== void 0,
        M = o.morphAttributes.color !== void 0,
        m = o.morphAttributes.position || [],
        d = o.morphAttributes.normal || [],
        E = o.morphAttributes.color || [];
      let y = 0;
      (p === !0 && (y = 1), g === !0 && (y = 2), M === !0 && (y = 3));
      let S = o.attributes.position.count * y,
        R = 1;
      S > t.maxTextureSize && ((R = Math.ceil(S / t.maxTextureSize)), (S = t.maxTextureSize));
      const w = new Float32Array(S * R * 4 * f),
        P = new Bl(w, S, R, f);
      ((P.type = en), (P.needsUpdate = !0));
      const x = y * 4;
      for (let H = 0; H < f; H++) {
        const C = m[H],
          N = d[H],
          z = E[H],
          k = S * R * 4 * H;
        for (let F = 0; F < C.count; F++) {
          const O = F * x;
          (p === !0 &&
            (s.fromBufferAttribute(C, F),
            (w[k + O + 0] = s.x),
            (w[k + O + 1] = s.y),
            (w[k + O + 2] = s.z),
            (w[k + O + 3] = 0)),
            g === !0 &&
              (s.fromBufferAttribute(N, F),
              (w[k + O + 4] = s.x),
              (w[k + O + 5] = s.y),
              (w[k + O + 6] = s.z),
              (w[k + O + 7] = 0)),
            M === !0 &&
              (s.fromBufferAttribute(z, F),
              (w[k + O + 8] = s.x),
              (w[k + O + 9] = s.y),
              (w[k + O + 10] = s.z),
              (w[k + O + 11] = z.itemSize === 4 ? s.w : 1)));
        }
      }
      ((u = { count: f, texture: P, size: new ct(S, R) }),
        n.set(o, u),
        o.addEventListener('dispose', b));
    }
    if (a.isInstancedMesh === !0 && a.morphTexture !== null)
      l.getUniforms().setValue(i, 'morphTexture', a.morphTexture, e);
    else {
      let p = 0;
      for (let M = 0; M < c.length; M++) p += c[M];
      const g = o.morphTargetsRelative ? 1 : 1 - p;
      (l.getUniforms().setValue(i, 'morphTargetBaseInfluence', g),
        l.getUniforms().setValue(i, 'morphTargetInfluences', c));
    }
    (l.getUniforms().setValue(i, 'morphTargetsTexture', u.texture, e),
      l.getUniforms().setValue(i, 'morphTargetsTextureSize', u.size));
  }
  return { update: r };
}
function Yp(i, t, e, n, s) {
  let r = new WeakMap();
  function a(c) {
    const h = s.render.frame,
      f = c.geometry,
      u = t.get(c, f);
    if (
      (r.get(u) !== h && (t.update(u), r.set(u, h)),
      c.isInstancedMesh &&
        (c.hasEventListener('dispose', l) === !1 && c.addEventListener('dispose', l),
        r.get(c) !== h &&
          (e.update(c.instanceMatrix, i.ARRAY_BUFFER),
          c.instanceColor !== null && e.update(c.instanceColor, i.ARRAY_BUFFER),
          r.set(c, h))),
      c.isSkinnedMesh)
    ) {
      const p = c.skeleton;
      r.get(p) !== h && (p.update(), r.set(p, h));
    }
    return u;
  }
  function o() {
    r = new WeakMap();
  }
  function l(c) {
    const h = c.target;
    (h.removeEventListener('dispose', l),
      n.releaseStatesOfObject(h),
      e.remove(h.instanceMatrix),
      h.instanceColor !== null && e.remove(h.instanceColor));
  }
  return { update: a, dispose: o };
}
const Zp = {
  [yl]: 'LINEAR_TONE_MAPPING',
  [El]: 'REINHARD_TONE_MAPPING',
  [bl]: 'CINEON_TONE_MAPPING',
  [Tl]: 'ACES_FILMIC_TONE_MAPPING',
  [wl]: 'AGX_TONE_MAPPING',
  [Rl]: 'NEUTRAL_TONE_MAPPING',
  [Al]: 'CUSTOM_TONE_MAPPING',
};
function Jp(i, t, e, n, s) {
  const r = new rn(t, e, { type: i, depthBuffer: n, stencilBuffer: s }),
    a = new rn(t, e, { type: Sn, depthBuffer: !1, stencilBuffer: !1 }),
    o = new xe();
  (o.setAttribute('position', new ee([-1, 3, 0, -1, -1, 0, 3, -1, 0], 3)),
    o.setAttribute('uv', new ee([0, 2, 0, 0, 2, 0], 2)));
  const l = new Du({
      uniforms: { tDiffuse: { value: null } },
      vertexShader: `
			precision highp float;

			uniform mat4 modelViewMatrix;
			uniform mat4 projectionMatrix;

			attribute vec3 position;
			attribute vec2 uv;

			varying vec2 vUv;

			void main() {
				vUv = uv;
				gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
			}`,
      fragmentShader: `
			precision highp float;

			uniform sampler2D tDiffuse;

			varying vec2 vUv;

			#include <tonemapping_pars_fragment>
			#include <colorspace_pars_fragment>

			void main() {
				gl_FragColor = texture2D( tDiffuse, vUv );

				#ifdef LINEAR_TONE_MAPPING
					gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );
				#elif defined( REINHARD_TONE_MAPPING )
					gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );
				#elif defined( CINEON_TONE_MAPPING )
					gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );
				#elif defined( ACES_FILMIC_TONE_MAPPING )
					gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );
				#elif defined( AGX_TONE_MAPPING )
					gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );
				#elif defined( NEUTRAL_TONE_MAPPING )
					gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );
				#elif defined( CUSTOM_TONE_MAPPING )
					gl_FragColor.rgb = CustomToneMapping( gl_FragColor.rgb );
				#endif

				#ifdef SRGB_TRANSFER
					gl_FragColor = sRGBTransferOETF( gl_FragColor );
				#endif
			}`,
      depthTest: !1,
      depthWrite: !1,
    }),
    c = new En(o, l),
    h = new to(-1, 1, 1, -1, 0, 1);
  let f = null,
    u = null,
    p = !1,
    g,
    M = null,
    m = [],
    d = !1;
  ((this.setSize = function (E, y) {
    (r.setSize(E, y), a.setSize(E, y));
    for (let S = 0; S < m.length; S++) {
      const R = m[S];
      R.setSize && R.setSize(E, y);
    }
  }),
    (this.setEffects = function (E) {
      ((m = E), (d = m.length > 0 && m[0].isRenderPass === !0));
      const y = r.width,
        S = r.height;
      for (let R = 0; R < m.length; R++) {
        const w = m[R];
        w.setSize && w.setSize(y, S);
      }
    }),
    (this.begin = function (E, y) {
      if (p || (E.toneMapping === nn && m.length === 0)) return !1;
      if (((M = y), y !== null)) {
        const S = y.width,
          R = y.height;
        (r.width !== S || r.height !== R) && this.setSize(S, R);
      }
      return (d === !1 && E.setRenderTarget(r), (g = E.toneMapping), (E.toneMapping = nn), !0);
    }),
    (this.hasRenderPass = function () {
      return d;
    }),
    (this.end = function (E, y) {
      ((E.toneMapping = g), (p = !0));
      let S = r,
        R = a;
      for (let w = 0; w < m.length; w++) {
        const P = m[w];
        if (P.enabled !== !1 && (P.render(E, R, S, y), P.needsSwap !== !1)) {
          const x = S;
          ((S = R), (R = x));
        }
      }
      if (f !== E.outputColorSpace || u !== E.toneMapping) {
        ((f = E.outputColorSpace),
          (u = E.toneMapping),
          (l.defines = {}),
          $t.getTransfer(f) === te && (l.defines.SRGB_TRANSFER = ''));
        const w = Zp[u];
        (w && (l.defines[w] = ''), (l.needsUpdate = !0));
      }
      ((l.uniforms.tDiffuse.value = S.texture),
        E.setRenderTarget(M),
        E.render(c, h),
        (M = null),
        (p = !1));
    }),
    (this.isCompositing = function () {
      return p;
    }),
    (this.dispose = function () {
      (r.dispose(), a.dispose(), o.dispose(), l.dispose());
    }));
}
const pc = new ye(),
  Fa = new Zi(1, 1),
  mc = new Bl(),
  gc = new Rh(),
  _c = new ql(),
  rl = [],
  al = [],
  ol = new Float32Array(16),
  ll = new Float32Array(9),
  cl = new Float32Array(4);
function Ci(i, t, e) {
  const n = i[0];
  if (n <= 0 || n > 0) return i;
  const s = t * e;
  let r = rl[s];
  if ((r === void 0 && ((r = new Float32Array(s)), (rl[s] = r)), t !== 0)) {
    n.toArray(r, 0);
    for (let a = 1, o = 0; a !== t; ++a) ((o += e), i[a].toArray(r, o));
  }
  return r;
}
function ge(i, t) {
  if (i.length !== t.length) return !1;
  for (let e = 0, n = i.length; e < n; e++) if (i[e] !== t[e]) return !1;
  return !0;
}
function _e(i, t) {
  for (let e = 0, n = t.length; e < n; e++) i[e] = t[e];
}
function tr(i, t) {
  let e = al[t];
  e === void 0 && ((e = new Int32Array(t)), (al[t] = e));
  for (let n = 0; n !== t; ++n) e[n] = i.allocateTextureUnit();
  return e;
}
function $p(i, t) {
  const e = this.cache;
  e[0] !== t && (i.uniform1f(this.addr, t), (e[0] = t));
}
function Kp(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y) &&
      (i.uniform2f(this.addr, t.x, t.y), (e[0] = t.x), (e[1] = t.y));
  else {
    if (ge(e, t)) return;
    (i.uniform2fv(this.addr, t), _e(e, t));
  }
}
function jp(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y || e[2] !== t.z) &&
      (i.uniform3f(this.addr, t.x, t.y, t.z), (e[0] = t.x), (e[1] = t.y), (e[2] = t.z));
  else if (t.r !== void 0)
    (e[0] !== t.r || e[1] !== t.g || e[2] !== t.b) &&
      (i.uniform3f(this.addr, t.r, t.g, t.b), (e[0] = t.r), (e[1] = t.g), (e[2] = t.b));
  else {
    if (ge(e, t)) return;
    (i.uniform3fv(this.addr, t), _e(e, t));
  }
}
function Qp(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y || e[2] !== t.z || e[3] !== t.w) &&
      (i.uniform4f(this.addr, t.x, t.y, t.z, t.w),
      (e[0] = t.x),
      (e[1] = t.y),
      (e[2] = t.z),
      (e[3] = t.w));
  else {
    if (ge(e, t)) return;
    (i.uniform4fv(this.addr, t), _e(e, t));
  }
}
function tm(i, t) {
  const e = this.cache,
    n = t.elements;
  if (n === void 0) {
    if (ge(e, t)) return;
    (i.uniformMatrix2fv(this.addr, !1, t), _e(e, t));
  } else {
    if (ge(e, n)) return;
    (cl.set(n), i.uniformMatrix2fv(this.addr, !1, cl), _e(e, n));
  }
}
function em(i, t) {
  const e = this.cache,
    n = t.elements;
  if (n === void 0) {
    if (ge(e, t)) return;
    (i.uniformMatrix3fv(this.addr, !1, t), _e(e, t));
  } else {
    if (ge(e, n)) return;
    (ll.set(n), i.uniformMatrix3fv(this.addr, !1, ll), _e(e, n));
  }
}
function nm(i, t) {
  const e = this.cache,
    n = t.elements;
  if (n === void 0) {
    if (ge(e, t)) return;
    (i.uniformMatrix4fv(this.addr, !1, t), _e(e, t));
  } else {
    if (ge(e, n)) return;
    (ol.set(n), i.uniformMatrix4fv(this.addr, !1, ol), _e(e, n));
  }
}
function im(i, t) {
  const e = this.cache;
  e[0] !== t && (i.uniform1i(this.addr, t), (e[0] = t));
}
function sm(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y) &&
      (i.uniform2i(this.addr, t.x, t.y), (e[0] = t.x), (e[1] = t.y));
  else {
    if (ge(e, t)) return;
    (i.uniform2iv(this.addr, t), _e(e, t));
  }
}
function rm(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y || e[2] !== t.z) &&
      (i.uniform3i(this.addr, t.x, t.y, t.z), (e[0] = t.x), (e[1] = t.y), (e[2] = t.z));
  else {
    if (ge(e, t)) return;
    (i.uniform3iv(this.addr, t), _e(e, t));
  }
}
function am(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y || e[2] !== t.z || e[3] !== t.w) &&
      (i.uniform4i(this.addr, t.x, t.y, t.z, t.w),
      (e[0] = t.x),
      (e[1] = t.y),
      (e[2] = t.z),
      (e[3] = t.w));
  else {
    if (ge(e, t)) return;
    (i.uniform4iv(this.addr, t), _e(e, t));
  }
}
function om(i, t) {
  const e = this.cache;
  e[0] !== t && (i.uniform1ui(this.addr, t), (e[0] = t));
}
function lm(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y) &&
      (i.uniform2ui(this.addr, t.x, t.y), (e[0] = t.x), (e[1] = t.y));
  else {
    if (ge(e, t)) return;
    (i.uniform2uiv(this.addr, t), _e(e, t));
  }
}
function cm(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y || e[2] !== t.z) &&
      (i.uniform3ui(this.addr, t.x, t.y, t.z), (e[0] = t.x), (e[1] = t.y), (e[2] = t.z));
  else {
    if (ge(e, t)) return;
    (i.uniform3uiv(this.addr, t), _e(e, t));
  }
}
function hm(i, t) {
  const e = this.cache;
  if (t.x !== void 0)
    (e[0] !== t.x || e[1] !== t.y || e[2] !== t.z || e[3] !== t.w) &&
      (i.uniform4ui(this.addr, t.x, t.y, t.z, t.w),
      (e[0] = t.x),
      (e[1] = t.y),
      (e[2] = t.z),
      (e[3] = t.w));
  else {
    if (ge(e, t)) return;
    (i.uniform4uiv(this.addr, t), _e(e, t));
  }
}
function um(i, t, e) {
  const n = this.cache,
    s = e.allocateTextureUnit();
  n[0] !== s && (i.uniform1i(this.addr, s), (n[0] = s));
  let r;
  (this.type === i.SAMPLER_2D_SHADOW
    ? ((Fa.compareFunction = e.isReversedDepthBuffer() ? qa : Xa), (r = Fa))
    : (r = pc),
    e.setTexture2D(t || r, s));
}
function fm(i, t, e) {
  const n = this.cache,
    s = e.allocateTextureUnit();
  (n[0] !== s && (i.uniform1i(this.addr, s), (n[0] = s)), e.setTexture3D(t || gc, s));
}
function dm(i, t, e) {
  const n = this.cache,
    s = e.allocateTextureUnit();
  (n[0] !== s && (i.uniform1i(this.addr, s), (n[0] = s)), e.setTextureCube(t || _c, s));
}
function pm(i, t, e) {
  const n = this.cache,
    s = e.allocateTextureUnit();
  (n[0] !== s && (i.uniform1i(this.addr, s), (n[0] = s)), e.setTexture2DArray(t || mc, s));
}
function mm(i) {
  switch (i) {
    case 5126:
      return $p;
    case 35664:
      return Kp;
    case 35665:
      return jp;
    case 35666:
      return Qp;
    case 35674:
      return tm;
    case 35675:
      return em;
    case 35676:
      return nm;
    case 5124:
    case 35670:
      return im;
    case 35667:
    case 35671:
      return sm;
    case 35668:
    case 35672:
      return rm;
    case 35669:
    case 35673:
      return am;
    case 5125:
      return om;
    case 36294:
      return lm;
    case 36295:
      return cm;
    case 36296:
      return hm;
    case 35678:
    case 36198:
    case 36298:
    case 36306:
    case 35682:
      return um;
    case 35679:
    case 36299:
    case 36307:
      return fm;
    case 35680:
    case 36300:
    case 36308:
    case 36293:
      return dm;
    case 36289:
    case 36303:
    case 36311:
    case 36292:
      return pm;
  }
}
function gm(i, t) {
  i.uniform1fv(this.addr, t);
}
function _m(i, t) {
  const e = Ci(t, this.size, 2);
  i.uniform2fv(this.addr, e);
}
function xm(i, t) {
  const e = Ci(t, this.size, 3);
  i.uniform3fv(this.addr, e);
}
function vm(i, t) {
  const e = Ci(t, this.size, 4);
  i.uniform4fv(this.addr, e);
}
function Mm(i, t) {
  const e = Ci(t, this.size, 4);
  i.uniformMatrix2fv(this.addr, !1, e);
}
function Sm(i, t) {
  const e = Ci(t, this.size, 9);
  i.uniformMatrix3fv(this.addr, !1, e);
}
function ym(i, t) {
  const e = Ci(t, this.size, 16);
  i.uniformMatrix4fv(this.addr, !1, e);
}
function Em(i, t) {
  i.uniform1iv(this.addr, t);
}
function bm(i, t) {
  i.uniform2iv(this.addr, t);
}
function Tm(i, t) {
  i.uniform3iv(this.addr, t);
}
function Am(i, t) {
  i.uniform4iv(this.addr, t);
}
function wm(i, t) {
  i.uniform1uiv(this.addr, t);
}
function Rm(i, t) {
  i.uniform2uiv(this.addr, t);
}
function Cm(i, t) {
  i.uniform3uiv(this.addr, t);
}
function Pm(i, t) {
  i.uniform4uiv(this.addr, t);
}
function Lm(i, t, e) {
  const n = this.cache,
    s = t.length,
    r = tr(e, s);
  ge(n, r) || (i.uniform1iv(this.addr, r), _e(n, r));
  let a;
  this.type === i.SAMPLER_2D_SHADOW ? (a = Fa) : (a = pc);
  for (let o = 0; o !== s; ++o) e.setTexture2D(t[o] || a, r[o]);
}
function Dm(i, t, e) {
  const n = this.cache,
    s = t.length,
    r = tr(e, s);
  ge(n, r) || (i.uniform1iv(this.addr, r), _e(n, r));
  for (let a = 0; a !== s; ++a) e.setTexture3D(t[a] || gc, r[a]);
}
function Im(i, t, e) {
  const n = this.cache,
    s = t.length,
    r = tr(e, s);
  ge(n, r) || (i.uniform1iv(this.addr, r), _e(n, r));
  for (let a = 0; a !== s; ++a) e.setTextureCube(t[a] || _c, r[a]);
}
function Um(i, t, e) {
  const n = this.cache,
    s = t.length,
    r = tr(e, s);
  ge(n, r) || (i.uniform1iv(this.addr, r), _e(n, r));
  for (let a = 0; a !== s; ++a) e.setTexture2DArray(t[a] || mc, r[a]);
}
function Nm(i) {
  switch (i) {
    case 5126:
      return gm;
    case 35664:
      return _m;
    case 35665:
      return xm;
    case 35666:
      return vm;
    case 35674:
      return Mm;
    case 35675:
      return Sm;
    case 35676:
      return ym;
    case 5124:
    case 35670:
      return Em;
    case 35667:
    case 35671:
      return bm;
    case 35668:
    case 35672:
      return Tm;
    case 35669:
    case 35673:
      return Am;
    case 5125:
      return wm;
    case 36294:
      return Rm;
    case 36295:
      return Cm;
    case 36296:
      return Pm;
    case 35678:
    case 36198:
    case 36298:
    case 36306:
    case 35682:
      return Lm;
    case 35679:
    case 36299:
    case 36307:
      return Dm;
    case 35680:
    case 36300:
    case 36308:
    case 36293:
      return Im;
    case 36289:
    case 36303:
    case 36311:
    case 36292:
      return Um;
  }
}
class Fm {
  constructor(t, e, n) {
    ((this.id = t),
      (this.addr = n),
      (this.cache = []),
      (this.type = e.type),
      (this.setValue = mm(e.type)));
  }
}
class Om {
  constructor(t, e, n) {
    ((this.id = t),
      (this.addr = n),
      (this.cache = []),
      (this.type = e.type),
      (this.size = e.size),
      (this.setValue = Nm(e.type)));
  }
}
class Bm {
  constructor(t) {
    ((this.id = t), (this.seq = []), (this.map = {}));
  }
  setValue(t, e, n) {
    const s = this.seq;
    for (let r = 0, a = s.length; r !== a; ++r) {
      const o = s[r];
      o.setValue(t, e[o.id], n);
    }
  }
}
const zr = /(\w+)(\])?(\[|\.)?/g;
function hl(i, t) {
  (i.seq.push(t), (i.map[t.id] = t));
}
function zm(i, t, e) {
  const n = i.name,
    s = n.length;
  for (zr.lastIndex = 0; ; ) {
    const r = zr.exec(n),
      a = zr.lastIndex;
    let o = r[1];
    const l = r[2] === ']',
      c = r[3];
    if ((l && (o = o | 0), c === void 0 || (c === '[' && a + 2 === s))) {
      hl(e, c === void 0 ? new Fm(o, i, t) : new Om(o, i, t));
      break;
    } else {
      let f = e.map[o];
      (f === void 0 && ((f = new Bm(o)), hl(e, f)), (e = f));
    }
  }
}
class Gs {
  constructor(t, e) {
    ((this.seq = []), (this.map = {}));
    const n = t.getProgramParameter(e, t.ACTIVE_UNIFORMS);
    for (let a = 0; a < n; ++a) {
      const o = t.getActiveUniform(e, a),
        l = t.getUniformLocation(e, o.name);
      zm(o, l, this);
    }
    const s = [],
      r = [];
    for (const a of this.seq)
      a.type === t.SAMPLER_2D_SHADOW ||
      a.type === t.SAMPLER_CUBE_SHADOW ||
      a.type === t.SAMPLER_2D_ARRAY_SHADOW
        ? s.push(a)
        : r.push(a);
    s.length > 0 && (this.seq = s.concat(r));
  }
  setValue(t, e, n, s) {
    const r = this.map[e];
    r !== void 0 && r.setValue(t, n, s);
  }
  setOptional(t, e, n) {
    const s = e[n];
    s !== void 0 && this.setValue(t, n, s);
  }
  static upload(t, e, n, s) {
    for (let r = 0, a = e.length; r !== a; ++r) {
      const o = e[r],
        l = n[o.id];
      l.needsUpdate !== !1 && o.setValue(t, l.value, s);
    }
  }
  static seqWithValue(t, e) {
    const n = [];
    for (let s = 0, r = t.length; s !== r; ++s) {
      const a = t[s];
      a.id in e && n.push(a);
    }
    return n;
  }
}
function ul(i, t, e) {
  const n = i.createShader(t);
  return (i.shaderSource(n, e), i.compileShader(n), n);
}
const Vm = 37297;
let Gm = 0;
function Hm(i, t) {
  const e = i.split(`
`),
    n = [],
    s = Math.max(t - 6, 0),
    r = Math.min(t + 6, e.length);
  for (let a = s; a < r; a++) {
    const o = a + 1;
    n.push(`${o === t ? '>' : ' '} ${o}: ${e[a]}`);
  }
  return n.join(`
`);
}
const fl = new Xt();
function km(i) {
  $t._getMatrix(fl, $t.workingColorSpace, i);
  const t = `mat3( ${fl.elements.map((e) => e.toFixed(4))} )`;
  switch ($t.getTransfer(i)) {
    case Hs:
      return [t, 'LinearTransferOETF'];
    case te:
      return [t, 'sRGBTransferOETF'];
    default:
      return (Ft('WebGLProgram: Unsupported color space: ', i), [t, 'LinearTransferOETF']);
  }
}
function dl(i, t, e) {
  const n = i.getShaderParameter(t, i.COMPILE_STATUS),
    r = (i.getShaderInfoLog(t) || '').trim();
  if (n && r === '') return '';
  const a = /ERROR: 0:(\d+)/.exec(r);
  if (a) {
    const o = parseInt(a[1]);
    return (
      e.toUpperCase() +
      `

` +
      r +
      `

` +
      Hm(i.getShaderSource(t), o)
    );
  } else return r;
}
function Wm(i, t) {
  const e = km(t);
  return [
    `vec4 ${i}( vec4 value ) {`,
    `	return ${e[1]}( vec4( value.rgb * ${e[0]}, value.a ) );`,
    '}',
  ].join(`
`);
}
const Xm = {
  [yl]: 'Linear',
  [El]: 'Reinhard',
  [bl]: 'Cineon',
  [Tl]: 'ACESFilmic',
  [wl]: 'AgX',
  [Rl]: 'Neutral',
  [Al]: 'Custom',
};
function qm(i, t) {
  const e = Xm[t];
  return e === void 0
    ? (Ft('WebGLProgram: Unsupported toneMapping:', t),
      'vec3 ' + i + '( vec3 color ) { return LinearToneMapping( color ); }')
    : 'vec3 ' + i + '( vec3 color ) { return ' + e + 'ToneMapping( color ); }';
}
const Us = new L();
function Ym() {
  $t.getLuminanceCoefficients(Us);
  const i = Us.x.toFixed(4),
    t = Us.y.toFixed(4),
    e = Us.z.toFixed(4);
  return [
    'float luminance( const in vec3 rgb ) {',
    `	const vec3 weights = vec3( ${i}, ${t}, ${e} );`,
    '	return dot( weights, rgb );',
    '}',
  ].join(`
`);
}
function Zm(i) {
  return [
    i.extensionClipCullDistance ? '#extension GL_ANGLE_clip_cull_distance : require' : '',
    i.extensionMultiDraw ? '#extension GL_ANGLE_multi_draw : require' : '',
  ].filter(zi).join(`
`);
}
function Jm(i) {
  const t = [];
  for (const e in i) {
    const n = i[e];
    n !== !1 && t.push('#define ' + e + ' ' + n);
  }
  return t.join(`
`);
}
function $m(i, t) {
  const e = {},
    n = i.getProgramParameter(t, i.ACTIVE_ATTRIBUTES);
  for (let s = 0; s < n; s++) {
    const r = i.getActiveAttrib(t, s),
      a = r.name;
    let o = 1;
    (r.type === i.FLOAT_MAT2 && (o = 2),
      r.type === i.FLOAT_MAT3 && (o = 3),
      r.type === i.FLOAT_MAT4 && (o = 4),
      (e[a] = { type: r.type, location: i.getAttribLocation(t, a), locationSize: o }));
  }
  return e;
}
function zi(i) {
  return i !== '';
}
function pl(i, t) {
  const e = t.numSpotLightShadows + t.numSpotLightMaps - t.numSpotLightShadowsWithMaps;
  return i
    .replace(/NUM_DIR_LIGHTS/g, t.numDirLights)
    .replace(/NUM_SPOT_LIGHTS/g, t.numSpotLights)
    .replace(/NUM_SPOT_LIGHT_MAPS/g, t.numSpotLightMaps)
    .replace(/NUM_SPOT_LIGHT_COORDS/g, e)
    .replace(/NUM_RECT_AREA_LIGHTS/g, t.numRectAreaLights)
    .replace(/NUM_POINT_LIGHTS/g, t.numPointLights)
    .replace(/NUM_HEMI_LIGHTS/g, t.numHemiLights)
    .replace(/NUM_DIR_LIGHT_SHADOWS/g, t.numDirLightShadows)
    .replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g, t.numSpotLightShadowsWithMaps)
    .replace(/NUM_SPOT_LIGHT_SHADOWS/g, t.numSpotLightShadows)
    .replace(/NUM_POINT_LIGHT_SHADOWS/g, t.numPointLightShadows);
}
function ml(i, t) {
  return i
    .replace(/NUM_CLIPPING_PLANES/g, t.numClippingPlanes)
    .replace(/UNION_CLIPPING_PLANES/g, t.numClippingPlanes - t.numClipIntersection);
}
const Km = /^[ \t]*#include +<([\w\d./]+)>/gm;
function Oa(i) {
  return i.replace(Km, Qm);
}
const jm = new Map();
function Qm(i, t) {
  let e = qt[t];
  if (e === void 0) {
    const n = jm.get(t);
    if (n !== void 0)
      ((e = qt[n]),
        Ft('WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.', t, n));
    else throw new Error('Can not resolve #include <' + t + '>');
  }
  return Oa(e);
}
const tg =
  /#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;
function gl(i) {
  return i.replace(tg, eg);
}
function eg(i, t, e, n) {
  let s = '';
  for (let r = parseInt(t); r < parseInt(e); r++)
    s += n.replace(/\[\s*i\s*\]/g, '[ ' + r + ' ]').replace(/UNROLLED_LOOP_INDEX/g, r);
  return s;
}
function _l(i) {
  let t = `precision ${i.precision} float;
	precision ${i.precision} int;
	precision ${i.precision} sampler2D;
	precision ${i.precision} samplerCube;
	precision ${i.precision} sampler3D;
	precision ${i.precision} sampler2DArray;
	precision ${i.precision} sampler2DShadow;
	precision ${i.precision} samplerCubeShadow;
	precision ${i.precision} sampler2DArrayShadow;
	precision ${i.precision} isampler2D;
	precision ${i.precision} isampler3D;
	precision ${i.precision} isamplerCube;
	precision ${i.precision} isampler2DArray;
	precision ${i.precision} usampler2D;
	precision ${i.precision} usampler3D;
	precision ${i.precision} usamplerCube;
	precision ${i.precision} usampler2DArray;
	`;
  return (
    i.precision === 'highp'
      ? (t += `
#define HIGH_PRECISION`)
      : i.precision === 'mediump'
        ? (t += `
#define MEDIUM_PRECISION`)
        : i.precision === 'lowp' &&
          (t += `
#define LOW_PRECISION`),
    t
  );
}
const ng = { [Ns]: 'SHADOWMAP_TYPE_PCF', [Oi]: 'SHADOWMAP_TYPE_VSM' };
function ig(i) {
  return ng[i.shadowMapType] || 'SHADOWMAP_TYPE_BASIC';
}
const sg = { [Jn]: 'ENVMAP_TYPE_CUBE', [yi]: 'ENVMAP_TYPE_CUBE', [Js]: 'ENVMAP_TYPE_CUBE_UV' };
function rg(i) {
  return i.envMap === !1 ? 'ENVMAP_TYPE_CUBE' : sg[i.envMapMode] || 'ENVMAP_TYPE_CUBE';
}
const ag = { [yi]: 'ENVMAP_MODE_REFRACTION' };
function og(i) {
  return i.envMap === !1 ? 'ENVMAP_MODE_REFLECTION' : ag[i.envMapMode] || 'ENVMAP_MODE_REFLECTION';
}
const lg = {
  [Zs]: 'ENVMAP_BLENDING_MULTIPLY',
  [qc]: 'ENVMAP_BLENDING_MIX',
  [Yc]: 'ENVMAP_BLENDING_ADD',
};
function cg(i) {
  return i.envMap === !1 ? 'ENVMAP_BLENDING_NONE' : lg[i.combine] || 'ENVMAP_BLENDING_NONE';
}
function hg(i) {
  const t = i.envMapCubeUVHeight;
  if (t === null) return null;
  const e = Math.log2(t) - 2,
    n = 1 / t;
  return { texelWidth: 1 / (3 * Math.max(Math.pow(2, e), 7 * 16)), texelHeight: n, maxMip: e };
}
function ug(i, t, e, n) {
  const s = i.getContext(),
    r = e.defines;
  let a = e.vertexShader,
    o = e.fragmentShader;
  const l = ig(e),
    c = rg(e),
    h = og(e),
    f = cg(e),
    u = hg(e),
    p = Zm(e),
    g = Jm(r),
    M = s.createProgram();
  let m,
    d,
    E = e.glslVersion
      ? '#version ' +
        e.glslVersion +
        `
`
      : '';
  (e.isRawShaderMaterial
    ? ((m = [
        '#define SHADER_TYPE ' + e.shaderType,
        '#define SHADER_NAME ' + e.shaderName,
        g,
      ].filter(zi).join(`
`)),
      m.length > 0 &&
        (m += `
`),
      (d = ['#define SHADER_TYPE ' + e.shaderType, '#define SHADER_NAME ' + e.shaderName, g].filter(
        zi
      ).join(`
`)),
      d.length > 0 &&
        (d += `
`))
    : ((m = [
        _l(e),
        '#define SHADER_TYPE ' + e.shaderType,
        '#define SHADER_NAME ' + e.shaderName,
        g,
        e.extensionClipCullDistance ? '#define USE_CLIP_DISTANCE' : '',
        e.batching ? '#define USE_BATCHING' : '',
        e.batchingColor ? '#define USE_BATCHING_COLOR' : '',
        e.instancing ? '#define USE_INSTANCING' : '',
        e.instancingColor ? '#define USE_INSTANCING_COLOR' : '',
        e.instancingMorph ? '#define USE_INSTANCING_MORPH' : '',
        e.useFog && e.fog ? '#define USE_FOG' : '',
        e.useFog && e.fogExp2 ? '#define FOG_EXP2' : '',
        e.map ? '#define USE_MAP' : '',
        e.envMap ? '#define USE_ENVMAP' : '',
        e.envMap ? '#define ' + h : '',
        e.lightMap ? '#define USE_LIGHTMAP' : '',
        e.aoMap ? '#define USE_AOMAP' : '',
        e.bumpMap ? '#define USE_BUMPMAP' : '',
        e.normalMap ? '#define USE_NORMALMAP' : '',
        e.normalMapObjectSpace ? '#define USE_NORMALMAP_OBJECTSPACE' : '',
        e.normalMapTangentSpace ? '#define USE_NORMALMAP_TANGENTSPACE' : '',
        e.displacementMap ? '#define USE_DISPLACEMENTMAP' : '',
        e.emissiveMap ? '#define USE_EMISSIVEMAP' : '',
        e.anisotropy ? '#define USE_ANISOTROPY' : '',
        e.anisotropyMap ? '#define USE_ANISOTROPYMAP' : '',
        e.clearcoatMap ? '#define USE_CLEARCOATMAP' : '',
        e.clearcoatRoughnessMap ? '#define USE_CLEARCOAT_ROUGHNESSMAP' : '',
        e.clearcoatNormalMap ? '#define USE_CLEARCOAT_NORMALMAP' : '',
        e.iridescenceMap ? '#define USE_IRIDESCENCEMAP' : '',
        e.iridescenceThicknessMap ? '#define USE_IRIDESCENCE_THICKNESSMAP' : '',
        e.specularMap ? '#define USE_SPECULARMAP' : '',
        e.specularColorMap ? '#define USE_SPECULAR_COLORMAP' : '',
        e.specularIntensityMap ? '#define USE_SPECULAR_INTENSITYMAP' : '',
        e.roughnessMap ? '#define USE_ROUGHNESSMAP' : '',
        e.metalnessMap ? '#define USE_METALNESSMAP' : '',
        e.alphaMap ? '#define USE_ALPHAMAP' : '',
        e.alphaHash ? '#define USE_ALPHAHASH' : '',
        e.transmission ? '#define USE_TRANSMISSION' : '',
        e.transmissionMap ? '#define USE_TRANSMISSIONMAP' : '',
        e.thicknessMap ? '#define USE_THICKNESSMAP' : '',
        e.sheenColorMap ? '#define USE_SHEEN_COLORMAP' : '',
        e.sheenRoughnessMap ? '#define USE_SHEEN_ROUGHNESSMAP' : '',
        e.mapUv ? '#define MAP_UV ' + e.mapUv : '',
        e.alphaMapUv ? '#define ALPHAMAP_UV ' + e.alphaMapUv : '',
        e.lightMapUv ? '#define LIGHTMAP_UV ' + e.lightMapUv : '',
        e.aoMapUv ? '#define AOMAP_UV ' + e.aoMapUv : '',
        e.emissiveMapUv ? '#define EMISSIVEMAP_UV ' + e.emissiveMapUv : '',
        e.bumpMapUv ? '#define BUMPMAP_UV ' + e.bumpMapUv : '',
        e.normalMapUv ? '#define NORMALMAP_UV ' + e.normalMapUv : '',
        e.displacementMapUv ? '#define DISPLACEMENTMAP_UV ' + e.displacementMapUv : '',
        e.metalnessMapUv ? '#define METALNESSMAP_UV ' + e.metalnessMapUv : '',
        e.roughnessMapUv ? '#define ROUGHNESSMAP_UV ' + e.roughnessMapUv : '',
        e.anisotropyMapUv ? '#define ANISOTROPYMAP_UV ' + e.anisotropyMapUv : '',
        e.clearcoatMapUv ? '#define CLEARCOATMAP_UV ' + e.clearcoatMapUv : '',
        e.clearcoatNormalMapUv ? '#define CLEARCOAT_NORMALMAP_UV ' + e.clearcoatNormalMapUv : '',
        e.clearcoatRoughnessMapUv
          ? '#define CLEARCOAT_ROUGHNESSMAP_UV ' + e.clearcoatRoughnessMapUv
          : '',
        e.iridescenceMapUv ? '#define IRIDESCENCEMAP_UV ' + e.iridescenceMapUv : '',
        e.iridescenceThicknessMapUv
          ? '#define IRIDESCENCE_THICKNESSMAP_UV ' + e.iridescenceThicknessMapUv
          : '',
        e.sheenColorMapUv ? '#define SHEEN_COLORMAP_UV ' + e.sheenColorMapUv : '',
        e.sheenRoughnessMapUv ? '#define SHEEN_ROUGHNESSMAP_UV ' + e.sheenRoughnessMapUv : '',
        e.specularMapUv ? '#define SPECULARMAP_UV ' + e.specularMapUv : '',
        e.specularColorMapUv ? '#define SPECULAR_COLORMAP_UV ' + e.specularColorMapUv : '',
        e.specularIntensityMapUv
          ? '#define SPECULAR_INTENSITYMAP_UV ' + e.specularIntensityMapUv
          : '',
        e.transmissionMapUv ? '#define TRANSMISSIONMAP_UV ' + e.transmissionMapUv : '',
        e.thicknessMapUv ? '#define THICKNESSMAP_UV ' + e.thicknessMapUv : '',
        e.vertexTangents && e.flatShading === !1 ? '#define USE_TANGENT' : '',
        e.vertexColors ? '#define USE_COLOR' : '',
        e.vertexAlphas ? '#define USE_COLOR_ALPHA' : '',
        e.vertexUv1s ? '#define USE_UV1' : '',
        e.vertexUv2s ? '#define USE_UV2' : '',
        e.vertexUv3s ? '#define USE_UV3' : '',
        e.pointsUvs ? '#define USE_POINTS_UV' : '',
        e.flatShading ? '#define FLAT_SHADED' : '',
        e.skinning ? '#define USE_SKINNING' : '',
        e.morphTargets ? '#define USE_MORPHTARGETS' : '',
        e.morphNormals && e.flatShading === !1 ? '#define USE_MORPHNORMALS' : '',
        e.morphColors ? '#define USE_MORPHCOLORS' : '',
        e.morphTargetsCount > 0
          ? '#define MORPHTARGETS_TEXTURE_STRIDE ' + e.morphTextureStride
          : '',
        e.morphTargetsCount > 0 ? '#define MORPHTARGETS_COUNT ' + e.morphTargetsCount : '',
        e.doubleSided ? '#define DOUBLE_SIDED' : '',
        e.flipSided ? '#define FLIP_SIDED' : '',
        e.shadowMapEnabled ? '#define USE_SHADOWMAP' : '',
        e.shadowMapEnabled ? '#define ' + l : '',
        e.sizeAttenuation ? '#define USE_SIZEATTENUATION' : '',
        e.numLightProbes > 0 ? '#define USE_LIGHT_PROBES' : '',
        e.logarithmicDepthBuffer ? '#define USE_LOGARITHMIC_DEPTH_BUFFER' : '',
        e.reversedDepthBuffer ? '#define USE_REVERSED_DEPTH_BUFFER' : '',
        'uniform mat4 modelMatrix;',
        'uniform mat4 modelViewMatrix;',
        'uniform mat4 projectionMatrix;',
        'uniform mat4 viewMatrix;',
        'uniform mat3 normalMatrix;',
        'uniform vec3 cameraPosition;',
        'uniform bool isOrthographic;',
        '#ifdef USE_INSTANCING',
        '	attribute mat4 instanceMatrix;',
        '#endif',
        '#ifdef USE_INSTANCING_COLOR',
        '	attribute vec3 instanceColor;',
        '#endif',
        '#ifdef USE_INSTANCING_MORPH',
        '	uniform sampler2D morphTexture;',
        '#endif',
        'attribute vec3 position;',
        'attribute vec3 normal;',
        'attribute vec2 uv;',
        '#ifdef USE_UV1',
        '	attribute vec2 uv1;',
        '#endif',
        '#ifdef USE_UV2',
        '	attribute vec2 uv2;',
        '#endif',
        '#ifdef USE_UV3',
        '	attribute vec2 uv3;',
        '#endif',
        '#ifdef USE_TANGENT',
        '	attribute vec4 tangent;',
        '#endif',
        '#if defined( USE_COLOR_ALPHA )',
        '	attribute vec4 color;',
        '#elif defined( USE_COLOR )',
        '	attribute vec3 color;',
        '#endif',
        '#ifdef USE_SKINNING',
        '	attribute vec4 skinIndex;',
        '	attribute vec4 skinWeight;',
        '#endif',
        `
`,
      ].filter(zi).join(`
`)),
      (d = [
        _l(e),
        '#define SHADER_TYPE ' + e.shaderType,
        '#define SHADER_NAME ' + e.shaderName,
        g,
        e.useFog && e.fog ? '#define USE_FOG' : '',
        e.useFog && e.fogExp2 ? '#define FOG_EXP2' : '',
        e.alphaToCoverage ? '#define ALPHA_TO_COVERAGE' : '',
        e.map ? '#define USE_MAP' : '',
        e.matcap ? '#define USE_MATCAP' : '',
        e.envMap ? '#define USE_ENVMAP' : '',
        e.envMap ? '#define ' + c : '',
        e.envMap ? '#define ' + h : '',
        e.envMap ? '#define ' + f : '',
        u ? '#define CUBEUV_TEXEL_WIDTH ' + u.texelWidth : '',
        u ? '#define CUBEUV_TEXEL_HEIGHT ' + u.texelHeight : '',
        u ? '#define CUBEUV_MAX_MIP ' + u.maxMip + '.0' : '',
        e.lightMap ? '#define USE_LIGHTMAP' : '',
        e.aoMap ? '#define USE_AOMAP' : '',
        e.bumpMap ? '#define USE_BUMPMAP' : '',
        e.normalMap ? '#define USE_NORMALMAP' : '',
        e.normalMapObjectSpace ? '#define USE_NORMALMAP_OBJECTSPACE' : '',
        e.normalMapTangentSpace ? '#define USE_NORMALMAP_TANGENTSPACE' : '',
        e.emissiveMap ? '#define USE_EMISSIVEMAP' : '',
        e.anisotropy ? '#define USE_ANISOTROPY' : '',
        e.anisotropyMap ? '#define USE_ANISOTROPYMAP' : '',
        e.clearcoat ? '#define USE_CLEARCOAT' : '',
        e.clearcoatMap ? '#define USE_CLEARCOATMAP' : '',
        e.clearcoatRoughnessMap ? '#define USE_CLEARCOAT_ROUGHNESSMAP' : '',
        e.clearcoatNormalMap ? '#define USE_CLEARCOAT_NORMALMAP' : '',
        e.dispersion ? '#define USE_DISPERSION' : '',
        e.iridescence ? '#define USE_IRIDESCENCE' : '',
        e.iridescenceMap ? '#define USE_IRIDESCENCEMAP' : '',
        e.iridescenceThicknessMap ? '#define USE_IRIDESCENCE_THICKNESSMAP' : '',
        e.specularMap ? '#define USE_SPECULARMAP' : '',
        e.specularColorMap ? '#define USE_SPECULAR_COLORMAP' : '',
        e.specularIntensityMap ? '#define USE_SPECULAR_INTENSITYMAP' : '',
        e.roughnessMap ? '#define USE_ROUGHNESSMAP' : '',
        e.metalnessMap ? '#define USE_METALNESSMAP' : '',
        e.alphaMap ? '#define USE_ALPHAMAP' : '',
        e.alphaTest ? '#define USE_ALPHATEST' : '',
        e.alphaHash ? '#define USE_ALPHAHASH' : '',
        e.sheen ? '#define USE_SHEEN' : '',
        e.sheenColorMap ? '#define USE_SHEEN_COLORMAP' : '',
        e.sheenRoughnessMap ? '#define USE_SHEEN_ROUGHNESSMAP' : '',
        e.transmission ? '#define USE_TRANSMISSION' : '',
        e.transmissionMap ? '#define USE_TRANSMISSIONMAP' : '',
        e.thicknessMap ? '#define USE_THICKNESSMAP' : '',
        e.vertexTangents && e.flatShading === !1 ? '#define USE_TANGENT' : '',
        e.vertexColors || e.instancingColor ? '#define USE_COLOR' : '',
        e.vertexAlphas || e.batchingColor ? '#define USE_COLOR_ALPHA' : '',
        e.vertexUv1s ? '#define USE_UV1' : '',
        e.vertexUv2s ? '#define USE_UV2' : '',
        e.vertexUv3s ? '#define USE_UV3' : '',
        e.pointsUvs ? '#define USE_POINTS_UV' : '',
        e.gradientMap ? '#define USE_GRADIENTMAP' : '',
        e.flatShading ? '#define FLAT_SHADED' : '',
        e.doubleSided ? '#define DOUBLE_SIDED' : '',
        e.flipSided ? '#define FLIP_SIDED' : '',
        e.shadowMapEnabled ? '#define USE_SHADOWMAP' : '',
        e.shadowMapEnabled ? '#define ' + l : '',
        e.premultipliedAlpha ? '#define PREMULTIPLIED_ALPHA' : '',
        e.numLightProbes > 0 ? '#define USE_LIGHT_PROBES' : '',
        e.decodeVideoTexture ? '#define DECODE_VIDEO_TEXTURE' : '',
        e.decodeVideoTextureEmissive ? '#define DECODE_VIDEO_TEXTURE_EMISSIVE' : '',
        e.logarithmicDepthBuffer ? '#define USE_LOGARITHMIC_DEPTH_BUFFER' : '',
        e.reversedDepthBuffer ? '#define USE_REVERSED_DEPTH_BUFFER' : '',
        'uniform mat4 viewMatrix;',
        'uniform vec3 cameraPosition;',
        'uniform bool isOrthographic;',
        e.toneMapping !== nn ? '#define TONE_MAPPING' : '',
        e.toneMapping !== nn ? qt.tonemapping_pars_fragment : '',
        e.toneMapping !== nn ? qm('toneMapping', e.toneMapping) : '',
        e.dithering ? '#define DITHERING' : '',
        e.opaque ? '#define OPAQUE' : '',
        qt.colorspace_pars_fragment,
        Wm('linearToOutputTexel', e.outputColorSpace),
        Ym(),
        e.useDepthPacking ? '#define DEPTH_PACKING ' + e.depthPacking : '',
        `
`,
      ].filter(zi).join(`
`))),
    (a = Oa(a)),
    (a = pl(a, e)),
    (a = ml(a, e)),
    (o = Oa(o)),
    (o = pl(o, e)),
    (o = ml(o, e)),
    (a = gl(a)),
    (o = gl(o)),
    e.isRawShaderMaterial !== !0 &&
      ((E = `#version 300 es
`),
      (m =
        [p, '#define attribute in', '#define varying out', '#define texture2D texture'].join(`
`) +
        `
` +
        m),
      (d =
        [
          '#define varying in',
          e.glslVersion === go ? '' : 'layout(location = 0) out highp vec4 pc_fragColor;',
          e.glslVersion === go ? '' : '#define gl_FragColor pc_fragColor',
          '#define gl_FragDepthEXT gl_FragDepth',
          '#define texture2D texture',
          '#define textureCube texture',
          '#define texture2DProj textureProj',
          '#define texture2DLodEXT textureLod',
          '#define texture2DProjLodEXT textureProjLod',
          '#define textureCubeLodEXT textureLod',
          '#define texture2DGradEXT textureGrad',
          '#define texture2DProjGradEXT textureProjGrad',
          '#define textureCubeGradEXT textureGrad',
        ].join(`
`) +
        `
` +
        d)));
  const y = E + m + a,
    S = E + d + o,
    R = ul(s, s.VERTEX_SHADER, y),
    w = ul(s, s.FRAGMENT_SHADER, S);
  (s.attachShader(M, R),
    s.attachShader(M, w),
    e.index0AttributeName !== void 0
      ? s.bindAttribLocation(M, 0, e.index0AttributeName)
      : e.morphTargets === !0 && s.bindAttribLocation(M, 0, 'position'),
    s.linkProgram(M));
  function P(C) {
    if (i.debug.checkShaderErrors) {
      const N = s.getProgramInfoLog(M) || '',
        z = s.getShaderInfoLog(R) || '',
        k = s.getShaderInfoLog(w) || '',
        F = N.trim(),
        O = z.trim(),
        B = k.trim();
      let nt = !0,
        j = !0;
      if (s.getProgramParameter(M, s.LINK_STATUS) === !1)
        if (((nt = !1), typeof i.debug.onShaderError == 'function'))
          i.debug.onShaderError(s, M, R, w);
        else {
          const mt = dl(s, R, 'vertex'),
            _t = dl(s, w, 'fragment');
          Jt(
            'THREE.WebGLProgram: Shader Error ' +
              s.getError() +
              ' - VALIDATE_STATUS ' +
              s.getProgramParameter(M, s.VALIDATE_STATUS) +
              `

Material Name: ` +
              C.name +
              `
Material Type: ` +
              C.type +
              `

Program Info Log: ` +
              F +
              `
` +
              mt +
              `
` +
              _t
          );
        }
      else F !== '' ? Ft('WebGLProgram: Program Info Log:', F) : (O === '' || B === '') && (j = !1);
      j &&
        (C.diagnostics = {
          runnable: nt,
          programLog: F,
          vertexShader: { log: O, prefix: m },
          fragmentShader: { log: B, prefix: d },
        });
    }
    (s.deleteShader(R), s.deleteShader(w), (x = new Gs(s, M)), (b = $m(s, M)));
  }
  let x;
  this.getUniforms = function () {
    return (x === void 0 && P(this), x);
  };
  let b;
  this.getAttributes = function () {
    return (b === void 0 && P(this), b);
  };
  let H = e.rendererExtensionParallelShaderCompile === !1;
  return (
    (this.isReady = function () {
      return (H === !1 && (H = s.getProgramParameter(M, Vm)), H);
    }),
    (this.destroy = function () {
      (n.releaseStatesOfProgram(this), s.deleteProgram(M), (this.program = void 0));
    }),
    (this.type = e.shaderType),
    (this.name = e.shaderName),
    (this.id = Gm++),
    (this.cacheKey = t),
    (this.usedTimes = 1),
    (this.program = M),
    (this.vertexShader = R),
    (this.fragmentShader = w),
    this
  );
}
let fg = 0;
class dg {
  constructor() {
    ((this.shaderCache = new Map()), (this.materialCache = new Map()));
  }
  update(t) {
    const e = t.vertexShader,
      n = t.fragmentShader,
      s = this._getShaderStage(e),
      r = this._getShaderStage(n),
      a = this._getShaderCacheForMaterial(t);
    return (
      a.has(s) === !1 && (a.add(s), s.usedTimes++),
      a.has(r) === !1 && (a.add(r), r.usedTimes++),
      this
    );
  }
  remove(t) {
    const e = this.materialCache.get(t);
    for (const n of e) (n.usedTimes--, n.usedTimes === 0 && this.shaderCache.delete(n.code));
    return (this.materialCache.delete(t), this);
  }
  getVertexShaderID(t) {
    return this._getShaderStage(t.vertexShader).id;
  }
  getFragmentShaderID(t) {
    return this._getShaderStage(t.fragmentShader).id;
  }
  dispose() {
    (this.shaderCache.clear(), this.materialCache.clear());
  }
  _getShaderCacheForMaterial(t) {
    const e = this.materialCache;
    let n = e.get(t);
    return (n === void 0 && ((n = new Set()), e.set(t, n)), n);
  }
  _getShaderStage(t) {
    const e = this.shaderCache;
    let n = e.get(t);
    return (n === void 0 && ((n = new pg(t)), e.set(t, n)), n);
  }
}
class pg {
  constructor(t) {
    ((this.id = fg++), (this.code = t), (this.usedTimes = 0));
  }
}
function mg(i, t, e, n, s, r) {
  const a = new Ja(),
    o = new dg(),
    l = new Set(),
    c = [],
    h = new Map(),
    f = n.logarithmicDepthBuffer;
  let u = n.precision;
  const p = {
    MeshDepthMaterial: 'depth',
    MeshDistanceMaterial: 'distance',
    MeshNormalMaterial: 'normal',
    MeshBasicMaterial: 'basic',
    MeshLambertMaterial: 'lambert',
    MeshPhongMaterial: 'phong',
    MeshToonMaterial: 'toon',
    MeshStandardMaterial: 'physical',
    MeshPhysicalMaterial: 'physical',
    MeshMatcapMaterial: 'matcap',
    LineBasicMaterial: 'basic',
    LineDashedMaterial: 'dashed',
    PointsMaterial: 'points',
    ShadowMaterial: 'shadow',
    SpriteMaterial: 'sprite',
  };
  function g(x) {
    return (l.add(x), x === 0 ? 'uv' : `uv${x}`);
  }
  function M(x, b, H, C, N) {
    const z = C.fog,
      k = N.geometry,
      F =
        x.isMeshStandardMaterial || x.isMeshLambertMaterial || x.isMeshPhongMaterial
          ? C.environment
          : null,
      O =
        x.isMeshStandardMaterial ||
        (x.isMeshLambertMaterial && !x.envMap) ||
        (x.isMeshPhongMaterial && !x.envMap),
      B = t.get(x.envMap || F, O),
      nt = B && B.mapping === Js ? B.image.height : null,
      j = p[x.type];
    x.precision !== null &&
      ((u = n.getMaxPrecision(x.precision)),
      u !== x.precision &&
        Ft('WebGLProgram.getParameters:', x.precision, 'not supported, using', u, 'instead.'));
    const mt = k.morphAttributes.position || k.morphAttributes.normal || k.morphAttributes.color,
      _t = mt !== void 0 ? mt.length : 0;
    let gt = 0;
    (k.morphAttributes.position !== void 0 && (gt = 1),
      k.morphAttributes.normal !== void 0 && (gt = 2),
      k.morphAttributes.color !== void 0 && (gt = 3));
    let Ot, jt, ne, Z;
    if (j) {
      const Qt = tn[j];
      ((Ot = Qt.vertexShader), (jt = Qt.fragmentShader));
    } else
      ((Ot = x.vertexShader),
        (jt = x.fragmentShader),
        o.update(x),
        (ne = o.getVertexShaderID(x)),
        (Z = o.getFragmentShaderID(x)));
    const rt = i.getRenderTarget(),
      at = i.state.buffers.depth.getReversed(),
      It = N.isInstancedMesh === !0,
      Lt = N.isBatchedMesh === !0,
      Vt = !!x.map,
      ie = !!x.matcap,
      Ht = !!B,
      $ = !!x.aoMap,
      tt = !!x.lightMap,
      K = !!x.bumpMap,
      ut = !!x.normalMap,
      A = !!x.displacementMap,
      Dt = !!x.emissiveMap,
      xt = !!x.metalnessMap,
      Ut = !!x.roughnessMap,
      ot = x.anisotropy > 0,
      T = x.clearcoat > 0,
      _ = x.dispersion > 0,
      I = x.iridescence > 0,
      X = x.sheen > 0,
      J = x.transmission > 0,
      q = ot && !!x.anisotropyMap,
      yt = T && !!x.clearcoatMap,
      lt = T && !!x.clearcoatNormalMap,
      Ct = T && !!x.clearcoatRoughnessMap,
      Nt = I && !!x.iridescenceMap,
      Q = I && !!x.iridescenceThicknessMap,
      it = X && !!x.sheenColorMap,
      Et = X && !!x.sheenRoughnessMap,
      Tt = !!x.specularMap,
      vt = !!x.specularColorMap,
      Yt = !!x.specularIntensityMap,
      D = J && !!x.transmissionMap,
      ht = J && !!x.thicknessMap,
      st = !!x.gradientMap,
      St = !!x.alphaMap,
      et = x.alphaTest > 0,
      Y = !!x.alphaHash,
      bt = !!x.extensions;
    let Gt = nn;
    x.toneMapped && (rt === null || rt.isXRRenderTarget === !0) && (Gt = i.toneMapping);
    const le = {
      shaderID: j,
      shaderType: x.type,
      shaderName: x.name,
      vertexShader: Ot,
      fragmentShader: jt,
      defines: x.defines,
      customVertexShaderID: ne,
      customFragmentShaderID: Z,
      isRawShaderMaterial: x.isRawShaderMaterial === !0,
      glslVersion: x.glslVersion,
      precision: u,
      batching: Lt,
      batchingColor: Lt && N._colorsTexture !== null,
      instancing: It,
      instancingColor: It && N.instanceColor !== null,
      instancingMorph: It && N.morphTexture !== null,
      outputColorSpace:
        rt === null ? i.outputColorSpace : rt.isXRRenderTarget === !0 ? rt.texture.colorSpace : bi,
      alphaToCoverage: !!x.alphaToCoverage,
      map: Vt,
      matcap: ie,
      envMap: Ht,
      envMapMode: Ht && B.mapping,
      envMapCubeUVHeight: nt,
      aoMap: $,
      lightMap: tt,
      bumpMap: K,
      normalMap: ut,
      displacementMap: A,
      emissiveMap: Dt,
      normalMapObjectSpace: ut && x.normalMapType === $c,
      normalMapTangentSpace: ut && x.normalMapType === Kn,
      metalnessMap: xt,
      roughnessMap: Ut,
      anisotropy: ot,
      anisotropyMap: q,
      clearcoat: T,
      clearcoatMap: yt,
      clearcoatNormalMap: lt,
      clearcoatRoughnessMap: Ct,
      dispersion: _,
      iridescence: I,
      iridescenceMap: Nt,
      iridescenceThicknessMap: Q,
      sheen: X,
      sheenColorMap: it,
      sheenRoughnessMap: Et,
      specularMap: Tt,
      specularColorMap: vt,
      specularIntensityMap: Yt,
      transmission: J,
      transmissionMap: D,
      thicknessMap: ht,
      gradientMap: st,
      opaque: x.transparent === !1 && x.blending === vi && x.alphaToCoverage === !1,
      alphaMap: St,
      alphaTest: et,
      alphaHash: Y,
      combine: x.combine,
      mapUv: Vt && g(x.map.channel),
      aoMapUv: $ && g(x.aoMap.channel),
      lightMapUv: tt && g(x.lightMap.channel),
      bumpMapUv: K && g(x.bumpMap.channel),
      normalMapUv: ut && g(x.normalMap.channel),
      displacementMapUv: A && g(x.displacementMap.channel),
      emissiveMapUv: Dt && g(x.emissiveMap.channel),
      metalnessMapUv: xt && g(x.metalnessMap.channel),
      roughnessMapUv: Ut && g(x.roughnessMap.channel),
      anisotropyMapUv: q && g(x.anisotropyMap.channel),
      clearcoatMapUv: yt && g(x.clearcoatMap.channel),
      clearcoatNormalMapUv: lt && g(x.clearcoatNormalMap.channel),
      clearcoatRoughnessMapUv: Ct && g(x.clearcoatRoughnessMap.channel),
      iridescenceMapUv: Nt && g(x.iridescenceMap.channel),
      iridescenceThicknessMapUv: Q && g(x.iridescenceThicknessMap.channel),
      sheenColorMapUv: it && g(x.sheenColorMap.channel),
      sheenRoughnessMapUv: Et && g(x.sheenRoughnessMap.channel),
      specularMapUv: Tt && g(x.specularMap.channel),
      specularColorMapUv: vt && g(x.specularColorMap.channel),
      specularIntensityMapUv: Yt && g(x.specularIntensityMap.channel),
      transmissionMapUv: D && g(x.transmissionMap.channel),
      thicknessMapUv: ht && g(x.thicknessMap.channel),
      alphaMapUv: St && g(x.alphaMap.channel),
      vertexTangents: !!k.attributes.tangent && (ut || ot),
      vertexColors: x.vertexColors,
      vertexAlphas:
        x.vertexColors === !0 && !!k.attributes.color && k.attributes.color.itemSize === 4,
      pointsUvs: N.isPoints === !0 && !!k.attributes.uv && (Vt || St),
      fog: !!z,
      useFog: x.fog === !0,
      fogExp2: !!z && z.isFogExp2,
      flatShading:
        x.wireframe === !1 &&
        (x.flatShading === !0 ||
          (k.attributes.normal === void 0 &&
            ut === !1 &&
            (x.isMeshLambertMaterial ||
              x.isMeshPhongMaterial ||
              x.isMeshStandardMaterial ||
              x.isMeshPhysicalMaterial))),
      sizeAttenuation: x.sizeAttenuation === !0,
      logarithmicDepthBuffer: f,
      reversedDepthBuffer: at,
      skinning: N.isSkinnedMesh === !0,
      morphTargets: k.morphAttributes.position !== void 0,
      morphNormals: k.morphAttributes.normal !== void 0,
      morphColors: k.morphAttributes.color !== void 0,
      morphTargetsCount: _t,
      morphTextureStride: gt,
      numDirLights: b.directional.length,
      numPointLights: b.point.length,
      numSpotLights: b.spot.length,
      numSpotLightMaps: b.spotLightMap.length,
      numRectAreaLights: b.rectArea.length,
      numHemiLights: b.hemi.length,
      numDirLightShadows: b.directionalShadowMap.length,
      numPointLightShadows: b.pointShadowMap.length,
      numSpotLightShadows: b.spotShadowMap.length,
      numSpotLightShadowsWithMaps: b.numSpotLightShadowsWithMaps,
      numLightProbes: b.numLightProbes,
      numClippingPlanes: r.numPlanes,
      numClipIntersection: r.numIntersection,
      dithering: x.dithering,
      shadowMapEnabled: i.shadowMap.enabled && H.length > 0,
      shadowMapType: i.shadowMap.type,
      toneMapping: Gt,
      decodeVideoTexture:
        Vt && x.map.isVideoTexture === !0 && $t.getTransfer(x.map.colorSpace) === te,
      decodeVideoTextureEmissive:
        Dt &&
        x.emissiveMap.isVideoTexture === !0 &&
        $t.getTransfer(x.emissiveMap.colorSpace) === te,
      premultipliedAlpha: x.premultipliedAlpha,
      doubleSided: x.side === gn,
      flipSided: x.side === Pe,
      useDepthPacking: x.depthPacking >= 0,
      depthPacking: x.depthPacking || 0,
      index0AttributeName: x.index0AttributeName,
      extensionClipCullDistance:
        bt && x.extensions.clipCullDistance === !0 && e.has('WEBGL_clip_cull_distance'),
      extensionMultiDraw:
        ((bt && x.extensions.multiDraw === !0) || Lt) && e.has('WEBGL_multi_draw'),
      rendererExtensionParallelShaderCompile: e.has('KHR_parallel_shader_compile'),
      customProgramCacheKey: x.customProgramCacheKey(),
    };
    return (
      (le.vertexUv1s = l.has(1)),
      (le.vertexUv2s = l.has(2)),
      (le.vertexUv3s = l.has(3)),
      l.clear(),
      le
    );
  }
  function m(x) {
    const b = [];
    if (
      (x.shaderID
        ? b.push(x.shaderID)
        : (b.push(x.customVertexShaderID), b.push(x.customFragmentShaderID)),
      x.defines !== void 0)
    )
      for (const H in x.defines) (b.push(H), b.push(x.defines[H]));
    return (
      x.isRawShaderMaterial === !1 && (d(b, x), E(b, x), b.push(i.outputColorSpace)),
      b.push(x.customProgramCacheKey),
      b.join()
    );
  }
  function d(x, b) {
    (x.push(b.precision),
      x.push(b.outputColorSpace),
      x.push(b.envMapMode),
      x.push(b.envMapCubeUVHeight),
      x.push(b.mapUv),
      x.push(b.alphaMapUv),
      x.push(b.lightMapUv),
      x.push(b.aoMapUv),
      x.push(b.bumpMapUv),
      x.push(b.normalMapUv),
      x.push(b.displacementMapUv),
      x.push(b.emissiveMapUv),
      x.push(b.metalnessMapUv),
      x.push(b.roughnessMapUv),
      x.push(b.anisotropyMapUv),
      x.push(b.clearcoatMapUv),
      x.push(b.clearcoatNormalMapUv),
      x.push(b.clearcoatRoughnessMapUv),
      x.push(b.iridescenceMapUv),
      x.push(b.iridescenceThicknessMapUv),
      x.push(b.sheenColorMapUv),
      x.push(b.sheenRoughnessMapUv),
      x.push(b.specularMapUv),
      x.push(b.specularColorMapUv),
      x.push(b.specularIntensityMapUv),
      x.push(b.transmissionMapUv),
      x.push(b.thicknessMapUv),
      x.push(b.combine),
      x.push(b.fogExp2),
      x.push(b.sizeAttenuation),
      x.push(b.morphTargetsCount),
      x.push(b.morphAttributeCount),
      x.push(b.numDirLights),
      x.push(b.numPointLights),
      x.push(b.numSpotLights),
      x.push(b.numSpotLightMaps),
      x.push(b.numHemiLights),
      x.push(b.numRectAreaLights),
      x.push(b.numDirLightShadows),
      x.push(b.numPointLightShadows),
      x.push(b.numSpotLightShadows),
      x.push(b.numSpotLightShadowsWithMaps),
      x.push(b.numLightProbes),
      x.push(b.shadowMapType),
      x.push(b.toneMapping),
      x.push(b.numClippingPlanes),
      x.push(b.numClipIntersection),
      x.push(b.depthPacking));
  }
  function E(x, b) {
    (a.disableAll(),
      b.instancing && a.enable(0),
      b.instancingColor && a.enable(1),
      b.instancingMorph && a.enable(2),
      b.matcap && a.enable(3),
      b.envMap && a.enable(4),
      b.normalMapObjectSpace && a.enable(5),
      b.normalMapTangentSpace && a.enable(6),
      b.clearcoat && a.enable(7),
      b.iridescence && a.enable(8),
      b.alphaTest && a.enable(9),
      b.vertexColors && a.enable(10),
      b.vertexAlphas && a.enable(11),
      b.vertexUv1s && a.enable(12),
      b.vertexUv2s && a.enable(13),
      b.vertexUv3s && a.enable(14),
      b.vertexTangents && a.enable(15),
      b.anisotropy && a.enable(16),
      b.alphaHash && a.enable(17),
      b.batching && a.enable(18),
      b.dispersion && a.enable(19),
      b.batchingColor && a.enable(20),
      b.gradientMap && a.enable(21),
      x.push(a.mask),
      a.disableAll(),
      b.fog && a.enable(0),
      b.useFog && a.enable(1),
      b.flatShading && a.enable(2),
      b.logarithmicDepthBuffer && a.enable(3),
      b.reversedDepthBuffer && a.enable(4),
      b.skinning && a.enable(5),
      b.morphTargets && a.enable(6),
      b.morphNormals && a.enable(7),
      b.morphColors && a.enable(8),
      b.premultipliedAlpha && a.enable(9),
      b.shadowMapEnabled && a.enable(10),
      b.doubleSided && a.enable(11),
      b.flipSided && a.enable(12),
      b.useDepthPacking && a.enable(13),
      b.dithering && a.enable(14),
      b.transmission && a.enable(15),
      b.sheen && a.enable(16),
      b.opaque && a.enable(17),
      b.pointsUvs && a.enable(18),
      b.decodeVideoTexture && a.enable(19),
      b.decodeVideoTextureEmissive && a.enable(20),
      b.alphaToCoverage && a.enable(21),
      x.push(a.mask));
  }
  function y(x) {
    const b = p[x.type];
    let H;
    if (b) {
      const C = tn[b];
      H = Cu.clone(C.uniforms);
    } else H = x.uniforms;
    return H;
  }
  function S(x, b) {
    let H = h.get(b);
    return (H !== void 0 ? ++H.usedTimes : ((H = new ug(i, b, x, s)), c.push(H), h.set(b, H)), H);
  }
  function R(x) {
    if (--x.usedTimes === 0) {
      const b = c.indexOf(x);
      ((c[b] = c[c.length - 1]), c.pop(), h.delete(x.cacheKey), x.destroy());
    }
  }
  function w(x) {
    o.remove(x);
  }
  function P() {
    o.dispose();
  }
  return {
    getParameters: M,
    getProgramCacheKey: m,
    getUniforms: y,
    acquireProgram: S,
    releaseProgram: R,
    releaseShaderCache: w,
    programs: c,
    dispose: P,
  };
}
function gg() {
  let i = new WeakMap();
  function t(a) {
    return i.has(a);
  }
  function e(a) {
    let o = i.get(a);
    return (o === void 0 && ((o = {}), i.set(a, o)), o);
  }
  function n(a) {
    i.delete(a);
  }
  function s(a, o, l) {
    i.get(a)[o] = l;
  }
  function r() {
    i = new WeakMap();
  }
  return { has: t, get: e, remove: n, update: s, dispose: r };
}
function _g(i, t) {
  return i.groupOrder !== t.groupOrder
    ? i.groupOrder - t.groupOrder
    : i.renderOrder !== t.renderOrder
      ? i.renderOrder - t.renderOrder
      : i.material.id !== t.material.id
        ? i.material.id - t.material.id
        : i.materialVariant !== t.materialVariant
          ? i.materialVariant - t.materialVariant
          : i.z !== t.z
            ? i.z - t.z
            : i.id - t.id;
}
function xl(i, t) {
  return i.groupOrder !== t.groupOrder
    ? i.groupOrder - t.groupOrder
    : i.renderOrder !== t.renderOrder
      ? i.renderOrder - t.renderOrder
      : i.z !== t.z
        ? t.z - i.z
        : i.id - t.id;
}
function vl() {
  const i = [];
  let t = 0;
  const e = [],
    n = [],
    s = [];
  function r() {
    ((t = 0), (e.length = 0), (n.length = 0), (s.length = 0));
  }
  function a(u) {
    let p = 0;
    return (u.isInstancedMesh && (p += 2), u.isSkinnedMesh && (p += 1), p);
  }
  function o(u, p, g, M, m, d) {
    let E = i[t];
    return (
      E === void 0
        ? ((E = {
            id: u.id,
            object: u,
            geometry: p,
            material: g,
            materialVariant: a(u),
            groupOrder: M,
            renderOrder: u.renderOrder,
            z: m,
            group: d,
          }),
          (i[t] = E))
        : ((E.id = u.id),
          (E.object = u),
          (E.geometry = p),
          (E.material = g),
          (E.materialVariant = a(u)),
          (E.groupOrder = M),
          (E.renderOrder = u.renderOrder),
          (E.z = m),
          (E.group = d)),
      t++,
      E
    );
  }
  function l(u, p, g, M, m, d) {
    const E = o(u, p, g, M, m, d);
    g.transmission > 0 ? n.push(E) : g.transparent === !0 ? s.push(E) : e.push(E);
  }
  function c(u, p, g, M, m, d) {
    const E = o(u, p, g, M, m, d);
    g.transmission > 0 ? n.unshift(E) : g.transparent === !0 ? s.unshift(E) : e.unshift(E);
  }
  function h(u, p) {
    (e.length > 1 && e.sort(u || _g),
      n.length > 1 && n.sort(p || xl),
      s.length > 1 && s.sort(p || xl));
  }
  function f() {
    for (let u = t, p = i.length; u < p; u++) {
      const g = i[u];
      if (g.id === null) break;
      ((g.id = null),
        (g.object = null),
        (g.geometry = null),
        (g.material = null),
        (g.group = null));
    }
  }
  return {
    opaque: e,
    transmissive: n,
    transparent: s,
    init: r,
    push: l,
    unshift: c,
    finish: f,
    sort: h,
  };
}
function xg() {
  let i = new WeakMap();
  function t(n, s) {
    const r = i.get(n);
    let a;
    return (
      r === void 0
        ? ((a = new vl()), i.set(n, [a]))
        : s >= r.length
          ? ((a = new vl()), r.push(a))
          : (a = r[s]),
      a
    );
  }
  function e() {
    i = new WeakMap();
  }
  return { get: t, dispose: e };
}
function vg() {
  const i = {};
  return {
    get: function (t) {
      if (i[t.id] !== void 0) return i[t.id];
      let e;
      switch (t.type) {
        case 'DirectionalLight':
          e = { direction: new L(), color: new zt() };
          break;
        case 'SpotLight':
          e = {
            position: new L(),
            direction: new L(),
            color: new zt(),
            distance: 0,
            coneCos: 0,
            penumbraCos: 0,
            decay: 0,
          };
          break;
        case 'PointLight':
          e = { position: new L(), color: new zt(), distance: 0, decay: 0 };
          break;
        case 'HemisphereLight':
          e = { direction: new L(), skyColor: new zt(), groundColor: new zt() };
          break;
        case 'RectAreaLight':
          e = { color: new zt(), position: new L(), halfWidth: new L(), halfHeight: new L() };
          break;
      }
      return ((i[t.id] = e), e);
    },
  };
}
function Mg() {
  const i = {};
  return {
    get: function (t) {
      if (i[t.id] !== void 0) return i[t.id];
      let e;
      switch (t.type) {
        case 'DirectionalLight':
          e = {
            shadowIntensity: 1,
            shadowBias: 0,
            shadowNormalBias: 0,
            shadowRadius: 1,
            shadowMapSize: new ct(),
          };
          break;
        case 'SpotLight':
          e = {
            shadowIntensity: 1,
            shadowBias: 0,
            shadowNormalBias: 0,
            shadowRadius: 1,
            shadowMapSize: new ct(),
          };
          break;
        case 'PointLight':
          e = {
            shadowIntensity: 1,
            shadowBias: 0,
            shadowNormalBias: 0,
            shadowRadius: 1,
            shadowMapSize: new ct(),
            shadowCameraNear: 1,
            shadowCameraFar: 1e3,
          };
          break;
      }
      return ((i[t.id] = e), e);
    },
  };
}
let Sg = 0;
function yg(i, t) {
  return (t.castShadow ? 2 : 0) - (i.castShadow ? 2 : 0) + (t.map ? 1 : 0) - (i.map ? 1 : 0);
}
function Eg(i) {
  const t = new vg(),
    e = Mg(),
    n = {
      version: 0,
      hash: {
        directionalLength: -1,
        pointLength: -1,
        spotLength: -1,
        rectAreaLength: -1,
        hemiLength: -1,
        numDirectionalShadows: -1,
        numPointShadows: -1,
        numSpotShadows: -1,
        numSpotMaps: -1,
        numLightProbes: -1,
      },
      ambient: [0, 0, 0],
      probe: [],
      directional: [],
      directionalShadow: [],
      directionalShadowMap: [],
      directionalShadowMatrix: [],
      spot: [],
      spotLightMap: [],
      spotShadow: [],
      spotShadowMap: [],
      spotLightMatrix: [],
      rectArea: [],
      rectAreaLTC1: null,
      rectAreaLTC2: null,
      point: [],
      pointShadow: [],
      pointShadowMap: [],
      pointShadowMatrix: [],
      hemi: [],
      numSpotLightShadowsWithMaps: 0,
      numLightProbes: 0,
    };
  for (let c = 0; c < 9; c++) n.probe.push(new L());
  const s = new L(),
    r = new oe(),
    a = new oe();
  function o(c) {
    let h = 0,
      f = 0,
      u = 0;
    for (let b = 0; b < 9; b++) n.probe[b].set(0, 0, 0);
    let p = 0,
      g = 0,
      M = 0,
      m = 0,
      d = 0,
      E = 0,
      y = 0,
      S = 0,
      R = 0,
      w = 0,
      P = 0;
    c.sort(yg);
    for (let b = 0, H = c.length; b < H; b++) {
      const C = c[b],
        N = C.color,
        z = C.intensity,
        k = C.distance;
      let F = null;
      if (
        (C.shadow &&
          C.shadow.map &&
          (C.shadow.map.texture.format === Ei
            ? (F = C.shadow.map.texture)
            : (F = C.shadow.map.depthTexture || C.shadow.map.texture)),
        C.isAmbientLight)
      )
        ((h += N.r * z), (f += N.g * z), (u += N.b * z));
      else if (C.isLightProbe) {
        for (let O = 0; O < 9; O++) n.probe[O].addScaledVector(C.sh.coefficients[O], z);
        P++;
      } else if (C.isDirectionalLight) {
        const O = t.get(C);
        if ((O.color.copy(C.color).multiplyScalar(C.intensity), C.castShadow)) {
          const B = C.shadow,
            nt = e.get(C);
          ((nt.shadowIntensity = B.intensity),
            (nt.shadowBias = B.bias),
            (nt.shadowNormalBias = B.normalBias),
            (nt.shadowRadius = B.radius),
            (nt.shadowMapSize = B.mapSize),
            (n.directionalShadow[p] = nt),
            (n.directionalShadowMap[p] = F),
            (n.directionalShadowMatrix[p] = C.shadow.matrix),
            E++);
        }
        ((n.directional[p] = O), p++);
      } else if (C.isSpotLight) {
        const O = t.get(C);
        (O.position.setFromMatrixPosition(C.matrixWorld),
          O.color.copy(N).multiplyScalar(z),
          (O.distance = k),
          (O.coneCos = Math.cos(C.angle)),
          (O.penumbraCos = Math.cos(C.angle * (1 - C.penumbra))),
          (O.decay = C.decay),
          (n.spot[M] = O));
        const B = C.shadow;
        if (
          (C.map && ((n.spotLightMap[R] = C.map), R++, B.updateMatrices(C), C.castShadow && w++),
          (n.spotLightMatrix[M] = B.matrix),
          C.castShadow)
        ) {
          const nt = e.get(C);
          ((nt.shadowIntensity = B.intensity),
            (nt.shadowBias = B.bias),
            (nt.shadowNormalBias = B.normalBias),
            (nt.shadowRadius = B.radius),
            (nt.shadowMapSize = B.mapSize),
            (n.spotShadow[M] = nt),
            (n.spotShadowMap[M] = F),
            S++);
        }
        M++;
      } else if (C.isRectAreaLight) {
        const O = t.get(C);
        (O.color.copy(N).multiplyScalar(z),
          O.halfWidth.set(C.width * 0.5, 0, 0),
          O.halfHeight.set(0, C.height * 0.5, 0),
          (n.rectArea[m] = O),
          m++);
      } else if (C.isPointLight) {
        const O = t.get(C);
        if (
          (O.color.copy(C.color).multiplyScalar(C.intensity),
          (O.distance = C.distance),
          (O.decay = C.decay),
          C.castShadow)
        ) {
          const B = C.shadow,
            nt = e.get(C);
          ((nt.shadowIntensity = B.intensity),
            (nt.shadowBias = B.bias),
            (nt.shadowNormalBias = B.normalBias),
            (nt.shadowRadius = B.radius),
            (nt.shadowMapSize = B.mapSize),
            (nt.shadowCameraNear = B.camera.near),
            (nt.shadowCameraFar = B.camera.far),
            (n.pointShadow[g] = nt),
            (n.pointShadowMap[g] = F),
            (n.pointShadowMatrix[g] = C.shadow.matrix),
            y++);
        }
        ((n.point[g] = O), g++);
      } else if (C.isHemisphereLight) {
        const O = t.get(C);
        (O.skyColor.copy(C.color).multiplyScalar(z),
          O.groundColor.copy(C.groundColor).multiplyScalar(z),
          (n.hemi[d] = O),
          d++);
      }
    }
    (m > 0 &&
      (i.has('OES_texture_float_linear') === !0
        ? ((n.rectAreaLTC1 = ft.LTC_FLOAT_1), (n.rectAreaLTC2 = ft.LTC_FLOAT_2))
        : ((n.rectAreaLTC1 = ft.LTC_HALF_1), (n.rectAreaLTC2 = ft.LTC_HALF_2))),
      (n.ambient[0] = h),
      (n.ambient[1] = f),
      (n.ambient[2] = u));
    const x = n.hash;
    (x.directionalLength !== p ||
      x.pointLength !== g ||
      x.spotLength !== M ||
      x.rectAreaLength !== m ||
      x.hemiLength !== d ||
      x.numDirectionalShadows !== E ||
      x.numPointShadows !== y ||
      x.numSpotShadows !== S ||
      x.numSpotMaps !== R ||
      x.numLightProbes !== P) &&
      ((n.directional.length = p),
      (n.spot.length = M),
      (n.rectArea.length = m),
      (n.point.length = g),
      (n.hemi.length = d),
      (n.directionalShadow.length = E),
      (n.directionalShadowMap.length = E),
      (n.pointShadow.length = y),
      (n.pointShadowMap.length = y),
      (n.spotShadow.length = S),
      (n.spotShadowMap.length = S),
      (n.directionalShadowMatrix.length = E),
      (n.pointShadowMatrix.length = y),
      (n.spotLightMatrix.length = S + R - w),
      (n.spotLightMap.length = R),
      (n.numSpotLightShadowsWithMaps = w),
      (n.numLightProbes = P),
      (x.directionalLength = p),
      (x.pointLength = g),
      (x.spotLength = M),
      (x.rectAreaLength = m),
      (x.hemiLength = d),
      (x.numDirectionalShadows = E),
      (x.numPointShadows = y),
      (x.numSpotShadows = S),
      (x.numSpotMaps = R),
      (x.numLightProbes = P),
      (n.version = Sg++));
  }
  function l(c, h) {
    let f = 0,
      u = 0,
      p = 0,
      g = 0,
      M = 0;
    const m = h.matrixWorldInverse;
    for (let d = 0, E = c.length; d < E; d++) {
      const y = c[d];
      if (y.isDirectionalLight) {
        const S = n.directional[f];
        (S.direction.setFromMatrixPosition(y.matrixWorld),
          s.setFromMatrixPosition(y.target.matrixWorld),
          S.direction.sub(s),
          S.direction.transformDirection(m),
          f++);
      } else if (y.isSpotLight) {
        const S = n.spot[p];
        (S.position.setFromMatrixPosition(y.matrixWorld),
          S.position.applyMatrix4(m),
          S.direction.setFromMatrixPosition(y.matrixWorld),
          s.setFromMatrixPosition(y.target.matrixWorld),
          S.direction.sub(s),
          S.direction.transformDirection(m),
          p++);
      } else if (y.isRectAreaLight) {
        const S = n.rectArea[g];
        (S.position.setFromMatrixPosition(y.matrixWorld),
          S.position.applyMatrix4(m),
          a.identity(),
          r.copy(y.matrixWorld),
          r.premultiply(m),
          a.extractRotation(r),
          S.halfWidth.set(y.width * 0.5, 0, 0),
          S.halfHeight.set(0, y.height * 0.5, 0),
          S.halfWidth.applyMatrix4(a),
          S.halfHeight.applyMatrix4(a),
          g++);
      } else if (y.isPointLight) {
        const S = n.point[u];
        (S.position.setFromMatrixPosition(y.matrixWorld), S.position.applyMatrix4(m), u++);
      } else if (y.isHemisphereLight) {
        const S = n.hemi[M];
        (S.direction.setFromMatrixPosition(y.matrixWorld), S.direction.transformDirection(m), M++);
      }
    }
  }
  return { setup: o, setupView: l, state: n };
}
function Ml(i) {
  const t = new Eg(i),
    e = [],
    n = [];
  function s(h) {
    ((c.camera = h), (e.length = 0), (n.length = 0));
  }
  function r(h) {
    e.push(h);
  }
  function a(h) {
    n.push(h);
  }
  function o() {
    t.setup(e);
  }
  function l(h) {
    t.setupView(e, h);
  }
  const c = {
    lightsArray: e,
    shadowsArray: n,
    camera: null,
    lights: t,
    transmissionRenderTarget: {},
  };
  return { init: s, state: c, setupLights: o, setupLightsView: l, pushLight: r, pushShadow: a };
}
function bg(i) {
  let t = new WeakMap();
  function e(s, r = 0) {
    const a = t.get(s);
    let o;
    return (
      a === void 0
        ? ((o = new Ml(i)), t.set(s, [o]))
        : r >= a.length
          ? ((o = new Ml(i)), a.push(o))
          : (o = a[r]),
      o
    );
  }
  function n() {
    t = new WeakMap();
  }
  return { get: e, dispose: n };
}
const Tg = `void main() {
	gl_Position = vec4( position, 1.0 );
}`,
  Ag = `uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ).rg;
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ).r;
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( max( 0.0, squared_mean - mean * mean ) );
	gl_FragColor = vec4( mean, std_dev, 0.0, 1.0 );
}`,
  wg = [
    new L(1, 0, 0),
    new L(-1, 0, 0),
    new L(0, 1, 0),
    new L(0, -1, 0),
    new L(0, 0, 1),
    new L(0, 0, -1),
  ],
  Rg = [
    new L(0, -1, 0),
    new L(0, -1, 0),
    new L(0, 0, 1),
    new L(0, 0, -1),
    new L(0, -1, 0),
    new L(0, -1, 0),
  ],
  Sl = new oe(),
  Fi = new L(),
  Vr = new L();
function Cg(i, t, e) {
  let n = new Ks();
  const s = new ct(),
    r = new ct(),
    a = new ue(),
    o = new Uu(),
    l = new Nu(),
    c = {},
    h = e.maxTextureSize,
    f = { [Un]: Pe, [Pe]: Un, [gn]: gn },
    u = new on({
      defines: { VSM_SAMPLES: 8 },
      uniforms: {
        shadow_pass: { value: null },
        resolution: { value: new ct() },
        radius: { value: 4 },
      },
      vertexShader: Tg,
      fragmentShader: Ag,
    }),
    p = u.clone();
  p.defines.HORIZONTAL_PASS = 1;
  const g = new xe();
  g.setAttribute('position', new Be(new Float32Array([-1, -1, 0.5, 3, -1, 0.5, -1, 3, 0.5]), 3));
  const M = new En(g, u),
    m = this;
  ((this.enabled = !1), (this.autoUpdate = !0), (this.needsUpdate = !1), (this.type = Ns));
  let d = this.type;
  this.render = function (w, P, x) {
    if (m.enabled === !1 || (m.autoUpdate === !1 && m.needsUpdate === !1) || w.length === 0) return;
    this.type === wc &&
      (Ft('WebGLShadowMap: PCFSoftShadowMap has been deprecated. Using PCFShadowMap instead.'),
      (this.type = Ns));
    const b = i.getRenderTarget(),
      H = i.getActiveCubeFace(),
      C = i.getActiveMipmapLevel(),
      N = i.state;
    (N.setBlending(vn),
      N.buffers.depth.getReversed() === !0
        ? N.buffers.color.setClear(0, 0, 0, 0)
        : N.buffers.color.setClear(1, 1, 1, 1),
      N.buffers.depth.setTest(!0),
      N.setScissorTest(!1));
    const z = d !== this.type;
    z &&
      P.traverse(function (k) {
        k.material &&
          (Array.isArray(k.material)
            ? k.material.forEach((F) => (F.needsUpdate = !0))
            : (k.material.needsUpdate = !0));
      });
    for (let k = 0, F = w.length; k < F; k++) {
      const O = w[k],
        B = O.shadow;
      if (B === void 0) {
        Ft('WebGLShadowMap:', O, 'has no shadow.');
        continue;
      }
      if (B.autoUpdate === !1 && B.needsUpdate === !1) continue;
      s.copy(B.mapSize);
      const nt = B.getFrameExtents();
      (s.multiply(nt),
        r.copy(B.mapSize),
        (s.x > h || s.y > h) &&
          (s.x > h && ((r.x = Math.floor(h / nt.x)), (s.x = r.x * nt.x), (B.mapSize.x = r.x)),
          s.y > h && ((r.y = Math.floor(h / nt.y)), (s.y = r.y * nt.y), (B.mapSize.y = r.y))));
      const j = i.state.buffers.depth.getReversed();
      if (((B.camera._reversedDepth = j), B.map === null || z === !0)) {
        if (
          (B.map !== null &&
            (B.map.depthTexture !== null &&
              (B.map.depthTexture.dispose(), (B.map.depthTexture = null)),
            B.map.dispose()),
          this.type === Oi)
        ) {
          if (O.isPointLight) {
            Ft(
              'WebGLShadowMap: VSM shadow maps are not supported for PointLights. Use PCF or BasicShadowMap instead.'
            );
            continue;
          }
          ((B.map = new rn(s.x, s.y, {
            format: Ei,
            type: Sn,
            minFilter: Ae,
            magFilter: Ae,
            generateMipmaps: !1,
          })),
            (B.map.texture.name = O.name + '.shadowMap'),
            (B.map.depthTexture = new Zi(s.x, s.y, en)),
            (B.map.depthTexture.name = O.name + '.shadowMapDepth'),
            (B.map.depthTexture.format = yn),
            (B.map.depthTexture.compareFunction = null),
            (B.map.depthTexture.minFilter = me),
            (B.map.depthTexture.magFilter = me));
        } else
          (O.isPointLight
            ? ((B.map = new dc(s.x)), (B.map.depthTexture = new Jh(s.x, an)))
            : ((B.map = new rn(s.x, s.y)), (B.map.depthTexture = new Zi(s.x, s.y, an))),
            (B.map.depthTexture.name = O.name + '.shadowMap'),
            (B.map.depthTexture.format = yn),
            this.type === Ns
              ? ((B.map.depthTexture.compareFunction = j ? qa : Xa),
                (B.map.depthTexture.minFilter = Ae),
                (B.map.depthTexture.magFilter = Ae))
              : ((B.map.depthTexture.compareFunction = null),
                (B.map.depthTexture.minFilter = me),
                (B.map.depthTexture.magFilter = me)));
        B.camera.updateProjectionMatrix();
      }
      const mt = B.map.isWebGLCubeRenderTarget ? 6 : 1;
      for (let _t = 0; _t < mt; _t++) {
        if (B.map.isWebGLCubeRenderTarget) (i.setRenderTarget(B.map, _t), i.clear());
        else {
          _t === 0 && (i.setRenderTarget(B.map), i.clear());
          const gt = B.getViewport(_t);
          (a.set(r.x * gt.x, r.y * gt.y, r.x * gt.z, r.y * gt.w), N.viewport(a));
        }
        if (O.isPointLight) {
          const gt = B.camera,
            Ot = B.matrix,
            jt = O.distance || gt.far;
          (jt !== gt.far && ((gt.far = jt), gt.updateProjectionMatrix()),
            Fi.setFromMatrixPosition(O.matrixWorld),
            gt.position.copy(Fi),
            Vr.copy(gt.position),
            Vr.add(wg[_t]),
            gt.up.copy(Rg[_t]),
            gt.lookAt(Vr),
            gt.updateMatrixWorld(),
            Ot.makeTranslation(-Fi.x, -Fi.y, -Fi.z),
            Sl.multiplyMatrices(gt.projectionMatrix, gt.matrixWorldInverse),
            B._frustum.setFromProjectionMatrix(Sl, gt.coordinateSystem, gt.reversedDepth));
        } else B.updateMatrices(O);
        ((n = B.getFrustum()), S(P, x, B.camera, O, this.type));
      }
      (B.isPointLightShadow !== !0 && this.type === Oi && E(B, x), (B.needsUpdate = !1));
    }
    ((d = this.type), (m.needsUpdate = !1), i.setRenderTarget(b, H, C));
  };
  function E(w, P) {
    const x = t.update(M);
    (u.defines.VSM_SAMPLES !== w.blurSamples &&
      ((u.defines.VSM_SAMPLES = w.blurSamples),
      (p.defines.VSM_SAMPLES = w.blurSamples),
      (u.needsUpdate = !0),
      (p.needsUpdate = !0)),
      w.mapPass === null && (w.mapPass = new rn(s.x, s.y, { format: Ei, type: Sn })),
      (u.uniforms.shadow_pass.value = w.map.depthTexture),
      (u.uniforms.resolution.value = w.mapSize),
      (u.uniforms.radius.value = w.radius),
      i.setRenderTarget(w.mapPass),
      i.clear(),
      i.renderBufferDirect(P, null, x, u, M, null),
      (p.uniforms.shadow_pass.value = w.mapPass.texture),
      (p.uniforms.resolution.value = w.mapSize),
      (p.uniforms.radius.value = w.radius),
      i.setRenderTarget(w.map),
      i.clear(),
      i.renderBufferDirect(P, null, x, p, M, null));
  }
  function y(w, P, x, b) {
    let H = null;
    const C = x.isPointLight === !0 ? w.customDistanceMaterial : w.customDepthMaterial;
    if (C !== void 0) H = C;
    else if (
      ((H = x.isPointLight === !0 ? l : o),
      (i.localClippingEnabled &&
        P.clipShadows === !0 &&
        Array.isArray(P.clippingPlanes) &&
        P.clippingPlanes.length !== 0) ||
        (P.displacementMap && P.displacementScale !== 0) ||
        (P.alphaMap && P.alphaTest > 0) ||
        (P.map && P.alphaTest > 0) ||
        P.alphaToCoverage === !0)
    ) {
      const N = H.uuid,
        z = P.uuid;
      let k = c[N];
      k === void 0 && ((k = {}), (c[N] = k));
      let F = k[z];
      (F === void 0 && ((F = H.clone()), (k[z] = F), P.addEventListener('dispose', R)), (H = F));
    }
    if (
      ((H.visible = P.visible),
      (H.wireframe = P.wireframe),
      b === Oi
        ? (H.side = P.shadowSide !== null ? P.shadowSide : P.side)
        : (H.side = P.shadowSide !== null ? P.shadowSide : f[P.side]),
      (H.alphaMap = P.alphaMap),
      (H.alphaTest = P.alphaToCoverage === !0 ? 0.5 : P.alphaTest),
      (H.map = P.map),
      (H.clipShadows = P.clipShadows),
      (H.clippingPlanes = P.clippingPlanes),
      (H.clipIntersection = P.clipIntersection),
      (H.displacementMap = P.displacementMap),
      (H.displacementScale = P.displacementScale),
      (H.displacementBias = P.displacementBias),
      (H.wireframeLinewidth = P.wireframeLinewidth),
      (H.linewidth = P.linewidth),
      x.isPointLight === !0 && H.isMeshDistanceMaterial === !0)
    ) {
      const N = i.properties.get(H);
      N.light = x;
    }
    return H;
  }
  function S(w, P, x, b, H) {
    if (w.visible === !1) return;
    if (
      w.layers.test(P.layers) &&
      (w.isMesh || w.isLine || w.isPoints) &&
      (w.castShadow || (w.receiveShadow && H === Oi)) &&
      (!w.frustumCulled || n.intersectsObject(w))
    ) {
      w.modelViewMatrix.multiplyMatrices(x.matrixWorldInverse, w.matrixWorld);
      const z = t.update(w),
        k = w.material;
      if (Array.isArray(k)) {
        const F = z.groups;
        for (let O = 0, B = F.length; O < B; O++) {
          const nt = F[O],
            j = k[nt.materialIndex];
          if (j && j.visible) {
            const mt = y(w, j, b, H);
            (w.onBeforeShadow(i, w, P, x, z, mt, nt),
              i.renderBufferDirect(x, null, z, mt, w, nt),
              w.onAfterShadow(i, w, P, x, z, mt, nt));
          }
        }
      } else if (k.visible) {
        const F = y(w, k, b, H);
        (w.onBeforeShadow(i, w, P, x, z, F, null),
          i.renderBufferDirect(x, null, z, F, w, null),
          w.onAfterShadow(i, w, P, x, z, F, null));
      }
    }
    const N = w.children;
    for (let z = 0, k = N.length; z < k; z++) S(N[z], P, x, b, H);
  }
  function R(w) {
    w.target.removeEventListener('dispose', R);
    for (const x in c) {
      const b = c[x],
        H = w.target.uuid;
      H in b && (b[H].dispose(), delete b[H]);
    }
  }
}
function Pg(i, t) {
  function e() {
    let D = !1;
    const ht = new ue();
    let st = null;
    const St = new ue(0, 0, 0, 0);
    return {
      setMask: function (et) {
        st !== et && !D && (i.colorMask(et, et, et, et), (st = et));
      },
      setLocked: function (et) {
        D = et;
      },
      setClear: function (et, Y, bt, Gt, le) {
        (le === !0 && ((et *= Gt), (Y *= Gt), (bt *= Gt)),
          ht.set(et, Y, bt, Gt),
          St.equals(ht) === !1 && (i.clearColor(et, Y, bt, Gt), St.copy(ht)));
      },
      reset: function () {
        ((D = !1), (st = null), St.set(-1, 0, 0, 0));
      },
    };
  }
  function n() {
    let D = !1,
      ht = !1,
      st = null,
      St = null,
      et = null;
    return {
      setReversed: function (Y) {
        if (ht !== Y) {
          const bt = t.get('EXT_clip_control');
          (Y
            ? bt.clipControlEXT(bt.LOWER_LEFT_EXT, bt.ZERO_TO_ONE_EXT)
            : bt.clipControlEXT(bt.LOWER_LEFT_EXT, bt.NEGATIVE_ONE_TO_ONE_EXT),
            (ht = Y));
          const Gt = et;
          ((et = null), this.setClear(Gt));
        }
      },
      getReversed: function () {
        return ht;
      },
      setTest: function (Y) {
        Y ? rt(i.DEPTH_TEST) : at(i.DEPTH_TEST);
      },
      setMask: function (Y) {
        st !== Y && !D && (i.depthMask(Y), (st = Y));
      },
      setFunc: function (Y) {
        if ((ht && (Y = ah[Y]), St !== Y)) {
          switch (Y) {
            case kr:
              i.depthFunc(i.NEVER);
              break;
            case Wr:
              i.depthFunc(i.ALWAYS);
              break;
            case Xr:
              i.depthFunc(i.LESS);
              break;
            case Si:
              i.depthFunc(i.LEQUAL);
              break;
            case qr:
              i.depthFunc(i.EQUAL);
              break;
            case Yr:
              i.depthFunc(i.GEQUAL);
              break;
            case Zr:
              i.depthFunc(i.GREATER);
              break;
            case Jr:
              i.depthFunc(i.NOTEQUAL);
              break;
            default:
              i.depthFunc(i.LEQUAL);
          }
          St = Y;
        }
      },
      setLocked: function (Y) {
        D = Y;
      },
      setClear: function (Y) {
        et !== Y && ((et = Y), ht && (Y = 1 - Y), i.clearDepth(Y));
      },
      reset: function () {
        ((D = !1), (st = null), (St = null), (et = null), (ht = !1));
      },
    };
  }
  function s() {
    let D = !1,
      ht = null,
      st = null,
      St = null,
      et = null,
      Y = null,
      bt = null,
      Gt = null,
      le = null;
    return {
      setTest: function (Qt) {
        D || (Qt ? rt(i.STENCIL_TEST) : at(i.STENCIL_TEST));
      },
      setMask: function (Qt) {
        ht !== Qt && !D && (i.stencilMask(Qt), (ht = Qt));
      },
      setFunc: function (Qt, cn, hn) {
        (st !== Qt || St !== cn || et !== hn) &&
          (i.stencilFunc(Qt, cn, hn), (st = Qt), (St = cn), (et = hn));
      },
      setOp: function (Qt, cn, hn) {
        (Y !== Qt || bt !== cn || Gt !== hn) &&
          (i.stencilOp(Qt, cn, hn), (Y = Qt), (bt = cn), (Gt = hn));
      },
      setLocked: function (Qt) {
        D = Qt;
      },
      setClear: function (Qt) {
        le !== Qt && (i.clearStencil(Qt), (le = Qt));
      },
      reset: function () {
        ((D = !1),
          (ht = null),
          (st = null),
          (St = null),
          (et = null),
          (Y = null),
          (bt = null),
          (Gt = null),
          (le = null));
      },
    };
  }
  const r = new e(),
    a = new n(),
    o = new s(),
    l = new WeakMap(),
    c = new WeakMap();
  let h = {},
    f = {},
    u = new WeakMap(),
    p = [],
    g = null,
    M = !1,
    m = null,
    d = null,
    E = null,
    y = null,
    S = null,
    R = null,
    w = null,
    P = new zt(0, 0, 0),
    x = 0,
    b = !1,
    H = null,
    C = null,
    N = null,
    z = null,
    k = null;
  const F = i.getParameter(i.MAX_COMBINED_TEXTURE_IMAGE_UNITS);
  let O = !1,
    B = 0;
  const nt = i.getParameter(i.VERSION);
  nt.indexOf('WebGL') !== -1
    ? ((B = parseFloat(/^WebGL (\d)/.exec(nt)[1])), (O = B >= 1))
    : nt.indexOf('OpenGL ES') !== -1 &&
      ((B = parseFloat(/^OpenGL ES (\d)/.exec(nt)[1])), (O = B >= 2));
  let j = null,
    mt = {};
  const _t = i.getParameter(i.SCISSOR_BOX),
    gt = i.getParameter(i.VIEWPORT),
    Ot = new ue().fromArray(_t),
    jt = new ue().fromArray(gt);
  function ne(D, ht, st, St) {
    const et = new Uint8Array(4),
      Y = i.createTexture();
    (i.bindTexture(D, Y),
      i.texParameteri(D, i.TEXTURE_MIN_FILTER, i.NEAREST),
      i.texParameteri(D, i.TEXTURE_MAG_FILTER, i.NEAREST));
    for (let bt = 0; bt < st; bt++)
      D === i.TEXTURE_3D || D === i.TEXTURE_2D_ARRAY
        ? i.texImage3D(ht, 0, i.RGBA, 1, 1, St, 0, i.RGBA, i.UNSIGNED_BYTE, et)
        : i.texImage2D(ht + bt, 0, i.RGBA, 1, 1, 0, i.RGBA, i.UNSIGNED_BYTE, et);
    return Y;
  }
  const Z = {};
  ((Z[i.TEXTURE_2D] = ne(i.TEXTURE_2D, i.TEXTURE_2D, 1)),
    (Z[i.TEXTURE_CUBE_MAP] = ne(i.TEXTURE_CUBE_MAP, i.TEXTURE_CUBE_MAP_POSITIVE_X, 6)),
    (Z[i.TEXTURE_2D_ARRAY] = ne(i.TEXTURE_2D_ARRAY, i.TEXTURE_2D_ARRAY, 1, 1)),
    (Z[i.TEXTURE_3D] = ne(i.TEXTURE_3D, i.TEXTURE_3D, 1, 1)),
    r.setClear(0, 0, 0, 1),
    a.setClear(1),
    o.setClear(0),
    rt(i.DEPTH_TEST),
    a.setFunc(Si),
    K(!1),
    ut(ho),
    rt(i.CULL_FACE),
    $(vn));
  function rt(D) {
    h[D] !== !0 && (i.enable(D), (h[D] = !0));
  }
  function at(D) {
    h[D] !== !1 && (i.disable(D), (h[D] = !1));
  }
  function It(D, ht) {
    return f[D] !== ht
      ? (i.bindFramebuffer(D, ht),
        (f[D] = ht),
        D === i.DRAW_FRAMEBUFFER && (f[i.FRAMEBUFFER] = ht),
        D === i.FRAMEBUFFER && (f[i.DRAW_FRAMEBUFFER] = ht),
        !0)
      : !1;
  }
  function Lt(D, ht) {
    let st = p,
      St = !1;
    if (D) {
      ((st = u.get(ht)), st === void 0 && ((st = []), u.set(ht, st)));
      const et = D.textures;
      if (st.length !== et.length || st[0] !== i.COLOR_ATTACHMENT0) {
        for (let Y = 0, bt = et.length; Y < bt; Y++) st[Y] = i.COLOR_ATTACHMENT0 + Y;
        ((st.length = et.length), (St = !0));
      }
    } else st[0] !== i.BACK && ((st[0] = i.BACK), (St = !0));
    St && i.drawBuffers(st);
  }
  function Vt(D) {
    return g !== D ? (i.useProgram(D), (g = D), !0) : !1;
  }
  const ie = { [Wn]: i.FUNC_ADD, [Cc]: i.FUNC_SUBTRACT, [Pc]: i.FUNC_REVERSE_SUBTRACT };
  ((ie[Lc] = i.MIN), (ie[Dc] = i.MAX));
  const Ht = {
    [Ic]: i.ZERO,
    [Uc]: i.ONE,
    [Nc]: i.SRC_COLOR,
    [Gr]: i.SRC_ALPHA,
    [Gc]: i.SRC_ALPHA_SATURATE,
    [zc]: i.DST_COLOR,
    [Oc]: i.DST_ALPHA,
    [Fc]: i.ONE_MINUS_SRC_COLOR,
    [Hr]: i.ONE_MINUS_SRC_ALPHA,
    [Vc]: i.ONE_MINUS_DST_COLOR,
    [Bc]: i.ONE_MINUS_DST_ALPHA,
    [Hc]: i.CONSTANT_COLOR,
    [kc]: i.ONE_MINUS_CONSTANT_COLOR,
    [Wc]: i.CONSTANT_ALPHA,
    [Xc]: i.ONE_MINUS_CONSTANT_ALPHA,
  };
  function $(D, ht, st, St, et, Y, bt, Gt, le, Qt) {
    if (D === vn) {
      M === !0 && (at(i.BLEND), (M = !1));
      return;
    }
    if ((M === !1 && (rt(i.BLEND), (M = !0)), D !== Rc)) {
      if (D !== m || Qt !== b) {
        if (((d !== Wn || S !== Wn) && (i.blendEquation(i.FUNC_ADD), (d = Wn), (S = Wn)), Qt))
          switch (D) {
            case vi:
              i.blendFuncSeparate(i.ONE, i.ONE_MINUS_SRC_ALPHA, i.ONE, i.ONE_MINUS_SRC_ALPHA);
              break;
            case uo:
              i.blendFunc(i.ONE, i.ONE);
              break;
            case fo:
              i.blendFuncSeparate(i.ZERO, i.ONE_MINUS_SRC_COLOR, i.ZERO, i.ONE);
              break;
            case po:
              i.blendFuncSeparate(i.DST_COLOR, i.ONE_MINUS_SRC_ALPHA, i.ZERO, i.ONE);
              break;
            default:
              Jt('WebGLState: Invalid blending: ', D);
              break;
          }
        else
          switch (D) {
            case vi:
              i.blendFuncSeparate(i.SRC_ALPHA, i.ONE_MINUS_SRC_ALPHA, i.ONE, i.ONE_MINUS_SRC_ALPHA);
              break;
            case uo:
              i.blendFuncSeparate(i.SRC_ALPHA, i.ONE, i.ONE, i.ONE);
              break;
            case fo:
              Jt('WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true');
              break;
            case po:
              Jt('WebGLState: MultiplyBlending requires material.premultipliedAlpha = true');
              break;
            default:
              Jt('WebGLState: Invalid blending: ', D);
              break;
          }
        ((E = null),
          (y = null),
          (R = null),
          (w = null),
          P.set(0, 0, 0),
          (x = 0),
          (m = D),
          (b = Qt));
      }
      return;
    }
    ((et = et || ht),
      (Y = Y || st),
      (bt = bt || St),
      (ht !== d || et !== S) && (i.blendEquationSeparate(ie[ht], ie[et]), (d = ht), (S = et)),
      (st !== E || St !== y || Y !== R || bt !== w) &&
        (i.blendFuncSeparate(Ht[st], Ht[St], Ht[Y], Ht[bt]), (E = st), (y = St), (R = Y), (w = bt)),
      (Gt.equals(P) === !1 || le !== x) &&
        (i.blendColor(Gt.r, Gt.g, Gt.b, le), P.copy(Gt), (x = le)),
      (m = D),
      (b = !1));
  }
  function tt(D, ht) {
    D.side === gn ? at(i.CULL_FACE) : rt(i.CULL_FACE);
    let st = D.side === Pe;
    (ht && (st = !st),
      K(st),
      D.blending === vi && D.transparent === !1
        ? $(vn)
        : $(
            D.blending,
            D.blendEquation,
            D.blendSrc,
            D.blendDst,
            D.blendEquationAlpha,
            D.blendSrcAlpha,
            D.blendDstAlpha,
            D.blendColor,
            D.blendAlpha,
            D.premultipliedAlpha
          ),
      a.setFunc(D.depthFunc),
      a.setTest(D.depthTest),
      a.setMask(D.depthWrite),
      r.setMask(D.colorWrite));
    const St = D.stencilWrite;
    (o.setTest(St),
      St &&
        (o.setMask(D.stencilWriteMask),
        o.setFunc(D.stencilFunc, D.stencilRef, D.stencilFuncMask),
        o.setOp(D.stencilFail, D.stencilZFail, D.stencilZPass)),
      Dt(D.polygonOffset, D.polygonOffsetFactor, D.polygonOffsetUnits),
      D.alphaToCoverage === !0 ? rt(i.SAMPLE_ALPHA_TO_COVERAGE) : at(i.SAMPLE_ALPHA_TO_COVERAGE));
  }
  function K(D) {
    H !== D && (D ? i.frontFace(i.CW) : i.frontFace(i.CCW), (H = D));
  }
  function ut(D) {
    (D !== Tc
      ? (rt(i.CULL_FACE),
        D !== C &&
          (D === ho
            ? i.cullFace(i.BACK)
            : D === Ac
              ? i.cullFace(i.FRONT)
              : i.cullFace(i.FRONT_AND_BACK)))
      : at(i.CULL_FACE),
      (C = D));
  }
  function A(D) {
    D !== N && (O && i.lineWidth(D), (N = D));
  }
  function Dt(D, ht, st) {
    D
      ? (rt(i.POLYGON_OFFSET_FILL),
        (z !== ht || k !== st) &&
          ((z = ht), (k = st), a.getReversed() && (ht = -ht), i.polygonOffset(ht, st)))
      : at(i.POLYGON_OFFSET_FILL);
  }
  function xt(D) {
    D ? rt(i.SCISSOR_TEST) : at(i.SCISSOR_TEST);
  }
  function Ut(D) {
    (D === void 0 && (D = i.TEXTURE0 + F - 1), j !== D && (i.activeTexture(D), (j = D)));
  }
  function ot(D, ht, st) {
    st === void 0 && (j === null ? (st = i.TEXTURE0 + F - 1) : (st = j));
    let St = mt[st];
    (St === void 0 && ((St = { type: void 0, texture: void 0 }), (mt[st] = St)),
      (St.type !== D || St.texture !== ht) &&
        (j !== st && (i.activeTexture(st), (j = st)),
        i.bindTexture(D, ht || Z[D]),
        (St.type = D),
        (St.texture = ht)));
  }
  function T() {
    const D = mt[j];
    D !== void 0 &&
      D.type !== void 0 &&
      (i.bindTexture(D.type, null), (D.type = void 0), (D.texture = void 0));
  }
  function _() {
    try {
      i.compressedTexImage2D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function I() {
    try {
      i.compressedTexImage3D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function X() {
    try {
      i.texSubImage2D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function J() {
    try {
      i.texSubImage3D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function q() {
    try {
      i.compressedTexSubImage2D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function yt() {
    try {
      i.compressedTexSubImage3D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function lt() {
    try {
      i.texStorage2D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function Ct() {
    try {
      i.texStorage3D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function Nt() {
    try {
      i.texImage2D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function Q() {
    try {
      i.texImage3D(...arguments);
    } catch (D) {
      Jt('WebGLState:', D);
    }
  }
  function it(D) {
    Ot.equals(D) === !1 && (i.scissor(D.x, D.y, D.z, D.w), Ot.copy(D));
  }
  function Et(D) {
    jt.equals(D) === !1 && (i.viewport(D.x, D.y, D.z, D.w), jt.copy(D));
  }
  function Tt(D, ht) {
    let st = c.get(ht);
    st === void 0 && ((st = new WeakMap()), c.set(ht, st));
    let St = st.get(D);
    St === void 0 && ((St = i.getUniformBlockIndex(ht, D.name)), st.set(D, St));
  }
  function vt(D, ht) {
    const St = c.get(ht).get(D);
    l.get(ht) !== St && (i.uniformBlockBinding(ht, St, D.__bindingPointIndex), l.set(ht, St));
  }
  function Yt() {
    (i.disable(i.BLEND),
      i.disable(i.CULL_FACE),
      i.disable(i.DEPTH_TEST),
      i.disable(i.POLYGON_OFFSET_FILL),
      i.disable(i.SCISSOR_TEST),
      i.disable(i.STENCIL_TEST),
      i.disable(i.SAMPLE_ALPHA_TO_COVERAGE),
      i.blendEquation(i.FUNC_ADD),
      i.blendFunc(i.ONE, i.ZERO),
      i.blendFuncSeparate(i.ONE, i.ZERO, i.ONE, i.ZERO),
      i.blendColor(0, 0, 0, 0),
      i.colorMask(!0, !0, !0, !0),
      i.clearColor(0, 0, 0, 0),
      i.depthMask(!0),
      i.depthFunc(i.LESS),
      a.setReversed(!1),
      i.clearDepth(1),
      i.stencilMask(4294967295),
      i.stencilFunc(i.ALWAYS, 0, 4294967295),
      i.stencilOp(i.KEEP, i.KEEP, i.KEEP),
      i.clearStencil(0),
      i.cullFace(i.BACK),
      i.frontFace(i.CCW),
      i.polygonOffset(0, 0),
      i.activeTexture(i.TEXTURE0),
      i.bindFramebuffer(i.FRAMEBUFFER, null),
      i.bindFramebuffer(i.DRAW_FRAMEBUFFER, null),
      i.bindFramebuffer(i.READ_FRAMEBUFFER, null),
      i.useProgram(null),
      i.lineWidth(1),
      i.scissor(0, 0, i.canvas.width, i.canvas.height),
      i.viewport(0, 0, i.canvas.width, i.canvas.height),
      (h = {}),
      (j = null),
      (mt = {}),
      (f = {}),
      (u = new WeakMap()),
      (p = []),
      (g = null),
      (M = !1),
      (m = null),
      (d = null),
      (E = null),
      (y = null),
      (S = null),
      (R = null),
      (w = null),
      (P = new zt(0, 0, 0)),
      (x = 0),
      (b = !1),
      (H = null),
      (C = null),
      (N = null),
      (z = null),
      (k = null),
      Ot.set(0, 0, i.canvas.width, i.canvas.height),
      jt.set(0, 0, i.canvas.width, i.canvas.height),
      r.reset(),
      a.reset(),
      o.reset());
  }
  return {
    buffers: { color: r, depth: a, stencil: o },
    enable: rt,
    disable: at,
    bindFramebuffer: It,
    drawBuffers: Lt,
    useProgram: Vt,
    setBlending: $,
    setMaterial: tt,
    setFlipSided: K,
    setCullFace: ut,
    setLineWidth: A,
    setPolygonOffset: Dt,
    setScissorTest: xt,
    activeTexture: Ut,
    bindTexture: ot,
    unbindTexture: T,
    compressedTexImage2D: _,
    compressedTexImage3D: I,
    texImage2D: Nt,
    texImage3D: Q,
    updateUBOMapping: Tt,
    uniformBlockBinding: vt,
    texStorage2D: lt,
    texStorage3D: Ct,
    texSubImage2D: X,
    texSubImage3D: J,
    compressedTexSubImage2D: q,
    compressedTexSubImage3D: yt,
    scissor: it,
    viewport: Et,
    reset: Yt,
  };
}
function Lg(i, t, e, n, s, r, a) {
  const o = t.has('WEBGL_multisampled_render_to_texture')
      ? t.get('WEBGL_multisampled_render_to_texture')
      : null,
    l = typeof navigator > 'u' ? !1 : /OculusBrowser/g.test(navigator.userAgent),
    c = new ct(),
    h = new WeakMap();
  let f;
  const u = new WeakMap();
  let p = !1;
  try {
    p = typeof OffscreenCanvas < 'u' && new OffscreenCanvas(1, 1).getContext('2d') !== null;
  } catch {}
  function g(T, _) {
    return p ? new OffscreenCanvas(T, _) : Yi('canvas');
  }
  function M(T, _, I) {
    let X = 1;
    const J = ot(T);
    if (((J.width > I || J.height > I) && (X = I / Math.max(J.width, J.height)), X < 1))
      if (
        (typeof HTMLImageElement < 'u' && T instanceof HTMLImageElement) ||
        (typeof HTMLCanvasElement < 'u' && T instanceof HTMLCanvasElement) ||
        (typeof ImageBitmap < 'u' && T instanceof ImageBitmap) ||
        (typeof VideoFrame < 'u' && T instanceof VideoFrame)
      ) {
        const q = Math.floor(X * J.width),
          yt = Math.floor(X * J.height);
        f === void 0 && (f = g(q, yt));
        const lt = _ ? g(q, yt) : f;
        return (
          (lt.width = q),
          (lt.height = yt),
          lt.getContext('2d').drawImage(T, 0, 0, q, yt),
          Ft(
            'WebGLRenderer: Texture has been resized from (' +
              J.width +
              'x' +
              J.height +
              ') to (' +
              q +
              'x' +
              yt +
              ').'
          ),
          lt
        );
      } else
        return (
          'data' in T &&
            Ft(
              'WebGLRenderer: Image in DataTexture is too big (' + J.width + 'x' + J.height + ').'
            ),
          T
        );
    return T;
  }
  function m(T) {
    return T.generateMipmaps;
  }
  function d(T) {
    i.generateMipmap(T);
  }
  function E(T) {
    return T.isWebGLCubeRenderTarget
      ? i.TEXTURE_CUBE_MAP
      : T.isWebGL3DRenderTarget
        ? i.TEXTURE_3D
        : T.isWebGLArrayRenderTarget || T.isCompressedArrayTexture
          ? i.TEXTURE_2D_ARRAY
          : i.TEXTURE_2D;
  }
  function y(T, _, I, X, J = !1) {
    if (T !== null) {
      if (i[T] !== void 0) return i[T];
      Ft("WebGLRenderer: Attempt to use non-existing WebGL internal format '" + T + "'");
    }
    let q = _;
    if (
      (_ === i.RED &&
        (I === i.FLOAT && (q = i.R32F),
        I === i.HALF_FLOAT && (q = i.R16F),
        I === i.UNSIGNED_BYTE && (q = i.R8)),
      _ === i.RED_INTEGER &&
        (I === i.UNSIGNED_BYTE && (q = i.R8UI),
        I === i.UNSIGNED_SHORT && (q = i.R16UI),
        I === i.UNSIGNED_INT && (q = i.R32UI),
        I === i.BYTE && (q = i.R8I),
        I === i.SHORT && (q = i.R16I),
        I === i.INT && (q = i.R32I)),
      _ === i.RG &&
        (I === i.FLOAT && (q = i.RG32F),
        I === i.HALF_FLOAT && (q = i.RG16F),
        I === i.UNSIGNED_BYTE && (q = i.RG8)),
      _ === i.RG_INTEGER &&
        (I === i.UNSIGNED_BYTE && (q = i.RG8UI),
        I === i.UNSIGNED_SHORT && (q = i.RG16UI),
        I === i.UNSIGNED_INT && (q = i.RG32UI),
        I === i.BYTE && (q = i.RG8I),
        I === i.SHORT && (q = i.RG16I),
        I === i.INT && (q = i.RG32I)),
      _ === i.RGB_INTEGER &&
        (I === i.UNSIGNED_BYTE && (q = i.RGB8UI),
        I === i.UNSIGNED_SHORT && (q = i.RGB16UI),
        I === i.UNSIGNED_INT && (q = i.RGB32UI),
        I === i.BYTE && (q = i.RGB8I),
        I === i.SHORT && (q = i.RGB16I),
        I === i.INT && (q = i.RGB32I)),
      _ === i.RGBA_INTEGER &&
        (I === i.UNSIGNED_BYTE && (q = i.RGBA8UI),
        I === i.UNSIGNED_SHORT && (q = i.RGBA16UI),
        I === i.UNSIGNED_INT && (q = i.RGBA32UI),
        I === i.BYTE && (q = i.RGBA8I),
        I === i.SHORT && (q = i.RGBA16I),
        I === i.INT && (q = i.RGBA32I)),
      _ === i.RGB &&
        (I === i.UNSIGNED_INT_5_9_9_9_REV && (q = i.RGB9_E5),
        I === i.UNSIGNED_INT_10F_11F_11F_REV && (q = i.R11F_G11F_B10F)),
      _ === i.RGBA)
    ) {
      const yt = J ? Hs : $t.getTransfer(X);
      (I === i.FLOAT && (q = i.RGBA32F),
        I === i.HALF_FLOAT && (q = i.RGBA16F),
        I === i.UNSIGNED_BYTE && (q = yt === te ? i.SRGB8_ALPHA8 : i.RGBA8),
        I === i.UNSIGNED_SHORT_4_4_4_4 && (q = i.RGBA4),
        I === i.UNSIGNED_SHORT_5_5_5_1 && (q = i.RGB5_A1));
    }
    return (
      (q === i.R16F ||
        q === i.R32F ||
        q === i.RG16F ||
        q === i.RG32F ||
        q === i.RGBA16F ||
        q === i.RGBA32F) &&
        t.get('EXT_color_buffer_float'),
      q
    );
  }
  function S(T, _) {
    let I;
    return (
      T
        ? _ === null || _ === an || _ === Xi
          ? (I = i.DEPTH24_STENCIL8)
          : _ === en
            ? (I = i.DEPTH32F_STENCIL8)
            : _ === Wi &&
              ((I = i.DEPTH24_STENCIL8),
              Ft(
                'DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.'
              ))
        : _ === null || _ === an || _ === Xi
          ? (I = i.DEPTH_COMPONENT24)
          : _ === en
            ? (I = i.DEPTH_COMPONENT32F)
            : _ === Wi && (I = i.DEPTH_COMPONENT16),
      I
    );
  }
  function R(T, _) {
    return m(T) === !0 || (T.isFramebufferTexture && T.minFilter !== me && T.minFilter !== Ae)
      ? Math.log2(Math.max(_.width, _.height)) + 1
      : T.mipmaps !== void 0 && T.mipmaps.length > 0
        ? T.mipmaps.length
        : T.isCompressedTexture && Array.isArray(T.image)
          ? _.mipmaps.length
          : 1;
  }
  function w(T) {
    const _ = T.target;
    (_.removeEventListener('dispose', w), x(_), _.isVideoTexture && h.delete(_));
  }
  function P(T) {
    const _ = T.target;
    (_.removeEventListener('dispose', P), H(_));
  }
  function x(T) {
    const _ = n.get(T);
    if (_.__webglInit === void 0) return;
    const I = T.source,
      X = u.get(I);
    if (X) {
      const J = X[_.__cacheKey];
      (J.usedTimes--, J.usedTimes === 0 && b(T), Object.keys(X).length === 0 && u.delete(I));
    }
    n.remove(T);
  }
  function b(T) {
    const _ = n.get(T);
    i.deleteTexture(_.__webglTexture);
    const I = T.source,
      X = u.get(I);
    (delete X[_.__cacheKey], a.memory.textures--);
  }
  function H(T) {
    const _ = n.get(T);
    if (
      (T.depthTexture && (T.depthTexture.dispose(), n.remove(T.depthTexture)),
      T.isWebGLCubeRenderTarget)
    )
      for (let X = 0; X < 6; X++) {
        if (Array.isArray(_.__webglFramebuffer[X]))
          for (let J = 0; J < _.__webglFramebuffer[X].length; J++)
            i.deleteFramebuffer(_.__webglFramebuffer[X][J]);
        else i.deleteFramebuffer(_.__webglFramebuffer[X]);
        _.__webglDepthbuffer && i.deleteRenderbuffer(_.__webglDepthbuffer[X]);
      }
    else {
      if (Array.isArray(_.__webglFramebuffer))
        for (let X = 0; X < _.__webglFramebuffer.length; X++)
          i.deleteFramebuffer(_.__webglFramebuffer[X]);
      else i.deleteFramebuffer(_.__webglFramebuffer);
      if (
        (_.__webglDepthbuffer && i.deleteRenderbuffer(_.__webglDepthbuffer),
        _.__webglMultisampledFramebuffer && i.deleteFramebuffer(_.__webglMultisampledFramebuffer),
        _.__webglColorRenderbuffer)
      )
        for (let X = 0; X < _.__webglColorRenderbuffer.length; X++)
          _.__webglColorRenderbuffer[X] && i.deleteRenderbuffer(_.__webglColorRenderbuffer[X]);
      _.__webglDepthRenderbuffer && i.deleteRenderbuffer(_.__webglDepthRenderbuffer);
    }
    const I = T.textures;
    for (let X = 0, J = I.length; X < J; X++) {
      const q = n.get(I[X]);
      (q.__webglTexture && (i.deleteTexture(q.__webglTexture), a.memory.textures--),
        n.remove(I[X]));
    }
    n.remove(T);
  }
  let C = 0;
  function N() {
    C = 0;
  }
  function z() {
    const T = C;
    return (
      T >= s.maxTextures &&
        Ft(
          'WebGLTextures: Trying to use ' +
            T +
            ' texture units while this GPU supports only ' +
            s.maxTextures
        ),
      (C += 1),
      T
    );
  }
  function k(T) {
    const _ = [];
    return (
      _.push(T.wrapS),
      _.push(T.wrapT),
      _.push(T.wrapR || 0),
      _.push(T.magFilter),
      _.push(T.minFilter),
      _.push(T.anisotropy),
      _.push(T.internalFormat),
      _.push(T.format),
      _.push(T.type),
      _.push(T.generateMipmaps),
      _.push(T.premultiplyAlpha),
      _.push(T.flipY),
      _.push(T.unpackAlignment),
      _.push(T.colorSpace),
      _.join()
    );
  }
  function F(T, _) {
    const I = n.get(T);
    if (
      (T.isVideoTexture && xt(T),
      T.isRenderTargetTexture === !1 &&
        T.isExternalTexture !== !0 &&
        T.version > 0 &&
        I.__version !== T.version)
    ) {
      const X = T.image;
      if (X === null) Ft('WebGLRenderer: Texture marked for update but no image data found.');
      else if (X.complete === !1)
        Ft('WebGLRenderer: Texture marked for update but image is incomplete');
      else {
        Z(I, T, _);
        return;
      }
    } else T.isExternalTexture && (I.__webglTexture = T.sourceTexture ? T.sourceTexture : null);
    e.bindTexture(i.TEXTURE_2D, I.__webglTexture, i.TEXTURE0 + _);
  }
  function O(T, _) {
    const I = n.get(T);
    if (T.isRenderTargetTexture === !1 && T.version > 0 && I.__version !== T.version) {
      Z(I, T, _);
      return;
    } else T.isExternalTexture && (I.__webglTexture = T.sourceTexture ? T.sourceTexture : null);
    e.bindTexture(i.TEXTURE_2D_ARRAY, I.__webglTexture, i.TEXTURE0 + _);
  }
  function B(T, _) {
    const I = n.get(T);
    if (T.isRenderTargetTexture === !1 && T.version > 0 && I.__version !== T.version) {
      Z(I, T, _);
      return;
    }
    e.bindTexture(i.TEXTURE_3D, I.__webglTexture, i.TEXTURE0 + _);
  }
  function nt(T, _) {
    const I = n.get(T);
    if (T.isCubeDepthTexture !== !0 && T.version > 0 && I.__version !== T.version) {
      rt(I, T, _);
      return;
    }
    e.bindTexture(i.TEXTURE_CUBE_MAP, I.__webglTexture, i.TEXTURE0 + _);
  }
  const j = { [$r]: i.REPEAT, [xn]: i.CLAMP_TO_EDGE, [Kr]: i.MIRRORED_REPEAT },
    mt = {
      [me]: i.NEAREST,
      [Zc]: i.NEAREST_MIPMAP_NEAREST,
      [is]: i.NEAREST_MIPMAP_LINEAR,
      [Ae]: i.LINEAR,
      [rr]: i.LINEAR_MIPMAP_NEAREST,
      [qn]: i.LINEAR_MIPMAP_LINEAR,
    },
    _t = {
      [Kc]: i.NEVER,
      [nh]: i.ALWAYS,
      [jc]: i.LESS,
      [Xa]: i.LEQUAL,
      [Qc]: i.EQUAL,
      [qa]: i.GEQUAL,
      [th]: i.GREATER,
      [eh]: i.NOTEQUAL,
    };
  function gt(T, _) {
    if (
      (_.type === en &&
        t.has('OES_texture_float_linear') === !1 &&
        (_.magFilter === Ae ||
          _.magFilter === rr ||
          _.magFilter === is ||
          _.magFilter === qn ||
          _.minFilter === Ae ||
          _.minFilter === rr ||
          _.minFilter === is ||
          _.minFilter === qn) &&
        Ft(
          'WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device.'
        ),
      i.texParameteri(T, i.TEXTURE_WRAP_S, j[_.wrapS]),
      i.texParameteri(T, i.TEXTURE_WRAP_T, j[_.wrapT]),
      (T === i.TEXTURE_3D || T === i.TEXTURE_2D_ARRAY) &&
        i.texParameteri(T, i.TEXTURE_WRAP_R, j[_.wrapR]),
      i.texParameteri(T, i.TEXTURE_MAG_FILTER, mt[_.magFilter]),
      i.texParameteri(T, i.TEXTURE_MIN_FILTER, mt[_.minFilter]),
      _.compareFunction &&
        (i.texParameteri(T, i.TEXTURE_COMPARE_MODE, i.COMPARE_REF_TO_TEXTURE),
        i.texParameteri(T, i.TEXTURE_COMPARE_FUNC, _t[_.compareFunction])),
      t.has('EXT_texture_filter_anisotropic') === !0)
    ) {
      if (
        _.magFilter === me ||
        (_.minFilter !== is && _.minFilter !== qn) ||
        (_.type === en && t.has('OES_texture_float_linear') === !1)
      )
        return;
      if (_.anisotropy > 1 || n.get(_).__currentAnisotropy) {
        const I = t.get('EXT_texture_filter_anisotropic');
        (i.texParameterf(
          T,
          I.TEXTURE_MAX_ANISOTROPY_EXT,
          Math.min(_.anisotropy, s.getMaxAnisotropy())
        ),
          (n.get(_).__currentAnisotropy = _.anisotropy));
      }
    }
  }
  function Ot(T, _) {
    let I = !1;
    T.__webglInit === void 0 && ((T.__webglInit = !0), _.addEventListener('dispose', w));
    const X = _.source;
    let J = u.get(X);
    J === void 0 && ((J = {}), u.set(X, J));
    const q = k(_);
    if (q !== T.__cacheKey) {
      (J[q] === void 0 &&
        ((J[q] = { texture: i.createTexture(), usedTimes: 0 }), a.memory.textures++, (I = !0)),
        J[q].usedTimes++);
      const yt = J[T.__cacheKey];
      (yt !== void 0 && (J[T.__cacheKey].usedTimes--, yt.usedTimes === 0 && b(_)),
        (T.__cacheKey = q),
        (T.__webglTexture = J[q].texture));
    }
    return I;
  }
  function jt(T, _, I) {
    return Math.floor(Math.floor(T / I) / _);
  }
  function ne(T, _, I, X) {
    const q = T.updateRanges;
    if (q.length === 0) e.texSubImage2D(i.TEXTURE_2D, 0, 0, 0, _.width, _.height, I, X, _.data);
    else {
      q.sort((Q, it) => Q.start - it.start);
      let yt = 0;
      for (let Q = 1; Q < q.length; Q++) {
        const it = q[yt],
          Et = q[Q],
          Tt = it.start + it.count,
          vt = jt(Et.start, _.width, 4),
          Yt = jt(it.start, _.width, 4);
        Et.start <= Tt + 1 && vt === Yt && jt(Et.start + Et.count - 1, _.width, 4) === vt
          ? (it.count = Math.max(it.count, Et.start + Et.count - it.start))
          : (++yt, (q[yt] = Et));
      }
      q.length = yt + 1;
      const lt = i.getParameter(i.UNPACK_ROW_LENGTH),
        Ct = i.getParameter(i.UNPACK_SKIP_PIXELS),
        Nt = i.getParameter(i.UNPACK_SKIP_ROWS);
      i.pixelStorei(i.UNPACK_ROW_LENGTH, _.width);
      for (let Q = 0, it = q.length; Q < it; Q++) {
        const Et = q[Q],
          Tt = Math.floor(Et.start / 4),
          vt = Math.ceil(Et.count / 4),
          Yt = Tt % _.width,
          D = Math.floor(Tt / _.width),
          ht = vt,
          st = 1;
        (i.pixelStorei(i.UNPACK_SKIP_PIXELS, Yt),
          i.pixelStorei(i.UNPACK_SKIP_ROWS, D),
          e.texSubImage2D(i.TEXTURE_2D, 0, Yt, D, ht, st, I, X, _.data));
      }
      (T.clearUpdateRanges(),
        i.pixelStorei(i.UNPACK_ROW_LENGTH, lt),
        i.pixelStorei(i.UNPACK_SKIP_PIXELS, Ct),
        i.pixelStorei(i.UNPACK_SKIP_ROWS, Nt));
    }
  }
  function Z(T, _, I) {
    let X = i.TEXTURE_2D;
    ((_.isDataArrayTexture || _.isCompressedArrayTexture) && (X = i.TEXTURE_2D_ARRAY),
      _.isData3DTexture && (X = i.TEXTURE_3D));
    const J = Ot(T, _),
      q = _.source;
    e.bindTexture(X, T.__webglTexture, i.TEXTURE0 + I);
    const yt = n.get(q);
    if (q.version !== yt.__version || J === !0) {
      e.activeTexture(i.TEXTURE0 + I);
      const lt = $t.getPrimaries($t.workingColorSpace),
        Ct = _.colorSpace === Dn ? null : $t.getPrimaries(_.colorSpace),
        Nt = _.colorSpace === Dn || lt === Ct ? i.NONE : i.BROWSER_DEFAULT_WEBGL;
      (i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL, _.flipY),
        i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL, _.premultiplyAlpha),
        i.pixelStorei(i.UNPACK_ALIGNMENT, _.unpackAlignment),
        i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL, Nt));
      let Q = M(_.image, !1, s.maxTextureSize);
      Q = Ut(_, Q);
      const it = r.convert(_.format, _.colorSpace),
        Et = r.convert(_.type);
      let Tt = y(_.internalFormat, it, Et, _.colorSpace, _.isVideoTexture);
      gt(X, _);
      let vt;
      const Yt = _.mipmaps,
        D = _.isVideoTexture !== !0,
        ht = yt.__version === void 0 || J === !0,
        st = q.dataReady,
        St = R(_, Q);
      if (_.isDepthTexture)
        ((Tt = S(_.format === Yn, _.type)),
          ht &&
            (D
              ? e.texStorage2D(i.TEXTURE_2D, 1, Tt, Q.width, Q.height)
              : e.texImage2D(i.TEXTURE_2D, 0, Tt, Q.width, Q.height, 0, it, Et, null)));
      else if (_.isDataTexture)
        if (Yt.length > 0) {
          D && ht && e.texStorage2D(i.TEXTURE_2D, St, Tt, Yt[0].width, Yt[0].height);
          for (let et = 0, Y = Yt.length; et < Y; et++)
            ((vt = Yt[et]),
              D
                ? st &&
                  e.texSubImage2D(i.TEXTURE_2D, et, 0, 0, vt.width, vt.height, it, Et, vt.data)
                : e.texImage2D(i.TEXTURE_2D, et, Tt, vt.width, vt.height, 0, it, Et, vt.data));
          _.generateMipmaps = !1;
        } else
          D
            ? (ht && e.texStorage2D(i.TEXTURE_2D, St, Tt, Q.width, Q.height),
              st && ne(_, Q, it, Et))
            : e.texImage2D(i.TEXTURE_2D, 0, Tt, Q.width, Q.height, 0, it, Et, Q.data);
      else if (_.isCompressedTexture)
        if (_.isCompressedArrayTexture) {
          D && ht && e.texStorage3D(i.TEXTURE_2D_ARRAY, St, Tt, Yt[0].width, Yt[0].height, Q.depth);
          for (let et = 0, Y = Yt.length; et < Y; et++)
            if (((vt = Yt[et]), _.format !== Ye))
              if (it !== null)
                if (D) {
                  if (st)
                    if (_.layerUpdates.size > 0) {
                      const bt = jo(vt.width, vt.height, _.format, _.type);
                      for (const Gt of _.layerUpdates) {
                        const le = vt.data.subarray(
                          (Gt * bt) / vt.data.BYTES_PER_ELEMENT,
                          ((Gt + 1) * bt) / vt.data.BYTES_PER_ELEMENT
                        );
                        e.compressedTexSubImage3D(
                          i.TEXTURE_2D_ARRAY,
                          et,
                          0,
                          0,
                          Gt,
                          vt.width,
                          vt.height,
                          1,
                          it,
                          le
                        );
                      }
                      _.clearLayerUpdates();
                    } else
                      e.compressedTexSubImage3D(
                        i.TEXTURE_2D_ARRAY,
                        et,
                        0,
                        0,
                        0,
                        vt.width,
                        vt.height,
                        Q.depth,
                        it,
                        vt.data
                      );
                } else
                  e.compressedTexImage3D(
                    i.TEXTURE_2D_ARRAY,
                    et,
                    Tt,
                    vt.width,
                    vt.height,
                    Q.depth,
                    0,
                    vt.data,
                    0,
                    0
                  );
              else
                Ft(
                  'WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()'
                );
            else
              D
                ? st &&
                  e.texSubImage3D(
                    i.TEXTURE_2D_ARRAY,
                    et,
                    0,
                    0,
                    0,
                    vt.width,
                    vt.height,
                    Q.depth,
                    it,
                    Et,
                    vt.data
                  )
                : e.texImage3D(
                    i.TEXTURE_2D_ARRAY,
                    et,
                    Tt,
                    vt.width,
                    vt.height,
                    Q.depth,
                    0,
                    it,
                    Et,
                    vt.data
                  );
        } else {
          D && ht && e.texStorage2D(i.TEXTURE_2D, St, Tt, Yt[0].width, Yt[0].height);
          for (let et = 0, Y = Yt.length; et < Y; et++)
            ((vt = Yt[et]),
              _.format !== Ye
                ? it !== null
                  ? D
                    ? st &&
                      e.compressedTexSubImage2D(
                        i.TEXTURE_2D,
                        et,
                        0,
                        0,
                        vt.width,
                        vt.height,
                        it,
                        vt.data
                      )
                    : e.compressedTexImage2D(i.TEXTURE_2D, et, Tt, vt.width, vt.height, 0, vt.data)
                  : Ft(
                      'WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()'
                    )
                : D
                  ? st &&
                    e.texSubImage2D(i.TEXTURE_2D, et, 0, 0, vt.width, vt.height, it, Et, vt.data)
                  : e.texImage2D(i.TEXTURE_2D, et, Tt, vt.width, vt.height, 0, it, Et, vt.data));
        }
      else if (_.isDataArrayTexture)
        if (D) {
          if ((ht && e.texStorage3D(i.TEXTURE_2D_ARRAY, St, Tt, Q.width, Q.height, Q.depth), st))
            if (_.layerUpdates.size > 0) {
              const et = jo(Q.width, Q.height, _.format, _.type);
              for (const Y of _.layerUpdates) {
                const bt = Q.data.subarray(
                  (Y * et) / Q.data.BYTES_PER_ELEMENT,
                  ((Y + 1) * et) / Q.data.BYTES_PER_ELEMENT
                );
                e.texSubImage3D(i.TEXTURE_2D_ARRAY, 0, 0, 0, Y, Q.width, Q.height, 1, it, Et, bt);
              }
              _.clearLayerUpdates();
            } else
              e.texSubImage3D(
                i.TEXTURE_2D_ARRAY,
                0,
                0,
                0,
                0,
                Q.width,
                Q.height,
                Q.depth,
                it,
                Et,
                Q.data
              );
        } else
          e.texImage3D(i.TEXTURE_2D_ARRAY, 0, Tt, Q.width, Q.height, Q.depth, 0, it, Et, Q.data);
      else if (_.isData3DTexture)
        D
          ? (ht && e.texStorage3D(i.TEXTURE_3D, St, Tt, Q.width, Q.height, Q.depth),
            st &&
              e.texSubImage3D(i.TEXTURE_3D, 0, 0, 0, 0, Q.width, Q.height, Q.depth, it, Et, Q.data))
          : e.texImage3D(i.TEXTURE_3D, 0, Tt, Q.width, Q.height, Q.depth, 0, it, Et, Q.data);
      else if (_.isFramebufferTexture) {
        if (ht)
          if (D) e.texStorage2D(i.TEXTURE_2D, St, Tt, Q.width, Q.height);
          else {
            let et = Q.width,
              Y = Q.height;
            for (let bt = 0; bt < St; bt++)
              (e.texImage2D(i.TEXTURE_2D, bt, Tt, et, Y, 0, it, Et, null), (et >>= 1), (Y >>= 1));
          }
      } else if (Yt.length > 0) {
        if (D && ht) {
          const et = ot(Yt[0]);
          e.texStorage2D(i.TEXTURE_2D, St, Tt, et.width, et.height);
        }
        for (let et = 0, Y = Yt.length; et < Y; et++)
          ((vt = Yt[et]),
            D
              ? st && e.texSubImage2D(i.TEXTURE_2D, et, 0, 0, it, Et, vt)
              : e.texImage2D(i.TEXTURE_2D, et, Tt, it, Et, vt));
        _.generateMipmaps = !1;
      } else if (D) {
        if (ht) {
          const et = ot(Q);
          e.texStorage2D(i.TEXTURE_2D, St, Tt, et.width, et.height);
        }
        st && e.texSubImage2D(i.TEXTURE_2D, 0, 0, 0, it, Et, Q);
      } else e.texImage2D(i.TEXTURE_2D, 0, Tt, it, Et, Q);
      (m(_) && d(X), (yt.__version = q.version), _.onUpdate && _.onUpdate(_));
    }
    T.__version = _.version;
  }
  function rt(T, _, I) {
    if (_.image.length !== 6) return;
    const X = Ot(T, _),
      J = _.source;
    e.bindTexture(i.TEXTURE_CUBE_MAP, T.__webglTexture, i.TEXTURE0 + I);
    const q = n.get(J);
    if (J.version !== q.__version || X === !0) {
      e.activeTexture(i.TEXTURE0 + I);
      const yt = $t.getPrimaries($t.workingColorSpace),
        lt = _.colorSpace === Dn ? null : $t.getPrimaries(_.colorSpace),
        Ct = _.colorSpace === Dn || yt === lt ? i.NONE : i.BROWSER_DEFAULT_WEBGL;
      (i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL, _.flipY),
        i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL, _.premultiplyAlpha),
        i.pixelStorei(i.UNPACK_ALIGNMENT, _.unpackAlignment),
        i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL, Ct));
      const Nt = _.isCompressedTexture || _.image[0].isCompressedTexture,
        Q = _.image[0] && _.image[0].isDataTexture,
        it = [];
      for (let Y = 0; Y < 6; Y++)
        (!Nt && !Q
          ? (it[Y] = M(_.image[Y], !0, s.maxCubemapSize))
          : (it[Y] = Q ? _.image[Y].image : _.image[Y]),
          (it[Y] = Ut(_, it[Y])));
      const Et = it[0],
        Tt = r.convert(_.format, _.colorSpace),
        vt = r.convert(_.type),
        Yt = y(_.internalFormat, Tt, vt, _.colorSpace),
        D = _.isVideoTexture !== !0,
        ht = q.__version === void 0 || X === !0,
        st = J.dataReady;
      let St = R(_, Et);
      gt(i.TEXTURE_CUBE_MAP, _);
      let et;
      if (Nt) {
        D && ht && e.texStorage2D(i.TEXTURE_CUBE_MAP, St, Yt, Et.width, Et.height);
        for (let Y = 0; Y < 6; Y++) {
          et = it[Y].mipmaps;
          for (let bt = 0; bt < et.length; bt++) {
            const Gt = et[bt];
            _.format !== Ye
              ? Tt !== null
                ? D
                  ? st &&
                    e.compressedTexSubImage2D(
                      i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                      bt,
                      0,
                      0,
                      Gt.width,
                      Gt.height,
                      Tt,
                      Gt.data
                    )
                  : e.compressedTexImage2D(
                      i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                      bt,
                      Yt,
                      Gt.width,
                      Gt.height,
                      0,
                      Gt.data
                    )
                : Ft(
                    'WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()'
                  )
              : D
                ? st &&
                  e.texSubImage2D(
                    i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                    bt,
                    0,
                    0,
                    Gt.width,
                    Gt.height,
                    Tt,
                    vt,
                    Gt.data
                  )
                : e.texImage2D(
                    i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                    bt,
                    Yt,
                    Gt.width,
                    Gt.height,
                    0,
                    Tt,
                    vt,
                    Gt.data
                  );
          }
        }
      } else {
        if (((et = _.mipmaps), D && ht)) {
          et.length > 0 && St++;
          const Y = ot(it[0]);
          e.texStorage2D(i.TEXTURE_CUBE_MAP, St, Yt, Y.width, Y.height);
        }
        for (let Y = 0; Y < 6; Y++)
          if (Q) {
            D
              ? st &&
                e.texSubImage2D(
                  i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                  0,
                  0,
                  0,
                  it[Y].width,
                  it[Y].height,
                  Tt,
                  vt,
                  it[Y].data
                )
              : e.texImage2D(
                  i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                  0,
                  Yt,
                  it[Y].width,
                  it[Y].height,
                  0,
                  Tt,
                  vt,
                  it[Y].data
                );
            for (let bt = 0; bt < et.length; bt++) {
              const le = et[bt].image[Y].image;
              D
                ? st &&
                  e.texSubImage2D(
                    i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                    bt + 1,
                    0,
                    0,
                    le.width,
                    le.height,
                    Tt,
                    vt,
                    le.data
                  )
                : e.texImage2D(
                    i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                    bt + 1,
                    Yt,
                    le.width,
                    le.height,
                    0,
                    Tt,
                    vt,
                    le.data
                  );
            }
          } else {
            D
              ? st && e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + Y, 0, 0, 0, Tt, vt, it[Y])
              : e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + Y, 0, Yt, Tt, vt, it[Y]);
            for (let bt = 0; bt < et.length; bt++) {
              const Gt = et[bt];
              D
                ? st &&
                  e.texSubImage2D(
                    i.TEXTURE_CUBE_MAP_POSITIVE_X + Y,
                    bt + 1,
                    0,
                    0,
                    Tt,
                    vt,
                    Gt.image[Y]
                  )
                : e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + Y, bt + 1, Yt, Tt, vt, Gt.image[Y]);
            }
          }
      }
      (m(_) && d(i.TEXTURE_CUBE_MAP), (q.__version = J.version), _.onUpdate && _.onUpdate(_));
    }
    T.__version = _.version;
  }
  function at(T, _, I, X, J, q) {
    const yt = r.convert(I.format, I.colorSpace),
      lt = r.convert(I.type),
      Ct = y(I.internalFormat, yt, lt, I.colorSpace),
      Nt = n.get(_),
      Q = n.get(I);
    if (((Q.__renderTarget = _), !Nt.__hasExternalTextures)) {
      const it = Math.max(1, _.width >> q),
        Et = Math.max(1, _.height >> q);
      J === i.TEXTURE_3D || J === i.TEXTURE_2D_ARRAY
        ? e.texImage3D(J, q, Ct, it, Et, _.depth, 0, yt, lt, null)
        : e.texImage2D(J, q, Ct, it, Et, 0, yt, lt, null);
    }
    (e.bindFramebuffer(i.FRAMEBUFFER, T),
      Dt(_)
        ? o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER, X, J, Q.__webglTexture, 0, A(_))
        : (J === i.TEXTURE_2D ||
            (J >= i.TEXTURE_CUBE_MAP_POSITIVE_X && J <= i.TEXTURE_CUBE_MAP_NEGATIVE_Z)) &&
          i.framebufferTexture2D(i.FRAMEBUFFER, X, J, Q.__webglTexture, q),
      e.bindFramebuffer(i.FRAMEBUFFER, null));
  }
  function It(T, _, I) {
    if ((i.bindRenderbuffer(i.RENDERBUFFER, T), _.depthBuffer)) {
      const X = _.depthTexture,
        J = X && X.isDepthTexture ? X.type : null,
        q = S(_.stencilBuffer, J),
        yt = _.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT;
      (Dt(_)
        ? o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER, A(_), q, _.width, _.height)
        : I
          ? i.renderbufferStorageMultisample(i.RENDERBUFFER, A(_), q, _.width, _.height)
          : i.renderbufferStorage(i.RENDERBUFFER, q, _.width, _.height),
        i.framebufferRenderbuffer(i.FRAMEBUFFER, yt, i.RENDERBUFFER, T));
    } else {
      const X = _.textures;
      for (let J = 0; J < X.length; J++) {
        const q = X[J],
          yt = r.convert(q.format, q.colorSpace),
          lt = r.convert(q.type),
          Ct = y(q.internalFormat, yt, lt, q.colorSpace);
        Dt(_)
          ? o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER, A(_), Ct, _.width, _.height)
          : I
            ? i.renderbufferStorageMultisample(i.RENDERBUFFER, A(_), Ct, _.width, _.height)
            : i.renderbufferStorage(i.RENDERBUFFER, Ct, _.width, _.height);
      }
    }
    i.bindRenderbuffer(i.RENDERBUFFER, null);
  }
  function Lt(T, _, I) {
    const X = _.isWebGLCubeRenderTarget === !0;
    if ((e.bindFramebuffer(i.FRAMEBUFFER, T), !(_.depthTexture && _.depthTexture.isDepthTexture)))
      throw new Error('renderTarget.depthTexture must be an instance of THREE.DepthTexture');
    const J = n.get(_.depthTexture);
    if (
      ((J.__renderTarget = _),
      (!J.__webglTexture ||
        _.depthTexture.image.width !== _.width ||
        _.depthTexture.image.height !== _.height) &&
        ((_.depthTexture.image.width = _.width),
        (_.depthTexture.image.height = _.height),
        (_.depthTexture.needsUpdate = !0)),
      X)
    ) {
      if (
        (J.__webglInit === void 0 &&
          ((J.__webglInit = !0), _.depthTexture.addEventListener('dispose', w)),
        J.__webglTexture === void 0)
      ) {
        ((J.__webglTexture = i.createTexture()),
          e.bindTexture(i.TEXTURE_CUBE_MAP, J.__webglTexture),
          gt(i.TEXTURE_CUBE_MAP, _.depthTexture));
        const Nt = r.convert(_.depthTexture.format),
          Q = r.convert(_.depthTexture.type);
        let it;
        _.depthTexture.format === yn
          ? (it = i.DEPTH_COMPONENT24)
          : _.depthTexture.format === Yn && (it = i.DEPTH24_STENCIL8);
        for (let Et = 0; Et < 6; Et++)
          i.texImage2D(
            i.TEXTURE_CUBE_MAP_POSITIVE_X + Et,
            0,
            it,
            _.width,
            _.height,
            0,
            Nt,
            Q,
            null
          );
      }
    } else F(_.depthTexture, 0);
    const q = J.__webglTexture,
      yt = A(_),
      lt = X ? i.TEXTURE_CUBE_MAP_POSITIVE_X + I : i.TEXTURE_2D,
      Ct = _.depthTexture.format === Yn ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT;
    if (_.depthTexture.format === yn)
      Dt(_)
        ? o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER, Ct, lt, q, 0, yt)
        : i.framebufferTexture2D(i.FRAMEBUFFER, Ct, lt, q, 0);
    else if (_.depthTexture.format === Yn)
      Dt(_)
        ? o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER, Ct, lt, q, 0, yt)
        : i.framebufferTexture2D(i.FRAMEBUFFER, Ct, lt, q, 0);
    else throw new Error('Unknown depthTexture format');
  }
  function Vt(T) {
    const _ = n.get(T),
      I = T.isWebGLCubeRenderTarget === !0;
    if (_.__boundDepthTexture !== T.depthTexture) {
      const X = T.depthTexture;
      if ((_.__depthDisposeCallback && _.__depthDisposeCallback(), X)) {
        const J = () => {
          (delete _.__boundDepthTexture,
            delete _.__depthDisposeCallback,
            X.removeEventListener('dispose', J));
        };
        (X.addEventListener('dispose', J), (_.__depthDisposeCallback = J));
      }
      _.__boundDepthTexture = X;
    }
    if (T.depthTexture && !_.__autoAllocateDepthBuffer)
      if (I) for (let X = 0; X < 6; X++) Lt(_.__webglFramebuffer[X], T, X);
      else {
        const X = T.texture.mipmaps;
        X && X.length > 0 ? Lt(_.__webglFramebuffer[0], T, 0) : Lt(_.__webglFramebuffer, T, 0);
      }
    else if (I) {
      _.__webglDepthbuffer = [];
      for (let X = 0; X < 6; X++)
        if (
          (e.bindFramebuffer(i.FRAMEBUFFER, _.__webglFramebuffer[X]),
          _.__webglDepthbuffer[X] === void 0)
        )
          ((_.__webglDepthbuffer[X] = i.createRenderbuffer()), It(_.__webglDepthbuffer[X], T, !1));
        else {
          const J = T.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT,
            q = _.__webglDepthbuffer[X];
          (i.bindRenderbuffer(i.RENDERBUFFER, q),
            i.framebufferRenderbuffer(i.FRAMEBUFFER, J, i.RENDERBUFFER, q));
        }
    } else {
      const X = T.texture.mipmaps;
      if (
        (X && X.length > 0
          ? e.bindFramebuffer(i.FRAMEBUFFER, _.__webglFramebuffer[0])
          : e.bindFramebuffer(i.FRAMEBUFFER, _.__webglFramebuffer),
        _.__webglDepthbuffer === void 0)
      )
        ((_.__webglDepthbuffer = i.createRenderbuffer()), It(_.__webglDepthbuffer, T, !1));
      else {
        const J = T.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT,
          q = _.__webglDepthbuffer;
        (i.bindRenderbuffer(i.RENDERBUFFER, q),
          i.framebufferRenderbuffer(i.FRAMEBUFFER, J, i.RENDERBUFFER, q));
      }
    }
    e.bindFramebuffer(i.FRAMEBUFFER, null);
  }
  function ie(T, _, I) {
    const X = n.get(T);
    (_ !== void 0 && at(X.__webglFramebuffer, T, T.texture, i.COLOR_ATTACHMENT0, i.TEXTURE_2D, 0),
      I !== void 0 && Vt(T));
  }
  function Ht(T) {
    const _ = T.texture,
      I = n.get(T),
      X = n.get(_);
    T.addEventListener('dispose', P);
    const J = T.textures,
      q = T.isWebGLCubeRenderTarget === !0,
      yt = J.length > 1;
    if (
      (yt ||
        (X.__webglTexture === void 0 && (X.__webglTexture = i.createTexture()),
        (X.__version = _.version),
        a.memory.textures++),
      q)
    ) {
      I.__webglFramebuffer = [];
      for (let lt = 0; lt < 6; lt++)
        if (_.mipmaps && _.mipmaps.length > 0) {
          I.__webglFramebuffer[lt] = [];
          for (let Ct = 0; Ct < _.mipmaps.length; Ct++)
            I.__webglFramebuffer[lt][Ct] = i.createFramebuffer();
        } else I.__webglFramebuffer[lt] = i.createFramebuffer();
    } else {
      if (_.mipmaps && _.mipmaps.length > 0) {
        I.__webglFramebuffer = [];
        for (let lt = 0; lt < _.mipmaps.length; lt++)
          I.__webglFramebuffer[lt] = i.createFramebuffer();
      } else I.__webglFramebuffer = i.createFramebuffer();
      if (yt)
        for (let lt = 0, Ct = J.length; lt < Ct; lt++) {
          const Nt = n.get(J[lt]);
          Nt.__webglTexture === void 0 &&
            ((Nt.__webglTexture = i.createTexture()), a.memory.textures++);
        }
      if (T.samples > 0 && Dt(T) === !1) {
        ((I.__webglMultisampledFramebuffer = i.createFramebuffer()),
          (I.__webglColorRenderbuffer = []),
          e.bindFramebuffer(i.FRAMEBUFFER, I.__webglMultisampledFramebuffer));
        for (let lt = 0; lt < J.length; lt++) {
          const Ct = J[lt];
          ((I.__webglColorRenderbuffer[lt] = i.createRenderbuffer()),
            i.bindRenderbuffer(i.RENDERBUFFER, I.__webglColorRenderbuffer[lt]));
          const Nt = r.convert(Ct.format, Ct.colorSpace),
            Q = r.convert(Ct.type),
            it = y(Ct.internalFormat, Nt, Q, Ct.colorSpace, T.isXRRenderTarget === !0),
            Et = A(T);
          (i.renderbufferStorageMultisample(i.RENDERBUFFER, Et, it, T.width, T.height),
            i.framebufferRenderbuffer(
              i.FRAMEBUFFER,
              i.COLOR_ATTACHMENT0 + lt,
              i.RENDERBUFFER,
              I.__webglColorRenderbuffer[lt]
            ));
        }
        (i.bindRenderbuffer(i.RENDERBUFFER, null),
          T.depthBuffer &&
            ((I.__webglDepthRenderbuffer = i.createRenderbuffer()),
            It(I.__webglDepthRenderbuffer, T, !0)),
          e.bindFramebuffer(i.FRAMEBUFFER, null));
      }
    }
    if (q) {
      (e.bindTexture(i.TEXTURE_CUBE_MAP, X.__webglTexture), gt(i.TEXTURE_CUBE_MAP, _));
      for (let lt = 0; lt < 6; lt++)
        if (_.mipmaps && _.mipmaps.length > 0)
          for (let Ct = 0; Ct < _.mipmaps.length; Ct++)
            at(
              I.__webglFramebuffer[lt][Ct],
              T,
              _,
              i.COLOR_ATTACHMENT0,
              i.TEXTURE_CUBE_MAP_POSITIVE_X + lt,
              Ct
            );
        else
          at(
            I.__webglFramebuffer[lt],
            T,
            _,
            i.COLOR_ATTACHMENT0,
            i.TEXTURE_CUBE_MAP_POSITIVE_X + lt,
            0
          );
      (m(_) && d(i.TEXTURE_CUBE_MAP), e.unbindTexture());
    } else if (yt) {
      for (let lt = 0, Ct = J.length; lt < Ct; lt++) {
        const Nt = J[lt],
          Q = n.get(Nt);
        let it = i.TEXTURE_2D;
        ((T.isWebGL3DRenderTarget || T.isWebGLArrayRenderTarget) &&
          (it = T.isWebGL3DRenderTarget ? i.TEXTURE_3D : i.TEXTURE_2D_ARRAY),
          e.bindTexture(it, Q.__webglTexture),
          gt(it, Nt),
          at(I.__webglFramebuffer, T, Nt, i.COLOR_ATTACHMENT0 + lt, it, 0),
          m(Nt) && d(it));
      }
      e.unbindTexture();
    } else {
      let lt = i.TEXTURE_2D;
      if (
        ((T.isWebGL3DRenderTarget || T.isWebGLArrayRenderTarget) &&
          (lt = T.isWebGL3DRenderTarget ? i.TEXTURE_3D : i.TEXTURE_2D_ARRAY),
        e.bindTexture(lt, X.__webglTexture),
        gt(lt, _),
        _.mipmaps && _.mipmaps.length > 0)
      )
        for (let Ct = 0; Ct < _.mipmaps.length; Ct++)
          at(I.__webglFramebuffer[Ct], T, _, i.COLOR_ATTACHMENT0, lt, Ct);
      else at(I.__webglFramebuffer, T, _, i.COLOR_ATTACHMENT0, lt, 0);
      (m(_) && d(lt), e.unbindTexture());
    }
    T.depthBuffer && Vt(T);
  }
  function $(T) {
    const _ = T.textures;
    for (let I = 0, X = _.length; I < X; I++) {
      const J = _[I];
      if (m(J)) {
        const q = E(T),
          yt = n.get(J).__webglTexture;
        (e.bindTexture(q, yt), d(q), e.unbindTexture());
      }
    }
  }
  const tt = [],
    K = [];
  function ut(T) {
    if (T.samples > 0) {
      if (Dt(T) === !1) {
        const _ = T.textures,
          I = T.width,
          X = T.height;
        let J = i.COLOR_BUFFER_BIT;
        const q = T.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT,
          yt = n.get(T),
          lt = _.length > 1;
        if (lt)
          for (let Nt = 0; Nt < _.length; Nt++)
            (e.bindFramebuffer(i.FRAMEBUFFER, yt.__webglMultisampledFramebuffer),
              i.framebufferRenderbuffer(
                i.FRAMEBUFFER,
                i.COLOR_ATTACHMENT0 + Nt,
                i.RENDERBUFFER,
                null
              ),
              e.bindFramebuffer(i.FRAMEBUFFER, yt.__webglFramebuffer),
              i.framebufferTexture2D(
                i.DRAW_FRAMEBUFFER,
                i.COLOR_ATTACHMENT0 + Nt,
                i.TEXTURE_2D,
                null,
                0
              ));
        e.bindFramebuffer(i.READ_FRAMEBUFFER, yt.__webglMultisampledFramebuffer);
        const Ct = T.texture.mipmaps;
        Ct && Ct.length > 0
          ? e.bindFramebuffer(i.DRAW_FRAMEBUFFER, yt.__webglFramebuffer[0])
          : e.bindFramebuffer(i.DRAW_FRAMEBUFFER, yt.__webglFramebuffer);
        for (let Nt = 0; Nt < _.length; Nt++) {
          if (
            (T.resolveDepthBuffer &&
              (T.depthBuffer && (J |= i.DEPTH_BUFFER_BIT),
              T.stencilBuffer && T.resolveStencilBuffer && (J |= i.STENCIL_BUFFER_BIT)),
            lt)
          ) {
            i.framebufferRenderbuffer(
              i.READ_FRAMEBUFFER,
              i.COLOR_ATTACHMENT0,
              i.RENDERBUFFER,
              yt.__webglColorRenderbuffer[Nt]
            );
            const Q = n.get(_[Nt]).__webglTexture;
            i.framebufferTexture2D(i.DRAW_FRAMEBUFFER, i.COLOR_ATTACHMENT0, i.TEXTURE_2D, Q, 0);
          }
          (i.blitFramebuffer(0, 0, I, X, 0, 0, I, X, J, i.NEAREST),
            l === !0 &&
              ((tt.length = 0),
              (K.length = 0),
              tt.push(i.COLOR_ATTACHMENT0 + Nt),
              T.depthBuffer &&
                T.resolveDepthBuffer === !1 &&
                (tt.push(q), K.push(q), i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER, K)),
              i.invalidateFramebuffer(i.READ_FRAMEBUFFER, tt)));
        }
        if (
          (e.bindFramebuffer(i.READ_FRAMEBUFFER, null),
          e.bindFramebuffer(i.DRAW_FRAMEBUFFER, null),
          lt)
        )
          for (let Nt = 0; Nt < _.length; Nt++) {
            (e.bindFramebuffer(i.FRAMEBUFFER, yt.__webglMultisampledFramebuffer),
              i.framebufferRenderbuffer(
                i.FRAMEBUFFER,
                i.COLOR_ATTACHMENT0 + Nt,
                i.RENDERBUFFER,
                yt.__webglColorRenderbuffer[Nt]
              ));
            const Q = n.get(_[Nt]).__webglTexture;
            (e.bindFramebuffer(i.FRAMEBUFFER, yt.__webglFramebuffer),
              i.framebufferTexture2D(
                i.DRAW_FRAMEBUFFER,
                i.COLOR_ATTACHMENT0 + Nt,
                i.TEXTURE_2D,
                Q,
                0
              ));
          }
        e.bindFramebuffer(i.DRAW_FRAMEBUFFER, yt.__webglMultisampledFramebuffer);
      } else if (T.depthBuffer && T.resolveDepthBuffer === !1 && l) {
        const _ = T.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT;
        i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER, [_]);
      }
    }
  }
  function A(T) {
    return Math.min(s.maxSamples, T.samples);
  }
  function Dt(T) {
    const _ = n.get(T);
    return (
      T.samples > 0 &&
      t.has('WEBGL_multisampled_render_to_texture') === !0 &&
      _.__useRenderToTexture !== !1
    );
  }
  function xt(T) {
    const _ = a.render.frame;
    h.get(T) !== _ && (h.set(T, _), T.update());
  }
  function Ut(T, _) {
    const I = T.colorSpace,
      X = T.format,
      J = T.type;
    return (
      T.isCompressedTexture === !0 ||
        T.isVideoTexture === !0 ||
        (I !== bi &&
          I !== Dn &&
          ($t.getTransfer(I) === te
            ? (X !== Ye || J !== Oe) &&
              Ft(
                'WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType.'
              )
            : Jt('WebGLTextures: Unsupported texture color space:', I))),
      _
    );
  }
  function ot(T) {
    return (
      typeof HTMLImageElement < 'u' && T instanceof HTMLImageElement
        ? ((c.width = T.naturalWidth || T.width), (c.height = T.naturalHeight || T.height))
        : typeof VideoFrame < 'u' && T instanceof VideoFrame
          ? ((c.width = T.displayWidth), (c.height = T.displayHeight))
          : ((c.width = T.width), (c.height = T.height)),
      c
    );
  }
  ((this.allocateTextureUnit = z),
    (this.resetTextureUnits = N),
    (this.setTexture2D = F),
    (this.setTexture2DArray = O),
    (this.setTexture3D = B),
    (this.setTextureCube = nt),
    (this.rebindTextures = ie),
    (this.setupRenderTarget = Ht),
    (this.updateRenderTargetMipmap = $),
    (this.updateMultisampleRenderTarget = ut),
    (this.setupDepthRenderbuffer = Vt),
    (this.setupFrameBufferTexture = at),
    (this.useMultisampledRTT = Dt),
    (this.isReversedDepthBuffer = function () {
      return e.buffers.depth.getReversed();
    }));
}
function Dg(i, t) {
  function e(n, s = Dn) {
    let r;
    const a = $t.getTransfer(s);
    if (n === Oe) return i.UNSIGNED_BYTE;
    if (n === Va) return i.UNSIGNED_SHORT_4_4_4_4;
    if (n === Ga) return i.UNSIGNED_SHORT_5_5_5_1;
    if (n === Dl) return i.UNSIGNED_INT_5_9_9_9_REV;
    if (n === Il) return i.UNSIGNED_INT_10F_11F_11F_REV;
    if (n === Pl) return i.BYTE;
    if (n === Ll) return i.SHORT;
    if (n === Wi) return i.UNSIGNED_SHORT;
    if (n === za) return i.INT;
    if (n === an) return i.UNSIGNED_INT;
    if (n === en) return i.FLOAT;
    if (n === Sn) return i.HALF_FLOAT;
    if (n === Ul) return i.ALPHA;
    if (n === Nl) return i.RGB;
    if (n === Ye) return i.RGBA;
    if (n === yn) return i.DEPTH_COMPONENT;
    if (n === Yn) return i.DEPTH_STENCIL;
    if (n === Fl) return i.RED;
    if (n === Ha) return i.RED_INTEGER;
    if (n === Ei) return i.RG;
    if (n === ka) return i.RG_INTEGER;
    if (n === Wa) return i.RGBA_INTEGER;
    if (n === Fs || n === Os || n === Bs || n === zs)
      if (a === te)
        if (((r = t.get('WEBGL_compressed_texture_s3tc_srgb')), r !== null)) {
          if (n === Fs) return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;
          if (n === Os) return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;
          if (n === Bs) return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;
          if (n === zs) return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT;
        } else return null;
      else if (((r = t.get('WEBGL_compressed_texture_s3tc')), r !== null)) {
        if (n === Fs) return r.COMPRESSED_RGB_S3TC_DXT1_EXT;
        if (n === Os) return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;
        if (n === Bs) return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;
        if (n === zs) return r.COMPRESSED_RGBA_S3TC_DXT5_EXT;
      } else return null;
    if (n === jr || n === Qr || n === ta || n === ea)
      if (((r = t.get('WEBGL_compressed_texture_pvrtc')), r !== null)) {
        if (n === jr) return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;
        if (n === Qr) return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;
        if (n === ta) return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;
        if (n === ea) return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG;
      } else return null;
    if (n === na || n === ia || n === sa || n === ra || n === aa || n === oa || n === la)
      if (((r = t.get('WEBGL_compressed_texture_etc')), r !== null)) {
        if (n === na || n === ia)
          return a === te ? r.COMPRESSED_SRGB8_ETC2 : r.COMPRESSED_RGB8_ETC2;
        if (n === sa)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC : r.COMPRESSED_RGBA8_ETC2_EAC;
        if (n === ra) return r.COMPRESSED_R11_EAC;
        if (n === aa) return r.COMPRESSED_SIGNED_R11_EAC;
        if (n === oa) return r.COMPRESSED_RG11_EAC;
        if (n === la) return r.COMPRESSED_SIGNED_RG11_EAC;
      } else return null;
    if (
      n === ca ||
      n === ha ||
      n === ua ||
      n === fa ||
      n === da ||
      n === pa ||
      n === ma ||
      n === ga ||
      n === _a ||
      n === xa ||
      n === va ||
      n === Ma ||
      n === Sa ||
      n === ya
    )
      if (((r = t.get('WEBGL_compressed_texture_astc')), r !== null)) {
        if (n === ca)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR : r.COMPRESSED_RGBA_ASTC_4x4_KHR;
        if (n === ha)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR : r.COMPRESSED_RGBA_ASTC_5x4_KHR;
        if (n === ua)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR : r.COMPRESSED_RGBA_ASTC_5x5_KHR;
        if (n === fa)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR : r.COMPRESSED_RGBA_ASTC_6x5_KHR;
        if (n === da)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR : r.COMPRESSED_RGBA_ASTC_6x6_KHR;
        if (n === pa)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR : r.COMPRESSED_RGBA_ASTC_8x5_KHR;
        if (n === ma)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR : r.COMPRESSED_RGBA_ASTC_8x6_KHR;
        if (n === ga)
          return a === te ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR : r.COMPRESSED_RGBA_ASTC_8x8_KHR;
        if (n === _a)
          return a === te
            ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR
            : r.COMPRESSED_RGBA_ASTC_10x5_KHR;
        if (n === xa)
          return a === te
            ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR
            : r.COMPRESSED_RGBA_ASTC_10x6_KHR;
        if (n === va)
          return a === te
            ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR
            : r.COMPRESSED_RGBA_ASTC_10x8_KHR;
        if (n === Ma)
          return a === te
            ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR
            : r.COMPRESSED_RGBA_ASTC_10x10_KHR;
        if (n === Sa)
          return a === te
            ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR
            : r.COMPRESSED_RGBA_ASTC_12x10_KHR;
        if (n === ya)
          return a === te
            ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR
            : r.COMPRESSED_RGBA_ASTC_12x12_KHR;
      } else return null;
    if (n === Ea || n === ba || n === Ta)
      if (((r = t.get('EXT_texture_compression_bptc')), r !== null)) {
        if (n === Ea)
          return a === te
            ? r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT
            : r.COMPRESSED_RGBA_BPTC_UNORM_EXT;
        if (n === ba) return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;
        if (n === Ta) return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT;
      } else return null;
    if (n === Aa || n === wa || n === Ra || n === Ca)
      if (((r = t.get('EXT_texture_compression_rgtc')), r !== null)) {
        if (n === Aa) return r.COMPRESSED_RED_RGTC1_EXT;
        if (n === wa) return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;
        if (n === Ra) return r.COMPRESSED_RED_GREEN_RGTC2_EXT;
        if (n === Ca) return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT;
      } else return null;
    return n === Xi ? i.UNSIGNED_INT_24_8 : i[n] !== void 0 ? i[n] : null;
  }
  return { convert: e };
}
const Ig = `
void main() {

	gl_Position = vec4( position, 1.0 );

}`,
  Ug = `
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;
class Ng {
  constructor() {
    ((this.texture = null), (this.mesh = null), (this.depthNear = 0), (this.depthFar = 0));
  }
  init(t, e) {
    if (this.texture === null) {
      const n = new Yl(t.texture);
      ((t.depthNear !== e.depthNear || t.depthFar !== e.depthFar) &&
        ((this.depthNear = t.depthNear), (this.depthFar = t.depthFar)),
        (this.texture = n));
    }
  }
  getMesh(t) {
    if (this.texture !== null && this.mesh === null) {
      const e = t.cameras[0].viewport,
        n = new on({
          vertexShader: Ig,
          fragmentShader: Ug,
          uniforms: {
            depthColor: { value: this.texture },
            depthWidth: { value: e.z },
            depthHeight: { value: e.w },
          },
        });
      this.mesh = new En(new js(20, 20), n);
    }
    return this.mesh;
  }
  reset() {
    ((this.texture = null), (this.mesh = null));
  }
  getDepthTexture() {
    return this.texture;
  }
}
class Fg extends jn {
  constructor(t, e) {
    super();
    const n = this;
    let s = null,
      r = 1,
      a = null,
      o = 'local-floor',
      l = 1,
      c = null,
      h = null,
      f = null,
      u = null,
      p = null,
      g = null;
    const M = typeof XRWebGLBinding < 'u',
      m = new Ng(),
      d = {},
      E = e.getContextAttributes();
    let y = null,
      S = null;
    const R = [],
      w = [],
      P = new ct();
    let x = null;
    const b = new Fe();
    b.viewport = new ue();
    const H = new Fe();
    H.viewport = new ue();
    const C = [b, H],
      N = new Wu();
    let z = null,
      k = null;
    ((this.cameraAutoUpdate = !0),
      (this.enabled = !1),
      (this.isPresenting = !1),
      (this.getController = function (Z) {
        let rt = R[Z];
        return (rt === void 0 && ((rt = new ur()), (R[Z] = rt)), rt.getTargetRaySpace());
      }),
      (this.getControllerGrip = function (Z) {
        let rt = R[Z];
        return (rt === void 0 && ((rt = new ur()), (R[Z] = rt)), rt.getGripSpace());
      }),
      (this.getHand = function (Z) {
        let rt = R[Z];
        return (rt === void 0 && ((rt = new ur()), (R[Z] = rt)), rt.getHandSpace());
      }));
    function F(Z) {
      const rt = w.indexOf(Z.inputSource);
      if (rt === -1) return;
      const at = R[rt];
      at !== void 0 &&
        (at.update(Z.inputSource, Z.frame, c || a),
        at.dispatchEvent({ type: Z.type, data: Z.inputSource }));
    }
    function O() {
      (s.removeEventListener('select', F),
        s.removeEventListener('selectstart', F),
        s.removeEventListener('selectend', F),
        s.removeEventListener('squeeze', F),
        s.removeEventListener('squeezestart', F),
        s.removeEventListener('squeezeend', F),
        s.removeEventListener('end', O),
        s.removeEventListener('inputsourceschange', B));
      for (let Z = 0; Z < R.length; Z++) {
        const rt = w[Z];
        rt !== null && ((w[Z] = null), R[Z].disconnect(rt));
      }
      ((z = null), (k = null), m.reset());
      for (const Z in d) delete d[Z];
      (t.setRenderTarget(y),
        (p = null),
        (u = null),
        (f = null),
        (s = null),
        (S = null),
        ne.stop(),
        (n.isPresenting = !1),
        t.setPixelRatio(x),
        t.setSize(P.width, P.height, !1),
        n.dispatchEvent({ type: 'sessionend' }));
    }
    ((this.setFramebufferScaleFactor = function (Z) {
      ((r = Z),
        n.isPresenting === !0 &&
          Ft('WebXRManager: Cannot change framebuffer scale while presenting.'));
    }),
      (this.setReferenceSpaceType = function (Z) {
        ((o = Z),
          n.isPresenting === !0 &&
            Ft('WebXRManager: Cannot change reference space type while presenting.'));
      }),
      (this.getReferenceSpace = function () {
        return c || a;
      }),
      (this.setReferenceSpace = function (Z) {
        c = Z;
      }),
      (this.getBaseLayer = function () {
        return u !== null ? u : p;
      }),
      (this.getBinding = function () {
        return (f === null && M && (f = new XRWebGLBinding(s, e)), f);
      }),
      (this.getFrame = function () {
        return g;
      }),
      (this.getSession = function () {
        return s;
      }),
      (this.setSession = async function (Z) {
        if (((s = Z), s !== null)) {
          if (
            ((y = t.getRenderTarget()),
            s.addEventListener('select', F),
            s.addEventListener('selectstart', F),
            s.addEventListener('selectend', F),
            s.addEventListener('squeeze', F),
            s.addEventListener('squeezestart', F),
            s.addEventListener('squeezeend', F),
            s.addEventListener('end', O),
            s.addEventListener('inputsourceschange', B),
            E.xrCompatible !== !0 && (await e.makeXRCompatible()),
            (x = t.getPixelRatio()),
            t.getSize(P),
            M && 'createProjectionLayer' in XRWebGLBinding.prototype)
          ) {
            let at = null,
              It = null,
              Lt = null;
            E.depth &&
              ((Lt = E.stencil ? e.DEPTH24_STENCIL8 : e.DEPTH_COMPONENT24),
              (at = E.stencil ? Yn : yn),
              (It = E.stencil ? Xi : an));
            const Vt = { colorFormat: e.RGBA8, depthFormat: Lt, scaleFactor: r };
            ((f = this.getBinding()),
              (u = f.createProjectionLayer(Vt)),
              s.updateRenderState({ layers: [u] }),
              t.setPixelRatio(1),
              t.setSize(u.textureWidth, u.textureHeight, !1),
              (S = new rn(u.textureWidth, u.textureHeight, {
                format: Ye,
                type: Oe,
                depthTexture: new Zi(
                  u.textureWidth,
                  u.textureHeight,
                  It,
                  void 0,
                  void 0,
                  void 0,
                  void 0,
                  void 0,
                  void 0,
                  at
                ),
                stencilBuffer: E.stencil,
                colorSpace: t.outputColorSpace,
                samples: E.antialias ? 4 : 0,
                resolveDepthBuffer: u.ignoreDepthValues === !1,
                resolveStencilBuffer: u.ignoreDepthValues === !1,
              })));
          } else {
            const at = {
              antialias: E.antialias,
              alpha: !0,
              depth: E.depth,
              stencil: E.stencil,
              framebufferScaleFactor: r,
            };
            ((p = new XRWebGLLayer(s, e, at)),
              s.updateRenderState({ baseLayer: p }),
              t.setPixelRatio(1),
              t.setSize(p.framebufferWidth, p.framebufferHeight, !1),
              (S = new rn(p.framebufferWidth, p.framebufferHeight, {
                format: Ye,
                type: Oe,
                colorSpace: t.outputColorSpace,
                stencilBuffer: E.stencil,
                resolveDepthBuffer: p.ignoreDepthValues === !1,
                resolveStencilBuffer: p.ignoreDepthValues === !1,
              })));
          }
          ((S.isXRRenderTarget = !0),
            this.setFoveation(l),
            (c = null),
            (a = await s.requestReferenceSpace(o)),
            ne.setContext(s),
            ne.start(),
            (n.isPresenting = !0),
            n.dispatchEvent({ type: 'sessionstart' }));
        }
      }),
      (this.getEnvironmentBlendMode = function () {
        if (s !== null) return s.environmentBlendMode;
      }),
      (this.getDepthTexture = function () {
        return m.getDepthTexture();
      }));
    function B(Z) {
      for (let rt = 0; rt < Z.removed.length; rt++) {
        const at = Z.removed[rt],
          It = w.indexOf(at);
        It >= 0 && ((w[It] = null), R[It].disconnect(at));
      }
      for (let rt = 0; rt < Z.added.length; rt++) {
        const at = Z.added[rt];
        let It = w.indexOf(at);
        if (It === -1) {
          for (let Vt = 0; Vt < R.length; Vt++)
            if (Vt >= w.length) {
              (w.push(at), (It = Vt));
              break;
            } else if (w[Vt] === null) {
              ((w[Vt] = at), (It = Vt));
              break;
            }
          if (It === -1) break;
        }
        const Lt = R[It];
        Lt && Lt.connect(at);
      }
    }
    const nt = new L(),
      j = new L();
    function mt(Z, rt, at) {
      (nt.setFromMatrixPosition(rt.matrixWorld), j.setFromMatrixPosition(at.matrixWorld));
      const It = nt.distanceTo(j),
        Lt = rt.projectionMatrix.elements,
        Vt = at.projectionMatrix.elements,
        ie = Lt[14] / (Lt[10] - 1),
        Ht = Lt[14] / (Lt[10] + 1),
        $ = (Lt[9] + 1) / Lt[5],
        tt = (Lt[9] - 1) / Lt[5],
        K = (Lt[8] - 1) / Lt[0],
        ut = (Vt[8] + 1) / Vt[0],
        A = ie * K,
        Dt = ie * ut,
        xt = It / (-K + ut),
        Ut = xt * -K;
      if (
        (rt.matrixWorld.decompose(Z.position, Z.quaternion, Z.scale),
        Z.translateX(Ut),
        Z.translateZ(xt),
        Z.matrixWorld.compose(Z.position, Z.quaternion, Z.scale),
        Z.matrixWorldInverse.copy(Z.matrixWorld).invert(),
        Lt[10] === -1)
      )
        (Z.projectionMatrix.copy(rt.projectionMatrix),
          Z.projectionMatrixInverse.copy(rt.projectionMatrixInverse));
      else {
        const ot = ie + xt,
          T = Ht + xt,
          _ = A - Ut,
          I = Dt + (It - Ut),
          X = (($ * Ht) / T) * ot,
          J = ((tt * Ht) / T) * ot;
        (Z.projectionMatrix.makePerspective(_, I, X, J, ot, T),
          Z.projectionMatrixInverse.copy(Z.projectionMatrix).invert());
      }
    }
    function _t(Z, rt) {
      (rt === null
        ? Z.matrixWorld.copy(Z.matrix)
        : Z.matrixWorld.multiplyMatrices(rt.matrixWorld, Z.matrix),
        Z.matrixWorldInverse.copy(Z.matrixWorld).invert());
    }
    this.updateCamera = function (Z) {
      if (s === null) return;
      let rt = Z.near,
        at = Z.far;
      (m.texture !== null &&
        (m.depthNear > 0 && (rt = m.depthNear), m.depthFar > 0 && (at = m.depthFar)),
        (N.near = H.near = b.near = rt),
        (N.far = H.far = b.far = at),
        (z !== N.near || k !== N.far) &&
          (s.updateRenderState({ depthNear: N.near, depthFar: N.far }), (z = N.near), (k = N.far)),
        (N.layers.mask = Z.layers.mask | 6),
        (b.layers.mask = N.layers.mask & -5),
        (H.layers.mask = N.layers.mask & -3));
      const It = Z.parent,
        Lt = N.cameras;
      _t(N, It);
      for (let Vt = 0; Vt < Lt.length; Vt++) _t(Lt[Vt], It);
      (Lt.length === 2 ? mt(N, b, H) : N.projectionMatrix.copy(b.projectionMatrix), gt(Z, N, It));
    };
    function gt(Z, rt, at) {
      (at === null
        ? Z.matrix.copy(rt.matrixWorld)
        : (Z.matrix.copy(at.matrixWorld), Z.matrix.invert(), Z.matrix.multiply(rt.matrixWorld)),
        Z.matrix.decompose(Z.position, Z.quaternion, Z.scale),
        Z.updateMatrixWorld(!0),
        Z.projectionMatrix.copy(rt.projectionMatrix),
        Z.projectionMatrixInverse.copy(rt.projectionMatrixInverse),
        Z.isPerspectiveCamera &&
          ((Z.fov = Ti * 2 * Math.atan(1 / Z.projectionMatrix.elements[5])), (Z.zoom = 1)));
    }
    ((this.getCamera = function () {
      return N;
    }),
      (this.getFoveation = function () {
        if (!(u === null && p === null)) return l;
      }),
      (this.setFoveation = function (Z) {
        ((l = Z),
          u !== null && (u.fixedFoveation = Z),
          p !== null && p.fixedFoveation !== void 0 && (p.fixedFoveation = Z));
      }),
      (this.hasDepthSensing = function () {
        return m.texture !== null;
      }),
      (this.getDepthSensingMesh = function () {
        return m.getMesh(N);
      }),
      (this.getCameraTexture = function (Z) {
        return d[Z];
      }));
    let Ot = null;
    function jt(Z, rt) {
      if (((h = rt.getViewerPose(c || a)), (g = rt), h !== null)) {
        const at = h.views;
        p !== null && (t.setRenderTargetFramebuffer(S, p.framebuffer), t.setRenderTarget(S));
        let It = !1;
        at.length !== N.cameras.length && ((N.cameras.length = 0), (It = !0));
        for (let Ht = 0; Ht < at.length; Ht++) {
          const $ = at[Ht];
          let tt = null;
          if (p !== null) tt = p.getViewport($);
          else {
            const ut = f.getViewSubImage(u, $);
            ((tt = ut.viewport),
              Ht === 0 &&
                (t.setRenderTargetTextures(S, ut.colorTexture, ut.depthStencilTexture),
                t.setRenderTarget(S)));
          }
          let K = C[Ht];
          (K === void 0 &&
            ((K = new Fe()), K.layers.enable(Ht), (K.viewport = new ue()), (C[Ht] = K)),
            K.matrix.fromArray($.transform.matrix),
            K.matrix.decompose(K.position, K.quaternion, K.scale),
            K.projectionMatrix.fromArray($.projectionMatrix),
            K.projectionMatrixInverse.copy(K.projectionMatrix).invert(),
            K.viewport.set(tt.x, tt.y, tt.width, tt.height),
            Ht === 0 &&
              (N.matrix.copy(K.matrix), N.matrix.decompose(N.position, N.quaternion, N.scale)),
            It === !0 && N.cameras.push(K));
        }
        const Lt = s.enabledFeatures;
        if (Lt && Lt.includes('depth-sensing') && s.depthUsage == 'gpu-optimized' && M) {
          f = n.getBinding();
          const Ht = f.getDepthInformation(at[0]);
          Ht && Ht.isValid && Ht.texture && m.init(Ht, s.renderState);
        }
        if (Lt && Lt.includes('camera-access') && M) {
          (t.state.unbindTexture(), (f = n.getBinding()));
          for (let Ht = 0; Ht < at.length; Ht++) {
            const $ = at[Ht].camera;
            if ($) {
              let tt = d[$];
              tt || ((tt = new Yl()), (d[$] = tt));
              const K = f.getCameraImage($);
              tt.sourceTexture = K;
            }
          }
        }
      }
      for (let at = 0; at < R.length; at++) {
        const It = w[at],
          Lt = R[at];
        It !== null && Lt !== void 0 && Lt.update(It, rt, c || a);
      }
      (Ot && Ot(Z, rt),
        rt.detectedPlanes && n.dispatchEvent({ type: 'planesdetected', data: rt }),
        (g = null));
    }
    const ne = new fc();
    (ne.setAnimationLoop(jt),
      (this.setAnimationLoop = function (Z) {
        Ot = Z;
      }),
      (this.dispose = function () {}));
  }
}
const Hn = new Ge(),
  Og = new oe();
function Bg(i, t) {
  function e(m, d) {
    (m.matrixAutoUpdate === !0 && m.updateMatrix(), d.value.copy(m.matrix));
  }
  function n(m, d) {
    (d.color.getRGB(m.fogColor.value, cc(i)),
      d.isFog
        ? ((m.fogNear.value = d.near), (m.fogFar.value = d.far))
        : d.isFogExp2 && (m.fogDensity.value = d.density));
  }
  function s(m, d, E, y, S) {
    d.isMeshBasicMaterial
      ? r(m, d)
      : d.isMeshLambertMaterial
        ? (r(m, d), d.envMap && (m.envMapIntensity.value = d.envMapIntensity))
        : d.isMeshToonMaterial
          ? (r(m, d), f(m, d))
          : d.isMeshPhongMaterial
            ? (r(m, d), h(m, d), d.envMap && (m.envMapIntensity.value = d.envMapIntensity))
            : d.isMeshStandardMaterial
              ? (r(m, d), u(m, d), d.isMeshPhysicalMaterial && p(m, d, S))
              : d.isMeshMatcapMaterial
                ? (r(m, d), g(m, d))
                : d.isMeshDepthMaterial
                  ? r(m, d)
                  : d.isMeshDistanceMaterial
                    ? (r(m, d), M(m, d))
                    : d.isMeshNormalMaterial
                      ? r(m, d)
                      : d.isLineBasicMaterial
                        ? (a(m, d), d.isLineDashedMaterial && o(m, d))
                        : d.isPointsMaterial
                          ? l(m, d, E, y)
                          : d.isSpriteMaterial
                            ? c(m, d)
                            : d.isShadowMaterial
                              ? (m.color.value.copy(d.color), (m.opacity.value = d.opacity))
                              : d.isShaderMaterial && (d.uniformsNeedUpdate = !1);
  }
  function r(m, d) {
    ((m.opacity.value = d.opacity),
      d.color && m.diffuse.value.copy(d.color),
      d.emissive && m.emissive.value.copy(d.emissive).multiplyScalar(d.emissiveIntensity),
      d.map && ((m.map.value = d.map), e(d.map, m.mapTransform)),
      d.alphaMap && ((m.alphaMap.value = d.alphaMap), e(d.alphaMap, m.alphaMapTransform)),
      d.bumpMap &&
        ((m.bumpMap.value = d.bumpMap),
        e(d.bumpMap, m.bumpMapTransform),
        (m.bumpScale.value = d.bumpScale),
        d.side === Pe && (m.bumpScale.value *= -1)),
      d.normalMap &&
        ((m.normalMap.value = d.normalMap),
        e(d.normalMap, m.normalMapTransform),
        m.normalScale.value.copy(d.normalScale),
        d.side === Pe && m.normalScale.value.negate()),
      d.displacementMap &&
        ((m.displacementMap.value = d.displacementMap),
        e(d.displacementMap, m.displacementMapTransform),
        (m.displacementScale.value = d.displacementScale),
        (m.displacementBias.value = d.displacementBias)),
      d.emissiveMap &&
        ((m.emissiveMap.value = d.emissiveMap), e(d.emissiveMap, m.emissiveMapTransform)),
      d.specularMap &&
        ((m.specularMap.value = d.specularMap), e(d.specularMap, m.specularMapTransform)),
      d.alphaTest > 0 && (m.alphaTest.value = d.alphaTest));
    const E = t.get(d),
      y = E.envMap,
      S = E.envMapRotation;
    (y &&
      ((m.envMap.value = y),
      Hn.copy(S),
      (Hn.x *= -1),
      (Hn.y *= -1),
      (Hn.z *= -1),
      y.isCubeTexture && y.isRenderTargetTexture === !1 && ((Hn.y *= -1), (Hn.z *= -1)),
      m.envMapRotation.value.setFromMatrix4(Og.makeRotationFromEuler(Hn)),
      (m.flipEnvMap.value = y.isCubeTexture && y.isRenderTargetTexture === !1 ? -1 : 1),
      (m.reflectivity.value = d.reflectivity),
      (m.ior.value = d.ior),
      (m.refractionRatio.value = d.refractionRatio)),
      d.lightMap &&
        ((m.lightMap.value = d.lightMap),
        (m.lightMapIntensity.value = d.lightMapIntensity),
        e(d.lightMap, m.lightMapTransform)),
      d.aoMap &&
        ((m.aoMap.value = d.aoMap),
        (m.aoMapIntensity.value = d.aoMapIntensity),
        e(d.aoMap, m.aoMapTransform)));
  }
  function a(m, d) {
    (m.diffuse.value.copy(d.color),
      (m.opacity.value = d.opacity),
      d.map && ((m.map.value = d.map), e(d.map, m.mapTransform)));
  }
  function o(m, d) {
    ((m.dashSize.value = d.dashSize),
      (m.totalSize.value = d.dashSize + d.gapSize),
      (m.scale.value = d.scale));
  }
  function l(m, d, E, y) {
    (m.diffuse.value.copy(d.color),
      (m.opacity.value = d.opacity),
      (m.size.value = d.size * E),
      (m.scale.value = y * 0.5),
      d.map && ((m.map.value = d.map), e(d.map, m.uvTransform)),
      d.alphaMap && ((m.alphaMap.value = d.alphaMap), e(d.alphaMap, m.alphaMapTransform)),
      d.alphaTest > 0 && (m.alphaTest.value = d.alphaTest));
  }
  function c(m, d) {
    (m.diffuse.value.copy(d.color),
      (m.opacity.value = d.opacity),
      (m.rotation.value = d.rotation),
      d.map && ((m.map.value = d.map), e(d.map, m.mapTransform)),
      d.alphaMap && ((m.alphaMap.value = d.alphaMap), e(d.alphaMap, m.alphaMapTransform)),
      d.alphaTest > 0 && (m.alphaTest.value = d.alphaTest));
  }
  function h(m, d) {
    (m.specular.value.copy(d.specular), (m.shininess.value = Math.max(d.shininess, 1e-4)));
  }
  function f(m, d) {
    d.gradientMap && (m.gradientMap.value = d.gradientMap);
  }
  function u(m, d) {
    ((m.metalness.value = d.metalness),
      d.metalnessMap &&
        ((m.metalnessMap.value = d.metalnessMap), e(d.metalnessMap, m.metalnessMapTransform)),
      (m.roughness.value = d.roughness),
      d.roughnessMap &&
        ((m.roughnessMap.value = d.roughnessMap), e(d.roughnessMap, m.roughnessMapTransform)),
      d.envMap && (m.envMapIntensity.value = d.envMapIntensity));
  }
  function p(m, d, E) {
    ((m.ior.value = d.ior),
      d.sheen > 0 &&
        (m.sheenColor.value.copy(d.sheenColor).multiplyScalar(d.sheen),
        (m.sheenRoughness.value = d.sheenRoughness),
        d.sheenColorMap &&
          ((m.sheenColorMap.value = d.sheenColorMap), e(d.sheenColorMap, m.sheenColorMapTransform)),
        d.sheenRoughnessMap &&
          ((m.sheenRoughnessMap.value = d.sheenRoughnessMap),
          e(d.sheenRoughnessMap, m.sheenRoughnessMapTransform))),
      d.clearcoat > 0 &&
        ((m.clearcoat.value = d.clearcoat),
        (m.clearcoatRoughness.value = d.clearcoatRoughness),
        d.clearcoatMap &&
          ((m.clearcoatMap.value = d.clearcoatMap), e(d.clearcoatMap, m.clearcoatMapTransform)),
        d.clearcoatRoughnessMap &&
          ((m.clearcoatRoughnessMap.value = d.clearcoatRoughnessMap),
          e(d.clearcoatRoughnessMap, m.clearcoatRoughnessMapTransform)),
        d.clearcoatNormalMap &&
          ((m.clearcoatNormalMap.value = d.clearcoatNormalMap),
          e(d.clearcoatNormalMap, m.clearcoatNormalMapTransform),
          m.clearcoatNormalScale.value.copy(d.clearcoatNormalScale),
          d.side === Pe && m.clearcoatNormalScale.value.negate())),
      d.dispersion > 0 && (m.dispersion.value = d.dispersion),
      d.iridescence > 0 &&
        ((m.iridescence.value = d.iridescence),
        (m.iridescenceIOR.value = d.iridescenceIOR),
        (m.iridescenceThicknessMinimum.value = d.iridescenceThicknessRange[0]),
        (m.iridescenceThicknessMaximum.value = d.iridescenceThicknessRange[1]),
        d.iridescenceMap &&
          ((m.iridescenceMap.value = d.iridescenceMap),
          e(d.iridescenceMap, m.iridescenceMapTransform)),
        d.iridescenceThicknessMap &&
          ((m.iridescenceThicknessMap.value = d.iridescenceThicknessMap),
          e(d.iridescenceThicknessMap, m.iridescenceThicknessMapTransform))),
      d.transmission > 0 &&
        ((m.transmission.value = d.transmission),
        (m.transmissionSamplerMap.value = E.texture),
        m.transmissionSamplerSize.value.set(E.width, E.height),
        d.transmissionMap &&
          ((m.transmissionMap.value = d.transmissionMap),
          e(d.transmissionMap, m.transmissionMapTransform)),
        (m.thickness.value = d.thickness),
        d.thicknessMap &&
          ((m.thicknessMap.value = d.thicknessMap), e(d.thicknessMap, m.thicknessMapTransform)),
        (m.attenuationDistance.value = d.attenuationDistance),
        m.attenuationColor.value.copy(d.attenuationColor)),
      d.anisotropy > 0 &&
        (m.anisotropyVector.value.set(
          d.anisotropy * Math.cos(d.anisotropyRotation),
          d.anisotropy * Math.sin(d.anisotropyRotation)
        ),
        d.anisotropyMap &&
          ((m.anisotropyMap.value = d.anisotropyMap),
          e(d.anisotropyMap, m.anisotropyMapTransform))),
      (m.specularIntensity.value = d.specularIntensity),
      m.specularColor.value.copy(d.specularColor),
      d.specularColorMap &&
        ((m.specularColorMap.value = d.specularColorMap),
        e(d.specularColorMap, m.specularColorMapTransform)),
      d.specularIntensityMap &&
        ((m.specularIntensityMap.value = d.specularIntensityMap),
        e(d.specularIntensityMap, m.specularIntensityMapTransform)));
  }
  function g(m, d) {
    d.matcap && (m.matcap.value = d.matcap);
  }
  function M(m, d) {
    const E = t.get(d).light;
    (m.referencePosition.value.setFromMatrixPosition(E.matrixWorld),
      (m.nearDistance.value = E.shadow.camera.near),
      (m.farDistance.value = E.shadow.camera.far));
  }
  return { refreshFogUniforms: n, refreshMaterialUniforms: s };
}
function zg(i, t, e, n) {
  let s = {},
    r = {},
    a = [];
  const o = i.getParameter(i.MAX_UNIFORM_BUFFER_BINDINGS);
  function l(E, y) {
    const S = y.program;
    n.uniformBlockBinding(E, S);
  }
  function c(E, y) {
    let S = s[E.id];
    S === void 0 && (g(E), (S = h(E)), (s[E.id] = S), E.addEventListener('dispose', m));
    const R = y.program;
    n.updateUBOMapping(E, R);
    const w = t.render.frame;
    r[E.id] !== w && (u(E), (r[E.id] = w));
  }
  function h(E) {
    const y = f();
    E.__bindingPointIndex = y;
    const S = i.createBuffer(),
      R = E.__size,
      w = E.usage;
    return (
      i.bindBuffer(i.UNIFORM_BUFFER, S),
      i.bufferData(i.UNIFORM_BUFFER, R, w),
      i.bindBuffer(i.UNIFORM_BUFFER, null),
      i.bindBufferBase(i.UNIFORM_BUFFER, y, S),
      S
    );
  }
  function f() {
    for (let E = 0; E < o; E++) if (a.indexOf(E) === -1) return (a.push(E), E);
    return (
      Jt('WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached.'),
      0
    );
  }
  function u(E) {
    const y = s[E.id],
      S = E.uniforms,
      R = E.__cache;
    i.bindBuffer(i.UNIFORM_BUFFER, y);
    for (let w = 0, P = S.length; w < P; w++) {
      const x = Array.isArray(S[w]) ? S[w] : [S[w]];
      for (let b = 0, H = x.length; b < H; b++) {
        const C = x[b];
        if (p(C, w, b, R) === !0) {
          const N = C.__offset,
            z = Array.isArray(C.value) ? C.value : [C.value];
          let k = 0;
          for (let F = 0; F < z.length; F++) {
            const O = z[F],
              B = M(O);
            typeof O == 'number' || typeof O == 'boolean'
              ? ((C.__data[0] = O), i.bufferSubData(i.UNIFORM_BUFFER, N + k, C.__data))
              : O.isMatrix3
                ? ((C.__data[0] = O.elements[0]),
                  (C.__data[1] = O.elements[1]),
                  (C.__data[2] = O.elements[2]),
                  (C.__data[3] = 0),
                  (C.__data[4] = O.elements[3]),
                  (C.__data[5] = O.elements[4]),
                  (C.__data[6] = O.elements[5]),
                  (C.__data[7] = 0),
                  (C.__data[8] = O.elements[6]),
                  (C.__data[9] = O.elements[7]),
                  (C.__data[10] = O.elements[8]),
                  (C.__data[11] = 0))
                : (O.toArray(C.__data, k), (k += B.storage / Float32Array.BYTES_PER_ELEMENT));
          }
          i.bufferSubData(i.UNIFORM_BUFFER, N, C.__data);
        }
      }
    }
    i.bindBuffer(i.UNIFORM_BUFFER, null);
  }
  function p(E, y, S, R) {
    const w = E.value,
      P = y + '_' + S;
    if (R[P] === void 0)
      return (typeof w == 'number' || typeof w == 'boolean' ? (R[P] = w) : (R[P] = w.clone()), !0);
    {
      const x = R[P];
      if (typeof w == 'number' || typeof w == 'boolean') {
        if (x !== w) return ((R[P] = w), !0);
      } else if (x.equals(w) === !1) return (x.copy(w), !0);
    }
    return !1;
  }
  function g(E) {
    const y = E.uniforms;
    let S = 0;
    const R = 16;
    for (let P = 0, x = y.length; P < x; P++) {
      const b = Array.isArray(y[P]) ? y[P] : [y[P]];
      for (let H = 0, C = b.length; H < C; H++) {
        const N = b[H],
          z = Array.isArray(N.value) ? N.value : [N.value];
        for (let k = 0, F = z.length; k < F; k++) {
          const O = z[k],
            B = M(O),
            nt = S % R,
            j = nt % B.boundary,
            mt = nt + j;
          ((S += j),
            mt !== 0 && R - mt < B.storage && (S += R - mt),
            (N.__data = new Float32Array(B.storage / Float32Array.BYTES_PER_ELEMENT)),
            (N.__offset = S),
            (S += B.storage));
        }
      }
    }
    const w = S % R;
    return (w > 0 && (S += R - w), (E.__size = S), (E.__cache = {}), this);
  }
  function M(E) {
    const y = { boundary: 0, storage: 0 };
    return (
      typeof E == 'number' || typeof E == 'boolean'
        ? ((y.boundary = 4), (y.storage = 4))
        : E.isVector2
          ? ((y.boundary = 8), (y.storage = 8))
          : E.isVector3 || E.isColor
            ? ((y.boundary = 16), (y.storage = 12))
            : E.isVector4
              ? ((y.boundary = 16), (y.storage = 16))
              : E.isMatrix3
                ? ((y.boundary = 48), (y.storage = 48))
                : E.isMatrix4
                  ? ((y.boundary = 64), (y.storage = 64))
                  : E.isTexture
                    ? Ft('WebGLRenderer: Texture samplers can not be part of an uniforms group.')
                    : Ft('WebGLRenderer: Unsupported uniform value type.', E),
      y
    );
  }
  function m(E) {
    const y = E.target;
    y.removeEventListener('dispose', m);
    const S = a.indexOf(y.__bindingPointIndex);
    (a.splice(S, 1), i.deleteBuffer(s[y.id]), delete s[y.id], delete r[y.id]);
  }
  function d() {
    for (const E in s) i.deleteBuffer(s[E]);
    ((a = []), (s = {}), (r = {}));
  }
  return { bind: l, update: c, dispose: d };
}
const Vg = new Uint16Array([
  12469, 15057, 12620, 14925, 13266, 14620, 13807, 14376, 14323, 13990, 14545, 13625, 14713, 13328,
  14840, 12882, 14931, 12528, 14996, 12233, 15039, 11829, 15066, 11525, 15080, 11295, 15085, 10976,
  15082, 10705, 15073, 10495, 13880, 14564, 13898, 14542, 13977, 14430, 14158, 14124, 14393, 13732,
  14556, 13410, 14702, 12996, 14814, 12596, 14891, 12291, 14937, 11834, 14957, 11489, 14958, 11194,
  14943, 10803, 14921, 10506, 14893, 10278, 14858, 9960, 14484, 14039, 14487, 14025, 14499, 13941,
  14524, 13740, 14574, 13468, 14654, 13106, 14743, 12678, 14818, 12344, 14867, 11893, 14889, 11509,
  14893, 11180, 14881, 10751, 14852, 10428, 14812, 10128, 14765, 9754, 14712, 9466, 14764, 13480,
  14764, 13475, 14766, 13440, 14766, 13347, 14769, 13070, 14786, 12713, 14816, 12387, 14844, 11957,
  14860, 11549, 14868, 11215, 14855, 10751, 14825, 10403, 14782, 10044, 14729, 9651, 14666, 9352,
  14599, 9029, 14967, 12835, 14966, 12831, 14963, 12804, 14954, 12723, 14936, 12564, 14917, 12347,
  14900, 11958, 14886, 11569, 14878, 11247, 14859, 10765, 14828, 10401, 14784, 10011, 14727, 9600,
  14660, 9289, 14586, 8893, 14508, 8533, 15111, 12234, 15110, 12234, 15104, 12216, 15092, 12156,
  15067, 12010, 15028, 11776, 14981, 11500, 14942, 11205, 14902, 10752, 14861, 10393, 14812, 9991,
  14752, 9570, 14682, 9252, 14603, 8808, 14519, 8445, 14431, 8145, 15209, 11449, 15208, 11451,
  15202, 11451, 15190, 11438, 15163, 11384, 15117, 11274, 15055, 10979, 14994, 10648, 14932, 10343,
  14871, 9936, 14803, 9532, 14729, 9218, 14645, 8742, 14556, 8381, 14461, 8020, 14365, 7603, 15273,
  10603, 15272, 10607, 15267, 10619, 15256, 10631, 15231, 10614, 15182, 10535, 15118, 10389, 15042,
  10167, 14963, 9787, 14883, 9447, 14800, 9115, 14710, 8665, 14615, 8318, 14514, 7911, 14411, 7507,
  14279, 7198, 15314, 9675, 15313, 9683, 15309, 9712, 15298, 9759, 15277, 9797, 15229, 9773, 15166,
  9668, 15084, 9487, 14995, 9274, 14898, 8910, 14800, 8539, 14697, 8234, 14590, 7790, 14479, 7409,
  14367, 7067, 14178, 6621, 15337, 8619, 15337, 8631, 15333, 8677, 15325, 8769, 15305, 8871, 15264,
  8940, 15202, 8909, 15119, 8775, 15022, 8565, 14916, 8328, 14804, 8009, 14688, 7614, 14569, 7287,
  14448, 6888, 14321, 6483, 14088, 6171, 15350, 7402, 15350, 7419, 15347, 7480, 15340, 7613, 15322,
  7804, 15287, 7973, 15229, 8057, 15148, 8012, 15046, 7846, 14933, 7611, 14810, 7357, 14682, 7069,
  14552, 6656, 14421, 6316, 14251, 5948, 14007, 5528, 15356, 5942, 15356, 5977, 15353, 6119, 15348,
  6294, 15332, 6551, 15302, 6824, 15249, 7044, 15171, 7122, 15070, 7050, 14949, 6861, 14818, 6611,
  14679, 6349, 14538, 6067, 14398, 5651, 14189, 5311, 13935, 4958, 15359, 4123, 15359, 4153, 15356,
  4296, 15353, 4646, 15338, 5160, 15311, 5508, 15263, 5829, 15188, 6042, 15088, 6094, 14966, 6001,
  14826, 5796, 14678, 5543, 14527, 5287, 14377, 4985, 14133, 4586, 13869, 4257, 15360, 1563, 15360,
  1642, 15358, 2076, 15354, 2636, 15341, 3350, 15317, 4019, 15273, 4429, 15203, 4732, 15105, 4911,
  14981, 4932, 14836, 4818, 14679, 4621, 14517, 4386, 14359, 4156, 14083, 3795, 13808, 3437, 15360,
  122, 15360, 137, 15358, 285, 15355, 636, 15344, 1274, 15322, 2177, 15281, 2765, 15215, 3223,
  15120, 3451, 14995, 3569, 14846, 3567, 14681, 3466, 14511, 3305, 14344, 3121, 14037, 2800, 13753,
  2467, 15360, 0, 15360, 1, 15359, 21, 15355, 89, 15346, 253, 15325, 479, 15287, 796, 15225, 1148,
  15133, 1492, 15008, 1749, 14856, 1882, 14685, 1886, 14506, 1783, 14324, 1608, 13996, 1398, 13702,
  1183,
]);
let Qe = null;
function Gg() {
  return (
    Qe === null &&
      ((Qe = new kh(Vg, 16, 16, Ei, Sn)),
      (Qe.name = 'DFG_LUT'),
      (Qe.minFilter = Ae),
      (Qe.magFilter = Ae),
      (Qe.wrapS = xn),
      (Qe.wrapT = xn),
      (Qe.generateMipmaps = !1),
      (Qe.needsUpdate = !0)),
    Qe
  );
}
class j0 {
  constructor(t = {}) {
    const {
      canvas: e = sh(),
      context: n = null,
      depth: s = !0,
      stencil: r = !1,
      alpha: a = !1,
      antialias: o = !1,
      premultipliedAlpha: l = !0,
      preserveDrawingBuffer: c = !1,
      powerPreference: h = 'default',
      failIfMajorPerformanceCaveat: f = !1,
      reversedDepthBuffer: u = !1,
      outputBufferType: p = Oe,
    } = t;
    this.isWebGLRenderer = !0;
    let g;
    if (n !== null) {
      if (typeof WebGLRenderingContext < 'u' && n instanceof WebGLRenderingContext)
        throw new Error('THREE.WebGLRenderer: WebGL 1 is not supported since r163.');
      g = n.getContextAttributes().alpha;
    } else g = a;
    const M = p,
      m = new Set([Wa, ka, Ha]),
      d = new Set([Oe, an, Wi, Xi, Va, Ga]),
      E = new Uint32Array(4),
      y = new Int32Array(4);
    let S = null,
      R = null;
    const w = [],
      P = [];
    let x = null;
    ((this.domElement = e),
      (this.debug = { checkShaderErrors: !0, onShaderError: null }),
      (this.autoClear = !0),
      (this.autoClearColor = !0),
      (this.autoClearDepth = !0),
      (this.autoClearStencil = !0),
      (this.sortObjects = !0),
      (this.clippingPlanes = []),
      (this.localClippingEnabled = !1),
      (this.toneMapping = nn),
      (this.toneMappingExposure = 1),
      (this.transmissionResolutionScale = 1));
    const b = this;
    let H = !1;
    this._outputColorSpace = Ve;
    let C = 0,
      N = 0,
      z = null,
      k = -1,
      F = null;
    const O = new ue(),
      B = new ue();
    let nt = null;
    const j = new zt(0);
    let mt = 0,
      _t = e.width,
      gt = e.height,
      Ot = 1,
      jt = null,
      ne = null;
    const Z = new ue(0, 0, _t, gt),
      rt = new ue(0, 0, _t, gt);
    let at = !1;
    const It = new Ks();
    let Lt = !1,
      Vt = !1;
    const ie = new oe(),
      Ht = new L(),
      $ = new ue(),
      tt = { background: null, fog: null, environment: null, overrideMaterial: null, isScene: !0 };
    let K = !1;
    function ut() {
      return z === null ? Ot : 1;
    }
    let A = n;
    function Dt(v, U) {
      return e.getContext(v, U);
    }
    try {
      const v = {
        alpha: !0,
        depth: s,
        stencil: r,
        antialias: o,
        premultipliedAlpha: l,
        preserveDrawingBuffer: c,
        powerPreference: h,
        failIfMajorPerformanceCaveat: f,
      };
      if (
        ('setAttribute' in e && e.setAttribute('data-engine', `three.js r${Ba}`),
        e.addEventListener('webglcontextlost', bt, !1),
        e.addEventListener('webglcontextrestored', Gt, !1),
        e.addEventListener('webglcontextcreationerror', le, !1),
        A === null)
      ) {
        const U = 'webgl2';
        if (((A = Dt(U, v)), A === null))
          throw Dt(U)
            ? new Error('Error creating WebGL context with your selected attributes.')
            : new Error('Error creating WebGL context.');
      }
    } catch (v) {
      throw (Jt('WebGLRenderer: ' + v.message), v);
    }
    let xt, Ut, ot, T, _, I, X, J, q, yt, lt, Ct, Nt, Q, it, Et, Tt, vt, Yt, D, ht, st, St;
    function et() {
      ((xt = new Hp(A)),
        xt.init(),
        (ht = new Dg(A, xt)),
        (Ut = new Up(A, xt, t, ht)),
        (ot = new Pg(A, xt)),
        Ut.reversedDepthBuffer && u && ot.buffers.depth.setReversed(!0),
        (T = new Xp(A)),
        (_ = new gg()),
        (I = new Lg(A, xt, ot, _, Ut, ht, T)),
        (X = new Gp(b)),
        (J = new Ju(A)),
        (st = new Dp(A, J)),
        (q = new kp(A, J, T, st)),
        (yt = new Yp(A, q, J, st, T)),
        (vt = new qp(A, Ut, I)),
        (it = new Np(_)),
        (lt = new mg(b, X, xt, Ut, st, it)),
        (Ct = new Bg(b, _)),
        (Nt = new xg()),
        (Q = new bg(xt)),
        (Tt = new Lp(b, X, ot, yt, g, l)),
        (Et = new Cg(b, yt, Ut)),
        (St = new zg(A, T, Ut, ot)),
        (Yt = new Ip(A, xt, T)),
        (D = new Wp(A, xt, T)),
        (T.programs = lt.programs),
        (b.capabilities = Ut),
        (b.extensions = xt),
        (b.properties = _),
        (b.renderLists = Nt),
        (b.shadowMap = Et),
        (b.state = ot),
        (b.info = T));
    }
    (et(), M !== Oe && (x = new Jp(M, e.width, e.height, s, r)));
    const Y = new Fg(b, A);
    ((this.xr = Y),
      (this.getContext = function () {
        return A;
      }),
      (this.getContextAttributes = function () {
        return A.getContextAttributes();
      }),
      (this.forceContextLoss = function () {
        const v = xt.get('WEBGL_lose_context');
        v && v.loseContext();
      }),
      (this.forceContextRestore = function () {
        const v = xt.get('WEBGL_lose_context');
        v && v.restoreContext();
      }),
      (this.getPixelRatio = function () {
        return Ot;
      }),
      (this.setPixelRatio = function (v) {
        v !== void 0 && ((Ot = v), this.setSize(_t, gt, !1));
      }),
      (this.getSize = function (v) {
        return v.set(_t, gt);
      }),
      (this.setSize = function (v, U, W = !0) {
        if (Y.isPresenting) {
          Ft("WebGLRenderer: Can't change size while VR device is presenting.");
          return;
        }
        ((_t = v),
          (gt = U),
          (e.width = Math.floor(v * Ot)),
          (e.height = Math.floor(U * Ot)),
          W === !0 && ((e.style.width = v + 'px'), (e.style.height = U + 'px')),
          x !== null && x.setSize(e.width, e.height),
          this.setViewport(0, 0, v, U));
      }),
      (this.getDrawingBufferSize = function (v) {
        return v.set(_t * Ot, gt * Ot).floor();
      }),
      (this.setDrawingBufferSize = function (v, U, W) {
        ((_t = v),
          (gt = U),
          (Ot = W),
          (e.width = Math.floor(v * W)),
          (e.height = Math.floor(U * W)),
          this.setViewport(0, 0, v, U));
      }),
      (this.setEffects = function (v) {
        if (M === Oe) {
          console.error(
            'THREE.WebGLRenderer: setEffects() requires outputBufferType set to HalfFloatType or FloatType.'
          );
          return;
        }
        if (v) {
          for (let U = 0; U < v.length; U++)
            if (v[U].isOutputPass === !0) {
              console.warn(
                'THREE.WebGLRenderer: OutputPass is not needed in setEffects(). Tone mapping and color space conversion are applied automatically.'
              );
              break;
            }
        }
        x.setEffects(v || []);
      }),
      (this.getCurrentViewport = function (v) {
        return v.copy(O);
      }),
      (this.getViewport = function (v) {
        return v.copy(Z);
      }),
      (this.setViewport = function (v, U, W, G) {
        (v.isVector4 ? Z.set(v.x, v.y, v.z, v.w) : Z.set(v, U, W, G),
          ot.viewport(O.copy(Z).multiplyScalar(Ot).round()));
      }),
      (this.getScissor = function (v) {
        return v.copy(rt);
      }),
      (this.setScissor = function (v, U, W, G) {
        (v.isVector4 ? rt.set(v.x, v.y, v.z, v.w) : rt.set(v, U, W, G),
          ot.scissor(B.copy(rt).multiplyScalar(Ot).round()));
      }),
      (this.getScissorTest = function () {
        return at;
      }),
      (this.setScissorTest = function (v) {
        ot.setScissorTest((at = v));
      }),
      (this.setOpaqueSort = function (v) {
        jt = v;
      }),
      (this.setTransparentSort = function (v) {
        ne = v;
      }),
      (this.getClearColor = function (v) {
        return v.copy(Tt.getClearColor());
      }),
      (this.setClearColor = function () {
        Tt.setClearColor(...arguments);
      }),
      (this.getClearAlpha = function () {
        return Tt.getClearAlpha();
      }),
      (this.setClearAlpha = function () {
        Tt.setClearAlpha(...arguments);
      }),
      (this.clear = function (v = !0, U = !0, W = !0) {
        let G = 0;
        if (v) {
          let V = !1;
          if (z !== null) {
            const dt = z.texture.format;
            V = m.has(dt);
          }
          if (V) {
            const dt = z.texture.type,
              Mt = d.has(dt),
              pt = Tt.getClearColor(),
              At = Tt.getClearAlpha(),
              Rt = pt.r,
              kt = pt.g,
              Zt = pt.b;
            Mt
              ? ((E[0] = Rt),
                (E[1] = kt),
                (E[2] = Zt),
                (E[3] = At),
                A.clearBufferuiv(A.COLOR, 0, E))
              : ((y[0] = Rt),
                (y[1] = kt),
                (y[2] = Zt),
                (y[3] = At),
                A.clearBufferiv(A.COLOR, 0, y));
          } else G |= A.COLOR_BUFFER_BIT;
        }
        (U && (G |= A.DEPTH_BUFFER_BIT),
          W && ((G |= A.STENCIL_BUFFER_BIT), this.state.buffers.stencil.setMask(4294967295)),
          G !== 0 && A.clear(G));
      }),
      (this.clearColor = function () {
        this.clear(!0, !1, !1);
      }),
      (this.clearDepth = function () {
        this.clear(!1, !0, !1);
      }),
      (this.clearStencil = function () {
        this.clear(!1, !1, !0);
      }),
      (this.dispose = function () {
        (e.removeEventListener('webglcontextlost', bt, !1),
          e.removeEventListener('webglcontextrestored', Gt, !1),
          e.removeEventListener('webglcontextcreationerror', le, !1),
          Tt.dispose(),
          Nt.dispose(),
          Q.dispose(),
          _.dispose(),
          X.dispose(),
          yt.dispose(),
          st.dispose(),
          St.dispose(),
          lt.dispose(),
          Y.dispose(),
          Y.removeEventListener('sessionstart', no),
          Y.removeEventListener('sessionend', io),
          Nn.stop());
      }));
    function bt(v) {
      (v.preventDefault(), ks('WebGLRenderer: Context Lost.'), (H = !0));
    }
    function Gt() {
      (ks('WebGLRenderer: Context Restored.'), (H = !1));
      const v = T.autoReset,
        U = Et.enabled,
        W = Et.autoUpdate,
        G = Et.needsUpdate,
        V = Et.type;
      (et(),
        (T.autoReset = v),
        (Et.enabled = U),
        (Et.autoUpdate = W),
        (Et.needsUpdate = G),
        (Et.type = V));
    }
    function le(v) {
      Jt('WebGLRenderer: A WebGL context could not be created. Reason: ', v.statusMessage);
    }
    function Qt(v) {
      const U = v.target;
      (U.removeEventListener('dispose', Qt), cn(U));
    }
    function cn(v) {
      (hn(v), _.remove(v));
    }
    function hn(v) {
      const U = _.get(v).programs;
      U !== void 0 &&
        (U.forEach(function (W) {
          lt.releaseProgram(W);
        }),
        v.isShaderMaterial && lt.releaseShaderCache(v));
    }
    this.renderBufferDirect = function (v, U, W, G, V, dt) {
      U === null && (U = tt);
      const Mt = V.isMesh && V.matrixWorld.determinant() < 0,
        pt = vc(v, U, W, G, V);
      ot.setMaterial(G, Mt);
      let At = W.index,
        Rt = 1;
      if (G.wireframe === !0) {
        if (((At = q.getWireframeAttribute(W)), At === void 0)) return;
        Rt = 2;
      }
      const kt = W.drawRange,
        Zt = W.attributes.position;
      let Pt = kt.start * Rt,
        se = (kt.start + kt.count) * Rt;
      (dt !== null &&
        ((Pt = Math.max(Pt, dt.start * Rt)), (se = Math.min(se, (dt.start + dt.count) * Rt))),
        At !== null
          ? ((Pt = Math.max(Pt, 0)), (se = Math.min(se, At.count)))
          : Zt != null && ((Pt = Math.max(Pt, 0)), (se = Math.min(se, Zt.count))));
      const fe = se - Pt;
      if (fe < 0 || fe === 1 / 0) return;
      st.setup(V, G, pt, W, At);
      let he,
        re = Yt;
      if ((At !== null && ((he = J.get(At)), (re = D), re.setIndex(he)), V.isMesh))
        G.wireframe === !0
          ? (ot.setLineWidth(G.wireframeLinewidth * ut()), re.setMode(A.LINES))
          : re.setMode(A.TRIANGLES);
      else if (V.isLine) {
        let Ee = G.linewidth;
        (Ee === void 0 && (Ee = 1),
          ot.setLineWidth(Ee * ut()),
          V.isLineSegments
            ? re.setMode(A.LINES)
            : V.isLineLoop
              ? re.setMode(A.LINE_LOOP)
              : re.setMode(A.LINE_STRIP));
      } else V.isPoints ? re.setMode(A.POINTS) : V.isSprite && re.setMode(A.TRIANGLES);
      if (V.isBatchedMesh)
        if (V._multiDrawInstances !== null)
          (Ws(
            'WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection.'
          ),
            re.renderMultiDrawInstances(
              V._multiDrawStarts,
              V._multiDrawCounts,
              V._multiDrawCount,
              V._multiDrawInstances
            ));
        else if (xt.get('WEBGL_multi_draw'))
          re.renderMultiDraw(V._multiDrawStarts, V._multiDrawCounts, V._multiDrawCount);
        else {
          const Ee = V._multiDrawStarts,
            wt = V._multiDrawCounts,
            De = V._multiDrawCount,
            Kt = At ? J.get(At).bytesPerElement : 1,
            He = _.get(G).currentProgram.getUniforms();
          for (let Je = 0; Je < De; Je++)
            (He.setValue(A, '_gl_DrawID', Je), re.render(Ee[Je] / Kt, wt[Je]));
        }
      else if (V.isInstancedMesh) re.renderInstances(Pt, fe, V.count);
      else if (W.isInstancedBufferGeometry) {
        const Ee = W._maxInstanceCount !== void 0 ? W._maxInstanceCount : 1 / 0,
          wt = Math.min(W.instanceCount, Ee);
        re.renderInstances(Pt, fe, wt);
      } else re.render(Pt, fe);
    };
    function eo(v, U, W) {
      v.transparent === !0 && v.side === gn && v.forceSinglePass === !1
        ? ((v.side = Pe),
          (v.needsUpdate = !0),
          ns(v, U, W),
          (v.side = Un),
          (v.needsUpdate = !0),
          ns(v, U, W),
          (v.side = gn))
        : ns(v, U, W);
    }
    ((this.compile = function (v, U, W = null) {
      (W === null && (W = v),
        (R = Q.get(W)),
        R.init(U),
        P.push(R),
        W.traverseVisible(function (V) {
          V.isLight && V.layers.test(U.layers) && (R.pushLight(V), V.castShadow && R.pushShadow(V));
        }),
        v !== W &&
          v.traverseVisible(function (V) {
            V.isLight &&
              V.layers.test(U.layers) &&
              (R.pushLight(V), V.castShadow && R.pushShadow(V));
          }),
        R.setupLights());
      const G = new Set();
      return (
        v.traverse(function (V) {
          if (!(V.isMesh || V.isPoints || V.isLine || V.isSprite)) return;
          const dt = V.material;
          if (dt)
            if (Array.isArray(dt))
              for (let Mt = 0; Mt < dt.length; Mt++) {
                const pt = dt[Mt];
                (eo(pt, W, V), G.add(pt));
              }
            else (eo(dt, W, V), G.add(dt));
        }),
        (R = P.pop()),
        G
      );
    }),
      (this.compileAsync = function (v, U, W = null) {
        const G = this.compile(v, U, W);
        return new Promise((V) => {
          function dt() {
            if (
              (G.forEach(function (Mt) {
                _.get(Mt).currentProgram.isReady() && G.delete(Mt);
              }),
              G.size === 0)
            ) {
              V(v);
              return;
            }
            setTimeout(dt, 10);
          }
          xt.get('KHR_parallel_shader_compile') !== null ? dt() : setTimeout(dt, 10);
        });
      }));
    let er = null;
    function xc(v) {
      er && er(v);
    }
    function no() {
      Nn.stop();
    }
    function io() {
      Nn.start();
    }
    const Nn = new fc();
    (Nn.setAnimationLoop(xc),
      typeof self < 'u' && Nn.setContext(self),
      (this.setAnimationLoop = function (v) {
        ((er = v), Y.setAnimationLoop(v), v === null ? Nn.stop() : Nn.start());
      }),
      Y.addEventListener('sessionstart', no),
      Y.addEventListener('sessionend', io),
      (this.render = function (v, U) {
        if (U !== void 0 && U.isCamera !== !0) {
          Jt('WebGLRenderer.render: camera is not an instance of THREE.Camera.');
          return;
        }
        if (H === !0) return;
        const W = Y.enabled === !0 && Y.isPresenting === !0,
          G = x !== null && (z === null || W) && x.begin(b, z);
        if (
          (v.matrixWorldAutoUpdate === !0 && v.updateMatrixWorld(),
          U.parent === null && U.matrixWorldAutoUpdate === !0 && U.updateMatrixWorld(),
          Y.enabled === !0 &&
            Y.isPresenting === !0 &&
            (x === null || x.isCompositing() === !1) &&
            (Y.cameraAutoUpdate === !0 && Y.updateCamera(U), (U = Y.getCamera())),
          v.isScene === !0 && v.onBeforeRender(b, v, U, z),
          (R = Q.get(v, P.length)),
          R.init(U),
          P.push(R),
          ie.multiplyMatrices(U.projectionMatrix, U.matrixWorldInverse),
          It.setFromProjectionMatrix(ie, Ze, U.reversedDepth),
          (Vt = this.localClippingEnabled),
          (Lt = it.init(this.clippingPlanes, Vt)),
          (S = Nt.get(v, w.length)),
          S.init(),
          w.push(S),
          Y.enabled === !0 && Y.isPresenting === !0)
        ) {
          const Mt = b.xr.getDepthSensingMesh();
          Mt !== null && nr(Mt, U, -1 / 0, b.sortObjects);
        }
        (nr(v, U, 0, b.sortObjects),
          S.finish(),
          b.sortObjects === !0 && S.sort(jt, ne),
          (K = Y.enabled === !1 || Y.isPresenting === !1 || Y.hasDepthSensing() === !1),
          K && Tt.addToRenderList(S, v),
          this.info.render.frame++,
          Lt === !0 && it.beginShadows());
        const V = R.state.shadowsArray;
        if (
          (Et.render(V, v, U),
          Lt === !0 && it.endShadows(),
          this.info.autoReset === !0 && this.info.reset(),
          (G && x.hasRenderPass()) === !1)
        ) {
          const Mt = S.opaque,
            pt = S.transmissive;
          if ((R.setupLights(), U.isArrayCamera)) {
            const At = U.cameras;
            if (pt.length > 0)
              for (let Rt = 0, kt = At.length; Rt < kt; Rt++) {
                const Zt = At[Rt];
                ro(Mt, pt, v, Zt);
              }
            K && Tt.render(v);
            for (let Rt = 0, kt = At.length; Rt < kt; Rt++) {
              const Zt = At[Rt];
              so(S, v, Zt, Zt.viewport);
            }
          } else (pt.length > 0 && ro(Mt, pt, v, U), K && Tt.render(v), so(S, v, U));
        }
        (z !== null &&
          N === 0 &&
          (I.updateMultisampleRenderTarget(z), I.updateRenderTargetMipmap(z)),
          G && x.end(b),
          v.isScene === !0 && v.onAfterRender(b, v, U),
          st.resetDefaultState(),
          (k = -1),
          (F = null),
          P.pop(),
          P.length > 0
            ? ((R = P[P.length - 1]),
              Lt === !0 && it.setGlobalState(b.clippingPlanes, R.state.camera))
            : (R = null),
          w.pop(),
          w.length > 0 ? (S = w[w.length - 1]) : (S = null));
      }));
    function nr(v, U, W, G) {
      if (v.visible === !1) return;
      if (v.layers.test(U.layers)) {
        if (v.isGroup) W = v.renderOrder;
        else if (v.isLOD) v.autoUpdate === !0 && v.update(U);
        else if (v.isLight) (R.pushLight(v), v.castShadow && R.pushShadow(v));
        else if (v.isSprite) {
          if (!v.frustumCulled || It.intersectsSprite(v)) {
            G && $.setFromMatrixPosition(v.matrixWorld).applyMatrix4(ie);
            const Mt = yt.update(v),
              pt = v.material;
            pt.visible && S.push(v, Mt, pt, W, $.z, null);
          }
        } else if (
          (v.isMesh || v.isLine || v.isPoints) &&
          (!v.frustumCulled || It.intersectsObject(v))
        ) {
          const Mt = yt.update(v),
            pt = v.material;
          if (
            (G &&
              (v.boundingSphere !== void 0
                ? (v.boundingSphere === null && v.computeBoundingSphere(),
                  $.copy(v.boundingSphere.center))
                : (Mt.boundingSphere === null && Mt.computeBoundingSphere(),
                  $.copy(Mt.boundingSphere.center)),
              $.applyMatrix4(v.matrixWorld).applyMatrix4(ie)),
            Array.isArray(pt))
          ) {
            const At = Mt.groups;
            for (let Rt = 0, kt = At.length; Rt < kt; Rt++) {
              const Zt = At[Rt],
                Pt = pt[Zt.materialIndex];
              Pt && Pt.visible && S.push(v, Mt, Pt, W, $.z, Zt);
            }
          } else pt.visible && S.push(v, Mt, pt, W, $.z, null);
        }
      }
      const dt = v.children;
      for (let Mt = 0, pt = dt.length; Mt < pt; Mt++) nr(dt[Mt], U, W, G);
    }
    function so(v, U, W, G) {
      const { opaque: V, transmissive: dt, transparent: Mt } = v;
      (R.setupLightsView(W),
        Lt === !0 && it.setGlobalState(b.clippingPlanes, W),
        G && ot.viewport(O.copy(G)),
        V.length > 0 && es(V, U, W),
        dt.length > 0 && es(dt, U, W),
        Mt.length > 0 && es(Mt, U, W),
        ot.buffers.depth.setTest(!0),
        ot.buffers.depth.setMask(!0),
        ot.buffers.color.setMask(!0),
        ot.setPolygonOffset(!1));
    }
    function ro(v, U, W, G) {
      if ((W.isScene === !0 ? W.overrideMaterial : null) !== null) return;
      if (R.state.transmissionRenderTarget[G.id] === void 0) {
        const Pt = xt.has('EXT_color_buffer_half_float') || xt.has('EXT_color_buffer_float');
        R.state.transmissionRenderTarget[G.id] = new rn(1, 1, {
          generateMipmaps: !0,
          type: Pt ? Sn : Oe,
          minFilter: qn,
          samples: Math.max(4, Ut.samples),
          stencilBuffer: r,
          resolveDepthBuffer: !1,
          resolveStencilBuffer: !1,
          colorSpace: $t.workingColorSpace,
        });
      }
      const dt = R.state.transmissionRenderTarget[G.id],
        Mt = G.viewport || O;
      dt.setSize(Mt.z * b.transmissionResolutionScale, Mt.w * b.transmissionResolutionScale);
      const pt = b.getRenderTarget(),
        At = b.getActiveCubeFace(),
        Rt = b.getActiveMipmapLevel();
      (b.setRenderTarget(dt),
        b.getClearColor(j),
        (mt = b.getClearAlpha()),
        mt < 1 && b.setClearColor(16777215, 0.5),
        b.clear(),
        K && Tt.render(W));
      const kt = b.toneMapping;
      b.toneMapping = nn;
      const Zt = G.viewport;
      if (
        (G.viewport !== void 0 && (G.viewport = void 0),
        R.setupLightsView(G),
        Lt === !0 && it.setGlobalState(b.clippingPlanes, G),
        es(v, W, G),
        I.updateMultisampleRenderTarget(dt),
        I.updateRenderTargetMipmap(dt),
        xt.has('WEBGL_multisampled_render_to_texture') === !1)
      ) {
        let Pt = !1;
        for (let se = 0, fe = U.length; se < fe; se++) {
          const he = U[se],
            { object: re, geometry: Ee, material: wt, group: De } = he;
          if (wt.side === gn && re.layers.test(G.layers)) {
            const Kt = wt.side;
            ((wt.side = Pe),
              (wt.needsUpdate = !0),
              ao(re, W, G, Ee, wt, De),
              (wt.side = Kt),
              (wt.needsUpdate = !0),
              (Pt = !0));
          }
        }
        Pt === !0 && (I.updateMultisampleRenderTarget(dt), I.updateRenderTargetMipmap(dt));
      }
      (b.setRenderTarget(pt, At, Rt),
        b.setClearColor(j, mt),
        Zt !== void 0 && (G.viewport = Zt),
        (b.toneMapping = kt));
    }
    function es(v, U, W) {
      const G = U.isScene === !0 ? U.overrideMaterial : null;
      for (let V = 0, dt = v.length; V < dt; V++) {
        const Mt = v[V],
          { object: pt, geometry: At, group: Rt } = Mt;
        let kt = Mt.material;
        (kt.allowOverride === !0 && G !== null && (kt = G),
          pt.layers.test(W.layers) && ao(pt, U, W, At, kt, Rt));
      }
    }
    function ao(v, U, W, G, V, dt) {
      (v.onBeforeRender(b, U, W, G, V, dt),
        v.modelViewMatrix.multiplyMatrices(W.matrixWorldInverse, v.matrixWorld),
        v.normalMatrix.getNormalMatrix(v.modelViewMatrix),
        V.onBeforeRender(b, U, W, G, v, dt),
        V.transparent === !0 && V.side === gn && V.forceSinglePass === !1
          ? ((V.side = Pe),
            (V.needsUpdate = !0),
            b.renderBufferDirect(W, U, G, V, v, dt),
            (V.side = Un),
            (V.needsUpdate = !0),
            b.renderBufferDirect(W, U, G, V, v, dt),
            (V.side = gn))
          : b.renderBufferDirect(W, U, G, V, v, dt),
        v.onAfterRender(b, U, W, G, V, dt));
    }
    function ns(v, U, W) {
      U.isScene !== !0 && (U = tt);
      const G = _.get(v),
        V = R.state.lights,
        dt = R.state.shadowsArray,
        Mt = V.state.version,
        pt = lt.getParameters(v, V.state, dt, U, W),
        At = lt.getProgramCacheKey(pt);
      let Rt = G.programs;
      ((G.environment =
        v.isMeshStandardMaterial || v.isMeshLambertMaterial || v.isMeshPhongMaterial
          ? U.environment
          : null),
        (G.fog = U.fog));
      const kt =
        v.isMeshStandardMaterial ||
        (v.isMeshLambertMaterial && !v.envMap) ||
        (v.isMeshPhongMaterial && !v.envMap);
      ((G.envMap = X.get(v.envMap || G.environment, kt)),
        (G.envMapRotation =
          G.environment !== null && v.envMap === null ? U.environmentRotation : v.envMapRotation),
        Rt === void 0 && (v.addEventListener('dispose', Qt), (Rt = new Map()), (G.programs = Rt)));
      let Zt = Rt.get(At);
      if (Zt !== void 0) {
        if (G.currentProgram === Zt && G.lightsStateVersion === Mt) return (lo(v, pt), Zt);
      } else
        ((pt.uniforms = lt.getUniforms(v)),
          v.onBeforeCompile(pt, b),
          (Zt = lt.acquireProgram(pt, At)),
          Rt.set(At, Zt),
          (G.uniforms = pt.uniforms));
      const Pt = G.uniforms;
      return (
        ((!v.isShaderMaterial && !v.isRawShaderMaterial) || v.clipping === !0) &&
          (Pt.clippingPlanes = it.uniform),
        lo(v, pt),
        (G.needsLights = Sc(v)),
        (G.lightsStateVersion = Mt),
        G.needsLights &&
          ((Pt.ambientLightColor.value = V.state.ambient),
          (Pt.lightProbe.value = V.state.probe),
          (Pt.directionalLights.value = V.state.directional),
          (Pt.directionalLightShadows.value = V.state.directionalShadow),
          (Pt.spotLights.value = V.state.spot),
          (Pt.spotLightShadows.value = V.state.spotShadow),
          (Pt.rectAreaLights.value = V.state.rectArea),
          (Pt.ltc_1.value = V.state.rectAreaLTC1),
          (Pt.ltc_2.value = V.state.rectAreaLTC2),
          (Pt.pointLights.value = V.state.point),
          (Pt.pointLightShadows.value = V.state.pointShadow),
          (Pt.hemisphereLights.value = V.state.hemi),
          (Pt.directionalShadowMatrix.value = V.state.directionalShadowMatrix),
          (Pt.spotLightMatrix.value = V.state.spotLightMatrix),
          (Pt.spotLightMap.value = V.state.spotLightMap),
          (Pt.pointShadowMatrix.value = V.state.pointShadowMatrix)),
        (G.currentProgram = Zt),
        (G.uniformsList = null),
        Zt
      );
    }
    function oo(v) {
      if (v.uniformsList === null) {
        const U = v.currentProgram.getUniforms();
        v.uniformsList = Gs.seqWithValue(U.seq, v.uniforms);
      }
      return v.uniformsList;
    }
    function lo(v, U) {
      const W = _.get(v);
      ((W.outputColorSpace = U.outputColorSpace),
        (W.batching = U.batching),
        (W.batchingColor = U.batchingColor),
        (W.instancing = U.instancing),
        (W.instancingColor = U.instancingColor),
        (W.instancingMorph = U.instancingMorph),
        (W.skinning = U.skinning),
        (W.morphTargets = U.morphTargets),
        (W.morphNormals = U.morphNormals),
        (W.morphColors = U.morphColors),
        (W.morphTargetsCount = U.morphTargetsCount),
        (W.numClippingPlanes = U.numClippingPlanes),
        (W.numIntersection = U.numClipIntersection),
        (W.vertexAlphas = U.vertexAlphas),
        (W.vertexTangents = U.vertexTangents),
        (W.toneMapping = U.toneMapping));
    }
    function vc(v, U, W, G, V) {
      (U.isScene !== !0 && (U = tt), I.resetTextureUnits());
      const dt = U.fog,
        Mt =
          G.isMeshStandardMaterial || G.isMeshLambertMaterial || G.isMeshPhongMaterial
            ? U.environment
            : null,
        pt =
          z === null ? b.outputColorSpace : z.isXRRenderTarget === !0 ? z.texture.colorSpace : bi,
        At =
          G.isMeshStandardMaterial ||
          (G.isMeshLambertMaterial && !G.envMap) ||
          (G.isMeshPhongMaterial && !G.envMap),
        Rt = X.get(G.envMap || Mt, At),
        kt = G.vertexColors === !0 && !!W.attributes.color && W.attributes.color.itemSize === 4,
        Zt = !!W.attributes.tangent && (!!G.normalMap || G.anisotropy > 0),
        Pt = !!W.morphAttributes.position,
        se = !!W.morphAttributes.normal,
        fe = !!W.morphAttributes.color;
      let he = nn;
      G.toneMapped && (z === null || z.isXRRenderTarget === !0) && (he = b.toneMapping);
      const re = W.morphAttributes.position || W.morphAttributes.normal || W.morphAttributes.color,
        Ee = re !== void 0 ? re.length : 0,
        wt = _.get(G),
        De = R.state.lights;
      if (Lt === !0 && (Vt === !0 || v !== F)) {
        const ve = v === F && G.id === k;
        it.setState(G, v, ve);
      }
      let Kt = !1;
      G.version === wt.__version
        ? ((wt.needsLights && wt.lightsStateVersion !== De.state.version) ||
            wt.outputColorSpace !== pt ||
            (V.isBatchedMesh && wt.batching === !1) ||
            (!V.isBatchedMesh && wt.batching === !0) ||
            (V.isBatchedMesh && wt.batchingColor === !0 && V.colorTexture === null) ||
            (V.isBatchedMesh && wt.batchingColor === !1 && V.colorTexture !== null) ||
            (V.isInstancedMesh && wt.instancing === !1) ||
            (!V.isInstancedMesh && wt.instancing === !0) ||
            (V.isSkinnedMesh && wt.skinning === !1) ||
            (!V.isSkinnedMesh && wt.skinning === !0) ||
            (V.isInstancedMesh && wt.instancingColor === !0 && V.instanceColor === null) ||
            (V.isInstancedMesh && wt.instancingColor === !1 && V.instanceColor !== null) ||
            (V.isInstancedMesh && wt.instancingMorph === !0 && V.morphTexture === null) ||
            (V.isInstancedMesh && wt.instancingMorph === !1 && V.morphTexture !== null) ||
            wt.envMap !== Rt ||
            (G.fog === !0 && wt.fog !== dt) ||
            (wt.numClippingPlanes !== void 0 &&
              (wt.numClippingPlanes !== it.numPlanes ||
                wt.numIntersection !== it.numIntersection)) ||
            wt.vertexAlphas !== kt ||
            wt.vertexTangents !== Zt ||
            wt.morphTargets !== Pt ||
            wt.morphNormals !== se ||
            wt.morphColors !== fe ||
            wt.toneMapping !== he ||
            wt.morphTargetsCount !== Ee) &&
          (Kt = !0)
        : ((Kt = !0), (wt.__version = G.version));
      let He = wt.currentProgram;
      Kt === !0 && (He = ns(G, U, V));
      let Je = !1,
        Fn = !1,
        ti = !1;
      const ae = He.getUniforms(),
        Se = wt.uniforms;
      if (
        (ot.useProgram(He.program) && ((Je = !0), (Fn = !0), (ti = !0)),
        G.id !== k && ((k = G.id), (Fn = !0)),
        Je || F !== v)
      ) {
        (ot.buffers.depth.getReversed() &&
          v.reversedDepth !== !0 &&
          ((v._reversedDepth = !0), v.updateProjectionMatrix()),
          ae.setValue(A, 'projectionMatrix', v.projectionMatrix),
          ae.setValue(A, 'viewMatrix', v.matrixWorldInverse));
        const Tn = ae.map.cameraPosition;
        (Tn !== void 0 && Tn.setValue(A, Ht.setFromMatrixPosition(v.matrixWorld)),
          Ut.logarithmicDepthBuffer &&
            ae.setValue(A, 'logDepthBufFC', 2 / (Math.log(v.far + 1) / Math.LN2)),
          (G.isMeshPhongMaterial ||
            G.isMeshToonMaterial ||
            G.isMeshLambertMaterial ||
            G.isMeshBasicMaterial ||
            G.isMeshStandardMaterial ||
            G.isShaderMaterial) &&
            ae.setValue(A, 'isOrthographic', v.isOrthographicCamera === !0),
          F !== v && ((F = v), (Fn = !0), (ti = !0)));
      }
      if (
        (wt.needsLights &&
          (De.state.directionalShadowMap.length > 0 &&
            ae.setValue(A, 'directionalShadowMap', De.state.directionalShadowMap, I),
          De.state.spotShadowMap.length > 0 &&
            ae.setValue(A, 'spotShadowMap', De.state.spotShadowMap, I),
          De.state.pointShadowMap.length > 0 &&
            ae.setValue(A, 'pointShadowMap', De.state.pointShadowMap, I)),
        V.isSkinnedMesh)
      ) {
        (ae.setOptional(A, V, 'bindMatrix'), ae.setOptional(A, V, 'bindMatrixInverse'));
        const ve = V.skeleton;
        ve &&
          (ve.boneTexture === null && ve.computeBoneTexture(),
          ae.setValue(A, 'boneTexture', ve.boneTexture, I));
      }
      V.isBatchedMesh &&
        (ae.setOptional(A, V, 'batchingTexture'),
        ae.setValue(A, 'batchingTexture', V._matricesTexture, I),
        ae.setOptional(A, V, 'batchingIdTexture'),
        ae.setValue(A, 'batchingIdTexture', V._indirectTexture, I),
        ae.setOptional(A, V, 'batchingColorTexture'),
        V._colorsTexture !== null && ae.setValue(A, 'batchingColorTexture', V._colorsTexture, I));
      const bn = W.morphAttributes;
      if (
        ((bn.position !== void 0 || bn.normal !== void 0 || bn.color !== void 0) &&
          vt.update(V, W, He),
        (Fn || wt.receiveShadow !== V.receiveShadow) &&
          ((wt.receiveShadow = V.receiveShadow), ae.setValue(A, 'receiveShadow', V.receiveShadow)),
        (G.isMeshStandardMaterial || G.isMeshLambertMaterial || G.isMeshPhongMaterial) &&
          G.envMap === null &&
          U.environment !== null &&
          (Se.envMapIntensity.value = U.environmentIntensity),
        Se.dfgLUT !== void 0 && (Se.dfgLUT.value = Gg()),
        Fn &&
          (ae.setValue(A, 'toneMappingExposure', b.toneMappingExposure),
          wt.needsLights && Mc(Se, ti),
          dt && G.fog === !0 && Ct.refreshFogUniforms(Se, dt),
          Ct.refreshMaterialUniforms(Se, G, Ot, gt, R.state.transmissionRenderTarget[v.id]),
          Gs.upload(A, oo(wt), Se, I)),
        G.isShaderMaterial &&
          G.uniformsNeedUpdate === !0 &&
          (Gs.upload(A, oo(wt), Se, I), (G.uniformsNeedUpdate = !1)),
        G.isSpriteMaterial && ae.setValue(A, 'center', V.center),
        ae.setValue(A, 'modelViewMatrix', V.modelViewMatrix),
        ae.setValue(A, 'normalMatrix', V.normalMatrix),
        ae.setValue(A, 'modelMatrix', V.matrixWorld),
        G.isShaderMaterial || G.isRawShaderMaterial)
      ) {
        const ve = G.uniformsGroups;
        for (let Tn = 0, ei = ve.length; Tn < ei; Tn++) {
          const co = ve[Tn];
          (St.update(co, He), St.bind(co, He));
        }
      }
      return He;
    }
    function Mc(v, U) {
      ((v.ambientLightColor.needsUpdate = U),
        (v.lightProbe.needsUpdate = U),
        (v.directionalLights.needsUpdate = U),
        (v.directionalLightShadows.needsUpdate = U),
        (v.pointLights.needsUpdate = U),
        (v.pointLightShadows.needsUpdate = U),
        (v.spotLights.needsUpdate = U),
        (v.spotLightShadows.needsUpdate = U),
        (v.rectAreaLights.needsUpdate = U),
        (v.hemisphereLights.needsUpdate = U));
    }
    function Sc(v) {
      return (
        v.isMeshLambertMaterial ||
        v.isMeshToonMaterial ||
        v.isMeshPhongMaterial ||
        v.isMeshStandardMaterial ||
        v.isShadowMaterial ||
        (v.isShaderMaterial && v.lights === !0)
      );
    }
    ((this.getActiveCubeFace = function () {
      return C;
    }),
      (this.getActiveMipmapLevel = function () {
        return N;
      }),
      (this.getRenderTarget = function () {
        return z;
      }),
      (this.setRenderTargetTextures = function (v, U, W) {
        const G = _.get(v);
        ((G.__autoAllocateDepthBuffer = v.resolveDepthBuffer === !1),
          G.__autoAllocateDepthBuffer === !1 && (G.__useRenderToTexture = !1),
          (_.get(v.texture).__webglTexture = U),
          (_.get(v.depthTexture).__webglTexture = G.__autoAllocateDepthBuffer ? void 0 : W),
          (G.__hasExternalTextures = !0));
      }),
      (this.setRenderTargetFramebuffer = function (v, U) {
        const W = _.get(v);
        ((W.__webglFramebuffer = U), (W.__useDefaultFramebuffer = U === void 0));
      }));
    const yc = A.createFramebuffer();
    ((this.setRenderTarget = function (v, U = 0, W = 0) {
      ((z = v), (C = U), (N = W));
      let G = null,
        V = !1,
        dt = !1;
      if (v) {
        const pt = _.get(v);
        if (pt.__useDefaultFramebuffer !== void 0) {
          (ot.bindFramebuffer(A.FRAMEBUFFER, pt.__webglFramebuffer),
            O.copy(v.viewport),
            B.copy(v.scissor),
            (nt = v.scissorTest),
            ot.viewport(O),
            ot.scissor(B),
            ot.setScissorTest(nt),
            (k = -1));
          return;
        } else if (pt.__webglFramebuffer === void 0) I.setupRenderTarget(v);
        else if (pt.__hasExternalTextures)
          I.rebindTextures(
            v,
            _.get(v.texture).__webglTexture,
            _.get(v.depthTexture).__webglTexture
          );
        else if (v.depthBuffer) {
          const kt = v.depthTexture;
          if (pt.__boundDepthTexture !== kt) {
            if (
              kt !== null &&
              _.has(kt) &&
              (v.width !== kt.image.width || v.height !== kt.image.height)
            )
              throw new Error(
                'WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.'
              );
            I.setupDepthRenderbuffer(v);
          }
        }
        const At = v.texture;
        (At.isData3DTexture || At.isDataArrayTexture || At.isCompressedArrayTexture) && (dt = !0);
        const Rt = _.get(v).__webglFramebuffer;
        (v.isWebGLCubeRenderTarget
          ? (Array.isArray(Rt[U]) ? (G = Rt[U][W]) : (G = Rt[U]), (V = !0))
          : v.samples > 0 && I.useMultisampledRTT(v) === !1
            ? (G = _.get(v).__webglMultisampledFramebuffer)
            : Array.isArray(Rt)
              ? (G = Rt[W])
              : (G = Rt),
          O.copy(v.viewport),
          B.copy(v.scissor),
          (nt = v.scissorTest));
      } else
        (O.copy(Z).multiplyScalar(Ot).floor(), B.copy(rt).multiplyScalar(Ot).floor(), (nt = at));
      if (
        (W !== 0 && (G = yc),
        ot.bindFramebuffer(A.FRAMEBUFFER, G) && ot.drawBuffers(v, G),
        ot.viewport(O),
        ot.scissor(B),
        ot.setScissorTest(nt),
        V)
      ) {
        const pt = _.get(v.texture);
        A.framebufferTexture2D(
          A.FRAMEBUFFER,
          A.COLOR_ATTACHMENT0,
          A.TEXTURE_CUBE_MAP_POSITIVE_X + U,
          pt.__webglTexture,
          W
        );
      } else if (dt) {
        const pt = U;
        for (let At = 0; At < v.textures.length; At++) {
          const Rt = _.get(v.textures[At]);
          A.framebufferTextureLayer(
            A.FRAMEBUFFER,
            A.COLOR_ATTACHMENT0 + At,
            Rt.__webglTexture,
            W,
            pt
          );
        }
      } else if (v !== null && W !== 0) {
        const pt = _.get(v.texture);
        A.framebufferTexture2D(
          A.FRAMEBUFFER,
          A.COLOR_ATTACHMENT0,
          A.TEXTURE_2D,
          pt.__webglTexture,
          W
        );
      }
      k = -1;
    }),
      (this.readRenderTargetPixels = function (v, U, W, G, V, dt, Mt, pt = 0) {
        if (!(v && v.isWebGLRenderTarget)) {
          Jt('WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.');
          return;
        }
        let At = _.get(v).__webglFramebuffer;
        if ((v.isWebGLCubeRenderTarget && Mt !== void 0 && (At = At[Mt]), At)) {
          ot.bindFramebuffer(A.FRAMEBUFFER, At);
          try {
            const Rt = v.textures[pt],
              kt = Rt.format,
              Zt = Rt.type;
            if (
              (v.textures.length > 1 && A.readBuffer(A.COLOR_ATTACHMENT0 + pt),
              !Ut.textureFormatReadable(kt))
            ) {
              Jt(
                'WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.'
              );
              return;
            }
            if (!Ut.textureTypeReadable(Zt)) {
              Jt(
                'WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.'
              );
              return;
            }
            U >= 0 &&
              U <= v.width - G &&
              W >= 0 &&
              W <= v.height - V &&
              A.readPixels(U, W, G, V, ht.convert(kt), ht.convert(Zt), dt);
          } finally {
            const Rt = z !== null ? _.get(z).__webglFramebuffer : null;
            ot.bindFramebuffer(A.FRAMEBUFFER, Rt);
          }
        }
      }),
      (this.readRenderTargetPixelsAsync = async function (v, U, W, G, V, dt, Mt, pt = 0) {
        if (!(v && v.isWebGLRenderTarget))
          throw new Error(
            'THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.'
          );
        let At = _.get(v).__webglFramebuffer;
        if ((v.isWebGLCubeRenderTarget && Mt !== void 0 && (At = At[Mt]), At))
          if (U >= 0 && U <= v.width - G && W >= 0 && W <= v.height - V) {
            ot.bindFramebuffer(A.FRAMEBUFFER, At);
            const Rt = v.textures[pt],
              kt = Rt.format,
              Zt = Rt.type;
            if (
              (v.textures.length > 1 && A.readBuffer(A.COLOR_ATTACHMENT0 + pt),
              !Ut.textureFormatReadable(kt))
            )
              throw new Error(
                'THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.'
              );
            if (!Ut.textureTypeReadable(Zt))
              throw new Error(
                'THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.'
              );
            const Pt = A.createBuffer();
            (A.bindBuffer(A.PIXEL_PACK_BUFFER, Pt),
              A.bufferData(A.PIXEL_PACK_BUFFER, dt.byteLength, A.STREAM_READ),
              A.readPixels(U, W, G, V, ht.convert(kt), ht.convert(Zt), 0));
            const se = z !== null ? _.get(z).__webglFramebuffer : null;
            ot.bindFramebuffer(A.FRAMEBUFFER, se);
            const fe = A.fenceSync(A.SYNC_GPU_COMMANDS_COMPLETE, 0);
            return (
              A.flush(),
              await rh(A, fe, 4),
              A.bindBuffer(A.PIXEL_PACK_BUFFER, Pt),
              A.getBufferSubData(A.PIXEL_PACK_BUFFER, 0, dt),
              A.deleteBuffer(Pt),
              A.deleteSync(fe),
              dt
            );
          } else
            throw new Error(
              'THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.'
            );
      }),
      (this.copyFramebufferToTexture = function (v, U = null, W = 0) {
        const G = Math.pow(2, -W),
          V = Math.floor(v.image.width * G),
          dt = Math.floor(v.image.height * G),
          Mt = U !== null ? U.x : 0,
          pt = U !== null ? U.y : 0;
        (I.setTexture2D(v, 0),
          A.copyTexSubImage2D(A.TEXTURE_2D, W, 0, 0, Mt, pt, V, dt),
          ot.unbindTexture());
      }));
    const Ec = A.createFramebuffer(),
      bc = A.createFramebuffer();
    ((this.copyTextureToTexture = function (v, U, W = null, G = null, V = 0, dt = 0) {
      let Mt, pt, At, Rt, kt, Zt, Pt, se, fe;
      const he = v.isCompressedTexture ? v.mipmaps[dt] : v.image;
      if (W !== null)
        ((Mt = W.max.x - W.min.x),
          (pt = W.max.y - W.min.y),
          (At = W.isBox3 ? W.max.z - W.min.z : 1),
          (Rt = W.min.x),
          (kt = W.min.y),
          (Zt = W.isBox3 ? W.min.z : 0));
      else {
        const Se = Math.pow(2, -V);
        ((Mt = Math.floor(he.width * Se)),
          (pt = Math.floor(he.height * Se)),
          v.isDataArrayTexture
            ? (At = he.depth)
            : v.isData3DTexture
              ? (At = Math.floor(he.depth * Se))
              : (At = 1),
          (Rt = 0),
          (kt = 0),
          (Zt = 0));
      }
      G !== null ? ((Pt = G.x), (se = G.y), (fe = G.z)) : ((Pt = 0), (se = 0), (fe = 0));
      const re = ht.convert(U.format),
        Ee = ht.convert(U.type);
      let wt;
      (U.isData3DTexture
        ? (I.setTexture3D(U, 0), (wt = A.TEXTURE_3D))
        : U.isDataArrayTexture || U.isCompressedArrayTexture
          ? (I.setTexture2DArray(U, 0), (wt = A.TEXTURE_2D_ARRAY))
          : (I.setTexture2D(U, 0), (wt = A.TEXTURE_2D)),
        A.pixelStorei(A.UNPACK_FLIP_Y_WEBGL, U.flipY),
        A.pixelStorei(A.UNPACK_PREMULTIPLY_ALPHA_WEBGL, U.premultiplyAlpha),
        A.pixelStorei(A.UNPACK_ALIGNMENT, U.unpackAlignment));
      const De = A.getParameter(A.UNPACK_ROW_LENGTH),
        Kt = A.getParameter(A.UNPACK_IMAGE_HEIGHT),
        He = A.getParameter(A.UNPACK_SKIP_PIXELS),
        Je = A.getParameter(A.UNPACK_SKIP_ROWS),
        Fn = A.getParameter(A.UNPACK_SKIP_IMAGES);
      (A.pixelStorei(A.UNPACK_ROW_LENGTH, he.width),
        A.pixelStorei(A.UNPACK_IMAGE_HEIGHT, he.height),
        A.pixelStorei(A.UNPACK_SKIP_PIXELS, Rt),
        A.pixelStorei(A.UNPACK_SKIP_ROWS, kt),
        A.pixelStorei(A.UNPACK_SKIP_IMAGES, Zt));
      const ti = v.isDataArrayTexture || v.isData3DTexture,
        ae = U.isDataArrayTexture || U.isData3DTexture;
      if (v.isDepthTexture) {
        const Se = _.get(v),
          bn = _.get(U),
          ve = _.get(Se.__renderTarget),
          Tn = _.get(bn.__renderTarget);
        (ot.bindFramebuffer(A.READ_FRAMEBUFFER, ve.__webglFramebuffer),
          ot.bindFramebuffer(A.DRAW_FRAMEBUFFER, Tn.__webglFramebuffer));
        for (let ei = 0; ei < At; ei++)
          (ti &&
            (A.framebufferTextureLayer(
              A.READ_FRAMEBUFFER,
              A.COLOR_ATTACHMENT0,
              _.get(v).__webglTexture,
              V,
              Zt + ei
            ),
            A.framebufferTextureLayer(
              A.DRAW_FRAMEBUFFER,
              A.COLOR_ATTACHMENT0,
              _.get(U).__webglTexture,
              dt,
              fe + ei
            )),
            A.blitFramebuffer(Rt, kt, Mt, pt, Pt, se, Mt, pt, A.DEPTH_BUFFER_BIT, A.NEAREST));
        (ot.bindFramebuffer(A.READ_FRAMEBUFFER, null),
          ot.bindFramebuffer(A.DRAW_FRAMEBUFFER, null));
      } else if (V !== 0 || v.isRenderTargetTexture || _.has(v)) {
        const Se = _.get(v),
          bn = _.get(U);
        (ot.bindFramebuffer(A.READ_FRAMEBUFFER, Ec), ot.bindFramebuffer(A.DRAW_FRAMEBUFFER, bc));
        for (let ve = 0; ve < At; ve++)
          (ti
            ? A.framebufferTextureLayer(
                A.READ_FRAMEBUFFER,
                A.COLOR_ATTACHMENT0,
                Se.__webglTexture,
                V,
                Zt + ve
              )
            : A.framebufferTexture2D(
                A.READ_FRAMEBUFFER,
                A.COLOR_ATTACHMENT0,
                A.TEXTURE_2D,
                Se.__webglTexture,
                V
              ),
            ae
              ? A.framebufferTextureLayer(
                  A.DRAW_FRAMEBUFFER,
                  A.COLOR_ATTACHMENT0,
                  bn.__webglTexture,
                  dt,
                  fe + ve
                )
              : A.framebufferTexture2D(
                  A.DRAW_FRAMEBUFFER,
                  A.COLOR_ATTACHMENT0,
                  A.TEXTURE_2D,
                  bn.__webglTexture,
                  dt
                ),
            V !== 0
              ? A.blitFramebuffer(Rt, kt, Mt, pt, Pt, se, Mt, pt, A.COLOR_BUFFER_BIT, A.NEAREST)
              : ae
                ? A.copyTexSubImage3D(wt, dt, Pt, se, fe + ve, Rt, kt, Mt, pt)
                : A.copyTexSubImage2D(wt, dt, Pt, se, Rt, kt, Mt, pt));
        (ot.bindFramebuffer(A.READ_FRAMEBUFFER, null),
          ot.bindFramebuffer(A.DRAW_FRAMEBUFFER, null));
      } else
        ae
          ? v.isDataTexture || v.isData3DTexture
            ? A.texSubImage3D(wt, dt, Pt, se, fe, Mt, pt, At, re, Ee, he.data)
            : U.isCompressedArrayTexture
              ? A.compressedTexSubImage3D(wt, dt, Pt, se, fe, Mt, pt, At, re, he.data)
              : A.texSubImage3D(wt, dt, Pt, se, fe, Mt, pt, At, re, Ee, he)
          : v.isDataTexture
            ? A.texSubImage2D(A.TEXTURE_2D, dt, Pt, se, Mt, pt, re, Ee, he.data)
            : v.isCompressedTexture
              ? A.compressedTexSubImage2D(
                  A.TEXTURE_2D,
                  dt,
                  Pt,
                  se,
                  he.width,
                  he.height,
                  re,
                  he.data
                )
              : A.texSubImage2D(A.TEXTURE_2D, dt, Pt, se, Mt, pt, re, Ee, he);
      (A.pixelStorei(A.UNPACK_ROW_LENGTH, De),
        A.pixelStorei(A.UNPACK_IMAGE_HEIGHT, Kt),
        A.pixelStorei(A.UNPACK_SKIP_PIXELS, He),
        A.pixelStorei(A.UNPACK_SKIP_ROWS, Je),
        A.pixelStorei(A.UNPACK_SKIP_IMAGES, Fn),
        dt === 0 && U.generateMipmaps && A.generateMipmap(wt),
        ot.unbindTexture());
    }),
      (this.initRenderTarget = function (v) {
        _.get(v).__webglFramebuffer === void 0 && I.setupRenderTarget(v);
      }),
      (this.initTexture = function (v) {
        (v.isCubeTexture
          ? I.setTextureCube(v, 0)
          : v.isData3DTexture
            ? I.setTexture3D(v, 0)
            : v.isDataArrayTexture || v.isCompressedArrayTexture
              ? I.setTexture2DArray(v, 0)
              : I.setTexture2D(v, 0),
          ot.unbindTexture());
      }),
      (this.resetState = function () {
        ((C = 0), (N = 0), (z = null), ot.reset(), st.reset());
      }),
      typeof __THREE_DEVTOOLS__ < 'u' &&
        __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent('observe', { detail: this })));
  }
  get coordinateSystem() {
    return Ze;
  }
  get outputColorSpace() {
    return this._outputColorSpace;
  }
  set outputColorSpace(t) {
    this._outputColorSpace = t;
    const e = this.getContext();
    ((e.drawingBufferColorSpace = $t._getDrawingBufferColorSpace(t)),
      (e.unpackColorSpace = $t._getUnpackColorSpace()));
  }
}
export {
  wl as $,
  z0 as A,
  xe as B,
  hc as C,
  gn as D,
  G0 as E,
  Ks as F,
  as as G,
  Sn as H,
  y0 as I,
  O0 as J,
  V0 as K,
  Ae as L,
  oe as M,
  nn as N,
  de as O,
  Ns as P,
  F0 as Q,
  wh as R,
  oc as S,
  N0 as T,
  H0 as U,
  ct as V,
  Ze as W,
  yl as X,
  El as Y,
  bl as Z,
  Tl as _,
  L as a,
  Gc as a$,
  Rl as a0,
  jn as a1,
  T0 as a2,
  Zi as a3,
  to as a4,
  Le as a5,
  zt as a6,
  Fe as a7,
  Wu as a8,
  js as a9,
  xn as aA,
  $r as aB,
  qn as aC,
  rr as aD,
  is as aE,
  Zc as aF,
  me as aG,
  eh as aH,
  th as aI,
  qa as aJ,
  Qc as aK,
  Xa as aL,
  jc as aM,
  nh as aN,
  Kc as aO,
  Hs as aP,
  Dn as aQ,
  en as aR,
  jo as aS,
  Pc as aT,
  Cc as aU,
  Bc as aV,
  Vc as aW,
  Hr as aX,
  Fc as aY,
  Oc as aZ,
  zc as a_,
  Oe as aa,
  Xi as ab,
  an as ac,
  Yn as ad,
  yn as ae,
  Rc as af,
  Wn as ag,
  Ic as ah,
  Jl as ai,
  Ri as aj,
  ur as ak,
  ir as al,
  sr as am,
  Js as an,
  ql as ao,
  ye as ap,
  p0 as aq,
  te as ar,
  Xt as as,
  kn as at,
  Ba as au,
  qi as av,
  sh as aw,
  _0 as ax,
  za as ay,
  Kr as az,
  En as b,
  Ea as b$,
  Gr as b0,
  Nc as b1,
  Uc as b2,
  Tc as b3,
  ho as b4,
  Ac as b5,
  Xg as b6,
  vn as b7,
  po as b8,
  fo as b9,
  Bs as bA,
  zs as bB,
  jr as bC,
  Qr as bD,
  ta as bE,
  ea as bF,
  na as bG,
  ia as bH,
  sa as bI,
  ra as bJ,
  aa as bK,
  oa as bL,
  la as bM,
  ca as bN,
  ha as bO,
  ua as bP,
  fa as bQ,
  da as bR,
  pa as bS,
  ma as bT,
  ga as bU,
  _a as bV,
  xa as bW,
  va as bX,
  Ma as bY,
  Sa as bZ,
  ya as b_,
  uo as ba,
  vi as bb,
  Jr as bc,
  Zr as bd,
  Yr as be,
  qr as bf,
  Si as bg,
  Xr as bh,
  Wr as bi,
  kr as bj,
  Va as bk,
  Ga as bl,
  Dl as bm,
  Il as bn,
  Pl as bo,
  Ll as bp,
  Wi as bq,
  Ul as br,
  Nl as bs,
  Fl as bt,
  Ha as bu,
  Ei as bv,
  ka as bw,
  Wa as bx,
  Fs as by,
  Os as bz,
  kl as c,
  bi as c$,
  Aa as c0,
  wa as c1,
  Ra as c2,
  Ca as c3,
  kh as c4,
  C0 as c5,
  Iu as c6,
  R0 as c7,
  P0 as c8,
  L0 as c9,
  e0 as cA,
  t0 as cB,
  ni as cC,
  Dc as cD,
  Lc as cE,
  ah as cF,
  M0 as cG,
  Yg as cH,
  Yc as cI,
  qc as cJ,
  Zs as cK,
  Wg as cL,
  Jh as cM,
  jg as cN,
  ts as cO,
  ku as cP,
  wc as cQ,
  Qi as cR,
  Jn as cS,
  yi as cT,
  Kn as cU,
  Kg as cV,
  Qg as cW,
  $c as cX,
  Pa as cY,
  X0 as cZ,
  Bl as c_,
  I0 as ca,
  Xl as cb,
  U0 as cc,
  Zh as cd,
  S0 as ce,
  w0 as cf,
  Ti as cg,
  Cl as ch,
  Ge as ci,
  Gl as cj,
  Vl as ck,
  uc as cl,
  x0 as cm,
  f0 as cn,
  u0 as co,
  d0 as cp,
  c0 as cq,
  h0 as cr,
  l0 as cs,
  mo as ct,
  o0 as cu,
  r0 as cv,
  s0 as cw,
  i0 as cx,
  n0 as cy,
  a0 as cz,
  D0 as d,
  ks as d0,
  qg as d1,
  k0 as d2,
  A0 as d3,
  ji as d4,
  on as d5,
  tn as d6,
  Cu as d7,
  ft as d8,
  J0 as d9,
  rc as da,
  $0 as db,
  E0 as dc,
  Yh as dd,
  lc as de,
  ru as df,
  ln as dg,
  Zl as dh,
  b0 as di,
  qt as dj,
  K0 as dk,
  Hg as dl,
  kg as dm,
  Z0 as dn,
  $s as dp,
  rn as dq,
  W0 as dr,
  j0 as ds,
  Y0 as dt,
  q0 as du,
  ac as dv,
  Ve as e,
  ee as f,
  Be as g,
  Vh as h,
  Hl as i,
  Zg as j,
  $g as k,
  Jg as l,
  v0 as m,
  Ws as n,
  Jt as o,
  $t as p,
  Ye as q,
  ue as r,
  Wl as s,
  Pe as t,
  Un as u,
  Oi as v,
  Ft as w,
  m0 as x,
  g0 as y,
  B0 as z,
};
//# sourceMappingURL=three-BdLAxraL.js.map

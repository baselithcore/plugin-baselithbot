import {
  s as nt,
  p as tt,
  i as Un,
  a as nn,
  b as Hn,
  c as en,
  n as dn,
  d as Kn,
  m as Wn,
  e as Zn,
  f as Qn,
  g as $t,
  h as Jn,
  j as ft,
  k as jn,
} from './globe-gl-CizBKTRg.js';
var te = { value: () => {} };
function Mt() {
  for (var t = 0, n = arguments.length, e = {}, i; t < n; ++t) {
    if (!(i = arguments[t] + '') || i in e || /[\s.]/.test(i))
      throw new Error('illegal type: ' + i);
    e[i] = [];
  }
  return new dt(e);
}
function dt(t) {
  this._ = t;
}
function ne(t, n) {
  return t
    .trim()
    .split(/^|\s+/)
    .map(function (e) {
      var i = '',
        r = e.indexOf('.');
      if ((r >= 0 && ((i = e.slice(r + 1)), (e = e.slice(0, r))), e && !n.hasOwnProperty(e)))
        throw new Error('unknown type: ' + e);
      return { type: e, name: i };
    });
}
dt.prototype = Mt.prototype = {
  constructor: dt,
  on: function (t, n) {
    var e = this._,
      i = ne(t + '', e),
      r,
      o = -1,
      s = i.length;
    if (arguments.length < 2) {
      for (; ++o < s; ) if ((r = (t = i[o]).type) && (r = ee(e[r], t.name))) return r;
      return;
    }
    if (n != null && typeof n != 'function') throw new Error('invalid callback: ' + n);
    for (; ++o < s; )
      if ((r = (t = i[o]).type)) e[r] = rn(e[r], t.name, n);
      else if (n == null) for (r in e) e[r] = rn(e[r], t.name, null);
    return this;
  },
  copy: function () {
    var t = {},
      n = this._;
    for (var e in n) t[e] = n[e].slice();
    return new dt(t);
  },
  call: function (t, n) {
    if ((r = arguments.length - 2) > 0)
      for (var e = new Array(r), i = 0, r, o; i < r; ++i) e[i] = arguments[i + 2];
    if (!this._.hasOwnProperty(t)) throw new Error('unknown type: ' + t);
    for (o = this._[t], i = 0, r = o.length; i < r; ++i) o[i].value.apply(n, e);
  },
  apply: function (t, n, e) {
    if (!this._.hasOwnProperty(t)) throw new Error('unknown type: ' + t);
    for (var i = this._[t], r = 0, o = i.length; r < o; ++r) i[r].value.apply(n, e);
  },
};
function ee(t, n) {
  for (var e = 0, i = t.length, r; e < i; ++e) if ((r = t[e]).name === n) return r.value;
}
function rn(t, n, e) {
  for (var i = 0, r = t.length; i < r; ++i)
    if (t[i].name === n) {
      ((t[i] = te), (t = t.slice(0, i).concat(t.slice(i + 1))));
      break;
    }
  return (e != null && t.push({ name: n, value: e }), t);
}
const ie = { passive: !1 },
  _t = { capture: !0, passive: !1 };
function Yt(t) {
  t.stopImmediatePropagation();
}
function st(t) {
  (t.preventDefault(), t.stopImmediatePropagation());
}
function mn(t) {
  var n = t.document.documentElement,
    e = nt(t).on('dragstart.drag', st, _t);
  'onselectstart' in n
    ? e.on('selectstart.drag', st, _t)
    : ((n.__noselect = n.style.MozUserSelect), (n.style.MozUserSelect = 'none'));
}
function wn(t, n) {
  var e = t.document.documentElement,
    i = nt(t).on('dragstart.drag', null);
  (n &&
    (i.on('click.drag', st, _t),
    setTimeout(function () {
      i.on('click.drag', null);
    }, 0)),
    'onselectstart' in e
      ? i.on('selectstart.drag', null)
      : ((e.style.MozUserSelect = e.__noselect), delete e.__noselect));
}
const vt = (t) => () => t;
function Bt(
  t,
  {
    sourceEvent: n,
    subject: e,
    target: i,
    identifier: r,
    active: o,
    x: s,
    y: a,
    dx: h,
    dy: u,
    dispatch: f,
  }
) {
  Object.defineProperties(this, {
    type: { value: t, enumerable: !0, configurable: !0 },
    sourceEvent: { value: n, enumerable: !0, configurable: !0 },
    subject: { value: e, enumerable: !0, configurable: !0 },
    target: { value: i, enumerable: !0, configurable: !0 },
    identifier: { value: r, enumerable: !0, configurable: !0 },
    active: { value: o, enumerable: !0, configurable: !0 },
    x: { value: s, enumerable: !0, configurable: !0 },
    y: { value: a, enumerable: !0, configurable: !0 },
    dx: { value: h, enumerable: !0, configurable: !0 },
    dy: { value: u, enumerable: !0, configurable: !0 },
    _: { value: f },
  });
}
Bt.prototype.on = function () {
  var t = this._.on.apply(this._, arguments);
  return t === this._ ? this : t;
};
function re(t) {
  return !t.ctrlKey && !t.button;
}
function oe() {
  return this.parentNode;
}
function se(t, n) {
  return n ?? { x: t.x, y: t.y };
}
function ue() {
  return navigator.maxTouchPoints || 'ontouchstart' in this;
}
function ir() {
  var t = re,
    n = oe,
    e = se,
    i = ue,
    r = {},
    o = Mt('start', 'drag', 'end'),
    s = 0,
    a,
    h,
    u,
    f,
    c = 0;
  function _(g) {
    g.on('mousedown.drag', v)
      .filter(i)
      .on('touchstart.drag', T)
      .on('touchmove.drag', y, ie)
      .on('touchend.drag touchcancel.drag', M)
      .style('touch-action', 'none')
      .style('-webkit-tap-highlight-color', 'rgba(0,0,0,0)');
  }
  function v(g, E) {
    if (!(f || !t.call(this, g, E))) {
      var z = P(this, n.call(this, g, E), g, E, 'mouse');
      z &&
        (nt(g.view).on('mousemove.drag', x, _t).on('mouseup.drag', N, _t),
        mn(g.view),
        Yt(g),
        (u = !1),
        (a = g.clientX),
        (h = g.clientY),
        z('start', g));
    }
  }
  function x(g) {
    if ((st(g), !u)) {
      var E = g.clientX - a,
        z = g.clientY - h;
      u = E * E + z * z > c;
    }
    r.mouse('drag', g);
  }
  function N(g) {
    (nt(g.view).on('mousemove.drag mouseup.drag', null), wn(g.view, u), st(g), r.mouse('end', g));
  }
  function T(g, E) {
    if (t.call(this, g, E)) {
      var z = g.changedTouches,
        C = n.call(this, g, E),
        $ = z.length,
        F,
        I;
      for (F = 0; F < $; ++F)
        (I = P(this, C, g, E, z[F].identifier, z[F])) && (Yt(g), I('start', g, z[F]));
    }
  }
  function y(g) {
    var E = g.changedTouches,
      z = E.length,
      C,
      $;
    for (C = 0; C < z; ++C) ($ = r[E[C].identifier]) && (st(g), $('drag', g, E[C]));
  }
  function M(g) {
    var E = g.changedTouches,
      z = E.length,
      C,
      $;
    for (
      f && clearTimeout(f),
        f = setTimeout(function () {
          f = null;
        }, 500),
        C = 0;
      C < z;
      ++C
    )
      ($ = r[E[C].identifier]) && (Yt(g), $('end', g, E[C]));
  }
  function P(g, E, z, C, $, F) {
    var I = o.copy(),
      D = tt(F || z, E),
      R,
      B,
      l;
    if (
      (l = e.call(
        g,
        new Bt('beforestart', {
          sourceEvent: z,
          target: _,
          identifier: $,
          active: s,
          x: D[0],
          y: D[1],
          dx: 0,
          dy: 0,
          dispatch: I,
        }),
        C
      )) != null
    )
      return (
        (R = l.x - D[0] || 0),
        (B = l.y - D[1] || 0),
        function d(p, m, w) {
          var b = D,
            k;
          switch (p) {
            case 'start':
              ((r[$] = d), (k = s++));
              break;
            case 'end':
              (delete r[$], --s);
            case 'drag':
              ((D = tt(w || m, E)), (k = s));
              break;
          }
          I.call(
            p,
            g,
            new Bt(p, {
              sourceEvent: m,
              subject: l,
              target: _,
              identifier: $,
              active: k,
              x: D[0] + R,
              y: D[1] + B,
              dx: D[0] - b[0],
              dy: D[1] - b[1],
              dispatch: I,
            }),
            C
          );
        }
      );
  }
  return (
    (_.filter = function (g) {
      return arguments.length ? ((t = typeof g == 'function' ? g : vt(!!g)), _) : t;
    }),
    (_.container = function (g) {
      return arguments.length ? ((n = typeof g == 'function' ? g : vt(g)), _) : n;
    }),
    (_.subject = function (g) {
      return arguments.length ? ((e = typeof g == 'function' ? g : vt(g)), _) : e;
    }),
    (_.touchable = function (g) {
      return arguments.length ? ((i = typeof g == 'function' ? g : vt(!!g)), _) : i;
    }),
    (_.on = function () {
      var g = o.on.apply(o, arguments);
      return g === o ? _ : g;
    }),
    (_.clickDistance = function (g) {
      return arguments.length ? ((c = (g = +g) * g), _) : Math.sqrt(c);
    }),
    _
  );
}
var ut = 0,
  lt = 0,
  at = 0,
  xn = 1e3,
  Tt,
  ct,
  bt = 0,
  ot = 0,
  Pt = 0,
  pt = typeof performance == 'object' && performance.now ? performance : Date,
  Tn =
    typeof window == 'object' && window.requestAnimationFrame
      ? window.requestAnimationFrame.bind(window)
      : function (t) {
          setTimeout(t, 17);
        };
function Kt() {
  return ot || (Tn(ae), (ot = pt.now() + Pt));
}
function ae() {
  ot = 0;
}
function kt() {
  this._call = this._time = this._next = null;
}
kt.prototype = bn.prototype = {
  constructor: kt,
  restart: function (t, n, e) {
    if (typeof t != 'function') throw new TypeError('callback is not a function');
    ((e = (e == null ? Kt() : +e) + (n == null ? 0 : +n)),
      !this._next && ct !== this && (ct ? (ct._next = this) : (Tt = this), (ct = this)),
      (this._call = t),
      (this._time = e),
      Rt());
  },
  stop: function () {
    this._call && ((this._call = null), (this._time = 1 / 0), Rt());
  },
};
function bn(t, n, e) {
  var i = new kt();
  return (i.restart(t, n, e), i);
}
function he() {
  (Kt(), ++ut);
  for (var t = Tt, n; t; ) ((n = ot - t._time) >= 0 && t._call.call(void 0, n), (t = t._next));
  --ut;
}
function on() {
  ((ot = (bt = pt.now()) + Pt), (ut = lt = 0));
  try {
    he();
  } finally {
    ((ut = 0), ce(), (ot = 0));
  }
}
function le() {
  var t = pt.now(),
    n = t - bt;
  n > xn && ((Pt -= n), (bt = t));
}
function ce() {
  for (var t, n = Tt, e, i = 1 / 0; n; )
    n._call
      ? (i > n._time && (i = n._time), (t = n), (n = n._next))
      : ((e = n._next), (n._next = null), (n = t ? (t._next = e) : (Tt = e)));
  ((ct = t), Rt(i));
}
function Rt(t) {
  if (!ut) {
    lt && (lt = clearTimeout(lt));
    var n = t - ot;
    n > 24
      ? (t < 1 / 0 && (lt = setTimeout(on, t - pt.now() - Pt)), at && (at = clearInterval(at)))
      : (at || ((bt = pt.now()), (at = setInterval(le, xn))), (ut = 1), Tn(on));
  }
}
function sn(t, n, e) {
  var i = new kt();
  return (
    (n = n == null ? 0 : +n),
    i.restart(
      (r) => {
        (i.stop(), t(r + n));
      },
      n,
      e
    ),
    i
  );
}
var fe = Mt('start', 'end', 'cancel', 'interrupt'),
  _e = [],
  kn = 0,
  un = 1,
  Lt = 2,
  mt = 3,
  an = 4,
  Vt = 5,
  wt = 6;
function Ct(t, n, e, i, r, o) {
  var s = t.__transition;
  if (!s) t.__transition = {};
  else if (e in s) return;
  pe(t, e, {
    name: n,
    index: i,
    group: r,
    on: fe,
    tween: _e,
    time: o.time,
    delay: o.delay,
    duration: o.duration,
    ease: o.ease,
    timer: null,
    state: kn,
  });
}
function Wt(t, n) {
  var e = H(t, n);
  if (e.state > kn) throw new Error('too late; already scheduled');
  return e;
}
function Z(t, n) {
  var e = H(t, n);
  if (e.state > mt) throw new Error('too late; already running');
  return e;
}
function H(t, n) {
  var e = t.__transition;
  if (!e || !(e = e[n])) throw new Error('transition not found');
  return e;
}
function pe(t, n, e) {
  var i = t.__transition,
    r;
  ((i[n] = e), (e.timer = bn(o, 0, e.time)));
  function o(u) {
    ((e.state = un), e.timer.restart(s, e.delay, e.time), e.delay <= u && s(u - e.delay));
  }
  function s(u) {
    var f, c, _, v;
    if (e.state !== un) return h();
    for (f in i)
      if (((v = i[f]), v.name === e.name)) {
        if (v.state === mt) return sn(s);
        v.state === an
          ? ((v.state = wt),
            v.timer.stop(),
            v.on.call('interrupt', t, t.__data__, v.index, v.group),
            delete i[f])
          : +f < n &&
            ((v.state = wt),
            v.timer.stop(),
            v.on.call('cancel', t, t.__data__, v.index, v.group),
            delete i[f]);
      }
    if (
      (sn(function () {
        e.state === mt && ((e.state = an), e.timer.restart(a, e.delay, e.time), a(u));
      }),
      (e.state = Lt),
      e.on.call('start', t, t.__data__, e.index, e.group),
      e.state === Lt)
    ) {
      for (e.state = mt, r = new Array((_ = e.tween.length)), f = 0, c = -1; f < _; ++f)
        (v = e.tween[f].value.call(t, t.__data__, e.index, e.group)) && (r[++c] = v);
      r.length = c + 1;
    }
  }
  function a(u) {
    for (
      var f =
          u < e.duration
            ? e.ease.call(null, u / e.duration)
            : (e.timer.restart(h), (e.state = Vt), 1),
        c = -1,
        _ = r.length;
      ++c < _;
    )
      r[c].call(t, f);
    e.state === Vt && (e.on.call('end', t, t.__data__, e.index, e.group), h());
  }
  function h() {
    ((e.state = wt), e.timer.stop(), delete i[n]);
    for (var u in i) return;
    delete t.__transition;
  }
}
function xt(t, n) {
  var e = t.__transition,
    i,
    r,
    o = !0,
    s;
  if (e) {
    n = n == null ? null : n + '';
    for (s in e) {
      if ((i = e[s]).name !== n) {
        o = !1;
        continue;
      }
      ((r = i.state > Lt && i.state < Vt),
        (i.state = wt),
        i.timer.stop(),
        i.on.call(r ? 'interrupt' : 'cancel', t, t.__data__, i.index, i.group),
        delete e[s]);
    }
    o && delete t.__transition;
  }
}
function ge(t) {
  return this.each(function () {
    xt(this, t);
  });
}
function ve(t, n) {
  var e, i;
  return function () {
    var r = Z(this, t),
      o = r.tween;
    if (o !== e) {
      i = e = o;
      for (var s = 0, a = i.length; s < a; ++s)
        if (i[s].name === n) {
          ((i = i.slice()), i.splice(s, 1));
          break;
        }
    }
    r.tween = i;
  };
}
function ye(t, n, e) {
  var i, r;
  if (typeof e != 'function') throw new Error();
  return function () {
    var o = Z(this, t),
      s = o.tween;
    if (s !== i) {
      r = (i = s).slice();
      for (var a = { name: n, value: e }, h = 0, u = r.length; h < u; ++h)
        if (r[h].name === n) {
          r[h] = a;
          break;
        }
      h === u && r.push(a);
    }
    o.tween = r;
  };
}
function de(t, n) {
  var e = this._id;
  if (((t += ''), arguments.length < 2)) {
    for (var i = H(this.node(), e).tween, r = 0, o = i.length, s; r < o; ++r)
      if ((s = i[r]).name === t) return s.value;
    return null;
  }
  return this.each((n == null ? ve : ye)(e, t, n));
}
function Zt(t, n, e) {
  var i = t._id;
  return (
    t.each(function () {
      var r = Z(this, i);
      (r.value || (r.value = {}))[n] = e.apply(this, arguments);
    }),
    function (r) {
      return H(r, i).value[n];
    }
  );
}
function Nn(t, n) {
  var e;
  return (typeof n == 'number' ? Un : n instanceof en ? nn : (e = en(n)) ? ((n = e), nn) : Hn)(
    t,
    n
  );
}
function me(t) {
  return function () {
    this.removeAttribute(t);
  };
}
function we(t) {
  return function () {
    this.removeAttributeNS(t.space, t.local);
  };
}
function xe(t, n, e) {
  var i,
    r = e + '',
    o;
  return function () {
    var s = this.getAttribute(t);
    return s === r ? null : s === i ? o : (o = n((i = s), e));
  };
}
function Te(t, n, e) {
  var i,
    r = e + '',
    o;
  return function () {
    var s = this.getAttributeNS(t.space, t.local);
    return s === r ? null : s === i ? o : (o = n((i = s), e));
  };
}
function be(t, n, e) {
  var i, r, o;
  return function () {
    var s,
      a = e(this),
      h;
    return a == null
      ? void this.removeAttribute(t)
      : ((s = this.getAttribute(t)),
        (h = a + ''),
        s === h ? null : s === i && h === r ? o : ((r = h), (o = n((i = s), a))));
  };
}
function ke(t, n, e) {
  var i, r, o;
  return function () {
    var s,
      a = e(this),
      h;
    return a == null
      ? void this.removeAttributeNS(t.space, t.local)
      : ((s = this.getAttributeNS(t.space, t.local)),
        (h = a + ''),
        s === h ? null : s === i && h === r ? o : ((r = h), (o = n((i = s), a))));
  };
}
function Ne(t, n) {
  var e = dn(t),
    i = e === 'transform' ? Kn : Nn;
  return this.attrTween(
    t,
    typeof n == 'function'
      ? (e.local ? ke : be)(e, i, Zt(this, 'attr.' + t, n))
      : n == null
        ? (e.local ? we : me)(e)
        : (e.local ? Te : xe)(e, i, n)
  );
}
function Ee(t, n) {
  return function (e) {
    this.setAttribute(t, n.call(this, e));
  };
}
function ze(t, n) {
  return function (e) {
    this.setAttributeNS(t.space, t.local, n.call(this, e));
  };
}
function Ae(t, n) {
  var e, i;
  function r() {
    var o = n.apply(this, arguments);
    return (o !== i && (e = (i = o) && ze(t, o)), e);
  }
  return ((r._value = n), r);
}
function Se(t, n) {
  var e, i;
  function r() {
    var o = n.apply(this, arguments);
    return (o !== i && (e = (i = o) && Ee(t, o)), e);
  }
  return ((r._value = n), r);
}
function $e(t, n) {
  var e = 'attr.' + t;
  if (arguments.length < 2) return (e = this.tween(e)) && e._value;
  if (n == null) return this.tween(e, null);
  if (typeof n != 'function') throw new Error();
  var i = dn(t);
  return this.tween(e, (i.local ? Ae : Se)(i, n));
}
function Me(t, n) {
  return function () {
    Wt(this, t).delay = +n.apply(this, arguments);
  };
}
function Pe(t, n) {
  return (
    (n = +n),
    function () {
      Wt(this, t).delay = n;
    }
  );
}
function Ce(t) {
  var n = this._id;
  return arguments.length
    ? this.each((typeof t == 'function' ? Me : Pe)(n, t))
    : H(this.node(), n).delay;
}
function Ie(t, n) {
  return function () {
    Z(this, t).duration = +n.apply(this, arguments);
  };
}
function De(t, n) {
  return (
    (n = +n),
    function () {
      Z(this, t).duration = n;
    }
  );
}
function Oe(t) {
  var n = this._id;
  return arguments.length
    ? this.each((typeof t == 'function' ? Ie : De)(n, t))
    : H(this.node(), n).duration;
}
function Ye(t, n) {
  if (typeof n != 'function') throw new Error();
  return function () {
    Z(this, t).ease = n;
  };
}
function Fe(t) {
  var n = this._id;
  return arguments.length ? this.each(Ye(n, t)) : H(this.node(), n).ease;
}
function Xe(t, n) {
  return function () {
    var e = n.apply(this, arguments);
    if (typeof e != 'function') throw new Error();
    Z(this, t).ease = e;
  };
}
function qe(t) {
  if (typeof t != 'function') throw new Error();
  return this.each(Xe(this._id, t));
}
function Be(t) {
  typeof t != 'function' && (t = Wn(t));
  for (var n = this._groups, e = n.length, i = new Array(e), r = 0; r < e; ++r)
    for (var o = n[r], s = o.length, a = (i[r] = []), h, u = 0; u < s; ++u)
      (h = o[u]) && t.call(h, h.__data__, u, o) && a.push(h);
  return new it(i, this._parents, this._name, this._id);
}
function Re(t) {
  if (t._id !== this._id) throw new Error();
  for (
    var n = this._groups,
      e = t._groups,
      i = n.length,
      r = e.length,
      o = Math.min(i, r),
      s = new Array(i),
      a = 0;
    a < o;
    ++a
  )
    for (var h = n[a], u = e[a], f = h.length, c = (s[a] = new Array(f)), _, v = 0; v < f; ++v)
      (_ = h[v] || u[v]) && (c[v] = _);
  for (; a < i; ++a) s[a] = n[a];
  return new it(s, this._parents, this._name, this._id);
}
function Le(t) {
  return (t + '')
    .trim()
    .split(/^|\s+/)
    .every(function (n) {
      var e = n.indexOf('.');
      return (e >= 0 && (n = n.slice(0, e)), !n || n === 'start');
    });
}
function Ve(t, n, e) {
  var i,
    r,
    o = Le(n) ? Wt : Z;
  return function () {
    var s = o(this, t),
      a = s.on;
    (a !== i && (r = (i = a).copy()).on(n, e), (s.on = r));
  };
}
function Ge(t, n) {
  var e = this._id;
  return arguments.length < 2 ? H(this.node(), e).on.on(t) : this.each(Ve(e, t, n));
}
function Ue(t) {
  return function () {
    var n = this.parentNode;
    for (var e in this.__transition) if (+e !== t) return;
    n && n.removeChild(this);
  };
}
function He() {
  return this.on('end.remove', Ue(this._id));
}
function Ke(t) {
  var n = this._name,
    e = this._id;
  typeof t != 'function' && (t = Zn(t));
  for (var i = this._groups, r = i.length, o = new Array(r), s = 0; s < r; ++s)
    for (var a = i[s], h = a.length, u = (o[s] = new Array(h)), f, c, _ = 0; _ < h; ++_)
      (f = a[_]) &&
        (c = t.call(f, f.__data__, _, a)) &&
        ('__data__' in f && (c.__data__ = f.__data__), (u[_] = c), Ct(u[_], n, e, _, u, H(f, e)));
  return new it(o, this._parents, n, e);
}
function We(t) {
  var n = this._name,
    e = this._id;
  typeof t != 'function' && (t = Qn(t));
  for (var i = this._groups, r = i.length, o = [], s = [], a = 0; a < r; ++a)
    for (var h = i[a], u = h.length, f, c = 0; c < u; ++c)
      if ((f = h[c])) {
        for (var _ = t.call(f, f.__data__, c, h), v, x = H(f, e), N = 0, T = _.length; N < T; ++N)
          (v = _[N]) && Ct(v, n, e, N, _, x);
        (o.push(_), s.push(f));
      }
  return new it(o, s, n, e);
}
var Ze = $t.prototype.constructor;
function Qe() {
  return new Ze(this._groups, this._parents);
}
function Je(t, n) {
  var e, i, r;
  return function () {
    var o = ft(this, t),
      s = (this.style.removeProperty(t), ft(this, t));
    return o === s ? null : o === e && s === i ? r : (r = n((e = o), (i = s)));
  };
}
function En(t) {
  return function () {
    this.style.removeProperty(t);
  };
}
function je(t, n, e) {
  var i,
    r = e + '',
    o;
  return function () {
    var s = ft(this, t);
    return s === r ? null : s === i ? o : (o = n((i = s), e));
  };
}
function ti(t, n, e) {
  var i, r, o;
  return function () {
    var s = ft(this, t),
      a = e(this),
      h = a + '';
    return (
      a == null && (h = a = (this.style.removeProperty(t), ft(this, t))),
      s === h ? null : s === i && h === r ? o : ((r = h), (o = n((i = s), a)))
    );
  };
}
function ni(t, n) {
  var e,
    i,
    r,
    o = 'style.' + n,
    s = 'end.' + o,
    a;
  return function () {
    var h = Z(this, t),
      u = h.on,
      f = h.value[o] == null ? a || (a = En(n)) : void 0;
    ((u !== e || r !== f) && (i = (e = u).copy()).on(s, (r = f)), (h.on = i));
  };
}
function ei(t, n, e) {
  var i = (t += '') == 'transform' ? Jn : Nn;
  return n == null
    ? this.styleTween(t, Je(t, i)).on('end.style.' + t, En(t))
    : typeof n == 'function'
      ? this.styleTween(t, ti(t, i, Zt(this, 'style.' + t, n))).each(ni(this._id, t))
      : this.styleTween(t, je(t, i, n), e).on('end.style.' + t, null);
}
function ii(t, n, e) {
  return function (i) {
    this.style.setProperty(t, n.call(this, i), e);
  };
}
function ri(t, n, e) {
  var i, r;
  function o() {
    var s = n.apply(this, arguments);
    return (s !== r && (i = (r = s) && ii(t, s, e)), i);
  }
  return ((o._value = n), o);
}
function oi(t, n, e) {
  var i = 'style.' + (t += '');
  if (arguments.length < 2) return (i = this.tween(i)) && i._value;
  if (n == null) return this.tween(i, null);
  if (typeof n != 'function') throw new Error();
  return this.tween(i, ri(t, n, e ?? ''));
}
function si(t) {
  return function () {
    this.textContent = t;
  };
}
function ui(t) {
  return function () {
    var n = t(this);
    this.textContent = n ?? '';
  };
}
function ai(t) {
  return this.tween(
    'text',
    typeof t == 'function' ? ui(Zt(this, 'text', t)) : si(t == null ? '' : t + '')
  );
}
function hi(t) {
  return function (n) {
    this.textContent = t.call(this, n);
  };
}
function li(t) {
  var n, e;
  function i() {
    var r = t.apply(this, arguments);
    return (r !== e && (n = (e = r) && hi(r)), n);
  }
  return ((i._value = t), i);
}
function ci(t) {
  var n = 'text';
  if (arguments.length < 1) return (n = this.tween(n)) && n._value;
  if (t == null) return this.tween(n, null);
  if (typeof t != 'function') throw new Error();
  return this.tween(n, li(t));
}
function fi() {
  for (
    var t = this._name, n = this._id, e = zn(), i = this._groups, r = i.length, o = 0;
    o < r;
    ++o
  )
    for (var s = i[o], a = s.length, h, u = 0; u < a; ++u)
      if ((h = s[u])) {
        var f = H(h, n);
        Ct(h, t, e, u, s, {
          time: f.time + f.delay + f.duration,
          delay: 0,
          duration: f.duration,
          ease: f.ease,
        });
      }
  return new it(i, this._parents, t, e);
}
function _i() {
  var t,
    n,
    e = this,
    i = e._id,
    r = e.size();
  return new Promise(function (o, s) {
    var a = { value: s },
      h = {
        value: function () {
          --r === 0 && o();
        },
      };
    (e.each(function () {
      var u = Z(this, i),
        f = u.on;
      (f !== t &&
        ((n = (t = f).copy()), n._.cancel.push(a), n._.interrupt.push(a), n._.end.push(h)),
        (u.on = n));
    }),
      r === 0 && o());
  });
}
var pi = 0;
function it(t, n, e, i) {
  ((this._groups = t), (this._parents = n), (this._name = e), (this._id = i));
}
function zn() {
  return ++pi;
}
var j = $t.prototype;
it.prototype = {
  constructor: it,
  select: Ke,
  selectAll: We,
  selectChild: j.selectChild,
  selectChildren: j.selectChildren,
  filter: Be,
  merge: Re,
  selection: Qe,
  transition: fi,
  call: j.call,
  nodes: j.nodes,
  node: j.node,
  size: j.size,
  empty: j.empty,
  each: j.each,
  on: Ge,
  attr: Ne,
  attrTween: $e,
  style: ei,
  styleTween: oi,
  text: ai,
  textTween: ci,
  remove: He,
  tween: de,
  delay: Ce,
  duration: Oe,
  ease: Fe,
  easeVarying: qe,
  end: _i,
  [Symbol.iterator]: j[Symbol.iterator],
};
function gi(t) {
  return ((t *= 2) <= 1 ? t * t * t : (t -= 2) * t * t + 2) / 2;
}
var vi = { time: null, delay: 0, duration: 250, ease: gi };
function yi(t, n) {
  for (var e; !(e = t.__transition) || !(e = e[n]); )
    if (!(t = t.parentNode)) throw new Error(`transition ${n} not found`);
  return e;
}
function di(t) {
  var n, e;
  t instanceof it
    ? ((n = t._id), (t = t._name))
    : ((n = zn()), ((e = vi).time = Kt()), (t = t == null ? null : t + ''));
  for (var i = this._groups, r = i.length, o = 0; o < r; ++o)
    for (var s = i[o], a = s.length, h, u = 0; u < a; ++u)
      (h = s[u]) && Ct(h, t, n, u, s, e || yi(h, n));
  return new it(i, this._parents, t, n);
}
$t.prototype.interrupt = ge;
$t.prototype.transition = di;
const Gt = Math.PI,
  Ut = 2 * Gt,
  rt = 1e-6,
  mi = Ut - rt;
function An(t) {
  this._ += t[0];
  for (let n = 1, e = t.length; n < e; ++n) this._ += arguments[n] + t[n];
}
function wi(t) {
  let n = Math.floor(t);
  if (!(n >= 0)) throw new Error(`invalid digits: ${t}`);
  if (n > 15) return An;
  const e = 10 ** n;
  return function (i) {
    this._ += i[0];
    for (let r = 1, o = i.length; r < o; ++r) this._ += Math.round(arguments[r] * e) / e + i[r];
  };
}
class xi {
  constructor(n) {
    ((this._x0 = this._y0 = this._x1 = this._y1 = null),
      (this._ = ''),
      (this._append = n == null ? An : wi(n)));
  }
  moveTo(n, e) {
    this._append`M${(this._x0 = this._x1 = +n)},${(this._y0 = this._y1 = +e)}`;
  }
  closePath() {
    this._x1 !== null && ((this._x1 = this._x0), (this._y1 = this._y0), this._append`Z`);
  }
  lineTo(n, e) {
    this._append`L${(this._x1 = +n)},${(this._y1 = +e)}`;
  }
  quadraticCurveTo(n, e, i, r) {
    this._append`Q${+n},${+e},${(this._x1 = +i)},${(this._y1 = +r)}`;
  }
  bezierCurveTo(n, e, i, r, o, s) {
    this._append`C${+n},${+e},${+i},${+r},${(this._x1 = +o)},${(this._y1 = +s)}`;
  }
  arcTo(n, e, i, r, o) {
    if (((n = +n), (e = +e), (i = +i), (r = +r), (o = +o), o < 0))
      throw new Error(`negative radius: ${o}`);
    let s = this._x1,
      a = this._y1,
      h = i - n,
      u = r - e,
      f = s - n,
      c = a - e,
      _ = f * f + c * c;
    if (this._x1 === null) this._append`M${(this._x1 = n)},${(this._y1 = e)}`;
    else if (_ > rt)
      if (!(Math.abs(c * h - u * f) > rt) || !o) this._append`L${(this._x1 = n)},${(this._y1 = e)}`;
      else {
        let v = i - s,
          x = r - a,
          N = h * h + u * u,
          T = v * v + x * x,
          y = Math.sqrt(N),
          M = Math.sqrt(_),
          P = o * Math.tan((Gt - Math.acos((N + _ - T) / (2 * y * M))) / 2),
          g = P / M,
          E = P / y;
        (Math.abs(g - 1) > rt && this._append`L${n + g * f},${e + g * c}`,
          this
            ._append`A${o},${o},0,0,${+(c * v > f * x)},${(this._x1 = n + E * h)},${(this._y1 = e + E * u)}`);
      }
  }
  arc(n, e, i, r, o, s) {
    if (((n = +n), (e = +e), (i = +i), (s = !!s), i < 0)) throw new Error(`negative radius: ${i}`);
    let a = i * Math.cos(r),
      h = i * Math.sin(r),
      u = n + a,
      f = e + h,
      c = 1 ^ s,
      _ = s ? r - o : o - r;
    (this._x1 === null
      ? this._append`M${u},${f}`
      : (Math.abs(this._x1 - u) > rt || Math.abs(this._y1 - f) > rt) && this._append`L${u},${f}`,
      i &&
        (_ < 0 && (_ = (_ % Ut) + Ut),
        _ > mi
          ? this
              ._append`A${i},${i},0,1,${c},${n - a},${e - h}A${i},${i},0,1,${c},${(this._x1 = u)},${(this._y1 = f)}`
          : _ > rt &&
            this
              ._append`A${i},${i},0,${+(_ >= Gt)},${c},${(this._x1 = n + i * Math.cos(o))},${(this._y1 = e + i * Math.sin(o))}`));
  }
  rect(n, e, i, r) {
    this
      ._append`M${(this._x0 = this._x1 = +n)},${(this._y0 = this._y1 = +e)}h${(i = +i)}v${+r}h${-i}Z`;
  }
  toString() {
    return this._;
  }
}
function Ti(t) {
  const n = +this._x.call(null, t),
    e = +this._y.call(null, t);
  return Sn(this.cover(n, e), n, e, t);
}
function Sn(t, n, e, i) {
  if (isNaN(n) || isNaN(e)) return t;
  var r,
    o = t._root,
    s = { data: i },
    a = t._x0,
    h = t._y0,
    u = t._x1,
    f = t._y1,
    c,
    _,
    v,
    x,
    N,
    T,
    y,
    M;
  if (!o) return ((t._root = s), t);
  for (; o.length; )
    if (
      ((N = n >= (c = (a + u) / 2)) ? (a = c) : (u = c),
      (T = e >= (_ = (h + f) / 2)) ? (h = _) : (f = _),
      (r = o),
      !(o = o[(y = (T << 1) | N)]))
    )
      return ((r[y] = s), t);
  if (((v = +t._x.call(null, o.data)), (x = +t._y.call(null, o.data)), n === v && e === x))
    return ((s.next = o), r ? (r[y] = s) : (t._root = s), t);
  do
    ((r = r ? (r[y] = new Array(4)) : (t._root = new Array(4))),
      (N = n >= (c = (a + u) / 2)) ? (a = c) : (u = c),
      (T = e >= (_ = (h + f) / 2)) ? (h = _) : (f = _));
  while ((y = (T << 1) | N) === (M = ((x >= _) << 1) | (v >= c)));
  return ((r[M] = o), (r[y] = s), t);
}
function bi(t) {
  var n,
    e,
    i = t.length,
    r,
    o,
    s = new Array(i),
    a = new Array(i),
    h = 1 / 0,
    u = 1 / 0,
    f = -1 / 0,
    c = -1 / 0;
  for (e = 0; e < i; ++e)
    isNaN((r = +this._x.call(null, (n = t[e])))) ||
      isNaN((o = +this._y.call(null, n))) ||
      ((s[e] = r),
      (a[e] = o),
      r < h && (h = r),
      r > f && (f = r),
      o < u && (u = o),
      o > c && (c = o));
  if (h > f || u > c) return this;
  for (this.cover(h, u).cover(f, c), e = 0; e < i; ++e) Sn(this, s[e], a[e], t[e]);
  return this;
}
function ki(t, n) {
  if (isNaN((t = +t)) || isNaN((n = +n))) return this;
  var e = this._x0,
    i = this._y0,
    r = this._x1,
    o = this._y1;
  if (isNaN(e)) ((r = (e = Math.floor(t)) + 1), (o = (i = Math.floor(n)) + 1));
  else {
    for (var s = r - e || 1, a = this._root, h, u; e > t || t >= r || i > n || n >= o; )
      switch (
        ((u = ((n < i) << 1) | (t < e)), (h = new Array(4)), (h[u] = a), (a = h), (s *= 2), u)
      ) {
        case 0:
          ((r = e + s), (o = i + s));
          break;
        case 1:
          ((e = r - s), (o = i + s));
          break;
        case 2:
          ((r = e + s), (i = o - s));
          break;
        case 3:
          ((e = r - s), (i = o - s));
          break;
      }
    this._root && this._root.length && (this._root = a);
  }
  return ((this._x0 = e), (this._y0 = i), (this._x1 = r), (this._y1 = o), this);
}
function Ni() {
  var t = [];
  return (
    this.visit(function (n) {
      if (!n.length)
        do t.push(n.data);
        while ((n = n.next));
    }),
    t
  );
}
function Ei(t) {
  return arguments.length
    ? this.cover(+t[0][0], +t[0][1]).cover(+t[1][0], +t[1][1])
    : isNaN(this._x0)
      ? void 0
      : [
          [this._x0, this._y0],
          [this._x1, this._y1],
        ];
}
function X(t, n, e, i, r) {
  ((this.node = t), (this.x0 = n), (this.y0 = e), (this.x1 = i), (this.y1 = r));
}
function zi(t, n, e) {
  var i,
    r = this._x0,
    o = this._y0,
    s,
    a,
    h,
    u,
    f = this._x1,
    c = this._y1,
    _ = [],
    v = this._root,
    x,
    N;
  for (
    v && _.push(new X(v, r, o, f, c)),
      e == null ? (e = 1 / 0) : ((r = t - e), (o = n - e), (f = t + e), (c = n + e), (e *= e));
    (x = _.pop());
  )
    if (!(!(v = x.node) || (s = x.x0) > f || (a = x.y0) > c || (h = x.x1) < r || (u = x.y1) < o))
      if (v.length) {
        var T = (s + h) / 2,
          y = (a + u) / 2;
        (_.push(
          new X(v[3], T, y, h, u),
          new X(v[2], s, y, T, u),
          new X(v[1], T, a, h, y),
          new X(v[0], s, a, T, y)
        ),
          (N = ((n >= y) << 1) | (t >= T)) &&
            ((x = _[_.length - 1]),
            (_[_.length - 1] = _[_.length - 1 - N]),
            (_[_.length - 1 - N] = x)));
      } else {
        var M = t - +this._x.call(null, v.data),
          P = n - +this._y.call(null, v.data),
          g = M * M + P * P;
        if (g < e) {
          var E = Math.sqrt((e = g));
          ((r = t - E), (o = n - E), (f = t + E), (c = n + E), (i = v.data));
        }
      }
  return i;
}
function Ai(t) {
  if (isNaN((f = +this._x.call(null, t))) || isNaN((c = +this._y.call(null, t)))) return this;
  var n,
    e = this._root,
    i,
    r,
    o,
    s = this._x0,
    a = this._y0,
    h = this._x1,
    u = this._y1,
    f,
    c,
    _,
    v,
    x,
    N,
    T,
    y;
  if (!e) return this;
  if (e.length)
    for (;;) {
      if (
        ((x = f >= (_ = (s + h) / 2)) ? (s = _) : (h = _),
        (N = c >= (v = (a + u) / 2)) ? (a = v) : (u = v),
        (n = e),
        !(e = e[(T = (N << 1) | x)]))
      )
        return this;
      if (!e.length) break;
      (n[(T + 1) & 3] || n[(T + 2) & 3] || n[(T + 3) & 3]) && ((i = n), (y = T));
    }
  for (; e.data !== t; ) if (((r = e), !(e = e.next))) return this;
  return (
    (o = e.next) && delete e.next,
    r
      ? (o ? (r.next = o) : delete r.next, this)
      : n
        ? (o ? (n[T] = o) : delete n[T],
          (e = n[0] || n[1] || n[2] || n[3]) &&
            e === (n[3] || n[2] || n[1] || n[0]) &&
            !e.length &&
            (i ? (i[y] = e) : (this._root = e)),
          this)
        : ((this._root = o), this)
  );
}
function Si(t) {
  for (var n = 0, e = t.length; n < e; ++n) this.remove(t[n]);
  return this;
}
function $i() {
  return this._root;
}
function Mi() {
  var t = 0;
  return (
    this.visit(function (n) {
      if (!n.length)
        do ++t;
        while ((n = n.next));
    }),
    t
  );
}
function Pi(t) {
  var n = [],
    e,
    i = this._root,
    r,
    o,
    s,
    a,
    h;
  for (i && n.push(new X(i, this._x0, this._y0, this._x1, this._y1)); (e = n.pop()); )
    if (!t((i = e.node), (o = e.x0), (s = e.y0), (a = e.x1), (h = e.y1)) && i.length) {
      var u = (o + a) / 2,
        f = (s + h) / 2;
      ((r = i[3]) && n.push(new X(r, u, f, a, h)),
        (r = i[2]) && n.push(new X(r, o, f, u, h)),
        (r = i[1]) && n.push(new X(r, u, s, a, f)),
        (r = i[0]) && n.push(new X(r, o, s, u, f)));
    }
  return this;
}
function Ci(t) {
  var n = [],
    e = [],
    i;
  for (
    this._root && n.push(new X(this._root, this._x0, this._y0, this._x1, this._y1));
    (i = n.pop());
  ) {
    var r = i.node;
    if (r.length) {
      var o,
        s = i.x0,
        a = i.y0,
        h = i.x1,
        u = i.y1,
        f = (s + h) / 2,
        c = (a + u) / 2;
      ((o = r[0]) && n.push(new X(o, s, a, f, c)),
        (o = r[1]) && n.push(new X(o, f, a, h, c)),
        (o = r[2]) && n.push(new X(o, s, c, f, u)),
        (o = r[3]) && n.push(new X(o, f, c, h, u)));
    }
    e.push(i);
  }
  for (; (i = e.pop()); ) t(i.node, i.x0, i.y0, i.x1, i.y1);
  return this;
}
function Ii(t) {
  return t[0];
}
function Di(t) {
  return arguments.length ? ((this._x = t), this) : this._x;
}
function Oi(t) {
  return t[1];
}
function Yi(t) {
  return arguments.length ? ((this._y = t), this) : this._y;
}
function $n(t, n, e) {
  var i = new Qt(n ?? Ii, e ?? Oi, NaN, NaN, NaN, NaN);
  return t == null ? i : i.addAll(t);
}
function Qt(t, n, e, i, r, o) {
  ((this._x = t),
    (this._y = n),
    (this._x0 = e),
    (this._y0 = i),
    (this._x1 = r),
    (this._y1 = o),
    (this._root = void 0));
}
function hn(t) {
  for (var n = { data: t.data }, e = n; (t = t.next); ) e = e.next = { data: t.data };
  return n;
}
var q = ($n.prototype = Qt.prototype);
q.copy = function () {
  var t = new Qt(this._x, this._y, this._x0, this._y0, this._x1, this._y1),
    n = this._root,
    e,
    i;
  if (!n) return t;
  if (!n.length) return ((t._root = hn(n)), t);
  for (e = [{ source: n, target: (t._root = new Array(4)) }]; (n = e.pop()); )
    for (var r = 0; r < 4; ++r)
      (i = n.source[r]) &&
        (i.length
          ? e.push({ source: i, target: (n.target[r] = new Array(4)) })
          : (n.target[r] = hn(i)));
  return t;
};
q.add = Ti;
q.addAll = bi;
q.cover = ki;
q.data = Ni;
q.extent = Ei;
q.find = zi;
q.remove = Ai;
q.removeAll = Si;
q.root = $i;
q.size = Mi;
q.visit = Pi;
q.visitAfter = Ci;
q.x = Di;
q.y = Yi;
function ln(t) {
  return function () {
    return t;
  };
}
function cn(t) {
  return (t() - 0.5) * 1e-6;
}
function Fi(t) {
  return t.x + t.vx;
}
function Xi(t) {
  return t.y + t.vy;
}
function rr(t) {
  var n,
    e,
    i,
    r = 1,
    o = 1;
  typeof t != 'function' && (t = ln(t == null ? 1 : +t));
  function s() {
    for (var u, f = n.length, c, _, v, x, N, T, y = 0; y < o; ++y)
      for (c = $n(n, Fi, Xi).visitAfter(a), u = 0; u < f; ++u)
        ((_ = n[u]), (N = e[_.index]), (T = N * N), (v = _.x + _.vx), (x = _.y + _.vy), c.visit(M));
    function M(P, g, E, z, C) {
      var $ = P.data,
        F = P.r,
        I = N + F;
      if ($) {
        if ($.index > _.index) {
          var D = v - $.x - $.vx,
            R = x - $.y - $.vy,
            B = D * D + R * R;
          B < I * I &&
            (D === 0 && ((D = cn(i)), (B += D * D)),
            R === 0 && ((R = cn(i)), (B += R * R)),
            (B = ((I - (B = Math.sqrt(B))) / B) * r),
            (_.vx += (D *= B) * (I = (F *= F) / (T + F))),
            (_.vy += (R *= B) * I),
            ($.vx -= D * (I = 1 - I)),
            ($.vy -= R * I));
        }
        return;
      }
      return g > v + I || z < v - I || E > x + I || C < x - I;
    }
  }
  function a(u) {
    if (u.data) return (u.r = e[u.data.index]);
    for (var f = (u.r = 0); f < 4; ++f) u[f] && u[f].r > u.r && (u.r = u[f].r);
  }
  function h() {
    if (n) {
      var u,
        f = n.length,
        c;
      for (e = new Array(f), u = 0; u < f; ++u) ((c = n[u]), (e[c.index] = +t(c, u, n)));
    }
  }
  return (
    (s.initialize = function (u, f) {
      ((n = u), (i = f), h());
    }),
    (s.iterations = function (u) {
      return arguments.length ? ((o = +u), s) : o;
    }),
    (s.strength = function (u) {
      return arguments.length ? ((r = +u), s) : r;
    }),
    (s.radius = function (u) {
      return arguments.length ? ((t = typeof u == 'function' ? u : ln(+u)), h(), s) : t;
    }),
    s
  );
}
function S(t) {
  return function () {
    return t;
  };
}
const Mn = Math.cos,
  Nt = Math.sin,
  K = Math.sqrt,
  Et = Math.PI,
  It = 2 * Et;
function Jt(t) {
  let n = 3;
  return (
    (t.digits = function (e) {
      if (!arguments.length) return n;
      if (e == null) n = null;
      else {
        const i = Math.floor(e);
        if (!(i >= 0)) throw new RangeError(`invalid digits: ${e}`);
        n = i;
      }
      return t;
    }),
    () => new xi(n)
  );
}
function jt(t) {
  return typeof t == 'object' && 'length' in t ? t : Array.from(t);
}
function Pn(t) {
  this._context = t;
}
Pn.prototype = {
  areaStart: function () {
    this._line = 0;
  },
  areaEnd: function () {
    this._line = NaN;
  },
  lineStart: function () {
    this._point = 0;
  },
  lineEnd: function () {
    ((this._line || (this._line !== 0 && this._point === 1)) && this._context.closePath(),
      (this._line = 1 - this._line));
  },
  point: function (t, n) {
    switch (((t = +t), (n = +n), this._point)) {
      case 0:
        ((this._point = 1), this._line ? this._context.lineTo(t, n) : this._context.moveTo(t, n));
        break;
      case 1:
        this._point = 2;
      default:
        this._context.lineTo(t, n);
        break;
    }
  },
};
function Cn(t) {
  return new Pn(t);
}
function In(t) {
  return t[0];
}
function Dn(t) {
  return t[1];
}
function qi(t, n) {
  var e = S(!0),
    i = null,
    r = Cn,
    o = null,
    s = Jt(a);
  ((t = typeof t == 'function' ? t : t === void 0 ? In : S(t)),
    (n = typeof n == 'function' ? n : n === void 0 ? Dn : S(n)));
  function a(h) {
    var u,
      f = (h = jt(h)).length,
      c,
      _ = !1,
      v;
    for (i == null && (o = r((v = s()))), u = 0; u <= f; ++u)
      (!(u < f && e((c = h[u]), u, h)) === _ && ((_ = !_) ? o.lineStart() : o.lineEnd()),
        _ && o.point(+t(c, u, h), +n(c, u, h)));
    if (v) return ((o = null), v + '' || null);
  }
  return (
    (a.x = function (h) {
      return arguments.length ? ((t = typeof h == 'function' ? h : S(+h)), a) : t;
    }),
    (a.y = function (h) {
      return arguments.length ? ((n = typeof h == 'function' ? h : S(+h)), a) : n;
    }),
    (a.defined = function (h) {
      return arguments.length ? ((e = typeof h == 'function' ? h : S(!!h)), a) : e;
    }),
    (a.curve = function (h) {
      return arguments.length ? ((r = h), i != null && (o = r(i)), a) : r;
    }),
    (a.context = function (h) {
      return arguments.length ? (h == null ? (i = o = null) : (o = r((i = h))), a) : i;
    }),
    a
  );
}
function or(t, n, e) {
  var i = null,
    r = S(!0),
    o = null,
    s = Cn,
    a = null,
    h = Jt(u);
  ((t = typeof t == 'function' ? t : t === void 0 ? In : S(+t)),
    (n = typeof n == 'function' ? n : S(n === void 0 ? 0 : +n)),
    (e = typeof e == 'function' ? e : e === void 0 ? Dn : S(+e)));
  function u(c) {
    var _,
      v,
      x,
      N = (c = jt(c)).length,
      T,
      y = !1,
      M,
      P = new Array(N),
      g = new Array(N);
    for (o == null && (a = s((M = h()))), _ = 0; _ <= N; ++_) {
      if (!(_ < N && r((T = c[_]), _, c)) === y)
        if ((y = !y)) ((v = _), a.areaStart(), a.lineStart());
        else {
          for (a.lineEnd(), a.lineStart(), x = _ - 1; x >= v; --x) a.point(P[x], g[x]);
          (a.lineEnd(), a.areaEnd());
        }
      y &&
        ((P[_] = +t(T, _, c)),
        (g[_] = +n(T, _, c)),
        a.point(i ? +i(T, _, c) : P[_], e ? +e(T, _, c) : g[_]));
    }
    if (M) return ((a = null), M + '' || null);
  }
  function f() {
    return qi().defined(r).curve(s).context(o);
  }
  return (
    (u.x = function (c) {
      return arguments.length ? ((t = typeof c == 'function' ? c : S(+c)), (i = null), u) : t;
    }),
    (u.x0 = function (c) {
      return arguments.length ? ((t = typeof c == 'function' ? c : S(+c)), u) : t;
    }),
    (u.x1 = function (c) {
      return arguments.length
        ? ((i = c == null ? null : typeof c == 'function' ? c : S(+c)), u)
        : i;
    }),
    (u.y = function (c) {
      return arguments.length ? ((n = typeof c == 'function' ? c : S(+c)), (e = null), u) : n;
    }),
    (u.y0 = function (c) {
      return arguments.length ? ((n = typeof c == 'function' ? c : S(+c)), u) : n;
    }),
    (u.y1 = function (c) {
      return arguments.length
        ? ((e = c == null ? null : typeof c == 'function' ? c : S(+c)), u)
        : e;
    }),
    (u.lineX0 = u.lineY0 =
      function () {
        return f().x(t).y(n);
      }),
    (u.lineY1 = function () {
      return f().x(t).y(e);
    }),
    (u.lineX1 = function () {
      return f().x(i).y(n);
    }),
    (u.defined = function (c) {
      return arguments.length ? ((r = typeof c == 'function' ? c : S(!!c)), u) : r;
    }),
    (u.curve = function (c) {
      return arguments.length ? ((s = c), o != null && (a = s(o)), u) : s;
    }),
    (u.context = function (c) {
      return arguments.length ? (c == null ? (o = a = null) : (a = s((o = c))), u) : o;
    }),
    u
  );
}
class On {
  constructor(n, e) {
    ((this._context = n), (this._x = e));
  }
  areaStart() {
    this._line = 0;
  }
  areaEnd() {
    this._line = NaN;
  }
  lineStart() {
    this._point = 0;
  }
  lineEnd() {
    ((this._line || (this._line !== 0 && this._point === 1)) && this._context.closePath(),
      (this._line = 1 - this._line));
  }
  point(n, e) {
    switch (((n = +n), (e = +e), this._point)) {
      case 0: {
        ((this._point = 1), this._line ? this._context.lineTo(n, e) : this._context.moveTo(n, e));
        break;
      }
      case 1:
        this._point = 2;
      default: {
        this._x
          ? this._context.bezierCurveTo(
              (this._x0 = (this._x0 + n) / 2),
              this._y0,
              this._x0,
              e,
              n,
              e
            )
          : this._context.bezierCurveTo(
              this._x0,
              (this._y0 = (this._y0 + e) / 2),
              n,
              this._y0,
              n,
              e
            );
        break;
      }
    }
    ((this._x0 = n), (this._y0 = e));
  }
}
function sr(t) {
  return new On(t, !0);
}
function ur(t) {
  return new On(t, !1);
}
const Bi = {
    draw(t, n) {
      const e = K(n / Et);
      (t.moveTo(e, 0), t.arc(0, 0, e, 0, It));
    },
  },
  ar = {
    draw(t, n) {
      const e = K(n / 5) / 2;
      (t.moveTo(-3 * e, -e),
        t.lineTo(-e, -e),
        t.lineTo(-e, -3 * e),
        t.lineTo(e, -3 * e),
        t.lineTo(e, -e),
        t.lineTo(3 * e, -e),
        t.lineTo(3 * e, e),
        t.lineTo(e, e),
        t.lineTo(e, 3 * e),
        t.lineTo(-e, 3 * e),
        t.lineTo(-e, e),
        t.lineTo(-3 * e, e),
        t.closePath());
    },
  },
  Yn = K(1 / 3),
  Ri = Yn * 2,
  hr = {
    draw(t, n) {
      const e = K(n / Ri),
        i = e * Yn;
      (t.moveTo(0, -e), t.lineTo(i, 0), t.lineTo(0, e), t.lineTo(-i, 0), t.closePath());
    },
  },
  lr = {
    draw(t, n) {
      const e = K(n),
        i = -e / 2;
      t.rect(i, i, e, e);
    },
  },
  Li = 0.8908130915292852,
  Fn = Nt(Et / 10) / Nt((7 * Et) / 10),
  Vi = Nt(It / 10) * Fn,
  Gi = -Mn(It / 10) * Fn,
  cr = {
    draw(t, n) {
      const e = K(n * Li),
        i = Vi * e,
        r = Gi * e;
      (t.moveTo(0, -e), t.lineTo(i, r));
      for (let o = 1; o < 5; ++o) {
        const s = (It * o) / 5,
          a = Mn(s),
          h = Nt(s);
        (t.lineTo(h * e, -a * e), t.lineTo(a * i - h * r, h * i + a * r));
      }
      t.closePath();
    },
  },
  Ft = K(3),
  fr = {
    draw(t, n) {
      const e = -K(n / (Ft * 3));
      (t.moveTo(0, e * 2), t.lineTo(-Ft * e, -e), t.lineTo(Ft * e, -e), t.closePath());
    },
  },
  L = -0.5,
  V = K(3) / 2,
  Ht = 1 / K(12),
  Ui = (Ht / 2 + 1) * 3,
  _r = {
    draw(t, n) {
      const e = K(n / Ui),
        i = e / 2,
        r = e * Ht,
        o = i,
        s = e * Ht + e,
        a = -o,
        h = s;
      (t.moveTo(i, r),
        t.lineTo(o, s),
        t.lineTo(a, h),
        t.lineTo(L * i - V * r, V * i + L * r),
        t.lineTo(L * o - V * s, V * o + L * s),
        t.lineTo(L * a - V * h, V * a + L * h),
        t.lineTo(L * i + V * r, L * r - V * i),
        t.lineTo(L * o + V * s, L * s - V * o),
        t.lineTo(L * a + V * h, L * h - V * a),
        t.closePath());
    },
  };
function pr(t, n) {
  let e = null,
    i = Jt(r);
  ((t = typeof t == 'function' ? t : S(t || Bi)),
    (n = typeof n == 'function' ? n : S(n === void 0 ? 64 : +n)));
  function r() {
    let o;
    if ((e || (e = o = i()), t.apply(this, arguments).draw(e, +n.apply(this, arguments)), o))
      return ((e = null), o + '' || null);
  }
  return (
    (r.type = function (o) {
      return arguments.length ? ((t = typeof o == 'function' ? o : S(o)), r) : t;
    }),
    (r.size = function (o) {
      return arguments.length ? ((n = typeof o == 'function' ? o : S(+o)), r) : n;
    }),
    (r.context = function (o) {
      return arguments.length ? ((e = o ?? null), r) : e;
    }),
    r
  );
}
function zt() {}
function At(t, n, e) {
  t._context.bezierCurveTo(
    (2 * t._x0 + t._x1) / 3,
    (2 * t._y0 + t._y1) / 3,
    (t._x0 + 2 * t._x1) / 3,
    (t._y0 + 2 * t._y1) / 3,
    (t._x0 + 4 * t._x1 + n) / 6,
    (t._y0 + 4 * t._y1 + e) / 6
  );
}
function Xn(t) {
  this._context = t;
}
Xn.prototype = {
  areaStart: function () {
    this._line = 0;
  },
  areaEnd: function () {
    this._line = NaN;
  },
  lineStart: function () {
    ((this._x0 = this._x1 = this._y0 = this._y1 = NaN), (this._point = 0));
  },
  lineEnd: function () {
    switch (this._point) {
      case 3:
        At(this, this._x1, this._y1);
      case 2:
        this._context.lineTo(this._x1, this._y1);
        break;
    }
    ((this._line || (this._line !== 0 && this._point === 1)) && this._context.closePath(),
      (this._line = 1 - this._line));
  },
  point: function (t, n) {
    switch (((t = +t), (n = +n), this._point)) {
      case 0:
        ((this._point = 1), this._line ? this._context.lineTo(t, n) : this._context.moveTo(t, n));
        break;
      case 1:
        this._point = 2;
        break;
      case 2:
        ((this._point = 3),
          this._context.lineTo((5 * this._x0 + this._x1) / 6, (5 * this._y0 + this._y1) / 6));
      default:
        At(this, t, n);
        break;
    }
    ((this._x0 = this._x1), (this._x1 = t), (this._y0 = this._y1), (this._y1 = n));
  },
};
function gr(t) {
  return new Xn(t);
}
function qn(t) {
  this._context = t;
}
qn.prototype = {
  areaStart: zt,
  areaEnd: zt,
  lineStart: function () {
    ((this._x0 =
      this._x1 =
      this._x2 =
      this._x3 =
      this._x4 =
      this._y0 =
      this._y1 =
      this._y2 =
      this._y3 =
      this._y4 =
        NaN),
      (this._point = 0));
  },
  lineEnd: function () {
    switch (this._point) {
      case 1: {
        (this._context.moveTo(this._x2, this._y2), this._context.closePath());
        break;
      }
      case 2: {
        (this._context.moveTo((this._x2 + 2 * this._x3) / 3, (this._y2 + 2 * this._y3) / 3),
          this._context.lineTo((this._x3 + 2 * this._x2) / 3, (this._y3 + 2 * this._y2) / 3),
          this._context.closePath());
        break;
      }
      case 3: {
        (this.point(this._x2, this._y2),
          this.point(this._x3, this._y3),
          this.point(this._x4, this._y4));
        break;
      }
    }
  },
  point: function (t, n) {
    switch (((t = +t), (n = +n), this._point)) {
      case 0:
        ((this._point = 1), (this._x2 = t), (this._y2 = n));
        break;
      case 1:
        ((this._point = 2), (this._x3 = t), (this._y3 = n));
        break;
      case 2:
        ((this._point = 3),
          (this._x4 = t),
          (this._y4 = n),
          this._context.moveTo(
            (this._x0 + 4 * this._x1 + t) / 6,
            (this._y0 + 4 * this._y1 + n) / 6
          ));
        break;
      default:
        At(this, t, n);
        break;
    }
    ((this._x0 = this._x1), (this._x1 = t), (this._y0 = this._y1), (this._y1 = n));
  },
};
function vr(t) {
  return new qn(t);
}
function Bn(t) {
  this._context = t;
}
Bn.prototype = {
  areaStart: function () {
    this._line = 0;
  },
  areaEnd: function () {
    this._line = NaN;
  },
  lineStart: function () {
    ((this._x0 = this._x1 = this._y0 = this._y1 = NaN), (this._point = 0));
  },
  lineEnd: function () {
    ((this._line || (this._line !== 0 && this._point === 3)) && this._context.closePath(),
      (this._line = 1 - this._line));
  },
  point: function (t, n) {
    switch (((t = +t), (n = +n), this._point)) {
      case 0:
        this._point = 1;
        break;
      case 1:
        this._point = 2;
        break;
      case 2:
        this._point = 3;
        var e = (this._x0 + 4 * this._x1 + t) / 6,
          i = (this._y0 + 4 * this._y1 + n) / 6;
        this._line ? this._context.lineTo(e, i) : this._context.moveTo(e, i);
        break;
      case 3:
        this._point = 4;
      default:
        At(this, t, n);
        break;
    }
    ((this._x0 = this._x1), (this._x1 = t), (this._y0 = this._y1), (this._y1 = n));
  },
};
function yr(t) {
  return new Bn(t);
}
function Rn(t) {
  this._context = t;
}
Rn.prototype = {
  areaStart: zt,
  areaEnd: zt,
  lineStart: function () {
    this._point = 0;
  },
  lineEnd: function () {
    this._point && this._context.closePath();
  },
  point: function (t, n) {
    ((t = +t),
      (n = +n),
      this._point ? this._context.lineTo(t, n) : ((this._point = 1), this._context.moveTo(t, n)));
  },
};
function dr(t) {
  return new Rn(t);
}
function fn(t) {
  return t < 0 ? -1 : 1;
}
function _n(t, n, e) {
  var i = t._x1 - t._x0,
    r = n - t._x1,
    o = (t._y1 - t._y0) / (i || (r < 0 && -0)),
    s = (e - t._y1) / (r || (i < 0 && -0)),
    a = (o * r + s * i) / (i + r);
  return (fn(o) + fn(s)) * Math.min(Math.abs(o), Math.abs(s), 0.5 * Math.abs(a)) || 0;
}
function pn(t, n) {
  var e = t._x1 - t._x0;
  return e ? ((3 * (t._y1 - t._y0)) / e - n) / 2 : n;
}
function Xt(t, n, e) {
  var i = t._x0,
    r = t._y0,
    o = t._x1,
    s = t._y1,
    a = (o - i) / 3;
  t._context.bezierCurveTo(i + a, r + a * n, o - a, s - a * e, o, s);
}
function St(t) {
  this._context = t;
}
St.prototype = {
  areaStart: function () {
    this._line = 0;
  },
  areaEnd: function () {
    this._line = NaN;
  },
  lineStart: function () {
    ((this._x0 = this._x1 = this._y0 = this._y1 = this._t0 = NaN), (this._point = 0));
  },
  lineEnd: function () {
    switch (this._point) {
      case 2:
        this._context.lineTo(this._x1, this._y1);
        break;
      case 3:
        Xt(this, this._t0, pn(this, this._t0));
        break;
    }
    ((this._line || (this._line !== 0 && this._point === 1)) && this._context.closePath(),
      (this._line = 1 - this._line));
  },
  point: function (t, n) {
    var e = NaN;
    if (((t = +t), (n = +n), !(t === this._x1 && n === this._y1))) {
      switch (this._point) {
        case 0:
          ((this._point = 1), this._line ? this._context.lineTo(t, n) : this._context.moveTo(t, n));
          break;
        case 1:
          this._point = 2;
          break;
        case 2:
          ((this._point = 3), Xt(this, pn(this, (e = _n(this, t, n))), e));
          break;
        default:
          Xt(this, this._t0, (e = _n(this, t, n)));
          break;
      }
      ((this._x0 = this._x1),
        (this._x1 = t),
        (this._y0 = this._y1),
        (this._y1 = n),
        (this._t0 = e));
    }
  },
};
function Ln(t) {
  this._context = new Vn(t);
}
(Ln.prototype = Object.create(St.prototype)).point = function (t, n) {
  St.prototype.point.call(this, n, t);
};
function Vn(t) {
  this._context = t;
}
Vn.prototype = {
  moveTo: function (t, n) {
    this._context.moveTo(n, t);
  },
  closePath: function () {
    this._context.closePath();
  },
  lineTo: function (t, n) {
    this._context.lineTo(n, t);
  },
  bezierCurveTo: function (t, n, e, i, r, o) {
    this._context.bezierCurveTo(n, t, i, e, o, r);
  },
};
function mr(t) {
  return new St(t);
}
function wr(t) {
  return new Ln(t);
}
function Gn(t) {
  this._context = t;
}
Gn.prototype = {
  areaStart: function () {
    this._line = 0;
  },
  areaEnd: function () {
    this._line = NaN;
  },
  lineStart: function () {
    ((this._x = []), (this._y = []));
  },
  lineEnd: function () {
    var t = this._x,
      n = this._y,
      e = t.length;
    if (e)
      if (
        (this._line ? this._context.lineTo(t[0], n[0]) : this._context.moveTo(t[0], n[0]), e === 2)
      )
        this._context.lineTo(t[1], n[1]);
      else
        for (var i = gn(t), r = gn(n), o = 0, s = 1; s < e; ++o, ++s)
          this._context.bezierCurveTo(i[0][o], r[0][o], i[1][o], r[1][o], t[s], n[s]);
    ((this._line || (this._line !== 0 && e === 1)) && this._context.closePath(),
      (this._line = 1 - this._line),
      (this._x = this._y = null));
  },
  point: function (t, n) {
    (this._x.push(+t), this._y.push(+n));
  },
};
function gn(t) {
  var n,
    e = t.length - 1,
    i,
    r = new Array(e),
    o = new Array(e),
    s = new Array(e);
  for (r[0] = 0, o[0] = 2, s[0] = t[0] + 2 * t[1], n = 1; n < e - 1; ++n)
    ((r[n] = 1), (o[n] = 4), (s[n] = 4 * t[n] + 2 * t[n + 1]));
  for (r[e - 1] = 2, o[e - 1] = 7, s[e - 1] = 8 * t[e - 1] + t[e], n = 1; n < e; ++n)
    ((i = r[n] / o[n - 1]), (o[n] -= i), (s[n] -= i * s[n - 1]));
  for (r[e - 1] = s[e - 1] / o[e - 1], n = e - 2; n >= 0; --n) r[n] = (s[n] - r[n + 1]) / o[n];
  for (o[e - 1] = (t[e] + r[e - 1]) / 2, n = 0; n < e - 1; ++n) o[n] = 2 * t[n + 1] - r[n + 1];
  return [r, o];
}
function xr(t) {
  return new Gn(t);
}
function Dt(t, n) {
  ((this._context = t), (this._t = n));
}
Dt.prototype = {
  areaStart: function () {
    this._line = 0;
  },
  areaEnd: function () {
    this._line = NaN;
  },
  lineStart: function () {
    ((this._x = this._y = NaN), (this._point = 0));
  },
  lineEnd: function () {
    (0 < this._t && this._t < 1 && this._point === 2 && this._context.lineTo(this._x, this._y),
      (this._line || (this._line !== 0 && this._point === 1)) && this._context.closePath(),
      this._line >= 0 && ((this._t = 1 - this._t), (this._line = 1 - this._line)));
  },
  point: function (t, n) {
    switch (((t = +t), (n = +n), this._point)) {
      case 0:
        ((this._point = 1), this._line ? this._context.lineTo(t, n) : this._context.moveTo(t, n));
        break;
      case 1:
        this._point = 2;
      default: {
        if (this._t <= 0) (this._context.lineTo(this._x, n), this._context.lineTo(t, n));
        else {
          var e = this._x * (1 - this._t) + t * this._t;
          (this._context.lineTo(e, this._y), this._context.lineTo(e, n));
        }
        break;
      }
    }
    ((this._x = t), (this._y = n));
  },
};
function Tr(t) {
  return new Dt(t, 0.5);
}
function br(t) {
  return new Dt(t, 0);
}
function kr(t) {
  return new Dt(t, 1);
}
function gt(t, n) {
  if ((s = t.length) > 1)
    for (var e = 1, i, r, o = t[n[0]], s, a = o.length; e < s; ++e)
      for (r = o, o = t[n[e]], i = 0; i < a; ++i)
        o[i][1] += o[i][0] = isNaN(r[i][1]) ? r[i][0] : r[i][1];
}
function vn(t) {
  for (var n = t.length, e = new Array(n); --n >= 0; ) e[n] = n;
  return e;
}
function Hi(t, n) {
  return t[n];
}
function Ki(t) {
  const n = [];
  return ((n.key = t), n);
}
function Nr() {
  var t = S([]),
    n = vn,
    e = gt,
    i = Hi;
  function r(o) {
    var s = Array.from(t.apply(this, arguments), Ki),
      a,
      h = s.length,
      u = -1,
      f;
    for (const c of o) for (a = 0, ++u; a < h; ++a) (s[a][u] = [0, +i(c, s[a].key, u, o)]).data = c;
    for (a = 0, f = jt(n(s)); a < h; ++a) s[f[a]].index = a;
    return (e(s, f), s);
  }
  return (
    (r.keys = function (o) {
      return arguments.length ? ((t = typeof o == 'function' ? o : S(Array.from(o))), r) : t;
    }),
    (r.value = function (o) {
      return arguments.length ? ((i = typeof o == 'function' ? o : S(+o)), r) : i;
    }),
    (r.order = function (o) {
      return arguments.length
        ? ((n = o == null ? vn : typeof o == 'function' ? o : S(Array.from(o))), r)
        : n;
    }),
    (r.offset = function (o) {
      return arguments.length ? ((e = o ?? gt), r) : e;
    }),
    r
  );
}
function Er(t, n) {
  if ((i = t.length) > 0) {
    for (var e, i, r = 0, o = t[0].length, s; r < o; ++r) {
      for (s = e = 0; e < i; ++e) s += t[e][r][1] || 0;
      if (s) for (e = 0; e < i; ++e) t[e][r][1] /= s;
    }
    gt(t, n);
  }
}
function zr(t, n) {
  if ((r = t.length) > 0) {
    for (var e = 0, i = t[n[0]], r, o = i.length; e < o; ++e) {
      for (var s = 0, a = 0; s < r; ++s) a += t[s][e][1] || 0;
      i[e][1] += i[e][0] = -a / 2;
    }
    gt(t, n);
  }
}
function Ar(t, n) {
  if (!(!((s = t.length) > 0) || !((o = (r = t[n[0]]).length) > 0))) {
    for (var e = 0, i = 1, r, o, s; i < o; ++i) {
      for (var a = 0, h = 0, u = 0; a < s; ++a) {
        for (
          var f = t[n[a]], c = f[i][1] || 0, _ = f[i - 1][1] || 0, v = (c - _) / 2, x = 0;
          x < a;
          ++x
        ) {
          var N = t[n[x]],
            T = N[i][1] || 0,
            y = N[i - 1][1] || 0;
          v += T - y;
        }
        ((h += c), (u += v * c));
      }
      ((r[i - 1][1] += r[i - 1][0] = e), h && (e -= u / h));
    }
    ((r[i - 1][1] += r[i - 1][0] = e), gt(t, n));
  }
}
const yt = (t) => () => t;
function Wi(t, { sourceEvent: n, target: e, transform: i, dispatch: r }) {
  Object.defineProperties(this, {
    type: { value: t, enumerable: !0, configurable: !0 },
    sourceEvent: { value: n, enumerable: !0, configurable: !0 },
    target: { value: e, enumerable: !0, configurable: !0 },
    transform: { value: i, enumerable: !0, configurable: !0 },
    _: { value: r },
  });
}
function et(t, n, e) {
  ((this.k = t), (this.x = n), (this.y = e));
}
et.prototype = {
  constructor: et,
  scale: function (t) {
    return t === 1 ? this : new et(this.k * t, this.x, this.y);
  },
  translate: function (t, n) {
    return (t === 0) & (n === 0) ? this : new et(this.k, this.x + this.k * t, this.y + this.k * n);
  },
  apply: function (t) {
    return [t[0] * this.k + this.x, t[1] * this.k + this.y];
  },
  applyX: function (t) {
    return t * this.k + this.x;
  },
  applyY: function (t) {
    return t * this.k + this.y;
  },
  invert: function (t) {
    return [(t[0] - this.x) / this.k, (t[1] - this.y) / this.k];
  },
  invertX: function (t) {
    return (t - this.x) / this.k;
  },
  invertY: function (t) {
    return (t - this.y) / this.k;
  },
  rescaleX: function (t) {
    return t.copy().domain(t.range().map(this.invertX, this).map(t.invert, t));
  },
  rescaleY: function (t) {
    return t.copy().domain(t.range().map(this.invertY, this).map(t.invert, t));
  },
  toString: function () {
    return 'translate(' + this.x + ',' + this.y + ') scale(' + this.k + ')';
  },
};
var tn = new et(1, 0, 0);
Zi.prototype = et.prototype;
function Zi(t) {
  for (; !t.__zoom; ) if (!(t = t.parentNode)) return tn;
  return t.__zoom;
}
function qt(t) {
  t.stopImmediatePropagation();
}
function ht(t) {
  (t.preventDefault(), t.stopImmediatePropagation());
}
function Qi(t) {
  return (!t.ctrlKey || t.type === 'wheel') && !t.button;
}
function Ji() {
  var t = this;
  return t instanceof SVGElement
    ? ((t = t.ownerSVGElement || t),
      t.hasAttribute('viewBox')
        ? ((t = t.viewBox.baseVal),
          [
            [t.x, t.y],
            [t.x + t.width, t.y + t.height],
          ])
        : [
            [0, 0],
            [t.width.baseVal.value, t.height.baseVal.value],
          ])
    : [
        [0, 0],
        [t.clientWidth, t.clientHeight],
      ];
}
function yn() {
  return this.__zoom || tn;
}
function ji(t) {
  return -t.deltaY * (t.deltaMode === 1 ? 0.05 : t.deltaMode ? 1 : 0.002) * (t.ctrlKey ? 10 : 1);
}
function tr() {
  return navigator.maxTouchPoints || 'ontouchstart' in this;
}
function nr(t, n, e) {
  var i = t.invertX(n[0][0]) - e[0][0],
    r = t.invertX(n[1][0]) - e[1][0],
    o = t.invertY(n[0][1]) - e[0][1],
    s = t.invertY(n[1][1]) - e[1][1];
  return t.translate(
    r > i ? (i + r) / 2 : Math.min(0, i) || Math.max(0, r),
    s > o ? (o + s) / 2 : Math.min(0, o) || Math.max(0, s)
  );
}
function Sr() {
  var t = Qi,
    n = Ji,
    e = nr,
    i = ji,
    r = tr,
    o = [0, 1 / 0],
    s = [
      [-1 / 0, -1 / 0],
      [1 / 0, 1 / 0],
    ],
    a = 250,
    h = jn,
    u = Mt('start', 'zoom', 'end'),
    f,
    c,
    _,
    v = 500,
    x = 150,
    N = 0,
    T = 10;
  function y(l) {
    l.property('__zoom', yn)
      .on('wheel.zoom', $, { passive: !1 })
      .on('mousedown.zoom', F)
      .on('dblclick.zoom', I)
      .filter(r)
      .on('touchstart.zoom', D)
      .on('touchmove.zoom', R)
      .on('touchend.zoom touchcancel.zoom', B)
      .style('-webkit-tap-highlight-color', 'rgba(0,0,0,0)');
  }
  ((y.transform = function (l, d, p, m) {
    var w = l.selection ? l.selection() : l;
    (w.property('__zoom', yn),
      l !== w
        ? E(l, d, p, m)
        : w.interrupt().each(function () {
            z(this, arguments)
              .event(m)
              .start()
              .zoom(null, typeof d == 'function' ? d.apply(this, arguments) : d)
              .end();
          }));
  }),
    (y.scaleBy = function (l, d, p, m) {
      y.scaleTo(
        l,
        function () {
          var w = this.__zoom.k,
            b = typeof d == 'function' ? d.apply(this, arguments) : d;
          return w * b;
        },
        p,
        m
      );
    }),
    (y.scaleTo = function (l, d, p, m) {
      y.transform(
        l,
        function () {
          var w = n.apply(this, arguments),
            b = this.__zoom,
            k = p == null ? g(w) : typeof p == 'function' ? p.apply(this, arguments) : p,
            A = b.invert(k),
            O = typeof d == 'function' ? d.apply(this, arguments) : d;
          return e(P(M(b, O), k, A), w, s);
        },
        p,
        m
      );
    }),
    (y.translateBy = function (l, d, p, m) {
      y.transform(
        l,
        function () {
          return e(
            this.__zoom.translate(
              typeof d == 'function' ? d.apply(this, arguments) : d,
              typeof p == 'function' ? p.apply(this, arguments) : p
            ),
            n.apply(this, arguments),
            s
          );
        },
        null,
        m
      );
    }),
    (y.translateTo = function (l, d, p, m, w) {
      y.transform(
        l,
        function () {
          var b = n.apply(this, arguments),
            k = this.__zoom,
            A = m == null ? g(b) : typeof m == 'function' ? m.apply(this, arguments) : m;
          return e(
            tn
              .translate(A[0], A[1])
              .scale(k.k)
              .translate(
                typeof d == 'function' ? -d.apply(this, arguments) : -d,
                typeof p == 'function' ? -p.apply(this, arguments) : -p
              ),
            b,
            s
          );
        },
        m,
        w
      );
    }));
  function M(l, d) {
    return ((d = Math.max(o[0], Math.min(o[1], d))), d === l.k ? l : new et(d, l.x, l.y));
  }
  function P(l, d, p) {
    var m = d[0] - p[0] * l.k,
      w = d[1] - p[1] * l.k;
    return m === l.x && w === l.y ? l : new et(l.k, m, w);
  }
  function g(l) {
    return [(+l[0][0] + +l[1][0]) / 2, (+l[0][1] + +l[1][1]) / 2];
  }
  function E(l, d, p, m) {
    l.on('start.zoom', function () {
      z(this, arguments).event(m).start();
    })
      .on('interrupt.zoom end.zoom', function () {
        z(this, arguments).event(m).end();
      })
      .tween('zoom', function () {
        var w = this,
          b = arguments,
          k = z(w, b).event(m),
          A = n.apply(w, b),
          O = p == null ? g(A) : typeof p == 'function' ? p.apply(w, b) : p,
          W = Math.max(A[1][0] - A[0][0], A[1][1] - A[0][1]),
          Y = w.__zoom,
          G = typeof d == 'function' ? d.apply(w, b) : d,
          Q = h(Y.invert(O).concat(W / Y.k), G.invert(O).concat(W / G.k));
        return function (U) {
          if (U === 1) U = G;
          else {
            var J = Q(U),
              Ot = W / J[2];
            U = new et(Ot, O[0] - J[0] * Ot, O[1] - J[1] * Ot);
          }
          k.zoom(null, U);
        };
      });
  }
  function z(l, d, p) {
    return (!p && l.__zooming) || new C(l, d);
  }
  function C(l, d) {
    ((this.that = l),
      (this.args = d),
      (this.active = 0),
      (this.sourceEvent = null),
      (this.extent = n.apply(l, d)),
      (this.taps = 0));
  }
  C.prototype = {
    event: function (l) {
      return (l && (this.sourceEvent = l), this);
    },
    start: function () {
      return (++this.active === 1 && ((this.that.__zooming = this), this.emit('start')), this);
    },
    zoom: function (l, d) {
      return (
        this.mouse && l !== 'mouse' && (this.mouse[1] = d.invert(this.mouse[0])),
        this.touch0 && l !== 'touch' && (this.touch0[1] = d.invert(this.touch0[0])),
        this.touch1 && l !== 'touch' && (this.touch1[1] = d.invert(this.touch1[0])),
        (this.that.__zoom = d),
        this.emit('zoom'),
        this
      );
    },
    end: function () {
      return (--this.active === 0 && (delete this.that.__zooming, this.emit('end')), this);
    },
    emit: function (l) {
      var d = nt(this.that).datum();
      u.call(
        l,
        this.that,
        new Wi(l, {
          sourceEvent: this.sourceEvent,
          target: y,
          transform: this.that.__zoom,
          dispatch: u,
        }),
        d
      );
    },
  };
  function $(l, ...d) {
    if (!t.apply(this, arguments)) return;
    var p = z(this, d).event(l),
      m = this.__zoom,
      w = Math.max(o[0], Math.min(o[1], m.k * Math.pow(2, i.apply(this, arguments)))),
      b = tt(l);
    if (p.wheel)
      ((p.mouse[0][0] !== b[0] || p.mouse[0][1] !== b[1]) &&
        (p.mouse[1] = m.invert((p.mouse[0] = b))),
        clearTimeout(p.wheel));
    else {
      if (m.k === w) return;
      ((p.mouse = [b, m.invert(b)]), xt(this), p.start());
    }
    (ht(l),
      (p.wheel = setTimeout(k, x)),
      p.zoom('mouse', e(P(M(m, w), p.mouse[0], p.mouse[1]), p.extent, s)));
    function k() {
      ((p.wheel = null), p.end());
    }
  }
  function F(l, ...d) {
    if (_ || !t.apply(this, arguments)) return;
    var p = l.currentTarget,
      m = z(this, d, !0).event(l),
      w = nt(l.view).on('mousemove.zoom', O, !0).on('mouseup.zoom', W, !0),
      b = tt(l, p),
      k = l.clientX,
      A = l.clientY;
    (mn(l.view), qt(l), (m.mouse = [b, this.__zoom.invert(b)]), xt(this), m.start());
    function O(Y) {
      if ((ht(Y), !m.moved)) {
        var G = Y.clientX - k,
          Q = Y.clientY - A;
        m.moved = G * G + Q * Q > N;
      }
      m.event(Y).zoom(
        'mouse',
        e(P(m.that.__zoom, (m.mouse[0] = tt(Y, p)), m.mouse[1]), m.extent, s)
      );
    }
    function W(Y) {
      (w.on('mousemove.zoom mouseup.zoom', null), wn(Y.view, m.moved), ht(Y), m.event(Y).end());
    }
  }
  function I(l, ...d) {
    if (t.apply(this, arguments)) {
      var p = this.__zoom,
        m = tt(l.changedTouches ? l.changedTouches[0] : l, this),
        w = p.invert(m),
        b = p.k * (l.shiftKey ? 0.5 : 2),
        k = e(P(M(p, b), m, w), n.apply(this, d), s);
      (ht(l),
        a > 0
          ? nt(this).transition().duration(a).call(E, k, m, l)
          : nt(this).call(y.transform, k, m, l));
    }
  }
  function D(l, ...d) {
    if (t.apply(this, arguments)) {
      var p = l.touches,
        m = p.length,
        w = z(this, d, l.changedTouches.length === m).event(l),
        b,
        k,
        A,
        O;
      for (qt(l), k = 0; k < m; ++k)
        ((A = p[k]),
          (O = tt(A, this)),
          (O = [O, this.__zoom.invert(O), A.identifier]),
          w.touch0
            ? !w.touch1 && w.touch0[2] !== O[2] && ((w.touch1 = O), (w.taps = 0))
            : ((w.touch0 = O), (b = !0), (w.taps = 1 + !!f)));
      (f && (f = clearTimeout(f)),
        b &&
          (w.taps < 2 &&
            ((c = O[0]),
            (f = setTimeout(function () {
              f = null;
            }, v))),
          xt(this),
          w.start()));
    }
  }
  function R(l, ...d) {
    if (this.__zooming) {
      var p = z(this, d).event(l),
        m = l.changedTouches,
        w = m.length,
        b,
        k,
        A,
        O;
      for (ht(l), b = 0; b < w; ++b)
        ((k = m[b]),
          (A = tt(k, this)),
          p.touch0 && p.touch0[2] === k.identifier
            ? (p.touch0[0] = A)
            : p.touch1 && p.touch1[2] === k.identifier && (p.touch1[0] = A));
      if (((k = p.that.__zoom), p.touch1)) {
        var W = p.touch0[0],
          Y = p.touch0[1],
          G = p.touch1[0],
          Q = p.touch1[1],
          U = (U = G[0] - W[0]) * U + (U = G[1] - W[1]) * U,
          J = (J = Q[0] - Y[0]) * J + (J = Q[1] - Y[1]) * J;
        ((k = M(k, Math.sqrt(U / J))),
          (A = [(W[0] + G[0]) / 2, (W[1] + G[1]) / 2]),
          (O = [(Y[0] + Q[0]) / 2, (Y[1] + Q[1]) / 2]));
      } else if (p.touch0) ((A = p.touch0[0]), (O = p.touch0[1]));
      else return;
      p.zoom('touch', e(P(k, A, O), p.extent, s));
    }
  }
  function B(l, ...d) {
    if (this.__zooming) {
      var p = z(this, d).event(l),
        m = l.changedTouches,
        w = m.length,
        b,
        k;
      for (
        qt(l),
          _ && clearTimeout(_),
          _ = setTimeout(function () {
            _ = null;
          }, v),
          b = 0;
        b < w;
        ++b
      )
        ((k = m[b]),
          p.touch0 && p.touch0[2] === k.identifier
            ? delete p.touch0
            : p.touch1 && p.touch1[2] === k.identifier && delete p.touch1);
      if ((p.touch1 && !p.touch0 && ((p.touch0 = p.touch1), delete p.touch1), p.touch0))
        p.touch0[1] = this.__zoom.invert(p.touch0[0]);
      else if (
        (p.end(), p.taps === 2 && ((k = tt(k, this)), Math.hypot(c[0] - k[0], c[1] - k[1]) < T))
      ) {
        var A = nt(this).on('dblclick.zoom');
        A && A.apply(this, arguments);
      }
    }
  }
  return (
    (y.wheelDelta = function (l) {
      return arguments.length ? ((i = typeof l == 'function' ? l : yt(+l)), y) : i;
    }),
    (y.filter = function (l) {
      return arguments.length ? ((t = typeof l == 'function' ? l : yt(!!l)), y) : t;
    }),
    (y.touchable = function (l) {
      return arguments.length ? ((r = typeof l == 'function' ? l : yt(!!l)), y) : r;
    }),
    (y.extent = function (l) {
      return arguments.length
        ? ((n =
            typeof l == 'function'
              ? l
              : yt([
                  [+l[0][0], +l[0][1]],
                  [+l[1][0], +l[1][1]],
                ])),
          y)
        : n;
    }),
    (y.scaleExtent = function (l) {
      return arguments.length ? ((o[0] = +l[0]), (o[1] = +l[1]), y) : [o[0], o[1]];
    }),
    (y.translateExtent = function (l) {
      return arguments.length
        ? ((s[0][0] = +l[0][0]),
          (s[1][0] = +l[1][0]),
          (s[0][1] = +l[0][1]),
          (s[1][1] = +l[1][1]),
          y)
        : [
            [s[0][0], s[0][1]],
            [s[1][0], s[1][1]],
          ];
    }),
    (y.constrain = function (l) {
      return arguments.length ? ((e = l), y) : e;
    }),
    (y.duration = function (l) {
      return arguments.length ? ((a = +l), y) : a;
    }),
    (y.interpolate = function (l) {
      return arguments.length ? ((h = l), y) : h;
    }),
    (y.on = function () {
      var l = u.on.apply(u, arguments);
      return l === u ? y : l;
    }),
    (y.clickDistance = function (l) {
      return arguments.length ? ((N = (l = +l) * l), y) : Math.sqrt(N);
    }),
    (y.tapDistance = function (l) {
      return arguments.length ? ((T = +l), y) : T;
    }),
    y
  );
}
export {
  wr as A,
  mr as B,
  Cn as C,
  dr as D,
  ur as E,
  sr as F,
  gr as G,
  yr as H,
  vr as I,
  pr as S,
  ir as a,
  Zi as b,
  rr as c,
  Mt as d,
  fr as e,
  cr as f,
  lr as g,
  hr as h,
  ar as i,
  Bi as j,
  Nr as k,
  vn as l,
  gt as m,
  Ar as n,
  zr as o,
  Er as p,
  $n as q,
  or as r,
  _r as s,
  bn as t,
  qi as u,
  br as v,
  kr as w,
  Tr as x,
  xr as y,
  Sr as z,
};
//# sourceMappingURL=d3-UADnCcqQ.js.map

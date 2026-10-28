# Engine of bpm_trajectory.bob, attached to plot_x.
# pvs[0] periodic tick, pvs[1] zone, pvs[2] mode, pvs[3] averages, pvs[4] SUM threshold,
# pvs[5] command (1 reset average, 2 clear reference, 3 reload yaml, 4 reference from mean)
from org.csstudio.display.builder.runtime.script import ScriptUtil, PVUtil
from org.csstudio.display.builder.model.properties import WidgetColor
from org.phoebus.pv import PVPool
from org.phoebus.core.vtypes import VTypeHelper
from org.epics.vtype import Alarm, AlarmSeverity
from java.util import Date
from java.text import SimpleDateFormat
from jarray import array
from collections import deque
import math

import bpmutil

NAN = float("nan")
HISTORY = 300

st = bpmutil.state(widget)
bpmutil.set_suffix(widget, pvs[1], "bpm_zone")
zone = PVUtil.getString(pvs[1]) or "ALL"
mode = PVUtil.getString(pvs[2])
navg = max(1, int(PVUtil.getDouble(pvs[3])))
sumthr = PVUtil.getDouble(pvs[4])
cmd = int(PVUtil.getDouble(pvs[5]))
diffmode = mode.startswith("Diff")


def locpv(base):
    cache = st.setdefault("loc", {})
    pv = cache.get(base)
    if pv is None:
        pv = PVPool.getPV(bpmutil.locname(widget, base))
        cache[base] = pv
    return pv


def write(base, values):
    if isinstance(values, basestring):
        locpv(base).write(values)
    else:
        locpv(base).write(array(values, 'd'))


def release_pvs():
    for b in st.get("bpms", []):
        for key in ("pvx", "pvy", "pvsum"):
            if b.get(key) is not None:
                PVPool.releasePV(b[key])
                b[key] = None


def read(pv):
    if pv is None:
        return None
    v = pv.read()
    if v is None:
        return None
    sev = Alarm.alarmOf(v).getSeverity()
    if sev == AlarmSeverity.INVALID or sev == AlarmSeverity.UNDEFINED:
        return None
    d = VTypeHelper.toDouble(v)
    if math.isnan(d):
        return None
    return d


def stats(samples):
    n = len(samples)
    if n == 0:
        return NAN, NAN
    mean = sum(samples) / n
    return mean, math.sqrt(sum((s - mean) ** 2 for s in samples) / n)


def rms(values):
    good = [v for v in values if not math.isnan(v)]
    if not good:
        return NAN
    return math.sqrt(sum(v * v for v in good) / len(good))


def fmt(v, f="%.3f"):
    return "" if v is None or math.isnan(v) else f % v


if cmd == 3 or "all" not in st:
    release_pvs()
    st["all"] = bpmutil.load_bpms(widget, bpmutil.macro(widget, "CONFFILE", "values.yaml"),
                                  float(bpmutil.macro(widget, "SCALE", "1e-6")),
                                  bpmutil.macro(widget, "SORT", "geo"))
    st["zone"] = None
    bpmutil.log("loaded %d BPMs" % len(st["all"]))
    combo = ScriptUtil.findWidgetByName(widget, "zone_combo")
    if combo is not None:
        try:
            combo.setPropertyValue("items", bpmutil.zones_of(st["all"]))
        except Exception as e:
            bpmutil.log("cannot set zone items: " + str(e))

if st.get("zone") != zone:
    release_pvs()
    bpms = [dict(b) for b in bpmutil.filter_zone(st["all"], zone)]
    for b in bpms:
        b["pvx"] = PVPool.getPV(b["x"])
        b["pvy"] = PVPool.getPV(b["y"])
        b["pvsum"] = PVPool.getPV(b["sum"]) if b["sum"] else None
    st["bpms"] = bpms
    st["zone"] = zone
    st["navg"] = None
    st["rmshist"] = deque(maxlen=HISTORY)
    use_s = len(bpms) > 0 and all(b["s"] is not None for b in bpms)
    st["coord"] = [b["s"] if use_s else float(i + 1) for i, b in enumerate(bpms)]
    lo = min(st["coord"]) if bpms else 0.0
    hi = max(st["coord"]) if bpms else 1.0
    margin = 0.05 * (hi - lo) if use_s else 0.5
    for name in ("plot_x", "plot_y"):
        plot = ScriptUtil.findWidgetByName(widget, name)
        if plot is not None:
            plot.setPropertyValue("x_axis.title", "s (m)" if use_s else "BPM index")
            plot.setPropertyValue("x_axis.minimum", lo - margin)
            plot.setPropertyValue("x_axis.maximum", hi + margin)

bpms = st["bpms"]

if cmd == 1 or st.get("navg") != navg:
    st["buf"] = [deque(maxlen=navg) for _ in bpms]
    st["navg"] = navg
    st["rmshist"].clear()
if cmd == 2:
    st["ref"] = None
    write("bpm_ref_name", "none")
    st["rmshist"].clear()
if cmd == 4 and st.get("mean"):
    st["ref"] = dict((b["name"], (mx, my)) for b, mx, my in zip(bpms, st["mean"][0], st["mean"][1])
                     if not math.isnan(mx) and not math.isnan(my))
    write("bpm_ref_name", "mean @ " + SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(Date()))
    st["rmshist"].clear()
if cmd != 0:
    pvs[5].write(0)

ref = st.get("ref") or {}
live_x, live_y, sums, valid = [], [], [], []
mean_x, mean_y, std_x, std_y = [], [], [], []
ref_x, ref_y = [], []
for i, b in enumerate(bpms):
    x = read(b["pvx"])
    y = read(b["pvy"])
    s = read(b["pvsum"])
    ok = x is not None and y is not None and (sumthr <= 0 or (s is not None and s >= sumthr))
    valid.append(ok)
    sums.append(NAN if s is None else s)
    if ok:
        x *= b["scale"]
        y *= b["scale"]
        st["buf"][i].append((x, y))
    live_x.append(x if ok else NAN)
    live_y.append(y if ok else NAN)
    mx, sx = stats([p[0] for p in st["buf"][i]])
    my, sy = stats([p[1] for p in st["buf"][i]])
    mean_x.append(mx)
    mean_y.append(my)
    std_x.append(sx)
    std_y.append(sy)
    r = ref.get(b["name"])
    ref_x.append(r[0] if r else NAN)
    ref_y.append(r[1] if r else NAN)
st["mean"] = (mean_x, mean_y, std_x, std_y, sums)

# deviation from the reference (or from the axis when no reference is loaded)
has_ref = len(ref) > 0
dev_x = [m - r for m, r in zip(mean_x, ref_x)] if has_ref else mean_x
dev_y = [m - r for m, r in zip(mean_y, ref_y)] if has_ref else mean_y

if diffmode and has_ref:
    plot_live_x = [v - r for v, r in zip(live_x, ref_x)]
    plot_live_y = [v - r for v, r in zip(live_y, ref_y)]
    plot_mean_x, plot_mean_y = dev_x, dev_y
    plot_ref_x = [0.0 if not math.isnan(r) else NAN for r in ref_x]
    plot_ref_y = [0.0 if not math.isnan(r) else NAN for r in ref_y]
else:
    plot_live_x, plot_live_y = live_x, live_y
    plot_mean_x, plot_mean_y = mean_x, mean_y
    plot_ref_x, plot_ref_y = ref_x, ref_y

coord = st["coord"]
if not coord:
    coord = [0.0]
    empty = [NAN]
    plot_live_x = plot_live_y = plot_mean_x = plot_mean_y = plot_ref_x = plot_ref_y = std_x = std_y = empty

write("bpm_coord", coord)
write("bpm_x", plot_live_x)
write("bpm_y", plot_live_y)
write("bpm_xavg", plot_mean_x)
write("bpm_yavg", plot_mean_y)
write("bpm_xstd", std_x)
write("bpm_ystd", std_y)
write("bpm_xref", plot_ref_x)
write("bpm_yref", plot_ref_y)

rx, ry = rms(dev_x), rms(dev_y)
if not math.isnan(rx) and not math.isnan(ry):
    st["rmshist"].append((rx, ry))
hist = list(st["rmshist"]) or [(NAN, NAN)]
write("bpm_hist_t", [float(i - len(hist) + 1) for i in range(len(hist))])
write("bpm_hist_x", [h[0] for h in hist])
write("bpm_hist_y", [h[1] for h in hist])
write("bpm_rms_x", fmt(rx))
write("bpm_rms_y", fmt(ry))
write("bpm_rms_label", "RMS vs reference (mm)" if has_ref else "RMS vs axis (mm)")
write("bpm_valid", "%d / %d" % (valid.count(True), len(bpms)))

table = ScriptUtil.findWidgetByName(widget, "bpm_table")
if table is not None:
    rows = []
    for i, b in enumerate(bpms):
        rows.append(["%d %s" % (i + 1, b["name"]), fmt(live_x[i]), fmt(live_y[i]), fmt(sums[i], "%.4g"),
                     fmt(mean_x[i]), fmt(mean_y[i]), fmt(std_x[i]), fmt(std_y[i]),
                     fmt(dev_x[i]) if has_ref else "", fmt(dev_y[i]) if has_ref else ""])
    table.setValue(rows)
    try:
        bad = WidgetColor(255, 180, 180)
        good = WidgetColor(255, 255, 255)
        for i in range(len(bpms)):
            table.setCellColor(i, 0, good if valid[i] else bad)
    except Exception:
        pass

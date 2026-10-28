"""Helpers for bpm_trajectory.bob: BPM discovery from the beamline values*.yaml
and per-display state shared between the engine, save and load scripts.

BPMs are discovered from epicsConfiguration.iocs:
  - template libera-sppp : one BPM per ioc, PVs <iocprefix>:{X,Y,SUM}
                           name = 'bpm' key or last field of iocprefix
  - template libera-spe  : one BPM per device, PVs <iocprefix>:<name>:spe.{x,y,sum} (bunch 0)
  - any ioc/device with devtype 'bpm' and explicit pvx/pvy[/pvsum] keys
    ($(P) and $(R) are replaced by iocprefix and device name)
Optional keys (ioc or device): bpm_scale (raw unit -> mm, default SCALE macro),
s (longitudinal position in m, used as x coordinate when all BPMs have it),
geo (ordering), zones, disable.
"""
from org.csstudio.display.builder.runtime.script import ScriptUtil
import sys
import os

STATE_KEY = "unibpm.trajectory"

DEFAULT_PVS = {
    'libera-sppp': ("$(P):X", "$(P):Y", "$(P):SUM"),
    'libera-spe': ("$(P):$(R):spe.x", "$(P):$(R):spe.y", "$(P):$(R):spe.sum"),
}


def _epik8sutil(widget):
    display_model = widget.getDisplayModel()
    display_path = os.path.dirname(display_model.getUserData(display_model.USER_DATA_INPUT_FILE))
    scripts_path = os.path.abspath(display_path + "/../Scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    import epik8sutil
    return epik8sutil


def find_conf(widget, conffile):
    """Resolve CONFFILE relative to the display, walking up like epik8sutil.conf_to_dev"""
    display_model = widget.getDisplayModel()
    display_path = os.path.dirname(display_model.getUserData(display_model.USER_DATA_INPUT_FILE))
    if os.path.isabs(conffile):
        return conffile
    confpath = display_path + "/" + conffile
    search_dir = display_path
    for _ in range(5):
        if os.path.exists(confpath):
            break
        search_dir = os.path.dirname(search_dir)
        if not search_dir:
            break
        confpath = search_dir + "/" + conffile
    return confpath


def _as_list(zones):
    if zones is None:
        return ["ALL"]
    if isinstance(zones, basestring):
        return [zones]
    return [str(z) for z in zones]


def _num(value):
    try:
        return float(value)
    except Exception:
        return None


def _expand(pattern, prefix, name):
    return pattern.replace("$(P)", prefix).replace("$(R)", name)


def load_bpms(widget, conffile, default_scale, sort="geo"):
    """Return the list of BPM dicts {name, x, y, sum, scale, s, geo, zones, ioc}"""
    util = _epik8sutil(widget)
    iocs = util.conf_to_iocs(find_conf(widget, conffile), widget)
    bpms = []
    for ioc in iocs or []:
        if str(ioc.get("disable", False)).lower() == "true":
            continue
        tmpl = ioc.get("template", "") or ""
        prefix = ioc.get("iocprefix", "") or ""
        devtype = ioc.get("devtype", "") or ""
        ioc_zones = _as_list(ioc.get("zones", "ALL"))
        ioc_scale = _num(ioc.get("bpm_scale")) or default_scale
        pvs = DEFAULT_PVS.get(tmpl)
        has_explicit = ioc.get("pvx") is not None
        if pvs is None and not has_explicit and devtype != "bpm":
            continue

        devices = ioc.get("devices") or []
        if tmpl == "libera-sppp" or not devices:
            devices = [{"name": ioc.get("bpm") or prefix.split(":")[-1]}]
            single = True
        else:
            single = False

        for dev in devices:
            name = dev.get("name")
            if not name:
                continue
            pvx = dev.get("pvx") or ioc.get("pvx") or (pvs and pvs[0])
            pvy = dev.get("pvy") or ioc.get("pvy") or (pvs and pvs[1])
            pvsum = dev.get("pvsum") or ioc.get("pvsum") or (pvs and pvs[2])
            if not pvx or not pvy:
                continue
            p = dev.get("prefix", prefix)
            zones = _as_list(dev.get("zones")) if dev.get("zones") is not None else ioc_zones
            bpms.append({
                "name": dev.get("alias", name),
                "x": _expand(pvx, p, name),
                "y": _expand(pvy, p, name),
                "sum": _expand(pvsum, p, name) if pvsum else None,
                "scale": _num(dev.get("bpm_scale")) or ioc_scale,
                "s": _num(dev.get("s", ioc.get("s") if single else None)),
                "geo": _num(dev.get("geo", ioc.get("geo") if single else None)),
                "zones": zones,
                "ioc": ioc.get("name", ""),
            })

    if sort == "name":
        bpms.sort(key=lambda b: b["name"])
    else:
        # s, then geo, then configuration order (sort is stable)
        bpms.sort(key=lambda b: (b["s"] is None and b["geo"] is None,
                                 b["s"] if b["s"] is not None else (b["geo"] or 0)))
    return bpms


def zones_of(bpms):
    zones = []
    for b in bpms:
        for z in b["zones"]:
            if z != "ALL" and z not in zones:
                zones.append(z)
    return ["ALL"] + sorted(zones)


def filter_zone(bpms, zone):
    if not zone or zone == "ALL":
        return list(bpms)
    return [b for b in bpms if zone in b["zones"] or "ALL" in b["zones"]]


def state(widget):
    """Per-display state dictionary shared by the trajectory scripts"""
    display = widget.getDisplayModel()
    st = display.getUserData(STATE_KEY)
    if st is None:
        st = {}
        display.setUserData(STATE_KEY, st)
    return st


def set_suffix(widget, pv, base):
    """Learn the display-private suffix ($(DID) as expanded by the runtime) from a
    script PV named loc://<base>$(DID); the script's own DID macro can differ from
    the one used to expand the widgets' pv names inside embedded displays."""
    name = pv.getName()
    for sep in ("(", "<"):
        if sep in name:
            name = name[:name.index(sep)]
    prefix = "loc://" + base
    if name.startswith(prefix):
        state(widget)["suffix"] = name[len(prefix):]


def locname(widget, base):
    """loc:// PV name private to this display instance"""
    suffix = state(widget).get("suffix")
    if suffix is None:
        suffix = widget.getEffectiveMacros().getValue("DID") or ""
    return "loc://" + base + suffix


def macro(widget, name, default=None):
    value = widget.getEffectiveMacros().getValue(name)
    if value is None or value == "" or value.startswith("$("):
        return default
    return value


def log(msg):
    ScriptUtil.getLogger().info("[unibpm] " + msg)

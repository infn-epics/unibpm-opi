# Load a reference trajectory for bpm_trajectory.bob; triggered by the file selector PV (pvs[0]).
# Accepts the per-BPM format written by SaveTrajectory.py and the legacy two line format
# (tab separated x values, then y values, in BPM order) written by the SPARC BPMpanel.
from org.csstudio.display.builder.runtime.script import ScriptUtil, PVUtil
from org.phoebus.pv import PVPool
import os

import bpmutil

path = PVUtil.getString(pvs[0])
st = bpmutil.state(widget)
bpmutil.set_suffix(widget, pvs[0], "bpm_loadfile")

if path and os.path.isfile(path):
    ref = {}
    try:
        with open(path, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        rows = [l.split() for l in lines if not l.startswith("#")]
        # per-BPM format: first column is a BPM name, legacy format: numbers only
        named = len(rows) > 0 and all(len(r) >= 3 for r in rows)
        try:
            float(rows[0][0])
            named = False
        except Exception:
            pass
        if named:
            for r in rows:
                ref[r[0]] = (float(r[1]), float(r[2]))
        elif len(rows) >= 2:
            names = [b["name"] for b in st.get("bpms", [])]
            for name, x, y in zip(names, rows[0], rows[1]):
                ref[name] = (float(x), float(y))
    except Exception as e:
        ScriptUtil.showMessageDialog(widget, "Error reading \"" + path + "\": " + str(e))
        ref = {}
    if ref:
        st["ref"] = ref
        if st.get("rmshist") is not None:
            st["rmshist"].clear()
        pv = PVPool.getPV(bpmutil.locname(widget, "bpm_ref_name"))
        pv.write(os.path.basename(path))
        PVPool.releasePV(pv)
        bpmutil.log("reference loaded from %s (%d BPMs)" % (path, len(ref)))

# Save the averaged trajectory of bpm_trajectory.bob to <DATADIR>/yyyy_MM_dd/Orbit/orbit_HHhMMmSSs.txt
# One row per BPM, so that it can be loaded back as reference even if the BPM list changes.
from org.csstudio.display.builder.runtime.script import ScriptUtil, PVUtil
from org.phoebus.pv import PVPool
from java.util import Date
from java.text import SimpleDateFormat
import os

import bpmutil

st = bpmutil.state(widget)
bpms = st.get("bpms")
data = st.get("mean")
if not bpms or not data:
    ScriptUtil.showMessageDialog(widget, "No trajectory acquired yet")
else:
    mean_x, mean_y, std_x, std_y, sums = data
    now = Date()
    folder = os.path.join(bpmutil.macro(widget, "DATADIR", "/nfs/data"),
                          SimpleDateFormat("yyyy_MM_dd").format(now), "Orbit")
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = os.path.join(folder, "orbit_" + SimpleDateFormat("HH'h'_mm'm'_ss's'").format(now) + ".txt")
    with open(filename, "w") as f:
        f.write("# BPM trajectory %s zone=%s averages=%s\n" % (
            SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(now), st.get("zone"), st.get("navg")))
        f.write("# name\tx_mm\ty_mm\tsx_mm\tsy_mm\tsum\n")
        for i, b in enumerate(bpms):
            f.write("%s\t%r\t%r\t%r\t%r\t%r\n" % (b["name"], mean_x[i], mean_y[i], std_x[i], std_y[i], sums[i]))
    pv = PVPool.getPV(bpmutil.locname(widget, "bpm_saved"))
    pv.write(filename)
    PVPool.releasePV(pv)
    bpmutil.log("trajectory saved to " + filename)

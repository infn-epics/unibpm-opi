# Display script of bpm_list.bob: one bpm_row.bob per BPM found in CONFFILE (see bpmutil.py).
# Positions are shown in mm (raw value * bpm_scale), per-bunch arrays use element 0.
from org.csstudio.display.builder.runtime.script import ScriptUtil
from org.csstudio.display.builder.model import WidgetFactory

import bpmutil


def formula(pv, scale, is_array):
    value = "elementAt(`%s`, 0)" % pv if is_array else "`%s`" % pv
    return "=%s*%s" % (value, ("%.12f" % scale).rstrip("0"))


def raw(pv, is_array):
    return "=elementAt(`%s`, 0)" % pv if is_array else pv


wtemplate = ScriptUtil.findWidgetByName(widget, "element_template")
row_w = wtemplate.getPropertyValue("width")
row_h = wtemplate.getPropertyValue("height")
y0 = wtemplate.getPropertyValue("y")

bpms = bpmutil.load_bpms(widget, bpmutil.macro(widget, "CONFFILE", "values.yaml"),
                         float(bpmutil.macro(widget, "SCALE", "1e-6")),
                         bpmutil.macro(widget, "SORT", "geo"))
bpms = bpmutil.filter_zone(bpms, bpmutil.macro(widget, "ZONE", "ALL"))

children = widget.runtimeChildren()
for child in list(children.getValue()):
    if child.getPropertyValue("name").startswith("Instance_bpm"):
        children.removeChild(child)

for i, b in enumerate(bpms):
    row = WidgetFactory.getInstance().getWidgetDescriptor("embedded").createWidget()
    row.setPropertyValue("name", "Instance_bpm%d" % i)
    row.setPropertyValue("file", wtemplate.getPropertyValue("file"))
    row.setPropertyValue("x", wtemplate.getPropertyValue("x"))
    row.setPropertyValue("y", y0 + i * row_h)
    row.setPropertyValue("width", row_w)
    row.setPropertyValue("height", row_h)
    macros = row.getPropertyValue("macros")
    macros.add("NAME", b["name"])
    macros.add("IOC", b["ioc"])
    macros.add("PVX", formula(b["x"], b["scale"], b["array"]))
    macros.add("PVY", formula(b["y"], b["scale"], b["array"]))
    macros.add("PVSUM", raw(b["sum"], b["array"]) if b["sum"] else "")
    macros.add("PVST", b["status"] or "")
    macros.add("S", "" if b["s"] is None else "%.2f" % b["s"])
    # device specific panel from the yaml 'opi' key, opened by the name button with these macros
    for k, v in b["macros"].items():
        macros.add(k, v)
    macros.add("OPI", b["opi"] or "")
    macros.add("OPI_ENABLED", "true" if b["opi"] else "false")
    children.addChild(row)

bpmutil.log("bpm_list: %d BPMs" % len(bpms))

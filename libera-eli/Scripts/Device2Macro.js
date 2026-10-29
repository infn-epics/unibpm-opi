importPackage(Packages.org.csstudio.opibuilder.scriptUtil);

var macroInput = DataUtil.createMacrosInput(true);
var pv0 = PVUtil.getString(pvArray[0]);
var pv1 = PVUtil.getString(pvArray[1]);
var device_macro = widget.getMacroValue("DEVICE");
var bpm_macro = widget.getMacroValue("BPM");

/* Don't display "0.0" in Device header when OPI first opens */
if (pv0 == 0.0) {
    if (device_macro != null) {
        pv0 = device_macro;
    } else {
        pv0 = "";
    }
}

/* Don't display "0.0" in Device header when OPI first opens */
if (pv1 == 0.0) {
    if (device_macro != null) {
        pv1 = device_macro;
    } else {
        pv1 = "";
    }
}

macroInput.put("DEVICE", pv0);
macroInput.put("BPM", pv1);
widgetController.setPropertyValue("macros", macroInput);

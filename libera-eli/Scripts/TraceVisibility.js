importPackage(Packages.org.csstudio.opibuilder.scriptUtil);

var trace0 = Boolean( Number( PVUtil.getLong(pvArray[0]) ) );
var trace1 = Boolean( Number( PVUtil.getLong(pvArray[1]) ) );
var trace2 = Boolean( Number( PVUtil.getLong(pvArray[2]) ) );
var trace3 = Boolean( Number( PVUtil.getLong(pvArray[3]) ) );
var trace4 = Boolean( Number( PVUtil.getLong(pvArray[4]) ) );
var trace5 = Boolean( Number( PVUtil.getLong(pvArray[5]) ) );
var trace6 = Boolean( Number( PVUtil.getLong(pvArray[6]) ) );
var trace7 = Boolean( Number( PVUtil.getLong(pvArray[7]) ) );

widget.setPropertyValue("trace_0_visible", trace0);
widget.setPropertyValue("trace_1_visible", trace1);
widget.setPropertyValue("trace_2_visible", trace2);
widget.setPropertyValue("trace_3_visible", trace3);
widget.setPropertyValue("trace_4_visible", trace4);
widget.setPropertyValue("trace_5_visible", trace5);
widget.setPropertyValue("trace_6_visible", trace6);
widget.setPropertyValue("trace_7_visible", trace7);
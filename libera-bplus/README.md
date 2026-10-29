# libera-bplus

Phoebus panels for **Libera Brilliance+** eBPM units running the IOC from the
`libera-bplus` template (epics-support-template-infn). Converted with the Phoebus
`Converter` from the vendor CSS BOY GUI
(`epik8-sparc/opi/diag/libera-bpm-opi/GUI/LiberaBrilliancePlus/CSS`, I-Tech 2019).

Entry point: `main.bob`. Macros (as passed by `bpm_row.bob` / `bpmutil.py`):

| macro          | meaning                                           |
|----------------|---------------------------------------------------|
| `P`            | ioc `iocprefix`                                   |
| `BPM1`..`BPM4` | device names of the ioc (one `raf` board each)    |
| `BPM`          | set by `main.bob` when opening a BPM panel        |

Changes from the vendor panels:

- `$(DEVICE)` -> `$(P)` (`DEVICE` is `P:name` in unibpm), hardcoded `bpm1..4` -> `$(BPM1..4)`
- `*.opi` links -> `*.bob`
- `_mon` / `_sp` suffixes dropped: this IOC exposes one bidirectional `libera`
  record per MCI node

PVs not provided by the current IOC (shown disconnected):
`$(BPM):conf:adc_offset:{A..D}` (coeff_off.bob) and `sensors:temp` on BPM/timing
boards (temperatures are in the `*_sensors.db` `ID_n` records).

To use it from bpm_list, set on the ioc in values.yaml:

```yaml
opi: libera-bplus/main.bob
```

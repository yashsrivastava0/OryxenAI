# Azure VM cost automation — auto-shutdown / auto-start

Read this before assuming the VM is down due to a fault, before touching
`oryxenai-vm-autostart`, and before changing the shutdown window. See D-112
in `DECISIONS.md` for the decision record; this file is the operational
detail underneath it.

## Current schedule

| Time (IST, UTC+05:30) | Action | Mechanism |
| --- | --- | --- |
| 01:00 daily | VM auto-shutdown (deallocate) | Azure Portal built-in Auto-shutdown, free, no extra resource |
| 07:00 daily | VM auto-start | Logic App `oryxenai-vm-autostart` (Consumption plan) |

**The VM is expected to be unreachable roughly 01:00–07:00 IST every day.**
This is intentional, not a bug — see "Why this window" below before changing
it or reporting it as an incident.

## Why this window (summary of D-112)

The VM (`Standard_B2as_v2`, ~$0.0492/hr, ~$35.92/month if run 24/7) is a
personal/resume portfolio project on a finite Azure for Students credit.
Running it around the clock is the single biggest addressable cost lever
available without touching VM size or storage.

The complication: this project's audience (recruiters in the US and EU) is
not on IST business hours. Mapped to IST, EU (9am–6pm CET), US East
(9am–6pm ET), and US West (9am–6pm PT) business hours together cover
roughly IST 12:30pm through the *entire* following night up to ~6:30am —
i.e. almost exactly when a naive "shut down overnight while I sleep"
schedule would want to run. There is no window that is both "IST
night/sleep hours" and "zero recruiter-hours overlap" — it's a real
trade-off, not something a smarter schedule avoids.

01:00–07:00 IST was chosen as the balance: deep enough into IST night to
meaningfully reduce cost (~27% of the compute line item) and roughly match
sleep hours, short enough that it only grazes the tail end of US-West
evening browsing rather than cutting into EU or US-East prime time.

**Cost-model caveat:** deallocating the VM only stops the **compute**
billing meter. The OS disk and the static public IP keep billing 24/7
regardless of VM power state — don't expect the total bill to drop by the
same ~27% the compute line item does.

## Initial state (before this automation existed)

- Subscription: `Azure for Students` (ID `55a5df59-3e8f-4276-a049-c2c0dce15eff`)
- Resource group: `oryxenai-demo-rg`
- VM: `oryxenai-demo-vm`, Central India, `Standard_B2as_v2`, Ubuntu 24.04
- VM was running 24/7, live at `https://app.oryxenai.me`, no shutdown/start
  schedule configured.
- No VM resizing, disk, networking, NSG, or application changes were made
  as part of this work — scope was strictly the power schedule.

## Cost snapshot at time of setup (2026-09-22, for reference only — re-check live)

- September 2026 actual spend: ₹616.20; forecast: ₹834.76 (~₹28.01/day avg).
- Cost by service: Storage ₹287.90, Virtual Network ₹192.42, Virtual
  Machines ₹135.86, Bandwidth ₹0.03, Network Watcher ₹0.00.
- Azure Credits: ₹8,938.35 remaining of ₹9,554.63 original (Azure for
  Students), effective 2026-09-05, expires 2027-09-05.
- No explicit "burn rate" field or spending-limit indicator was exposed by
  the portal at the time.

## Auto-shutdown configuration (Part 2)

Portal → VM `oryxenai-demo-vm` → Operations → **Auto-shutdown**:

- Auto-shutdown: On
- Shutdown time: 01:00
- Time zone: `(UTC+05:30) Chennai, Kolkata, Mumbai, New Delhi`
- Notification: Enabled, email `yashsrivastavaclass11@bbdec.ac.in`, webhook
  blank
- **Known portal limitation:** the Auto-shutdown blade does not expose a
  configurable "minutes before shutdown" field for the notification lead
  time — Azure's default lead time applies; it could not be independently
  set or confirmed through the UI.

## Auto-start Logic App (Part 3)

Resource: `oryxenai-vm-autostart`, Consumption plan, `oryxenai-demo-rg`,
Central India.

- System-assigned managed identity: enabled.
- IAM role assignment: `Virtual Machine Contributor`, scoped to
  `oryxenai-demo-vm`, granted to the Logic App's managed identity. Confirmed
  present in the VM's Access control (IAM) role assignments list.

### Trigger

- Recurrence, every 1 day, time zone `India Standard Time`, at 07:00
  (`hours: 7, minutes: 0`).
- **Gotcha:** the ARM `startTime` value must be given *without* a `+05:30`
  UTC-offset suffix when `timeZone` is explicitly set to `India Standard
  Time` — a first submission with the offset suffix included was rejected;
  the corrected submission (offset omitted) succeeded.

### Action — why it's a raw ARM HTTP call, not the native "Start virtual machine" connector action

The original design used the Azure VM connector's **Start virtual machine**
action with managed-identity auth. In the Portal Designer this repeatedly
failed to persist:

- The connector's API connection (`new_conn_cf642`) showed as connected in
  the designer but never appeared in the API Connections blade.
- Designer Save returned a generic "Failed to fetch" error, and the
  workflow disappeared entirely on reload.
- A fallback OAuth connection using the signed-in Azure account also timed
  out and did not persist.

**Workaround used:** the workflow was instead written directly via an ARM
REST update through Azure Cloud Shell. The resulting action is functionally
equivalent to "Start virtual machine," but implemented as a raw HTTP action:

- Method: `POST`
- Endpoint: the Azure Compute `start` action API for `oryxenai-demo-vm`
- API version: `2019-12-01`
- Auth: the Logic App's system-assigned managed identity,
  audience `https://management.azure.com/`

If you ever need to edit this Logic App: **expect the same connector
persistence bug** if you try to rebuild it with the native "Start virtual
machine" connector action in the Designer. Prefer editing the existing ARM
HTTP action (or resubmitting via ARM/Cloud Shell) over re-attempting the
connector, unless you've confirmed Microsoft has fixed the underlying
Portal bug.

### Manual test (confirmed working)

- Run ID `08584115066248759355070163555CU21`, triggered manually from the
  Designer's Run menu.
- Result: Succeeded, duration 15.76s.
- VM status after run: Running, size unchanged (`Standard_B2as_v2`).

This confirms: the Logic App is enabled, the recurrence definition is
valid, the managed identity authenticates to ARM successfully, and its
permission is sufficient to start the VM.

## Changing the schedule later

- To change the shutdown time: VM → Operations → Auto-shutdown → edit time
  → Save.
- To change the start time: open `oryxenai-vm-autostart`'s workflow
  definition (Designer or ARM) and edit the Recurrence trigger's
  `hours`/`minutes`. Remember the offset-suffix gotcha above if editing via
  ARM/Cloud Shell with `timeZone` explicitly set.
- If widening the window for more savings: re-read "Why this window" above
  first — a wider window trades directly against recruiter-hours coverage,
  not just against sleep hours.

## Resources intentionally left unchanged

VM size, OS disk, data disks, disk type, virtual network, subnet, public
IP, NSG rules, Docker Compose configuration, OryxenAI application code,
Caddy configuration, DNS/TLS configuration.

## Reverting this automation completely

This is fully reversible in two portal steps, with zero effect on the VM
itself, the running application, or anything else in this list — the VM
just goes back to running 24/7 with no schedule, exactly as it was before
this change:

1. VM `oryxenai-demo-vm` → Operations → Auto-shutdown → toggle **Off** →
   Save.
2. Delete (or just Disable, to keep it around for reference) the Logic App
   `oryxenai-vm-autostart`.

No VM restart, redeploy, or application change is needed either way — the
VM's own state (Docker containers, data, disks) is completely unaffected by
either enabling or reverting this schedule. The documentation changes in
this same commit (`DECISIONS.md` D-112, this file, the cross-links) are a
normal git revert of the commit(s) on `staging` if you want those undone
too, independent of the Azure-side revert above.

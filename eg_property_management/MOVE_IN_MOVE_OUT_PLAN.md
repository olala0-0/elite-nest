# Move-In / Move-Out / Inspection — Implementation Plan

Status: **Design only — no code changed yet.** This document is the plan to review before anything is built.

**Decisions locked in (2026-08-06):**
- Multi-company split → **separate follow-up project**, not part of this feature.
- State machine → **Option A** (old Terminate/Expire buttons untouched; guided Move-Out is additive and calls them at its final step).
- Approver (diagram's "Ms. Gawhar") → **the Administrator/system-admin role**, not a named person. See §3.3 and §8.3.
- Checklist master list → my first-draft proposal, seeded as editable data (§3.4). Edit freely in Odoo once installed.
- `sign_pdf_editor` integration → **held for later.** v1 uses the simple Binary signature/photo upload scoped in §3.1.

Source documents read: the "Property Management Workflow" diagram (Move-In 12 steps, Move-Out 15 steps) and the "Lease Module Automated Accounting Design" deck (7 lease processes, automated Dr/Cr entries, GHD Real Estate Development LLC vs Elite Nest Properties company split, "no manual journal entries" control objective).

---

## 1. What already exists today (audit)

Checked every file in `eg_property_management` before writing this plan. Current state:

| Area | Exists today | Gap vs. client's diagram |
|---|---|---|
| Contract lifecycle | `rent.contract.state`: `draft → running → terminate / expire / cancel` (`models/rent_contract.py:157`) | No `move_in` or `move_out` sub-states at all. Terminate/expire are one bare click, no process behind them. |
| Property status | `property.detail.state`: `draft/available/on_rent/rent/sold` | `action_state_running` sets property to `rent` (occupied); `action_state_terminate`/`action_state_cancel`/`action_expire` **immediately** set it back to `on_rent` (vacant/listed) — see finding below. |
| Invoicing / payments | `action_create_invoice`, `rent.installment` (payment_type: rent/deposit/maintenance/penalty/broker_bill/utility), full reconciliation-aware paid-amount logic just fixed this session | Solid foundation — new charge types (dilapidation, shortfall rent, move-in permit fee) can reuse this exact pattern. |
| Security deposit | `deposit` (configured amount), `deposit_invoice_id`, statement shows `deposit_received` | `deposit_utilized` is **hardcoded to `0.0`** in `get_tenant_financial_statement()` (`rent_contract.py:415`) — there is no deduction concept anywhere in the code today. `balance_held` is just `deposit_received`, never reduced. |
| Refunds | `get_tenant_financial_statement()` already searches `account.move` with `move_type = 'out_refund'` and lists them as credits on the statement | This is a ready-made landing spot for "Surplus Refund" (accounting deck, Process 4) — a move-out credit note will show up on the tenant statement **with zero report changes**, once something actually creates it. |
| Renewal | `wizards/rent_contract_extend_wizard.py` | Already covers the "Tenant Decision → No → Process Renewal" branch of the Move-Out diagram. Reuse as-is. |
| Inspections | Nothing. `models/maintenance_request.py` only adds `property_id`/`ticket_id` to Odoo's generic **equipment** maintenance model — wrong shape for a room-by-room condition checklist with tenant sign-off and cost estimates. | Needs a new, purpose-built model. |
| Multi-company split | Every invoice for a contract posts to one `company_id` (`rent_contract.py:81`) | The accounting deck explicitly splits **New Lease** (Rent/Deposit → GHD Real Estate Dev., Ejari/Admin/Commission → Elite Nest Properties) and **Early Termination** (Penalty/Shortfall → GHD, Dilapidation → Elite Nest) across two legal entities *within the same lease*. Current code cannot do this. Flagged as an open decision in §8 — it's bigger than Move-In/Move-Out and affects the existing New Lease flow too. |
| Signatures | `sign_pdf_editor` module (separate, just rebuilt this session) | Not yet linked to `rent.contract`. Could attach the signed contract PDF / move-out NOC / inspection report as a Sign template in a later phase. |

**Finding worth flagging now, independent of this new feature:** `action_state_terminate` today vacates the unit (`property_id.state = 'on_rent'`, i.e. immediately re-listable) the instant someone clicks "Terminate Contract" — before any inspection, deduction, or deposit settlement happens. The new workflow must not make this worse; see §5 (state machine) for how the plan keeps the existing button working for simple cases while gating the *guided* flow behind the new process.

---

## 2. Design principles (so nothing existing breaks)

1. **Additive only.** Every new field, model, and button is new; nothing already on `rent.contract`, `account.move`, `rent.installment`, or the tenant statement is renamed, retyped, or removed.
2. **Reuse, don't reinvent.** New charges go through the *same* `rent.installment` + `account.move` pattern already used for rent/deposit/maintenance. The refund block already in `get_tenant_financial_statement()` is reused for deposit refunds instead of writing a second code path.
3. **New models, not new required fields on old ones.** Move-In and Move-Out get their own transactional models (`rent.contract.movein`, `rent.contract.moveout`, `property.inspection`) linked back to `rent.contract` by `Many2one`/`One2many`. This means the migration is "add a table," not "alter existing rows" — safe, reversible, and Odoo.sh only needs a module **Upgrade**, not a data migration script.
4. **Old buttons keep working.** `action_state_terminate` / `action_expire` / `action_state_cancel` stay exactly as they are for anyone who wants the quick manual path (test contracts, edge cases, admin override). The guided Move-Out process is a *parallel*, opt-in path that — when completed — calls the same underlying state-change methods at its final step, so there's one source of truth for "what does terminating a contract actually do."
5. **Every phase ships independently testable.** Each phase below can be built, pushed to `Test`, and verified in isolation before the next starts — matching the fetch → verify → compile → commit → push workflow already in use this session.

---

## 3. New data models

### 3.1 `property.inspection` (shared engine for both Pre-Move-In and Final/Move-Out inspection)

One model, one `inspection_type` field, used twice — avoids building two near-identical models for diagram steps "Pre-Move-In Inspection" (Move-In #2) and "Final Inspection" (Move-Out #7–10).

| Field | Type | Notes |
|---|---|---|
| `rent_contract_id` | Many2one → `rent.contract` | |
| `property_id` | Many2one → `property.detail` | Related/default from contract |
| `inspection_type` | Selection: `move_in`, `move_out` | Drives which flow it's attached to |
| `inspector_id` | Many2one → `res.users` | "FM Team" per diagram |
| `inspection_date` | Datetime | |
| `line_ids` | One2many → `property.inspection.line` | Room-by-room / item-by-item checklist |
| `state` | Selection: `draft`, `in_progress`, `report_shared`, `tenant_acknowledged`, `done` | Maps to Move-Out diagram steps 8–10 |
| `report_shared_date` / `tenant_ack_date` | Datetime | Timestamps for the audit trail the accounting deck insists on ("every transaction time-stamped") |
| `tenant_signature` | Binary (or link to a `sign.request` if we wire in `sign_pdf_editor` in a later phase) | Digital sign-off per diagram step 10 |
| `total_deduction_amount` | Monetary, computed from lines | Feeds the Move-Out deposit settlement (§4) |

`property.inspection.line`: `inspection_id`, `item` (Char or a small `property.inspection.checklist.item` master list — walls, flooring, kitchen, AC units, plumbing, fixtures…), `condition` (Selection: ok / damaged / missing), `notes`, `photo` (Binary), `estimated_cost` (Monetary, only relevant on `move_out` type).

### 3.2 `rent.contract.movein`

One record per contract, created (draft) the moment the contract itself is created — mirrors diagram steps 3–12.

| Field | Purpose (diagram step) |
|---|---|
| `rent_contract_id` | link back |
| `pre_move_in_inspection_id` | Many2one → `property.inspection` (`inspection_type='move_in'`) — step 2 |
| `contract_signed_date` | step 4 |
| `move_in_permit_issued` (Bool) + `move_in_permit_date` | step 8 |
| `welcome_email_sent` (Bool) + date | steps 7, 9 |
| `handover_date` | step 10 |
| `state` | `draft → inspection_done → contract_signed → payment_verified → handed_over → settled` |

Payment Collection/Verification (steps 5–6) are **not duplicated here** — they already exist as `action_create_invoice` + the invoice `payment_state`. The move-in record just reads/displays that state, it doesn't own it.

### 3.3 `rent.contract.moveout`

One record per contract, created when someone starts the move-out process (either via "Tenant Decision → Yes" or directly). Mirrors diagram steps 1, 3–15 (step 2, Tenant Decision, is just which button gets clicked — Renew via the existing wizard, or Move-Out via this new record).

| Field | Purpose (diagram step) |
|---|---|
| `rent_contract_id` | link back |
| `renewal_notice_date` | step 1 (90 days before expiry — can be cron-generated, see §6) |
| `process_shared_date` | step 3 |
| `utilities_clearance_ids` | One2many attachments (DEWA / Logic Utilities / Lootah Gas) — step 4 |
| `noc_issued` (Bool) + `noc_date`, `noc_document` (report/attachment) | step 5 |
| `key_handover_date` | step 6 |
| `final_inspection_id` | Many2one → `property.inspection` (`inspection_type='move_out'`) — steps 7–10 |
| `deduction_line_ids` | One2many → `rent.contract.moveout.deduction` (pulled from `final_inspection_id.line_ids` where `condition != 'ok'`, editable by Finance) — feeds step 11–14 |
| `finance_reviewed_by`, `finance_reviewed_date` | step 11 |
| `approved_by`, `approved_date` | step 12 — `action_approve_deposit_release()` is restricted to Odoo's built-in **Administrator / Settings** group (`base.group_system`), matching "Ms. Gawhar is admin, this is a mock name for who approves." No new approver field/group needed; `approved_by` just records `self.env.user` when an admin clicks Approve. |
| `deposit_release_amount` (computed: `deposit_received - total_deductions`) | step 13 |
| `deduction_transfer_done` (Bool) | step 14 |
| `state` | `draft → clearance_pending → inspection_done → finance_review → approved → settled` — step 15 = `settled`, and **only `settled` is allowed to call `action_state_terminate`/`action_expire`+free the property** |

### 3.4 Inspection checklist — first-draft master list

Proposed seed data for `property.inspection.checklist.item` (loaded once, then fully editable in Odoo — add/remove/rename items per unit type without touching code). Grouped by area, generic enough for residential units; commercial-specific items can be added later without a code change since this is just data:

| Area | Checklist items |
|---|---|
| Walls & Ceiling | Paint condition, cracks, dampness/water stains |
| Flooring | Tiles/parquet condition, scratches, grout |
| Doors & Windows | Locks & keys, glass condition, handles, screens |
| Kitchen | Cabinets, countertop, sink & mixer, exhaust hood, built-in appliances (if any) |
| Bathroom(s) | Fixtures (basin/toilet/shower), tiles, mirror, drainage, silicone sealing |
| Electrical | Switches & sockets, light fixtures, main DB panel, fan/AC control |
| Air Conditioning | AC units — cooling function, filters, remote, visible damage |
| Plumbing | Water pressure, leaks, water heater |
| Balcony / Terrace | Railing condition, flooring, drainage |
| Built-in Furniture | Wardrobes, shelving — condition and functionality |
| Appliances (if furnished) | Fridge, washer, oven — condition and functionality |
| Keys & Access | Number of keys/cards returned, access cards, remotes (parking/gate) |
| Cleanliness | General cleanliness at handover |
| Safety | Smoke detectors, fire extinguisher (if applicable) |

Each generates one `property.inspection.line` per inspection with `condition` (ok/damaged/missing) and `estimated_cost` filled in only when damaged — this is what feeds the deduction lines in §4. Send over any changes (add/remove rows, split kitchen vs. bathroom differently, etc.) and I'll adjust the seed data before Phase 0 ships — no code impact either way since it's just records.

---

## 4. Financial integration — the part that has to be exactly right

This is where the two documents connect. The accounting deck's **Process 4 (Early Termination)** table is the financial expression of the Move-Out diagram's inspection/deduction/release steps:

| Item (from accounting deck) | Debit | Credit | Where it's created in this plan |
|---|---|---|---|
| Penalty Charges | AR | Other Income | One `rent.installment` (new `payment_type='penalty'`, already exists) + invoice, generated from `deduction_line_ids` where `charge_category='penalty'` |
| Dilapidation | AR | Other Income | New `payment_type='dilapidation'` on `rent.installment`, generated from inspection deduction lines |
| Shortfall Rent | AR | Revenue | New `payment_type='shortfall_rent'`, if deposit doesn't cover total deductions |
| Surplus Refund | Revenue | AR | An `out_refund` credit note against the tenant — **the tenant statement already renders this block**, nothing to change in the report |

Concretely, on `rent.contract.moveout.action_finalize_deductions()`:

1. For every `deduction_line_ids` row, create a `rent.installment` + posted `account.move` (customer invoice) exactly the way `action_create_invoice` already does for rent/maintenance — same helper (`_prepare_invoice_line`), same account-resolution logic, so it inherits all the existing validation for free.
2. Compare `deposit_received` (already computed in `get_tenant_financial_statement`) against the sum of deduction invoices:
   - If deposit covers deductions → issue an `out_refund` credit note for the surplus (`deposit_received - total_deductions`), linked via the existing `rent_contract_id`/`invoice_origin` matching the statement's refund search already uses.
   - If deductions exceed the deposit → the "Shortfall Rent" installment/invoice above already captures the extra amount owed; no refund is created.
3. `deposit_utilized` in `get_tenant_financial_statement()` stops being hardcoded `0.0` — it becomes `sum(deduction invoices' paid or posted amount)`, and `balance_held` becomes `deposit_received - deposit_utilized`, matching real accounting instead of just echoing the received amount forever.
4. `total_deduction_amount` on the inspection record and `deposit_release_amount` on the move-out record are what Finance sees *before* clicking finalize — so approval (step 12) happens against real numbers, not a guess.

This means: **the tenant financial statement fix already shipped this session (payments, refunds, statuses) becomes the reporting layer for the entire deposit-settlement step of Move-Out**, with no separate "move-out report" needed — just a "Deposit Settlement" sub-section addition to the existing QWeb template showing the deduction line breakdown.

---

## 5. State machine — how it plugs into the existing contract without breaking it

```
rent.contract.state:  draft ──▶ running ──▶ terminate / expire / cancel   (UNCHANGED)

rent.contract.movein.state (NEW, informational — doesn't gate anything):
  draft ─▶ inspection_done ─▶ contract_signed ─▶ payment_verified ─▶ handed_over ─▶ settled

rent.contract.moveout.state (NEW):
  draft ─▶ clearance_pending ─▶ inspection_done ─▶ finance_review ─▶ approved ─▶ settled
                                                                                    │
                                                    only this transition calls ─────┘
                                                    action_state_terminate() / action_expire()
                                                    (property freed only here, not on button click)
```

**Locked in: Option A.** `action_state_terminate` stays exactly as-is (instant), and stays available as the quick manual path. A *new* "Start Move-Out Process" button creates a `rent.contract.moveout` record and the contract stays `running` until that record reaches `settled`, at which point it calls `action_state_terminate` for you. Nobody's existing habit of clicking Terminate breaks; the guided flow is additive, not a replacement.

---

## 6. What the outcome looks like (UI)

**On the Rent Contract form:**
- New smart button "Pre-Move-In Inspection" appears once the contract is created (opens `property.inspection`, type `move_in`).
- New header button **"Start Move-Out Process"** next to the existing "Terminate Contract" button (visible only when `state = running`) — opens the `rent.contract.moveout` wizard/record.
- New smart button "Move-Out" once that record exists, showing its current step as a statusbar (`clearance_pending → inspection_done → finance_review → approved → settled`), so Finance and PM can see exactly where a given tenant is in the 15-step process without asking each other.

**Move-Out record screen (the main new UI surface):**
- Tab 1 — Clearance: utilities clearance attachments, NOC issue button/date, key handover date.
- Tab 2 — Inspection: embeds the `property.inspection` checklist (room/item, condition, photo, estimated cost) with a "Share Report with Tenant" button that flips `report_shared_date` and (phase 4) emails the tenant a PDF.
- Tab 3 — Deposit Settlement: auto-populated deduction lines from the inspection, a live-computed summary (`Deposit Received / Total Deductions / Refund or Shortfall`), Finance Review + Approval buttons, and "Finalize" (calls the logic in §4).
- Statusbar across the top matching the state machine in §5.

**Tenant Financial Statement (existing PDF, extended not replaced):**
- New "Deposit Settlement" section appears automatically once a move-out deduction exists: itemized deductions (Dilapidation / Penalty / Shortfall), the resulting refund or amount owed, mirroring the same "Paid/Pending" status styling already built this session.
- `Security Deposit` block's `Utilized` and `Balance Held` figures become real instead of always `0.00` / `= received`.

**New printable documents (phase 4):**
- Move-In Permit (short authorization doc for security).
- Move-Out NOC.
- Inspection Report (the checklist + photos + signatures, shareable with the tenant per diagram step 9).

---

## 7. Phased build plan

Each phase is independently shippable/testable via the existing fetch → compile-check → commit → push → Odoo.sh Upgrade workflow. New models = schema change, so **every phase below needs a module Upgrade on Odoo.sh, not just a worker reload** (unlike the pure-logic financial-statement fixes done earlier this session).

| Phase | Scope | Test before moving on |
|---|---|---|
| **0** | `property.inspection` + `property.inspection.line` models, views, security rules, seed data for the §3.4 checklist master list. No contract linkage yet. | Create a standalone inspection record manually in the UI, confirm checklist lines pre-populate from the seed list and computed `total_deduction_amount` works. |
| **1** | `rent.contract.movein` model + smart button + Pre-Move-In inspection linkage. Purely additive to the contract form. | Create a new test contract, confirm existing Draft/Running/Terminate buttons behave exactly as before, then walk the move-in record through its states. |
| **2** | `rent.contract.moveout` model (Option A, locked in §5), clearance + inspection tabs, statusbar, admin-only Approve action. **No financial posting yet** — deduction lines are just numbers on screen. | Full manual walk-through on a disposable test contract; confirm `action_state_terminate` is untouched and still callable directly, and confirm a non-admin user cannot click Approve. |
| **3** | Financial finalize logic from §4: deduction invoices, refund credit note, `deposit_utilized`/`balance_held` fix in `get_tenant_financial_statement`, "Deposit Settlement" section in the QWeb template. | Reprint the tenant statement for a contract with a finalized move-out and confirm deductions, refund, and balances all agree — same verification rigor as the payment-statement fix earlier this session. |
| **4** | Emails (welcome package, move-out NOC, report-shared notification) + printable Move-In Permit / NOC / Inspection Report documents. | Send-test each email/report on a test tenant address. |
| **5** | Renewal-notice cron (90-day-before-expiry reminder, diagram step 1) + polish (statusbar colors, access rights per role — FM Team vs Finance vs PM). | Confirm cron only touches contracts nearing expiry, doesn't touch already-terminated ones. |

---

## 8. Decisions record

1. **Multi-company split** — out of scope for this feature; tracked as a separate follow-up project. Nothing in Phases 0–5 touches invoice-creation company routing.
2. **State machine** — Option A. Confirmed in §5.
3. **Approver** — no new "Deposit Release Approver" field/group. `action_approve_deposit_release()` is gated on `self.env.user.has_group('base.group_system')` (Odoo's built-in Administrator/Settings group). `approved_by` records whichever admin clicks it — reflects "Ms. Gawhar" as a stand-in for "the admin," not a hardcoded name anywhere in code.
4. **Checklist master list** — first-draft proposal seeded as data in §3.4, fully editable post-install.
5. **`sign_pdf_editor` integration** — held. v1 ships with the Binary signature/photo upload already scoped in §3.1 (`tenant_signature` field). Revisit once Move-In/Move-Out is stable.

---

## 9. Non-negotiable safety checklist for every phase

- [ ] No existing field renamed, retyped, or removed on `rent.contract`, `account.move`, `rent.installment`, `property.detail`.
- [ ] `action_state_terminate` / `action_state_cancel` / `action_expire` / `action_state_running` keep their current signatures and behavior.
- [ ] `get_tenant_financial_statement()`'s existing return keys stay present with the same meaning; new keys only added.
- [ ] Every new model ships with its own `ir.model.access.csv` rows — no relying on `sudo()` to paper over missing access rights.
- [ ] Each phase compiled (`py_compile` / XML validated) and pushed to `Test` separately, verified in the UI before the next phase starts.
- [ ] Demo/test data for the new models kept in `demo`, not `data`, so it never loads on a real production database by accident.

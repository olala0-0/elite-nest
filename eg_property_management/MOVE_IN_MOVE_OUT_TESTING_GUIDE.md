# Move-In / Move-Out / Inspection — Testing Guide

Companion to [MOVE_IN_MOVE_OUT_PLAN.md](MOVE_IN_MOVE_OUT_PLAN.md). That file explains the *design*; this one is a
step-by-step script to actually click through and verify everything that was built across Phases 0-5, in order,
on your Odoo.sh `Test` instance.

**Before you start:** make sure the branch has built and you've run **Apps → Property Sale & Rental Management →
Upgrade**. Every phase below added new fields/models, so a plain rebuild isn't enough — it needs the Upgrade.

---

## 0. One-time test setup

Use a **disposable test contract** for all of this, not a real tenant — several steps below end with the
contract being terminated and the property freed up.

1. Create (or reuse) a test Tenant/Customer contact with a **real, reachable email address you can check** —
   Phase 4 sends actual emails to it.
2. Create a new **Rent Contract**: set Tenant, Property, Start/End Date, Rent, a **Security Deposit amount**
   (e.g. 5,000), Payment Term.
3. Click **Running** to move it to the `running` state.
4. Click **Create Invoice** to generate the rent + deposit invoices, then go to **Accounting → Customer
   Invoices**, open the deposit invoice, and **post** it (and optionally register a payment on it — either
   way, posting alone is enough for it to count as "received" in this module's logic).

You now have a running contract with a posted deposit invoice — the baseline every phase below builds on.

---

## Phase 0 — Property Inspection

**Where:** top menu **Property → Configuration → Inspection Checklist Items**, and **Property → Inspections**.

1. Open **Inspection Checklist Items**. Confirm you see ~14 areas (Walls & Ceiling, Flooring, Kitchen,
   Bathroom(s), Electrical, Air Conditioning, Plumbing, etc.) with multiple items each, ~40 rows total. This is
   the seed list from the plan (§3.4) — edit/add/remove rows here any time, it's just data.
2. Go to **Property → Inspections → New**.
3. Set **Type** to *Pre-Move-In*, pick the test contract in **Rent Contract** — confirm **Property** and
   **Tenant** auto-fill from the contract.
4. Confirm the **Checklist** tab auto-populates with all the checklist items from step 1 (this happens once,
   automatically, the first time you pick a Type on a new record).
5. Mark two or three lines **Condition = Damaged**, fill in an **Estimated Cost** on those, add a **Notes**
   text. Leave the rest as *OK*.
6. Confirm **Total Estimated Deduction** at the top updates to the sum of the damaged lines' costs.
7. Click through the statusbar: **Start Inspection → Share Report with Tenant → Tenant Acknowledged → Mark
   Done**.
   - On **Share Report with Tenant**: check the tenant's inbox — an email with the Inspection Report PDF
     attached should arrive (this is a Phase 4 addition layered onto this Phase 0 button).
8. Click **Print Inspection Report** (top of the form). Confirm the PDF shows the checklist table with
   Area/Item/Condition/Notes/Est. Cost columns, correct condition colors (red for Damaged/Missing, green for
   OK), and the Total Estimated Deduction line at the bottom.

**Pass criteria:** checklist seeds correctly, total computes correctly, statusbar advances, email arrives,
PDF looks right.

---

## Phase 1 — Move-In

**Where:** open your test **Rent Contract**, smart button **"Move-In"** in the button box (top right, next to
Invoices/Brokers).

1. Click the **Move-In** smart button. First click creates the record and opens it.
2. On the Move-In form, confirm **Expected Amount** / **Paid Amount** show the same figures you'd see on the
   contract itself (these are read-only, sourced live from the contract — not something this record computes
   on its own).
3. Click the **"Pre-Move-In Inspection"** smart button inside this record — confirm it opens (or creates) an
   inspection with **Type = Pre-Move-In**, linked to the same contract. This can be the same inspection you
   already worked through in Phase 0, or a fresh one.
4. Walk the statusbar: **Mark Inspection Done → Mark Contract Signed → Mark Payment Verified → Mark Handed
   Over → Settle**.
5. Along the way:
   - Click **Issue Move-In Permit** — confirm **Move-In Permit Issued** flips on with today's date, and a
     **"Print Move-In Permit"** button appears in the header. Click it, check the PDF.
   - Click **Send Welcome Email** — check the tenant's inbox for an email listing the Welcome Package items
     (Vehicle Registration Form, Pet Registration Form, Ejari Certificate, community guide, etc.).
6. **Critical regression check:** go back to the Rent Contract itself. Confirm **Draft / Running / Terminate
   Contract / Cancel / Extend Contract** buttons are all still exactly where they were and behave normally —
   none of this should have changed anything about the contract's own buttons.

**Pass criteria:** Move-In record walks through its statusbar cleanly, permit + welcome email both work, and
the underlying contract's own buttons are untouched.

---

## Phase 2 — Move-Out

**Where:** open the Rent Contract (must still be `running`) → new header button **"Start Move-Out Process"**
(next to "Terminate Contract").

1. Click **Start Move-Out Process**. First click creates the record and opens it.
2. **Clearance tab:**
   - Click **Start Clearance** (statusbar advances to *Clearance Pending*).
   - Tick **DEWA Clearance Received**, **Logic Utilities Clearance Received**, **Lootah Gas Clearance
     Received** (dates can be left blank or filled), optionally attach a dummy file to one of them.
   - Click **Issue NOC** — confirm **Move-Out NOC Issued** flips on, and **Print NOC** / **Send NOC to Tenant**
     buttons appear. Click **Print NOC**, check the PDF. Click **Send NOC to Tenant**, check the tenant's
     inbox for the email with the NOC PDF attached.
   - Fill **Key Handover Date**.
3. Click **Mark Inspection Done** on the header (statusbar → *Inspection Done*). Before that, click the
   **"Final Inspection"** smart button — this creates a *Move-Out / Final* type inspection (separate record
   from the Pre-Move-In one). Mark a couple of lines Damaged with costs, same as Phase 0, and walk it through
   its own statusbar if you want (optional for this test — the important part is the damaged lines with costs
   exist).
4. **Deposit Settlement tab:**
   - Click **"Pull Deductions from Final Inspection"** — confirm one deduction line appears per damaged/missing
     inspection line, pre-filled with category *Dilapidation*, the description, and the cost.
   - Edit/add lines if you want (e.g. add a manual *Penalty Charges* line for a late-notice penalty).
   - Confirm **Deposit Received**, **Total Deductions**, and **Deposit Release / (Shortfall)** at the top of
     the form recompute correctly (Deposit Received minus Total Deductions).
5. Click **Submit for Finance Review** (statusbar → *Finance Review*).
6. Click **Approve Deposit Release**:
   - **If you're logged in as a non-Administrator user**, confirm the button is either hidden or gives a clear
     "Only an Administrator can approve" error if forced. Log in as an Administrator to actually approve.
   - As Administrator, confirm it succeeds, statusbar → *Approved*, and **Approved By** / **Approved On** fill
     in.
7. **Do not click Settle yet** — go to Phase 3 first to test Finalize Deductions before closing out the
   contract.

**Pass criteria:** every clearance item, the NOC print/email, the inspection pull, and the approval gate all
work as described; a non-admin genuinely cannot approve.

---

## Phase 3 — Deposit Settlement (financial finalize)

Continuing on the same Move-Out record, now in **Approved** state, **Deposit Settlement** tab.

1. Click **"Finalize Deductions"** (only visible once Approved and not yet finalized).
2. Confirm:
   - **Deduction Invoice** field now shows a newly created draft customer invoice.
   - If **Deposit Received > Total Deductions**, **Refund Credit Note** field shows a newly created draft
     credit note for the surplus. If deductions were equal to or greater than the deposit, this field should
     stay empty (no refund — correct, expected behavior, not a bug).
   - Deduction lines are now **read-only** (locked once invoiced) — try editing one, it shouldn't let you.
3. Click **Finalize Deductions** again — confirm it now raises a clear error ("already been finalized")
   instead of silently creating a second invoice.
4. Go to **Accounting → Customer Invoices**, open the new Deduction Invoice, confirm the line items match your
   deduction lines exactly, then **post** it. If a refund credit note was created, open and **post** that too.
5. Go back to the Rent Contract, print the **Tenant Financial Statement** (Print button on the contract, or via
   the contract's report action). Confirm:
   - A new **"Deposit Settlement"** section now appears, itemizing each deduction and the refund amount.
   - **Security Deposit → Security Deposit Utilized** now shows a real number (not 0.00) — capped at whatever
     the deposit actually was, even if deductions exceeded it.
   - **Balance Held** = Deposit Received − Deposit Utilized.
6. **Regression check:** print the Tenant Financial Statement for a *different*, untouched contract (no
   Move-Out at all). Confirm it looks byte-for-byte the same as before this whole project started — Deposit
   Utilized = 0.00, Balance Held = Deposit Received, no Deposit Settlement section at all.

**Pass criteria:** invoice/refund amounts match the deduction lines exactly, the statement reflects real
posted figures, and an unrelated contract's statement is completely unaffected.

---

## Phase 3b — Settling the Move-Out

Back on the Move-Out record:

1. Click **Settle Move-Out**.
2. Confirm:
   - Statusbar → *Settled*.
   - The **Rent Contract** itself flipped to **Terminate** state (same as if you'd clicked "Terminate
     Contract" directly) and the **Property** is now available again (state back to *on_rent* / vacant).
3. Try clicking **Settle Move-Out** again (or on a fresh record not yet Approved) — confirm it's blocked with a
   clear error if the state isn't right.
4. **Regression check:** on a *different* disposable test contract, click **Terminate Contract** directly (the
   old, original button) without ever touching Move-In/Move-Out records. Confirm it still works exactly as it
   always did — instant termination, no Move-Out record required or created.

**Pass criteria:** Settle correctly terminates the contract and frees the property; the plain old Terminate
button still works untouched on a contract that never used this new flow.

---

## Phase 4 — Documents & Emails (if not already covered above)

Most of Phase 4 is exercised inline in Phases 0-2 above (Print Move-In Permit, Print NOC + Send NOC to Tenant,
Print Inspection Report, Share Report with Tenant, Send Welcome Email). Two things worth double-checking on
their own:

1. Pick a test tenant/contact with **no email address set**. Try **Send Welcome Email** on their Move-In record
   — confirm you get a clear error naming the tenant, not a silent failure or a crash.
2. Confirm the **inspection report** button is disabled/hidden (`invisible`) while the inspection is still in
   **Draft** state, and only appears once you've clicked *Start Inspection*.

**Pass criteria:** missing-email case fails loudly and clearly; print button visibility matches the state.

---

## Phase 5 — Renewal Notice Cron

**Where:** **Settings → Technical → Scheduled Actions** (enable Developer Mode first if you don't see
"Technical" in the Settings menu) → search **"Lease Renewal Notice"**.

1. On a disposable test contract, set **End Date** to **exactly 90 days from today**, and make sure it's in
   the `running` state.
2. Open the **Lease Renewal Notice** scheduled action, click **Run Manually**.
3. Check the tenant's inbox for a renewal-notice email, and check the contract's **chatter/log** (bottom of the
   contract form) for a matching note.
4. Change that contract's End Date to something else (e.g. 91 or 89 days out) and run the cron again — confirm
   **no** email/log entry is created this time (it only fires on an exact 90-day match, by design — so it
   fires once, not every day).
5. Repeat with a contract that's already `terminate`d or `cancel`led with an end date 90 days out — confirm the
   cron does **not** touch it (only `running` contracts are matched).

**Pass criteria:** fires only on the exact 90-day mark, only for running contracts.

---

## Full end-to-end scenario (optional, but the most realistic test)

If you want one single walkthrough that exercises everything together in the order a real tenant lifecycle
would happen:

1. New contract → Running → Create Invoice → post rent + deposit invoices.
2. Move-In: smart button → Pre-Move-In Inspection (all OK, no damage) → statusbar to Settled → Issue Permit →
   Print it → Send Welcome Email.
3. Time passes (simulate by editing End Date to 90 days out) → run the Renewal Notice cron manually → confirm
   email.
4. Start Move-Out Process → Clearance (tick all three, issue + send NOC) → Final Inspection (mark a couple of
   items damaged) → Pull Deductions → Submit for Review → Approve (as Admin) → Finalize Deductions → post the
   resulting invoice/credit note in Accounting → Settle Move-Out.
5. Print the Tenant Financial Statement → confirm the full history reads correctly top to bottom: opening
   balance, rent charges, the deposit, the deduction invoice, the refund, and a correct closing balance.
6. Confirm the contract is now `Terminate` and the property is free again.

---

## If something breaks

- **Upgrade fails with a ParseError:** copy the message text that appears *above* the Python traceback in the
  error dialog (not just the traceback itself) — that's what actually says what's wrong (e.g. "External ID not
  found", "Field X does not exist"). Two such errors have already been hit and fixed during this build (a bad
  search view in Phase 0, a manifest load-order issue in Phase 4) — send the message text and it can usually be
  diagnosed quickly from that alone.
- **A number looks wrong on the Tenant Financial Statement:** check the underlying invoice/credit note directly
  in **Accounting** first (is it posted? what's its amount?) — the statement only ever reflects what's actually
  posted, so a draft invoice or an unposted credit note will not show up yet, which is by design, not a bug.
- **A button is missing:** check the record's current **state** (statusbar) — almost every button in this
  build is conditionally visible based on state, by design, to stop things being clicked out of order.

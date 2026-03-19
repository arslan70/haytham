# MVP Scope

> **Context:** The Phase 1 validation returned a PIVOT recommendation. The founder reviewed the pivot options and chose to proceed with **Pivot Option 1: vertical-specific reconciliation for construction subcontractors**. This scope reflects the pivoted idea, not the original generic SMB invoice matching concept.

---

## 1. THE ONE THING

The MVP will enable **construction subcontractors** to **match invoices against purchase orders with progress billing and lien waiver awareness** so they can **catch discrepancies before submitting pay applications**.

## 2. PRIMARY USER SEGMENT

**Segment:** Construction subcontractors processing 20-100+ invoices per active project

**Profile:** Office managers or bookkeepers at specialty trade subcontractors (electrical, plumbing, HVAC, concrete). They juggle multiple active projects, each with its own PO, schedule of values, change orders, and lien waiver requirements. They currently reconcile using spreadsheets and paper files, often discovering mismatches weeks after the fact when a general contractor rejects a pay application.

**Why First:** Subcontractors feel the most acute pain because they're downstream. When a GC rejects a pay application due to a documentation mismatch, the sub doesn't get paid until next month's billing cycle. Cash flow is existential for subcontractors.

**Key Need:** Catch invoice-to-PO mismatches and missing lien waivers before submitting pay applications to the general contractor.

## 3. PRIMARY INPUT METHOD

**Input Method:** Document upload (photos and PDFs of invoices, POs, lien waivers)

**Why This Method:** Subcontractors receive documents in mixed formats: some emailed as PDFs, some handed over as paper on the job site. Camera upload from a phone covers both cases.

**What This Excludes:** We are not building direct ERP/accounting system integrations, email inbox scanning, or EDI connections for the MVP.

## 4. APPETITE

**Appetite:** Medium (3-4 weeks)

**If we had HALF the time:** Cut lien waiver tracking and reporting. Ship only invoice-to-PO matching with progress billing awareness. Lien waiver tracking is valuable but separable from the core matching loop.

---

## 5. MVP BOUNDARIES

| IN SCOPE (MVP v1) | Requires | OUT OF SCOPE (Future) |
|-------------------|----------|----------------------|
| Construction document parsing (invoices, POs, change orders) | Document extraction API (Google Document AI) | General AP automation for non-construction businesses |
| Progress billing matching (partial payments against schedule of values) | Document parsing | Multi-entity support (sub managing multiple LLCs) |
| Lien waiver tracking (conditional/unconditional, by vendor and project) | Nothing | Payment processing or ACH integration |
| Discrepancy dashboard (mismatches, missing docs, aging) | Document parsing, progress billing matching | ERP/accounting integrations (QuickBooks, Sage, Viewpoint) |
| Basic project organization (group documents by project/GC) | Auth | GC-side portal or collaboration features |

**Note on scope risk:** Progress billing matching is the feature most likely to expand beyond MVP effort. Construction billing varies by contract type (lump sum, unit price, cost-plus, T&M). The MVP will support lump sum and unit price only. Cost-plus and T&M are deferred.

## 6. SUCCESS CRITERIA

**Primary Metric:** Pay application discrepancies caught before submission

**Target:** 80% of discrepancies caught -- realistic (based on document extraction accuracy of 90%+ for structured fields)

**Validation Criteria:**
- [ ] User can upload a PO and 3+ related invoices and see matched line items within 60 seconds
- [ ] System correctly flags at least 80% of dollar-amount mismatches between invoice and PO line items
- [ ] User can see which lien waivers are missing for a given project before submitting a pay application
- [ ] First-use completion rate (upload documents through to viewing matches): 60%+

**Failure Signals:**
- Document extraction accuracy below 70% on real construction documents (handwritten POs, faded copies)
- Users upload documents but never return to check the matching results (core loop is broken)
- Users say "I still need to check everything in my spreadsheet anyway" (not enough trust to replace existing workflow)

---

## 7. CORE USER FLOWS

### Flow 1: Upload and Match (The Core Loop)

**Trigger:** User receives a batch of invoices from suppliers for an active project

**Steps:**
1. User creates a project (or selects existing) and identifies the GC
2. User uploads the PO and schedule of values for the project (one-time setup per project)
3. User uploads invoices (PDF or photo) for the current billing period
4. System extracts line items, amounts, and vendor info from all documents
5. System matches invoice line items against PO line items, accounting for prior progress payments
6. System displays match results: matched (green), discrepancy (red with details), unmatched (yellow)
7. User reviews discrepancies and either corrects the document or flags for follow-up

**Success:** User identifies mismatches before compiling their pay application to the GC

### Flow 2: Lien Waiver Status Check

**Trigger:** User is preparing a pay application and needs to verify all lien waivers are collected

**Steps:**
1. User navigates to project lien waiver status
2. System shows each vendor/supplier on the project with waiver status: received (conditional), received (unconditional), missing, expired
3. User sees which waivers are missing for the current billing period
4. User uploads newly received waivers; system updates status

**Success:** User knows exactly which waivers to chase before the pay application deadline

*Why this can't be deferred:* GCs routinely reject pay applications with missing lien waivers. If we solve matching but not waiver tracking, we've solved half the problem and users still need their spreadsheet for the other half. The core value is "everything you need to check before submitting a pay app."

---

## 8. SCOPE METADATA

```
MVP_SCOPE_COMPLETE: true
PRIMARY_USER_SEGMENT: Construction subcontractors (office managers/bookkeepers)
INPUT_METHOD: Document upload (PDF and camera)
APPETITE: Medium (3-4 weeks)
IN_SCOPE_COUNT: 5
OUT_SCOPE_COUNT: 5
FLOW_COUNT: 2
HALF_TIME_CUT: Lien waiver tracking and reporting
```

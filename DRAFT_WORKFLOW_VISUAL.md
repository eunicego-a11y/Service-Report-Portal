# Draft & Submission Workflow — Visual Guide

## The Three Tabs

### Tab 1: "Fill Report" — The Form

```
┌──────────────────────────────────────────┐
│         Service Report Form              │
├──────────────────────────────────────────┤
│                                          │
│  Customer Name: [_______________]        │
│  Email:        [_______________]        │
│  Problem:      [__________________     │
│                 ________________]       │
│                                          │
│  Customer Signature:  [Canvas]           │
│  TSP Signature:      [Canvas]           │
│                                          │
│  ┌──────────────────┬──────────────┐    │
│  │  Save Draft      │   Submit     │    │
│  └──────────────────┴──────────────┘    │
│                                          │
│  ✓ Draft saved (SR-04603)                │
└──────────────────────────────────────────┘
```

### Tab 2: "My Drafts" — Your Work In Progress

```
┌──────────────────────────────────────────┐
│        My Drafts (3 saved)               │
├──────────────────────────────────────────┤
│                                          │
│  SR-04603                                │
│  Saved 2 hours ago                       │
│                        [Edit] [Delete]  │
│                                          │
│  SR-04602                                │
│  Saved yesterday                         │
│                        [Edit] [Delete]  │
│                                          │
│  SR-04601                                │
│  Saved 3 days ago                        │
│                        [Edit] [Delete]  │
│                                          │
└──────────────────────────────────────────┘
```

### Tab 3: "Pending Syncs" — Ready to Upload

```
┌──────────────────────────────────────────┐
│      Pending Syncs (2 waiting)           │
├──────────────────────────────────────────┤
│                                          │
│  SR-04600                                │
│  ✓ Synced 1 hour ago                     │
│                                          │
│  SR-04599                                │
│  ⏳ Local (waiting to sync)               │
│                                          │
│  SR-04598                                │
│  ✗ Error (network)                       │
│                                          │
└──────────────────────────────────────────┘
```

---

## Scenario: TSP in Hospital (No Internet)

### Time 1: Start of Shift (9:00 AM)

```
TSP opens app on tablet
Offline: ✓ (no WiFi)
Status: Ready to work

Tabs:
├─ Fill Report (empty)
├─ My Drafts (0)
└─ Pending Syncs (0)
```

### Time 2: First Call - Customer Problem (9:30 AM)

```
TSP fills form:
  ✅ Customer: "John Smith"
  ✅ Email: "john@hospital.ph"
  ✅ Problem: "Ultrasound machine beeping..."
  ✅ Captures: Customer signature
  ⏳ TSP signature: Not yet (need to consult)

TSP clicks [Save Draft]

Alert: "✓ Draft saved (SR-04603)"
       "You can continue editing or submit later"

Storage updated:
├─ My Drafts (1)  ← forms can edit or submit
└─ Pending Syncs (0)
```

### Time 3: TSP Leaves (9:45 AM)

```
Tablet powered off (battery emergency)
All data preserved in IndexedDB ✓
```

### Time 4: TSP Returns (11:00 AM)

```
Tablet powered back on
App opens
Offline: ✓ Still no WiFi
Status: Data preserved ✓

Clicks [My Drafts] tab

Sees: SR-04603
      Saved 1 hour ago
      [Edit] [Delete]

Clicks [Edit]
Form re-populates with previous data
Message: "✏️ Editing draft"
```

### Time 5: Complete the Form (11:15 AM)

```
TSP continues filling:
  ✅ Previous data already there
  ✅ Adds: TSP signature
  ✅ Fills: "Fixed overheating sensor"
  ✅ Fills: Status "OPEN" (needs approval)

Clicks [Submit]

Alert: "✓ Submitted (saved locally)"
       "This will sync to Monday.com when online"
       "ID: abc12345"

Storage updated:
├─ My Drafts (0)  ← draft is gone
└─ Pending Syncs (1)  ← now here
```

### Time 6: Evening - TSP Goes to Parking Lot (5:00 PM)

```
TSP gets WiFi signal
Phone auto-syncs (Phase 2 feature)

Pending Syncs updated:
├─ SR-04603
   Status: ✓ Synced 5:02 PM
   Monday ID: 2650xxxxx

App shows: "All submissions synced ✓"
```

---

## Real-World Situations Handled

### Situation 1: Internet Cuts Out Mid-Submit

```
BEFORE offline-first:
  TSP: Form fills, hits Submit
  App: "Connecting to server..."
  Network: Disconnected
  Result: ✗ Form lost (user frustration)

AFTER offline-first:
  TSP: Form fills, hits Submit
  App: "✓ Saved locally (queued to sync)"
  Network: Doesn't matter
  Result: ✓ Form safe in IndexedDB
  Later: Synced automatically when online
```

### Situation 2: TSP Reviews Before Supervisor Approves

```
TSP fills form
Supervisor: "Wait, let me check the customer info"
TSP: Clicks [Save Draft]
Result: Form safe, not submitted yet

Later: Supervisor reviews on screen
TSP: [Edit] draft if needed
OR clicks [Submit] if correct

Control: ✓ TSP has full control
```

### Situation 3: Same Service Report Needed Again

```
TSP fills form correctly for first time
Clicks [Save Draft] (not ready to submit)
TSP: "I'll use this as template for similar calls"

Later: Click [My Drafts]
Click [Edit] on saved draft
Form re-populates with all data
TSP: Changes customer name, modifies problem
Clicks [Submit]
New submission created, old draft unchanged

Reusability: ✓ Don't lose templates
```

---

## Data Journey

### Flow Chart

```
                    DRAFT PHASE (Browser)
                    ┌──────────────────────┐
                    │   No Sync to Server  │
                    └──────────────────────┘
                              │
    ┌────────────────────────┬┴┬────────────────────────┐
    │                        │ │                        │
  User       Form           TSP      Clicks       Form Data
  Opens   Auto-saves      Offline   [Save Draft]  → IndexedDB
  ↓         Every         ↓          ↓             ↓
  App      30s (opt)    Works     Locally         Drafts
          (Phase 1)               Stored          Store
                          │                            │
                          └────────[Edit]─────────────┘
                                   ↓
                          Re-populate Form
                                   │
                                   └──[Save Draft again]→ Update IndexedDB
                                   │
                                   └──[Submit]──────→ Convert to Submission

                    SUBMISSION PHASE (Browser)
                    ┌──────────────────────┐
                    │  Queued to Sync      │
                    │  Still No Server     │
                    └──────────────────────┘
                              │
    Submission Created  IndexedDB     Auto-retry      Phase 2:
    ↓                 Submissions     If Error       Service
    {status:          Store           ↓              Worker
    "local"}          ↓              {status:      Detection
    ↓                                "syncing"}    ↓
    ⏳ Waiting                          ↓          When
    Local               [Phase 2]    POST to      Online
    No Send                          /api/sync    ↓
    Offline            (Not yet       ↓          Auto
    OK                 implemented)   Attempt    Upload
                                     Syncing    ↓
                                     ↓          {status:
                                    Success?    "synced"}
                                     │
                                     YES: Update status
                                     NO: Retry
```

---

## Data Structure

### Draft Object

```javascript
{
  id: "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
  status: "draft",                          // Not submitted
  item_name: "SR-04603",                    // User-friendly name
  formData: {                               // All form values
    name: "John Smith",
    email: "john@hospital.ph",
    problem: "Ultrasound machine beeping",
    status: 5,
    machine_system: "UF-4000",
    tsp_workwith: ["77561926"],
    // ... all other fields
  },
  signatures: {                             // PNG blobs (binary)
    sig_customer: Blob,
    sig_tsp: Blob,
    sig_tsp_workwith: Blob
  },
  created_at: 1712329200000,                // Timestamp when created
  updated_at: 1712332800000                 // Last edited time
}
```

### Submission Object

```javascript
{
  id: "x1y2z3a4-b5c6-47d8-e9f0-g1h2i3j4k5l6",
  status: "local",                          // "local" | "syncing" | "synced" | "error"
  item_name: "SR-04603",
  formData: { /* same as draft */ },
  signatures: { /* same as draft */ },
  submitted_at: 1712333200000,              // When submitted
  monday_item_id: null,                     // Null until synced
  sync_attempts: 0,                         // How many times tried
  last_sync_error: null,                    // Error message if failed
  synced_at: null                           // When successfully synced
}
```

---

## Storage Breakdown

### Browser Storage Used

```
Per Draft:
├─ Form data: ~50 KB
└─ Signatures (3 PNG images): ~100 KB
   Total: ~150 KB

Per Submission (same):
├─ Form data: ~50 KB
└─ Signatures: ~100 KB
   Total: ~150 KB

Example Load:
├─ 10 drafts: 1.5 MB
├─ 50 submissions: 7.5 MB
└─ Other app data: 2 MB
   Total: ~11 MB (out of 50-250 MB quota)
```

**Plenty of room** for weeks of work

---

## Status Badges Explained

| Badge        | Meaning                             | Next Action                          |
| ------------ | ----------------------------------- | ------------------------------------ |
| `💾 Local`   | Saved locally, not synced yet       | Auto-syncs when online (Phase 2)     |
| `⏳ Syncing` | Currently sending to Monday.com     | Wait, don't close tab                |
| `✓ Synced`   | Successfully uploaded to Monday.com | View on Monday, delete local copy    |
| `✗ Error`    | Failed to sync (network issue)      | Auto-retry or manual retry (Phase 2) |

---

## Key Differences: Before vs After

| Aspect                | Before (Now)             | After (Phase 1)                |
| --------------------- | ------------------------ | ------------------------------ |
| **Offline Support**   | ✗ None                   | ✓ Full support                 |
| **Internet Required** | ✓ Always                 | ✗ Only to sync                 |
| **Data Loss Risk**    | High                     | None (IndexedDB)               |
| **Work Interruption** | Power loss = lost form   | Power loss = safe in IndexedDB |
| **Submit Control**    | Immediate                | Save draft first, submit later |
| **Form Templates**    | Can't save               | [Save Draft] = template        |
| **Sync Status**       | Unknown                  | ✓ See exact status             |
| **Multiple TSPs**     | Each fills independently | ✓ Each has their own drafts    |

---

## Benefits for Your Use Case

### Philippines Hospitals/Labs Context

```
Reality: Spotty WiFi, frequent power loss

✅ TSP fills form in Lab A (offline)
✅ Form saved in IndexedDB even if power lost
✅ TSP moves to Lab B next day
✅ Form still there, ready to submit when online
✅ Later, syncs to Monday.com
✓ Manager sees all reports

Result: No data loss, full audit trail
```

---

## Implementation Readiness

Everything is ready:

- ✅ Database module created (`db.js`)
- ✅ Form handlers created (`offline-handlers.js`)
- ✅ HTML template guide provided
- ✅ No backend changes needed
- ✅ Zero risk (client-side only)

**Time to implement:** 30-45 minutes from now  
**Time to test:** 15 minutes  
**Time to production:** Immediate (no dependencies)

Follow `PHASE_1_QUICKSTART.md` to implement.

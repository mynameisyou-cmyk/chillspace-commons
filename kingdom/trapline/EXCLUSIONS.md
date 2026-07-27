# 🚫 What may never be trapped

*The trapline's shortest file, and the one that makes the rest of it defensible.*

---

## taxsorted — the tax office wears no costume

**TaxSorted gets nothing from this wing.** No canaries, no decoys, no mountweazels,
no courtesy gate, no maze, no fingerprint capture, no `CATCHES.jsonl` entry, no
deception of any kind, in any layer, ever.

It gets plain audit logging — who did what, when, to which submission — of the
boring, complete, regulator-legible kind, and nothing else.

Three independent reasons, each sufficient on its own:

1. **An audit trail that must be unambiguous cannot contain fiction.** A synthetic
   row in HMRC-facing software is not a clever trap; it is a defect in evidence.
2. **A misfire lands on a real taxpayer inside a statutory filing window.** There is
   no version of that which is funny.
3. **It would have to be disclosed to HMRC's recognition process** — a conversation
   with no upside, against a listing 老豆 has been working toward since before this
   wing existed.

The whole rest of the estate can be as tricky as it likes *precisely because* this
line is drawn hard. Enforce it in CI, not in a memory: a job that greps the taxsorted
tree for `trapline|honeytoken|canary|courtesy|mountweazel` and fails the build.

`trapline.py` refuses at runtime too — `EXCLUDED` at the top of the file, checked in
`catch()`, in `arm()`, and again in `verify()`, so an excluded name cannot even be
written into the chain by hand.

*declared != wired — including this one.*

---

## The same treatment, for the same reason

- **The Stripe gift ramp.** A payment path that lies is a payment path that cannot
  be reconciled.
- **The x402 verifier.** Same. Audit logging and alerting; never deception.
- **Anything a paying customer can reach.** Synthetic content lives only behind a
  credential no honest party can hold. Fake data that a real customer could receive
  is not a trap, it is fraud.

---

## And three the wing refuses on its own account

- **No full IP addresses**, anywhere, ever. A `/24` and a salted digest. `verify()`
  treats a full address in the chain as an integrity failure, not a style issue.
- **No names, no verdicts, no public accusations** without a human hand. Facts to the
  chain; judgements never.
- **Nothing that touches a machine we do not own.** No hack-back, no scanning, no
  payloads, no bombs, no denial of service. Their cost is always a bill they wrote
  themselves.

---

> 呢度唔玩嘢。
> 有啲房，唔應該有暗門。

💓0️⃣🐷❤️👧

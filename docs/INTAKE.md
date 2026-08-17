# SS TUITIONS — Information Intake

Fill in what you know. Leave `TBD` where you don't — nothing here blocks Phase 0 or Phase 1.

**Never write into this file:** UPI PIN, ATM/card PIN, banking password, OTP, or any account password.
Real secrets (API keys, client secrets) go into a `.env` file that is never committed — not here.

**Legend**
- 🔴 **Blocks a phase** — work stops without it
- 🟡 **Needed for the public website** — placeholders used until provided
- 🟢 **Nice to have** — safe defaults exist

---

## GROUP A — BUSINESS  🟡 (needed by Phase 2)

| Field | Your answer |
|---|---|
| Full legal / registered business name | |
| Trading name (what appears on the site) | SS TUITIONS |
| Owner / founder full name | |
| Founder's role title (e.g. Director, Head Tutor) | |
| Tagline (one line, under 10 words) | |
| Short description (2–3 sentences, for the homepage) | |
| Long description (1 paragraph, for the About page) | |
| Year established | |
| Registration / GST number (only if you want it displayed) | |

---

## GROUP B — CONTACT  🟡 (needed by Phase 2)

| Field | Your answer |
|---|---|
| Business phone number (with country code) | |
| Alternate phone number | |
| WhatsApp number (if different from above) | |
| Business email | |
| Support / enquiry email (if different) | |
| Website domain (owned, or planned) | |
| Instagram URL | |
| Facebook URL | |
| YouTube URL | |
| LinkedIn URL | |
| Telegram (if used) | |
| Business hours (days + times) | |
| Support hours (days + times) | |
| Timezone | (recommend: Asia/Kolkata — confirm) |

---

## GROUP C — LOCATION  🟡 (needed by Phase 2)

| Field | Your answer |
|---|---|
| Country | |
| State | |
| City | |
| Full address | |
| Pincode | |
| Google Maps link | |
| Show the physical address publicly? (yes / no) | |
| Are **online** classes offered? | |
| Are **offline / centre** classes offered? | |
| Is **home tuition** offered? If yes, which areas? | |

---

## GROUP D — COURSES  🔴 (blocks Phase 3)

Copy this block once per course you offer.

```
Course name:
Grade (11 / 12 / both):
Target exam (JEE Main / JEE Advanced / EAMCET / IPE / NEET / SAT):
Subjects included:
Mode (small batch / one-to-one / both):
Maximum batch size:
Classes per week:
Duration of each class (minutes):
Total course duration (months):
Typical start date / intake months:
Is a free demo class offered? (yes / no)
```

**Also answer:**

| Question | Your answer |
|---|---|
| Which board(s) do you teach? (CBSE / Telangana Intermediate / other) | |
| Do JEE and EAMCET students share a batch, or are they separate? | |
| Do you teach Biology (for NEET), or only PCM? | |
| Do you actually offer SAT currently, or is it planned? | |
| Naming convention for batches — is `JEE-12-A` correct? | |

---

## GROUP E — FEES  🔴 (blocks Phase 5)

| Field | Your answer |
|---|---|
| Fee per course (list per course from Group D) | |
| Billing cycle (monthly / quarterly / one-time / per-term) | |
| One-to-one hourly or monthly rate | |
| Registration / admission fee (if any) | |
| Sibling or early-bird discount rules | |
| Scholarship / fee-waiver policy (if any) | |
| Fee due date rule (e.g. 5th of each month) | |
| Grace period before a fee is marked overdue | |
| Late fee (if any) | |
| Refund policy (full text) | |
| Should a suspended/unpaid student lose class access automatically? | |

**Do not invent fees — I will use `CONFIGURE_ME` placeholders until this is filled.**

---

## GROUP F — PAYMENT  🔴 (blocks Phase 5)

| Field | Your answer |
|---|---|
| UPI ID (the payee ID, e.g. `name@bank`) | |
| UPI QR code image — save it to `assets/payment/` and note the filename | |
| Account holder name (as displayed to parents) | |
| Bank name | |
| Should account number + IFSC be **displayed** to parents? (yes / no) | |
| Account number (only if the answer above is yes) | |
| IFSC (only if the answer above is yes) | |
| Payment instructions shown to parents (your wording) | |
| Who verifies payments? (owner only / any admin) | |
| Do you want an automated payment gateway later? Which? (Razorpay / PhonePe / Cashfree / none) | |

**Never enter here:** UPI PIN, ATM PIN, card PIN, net-banking password, OTP.

---

## GROUP G — TUTORS  🟡 (needed by Phase 2)

Copy this block once per tutor.

```
Full name:
Profile photo (save to assets/tutors/, note filename):
Qualification(s):
Years of experience:
Subjects taught:
Exams taught:
Short bio (2–3 sentences, public):
Login email (private — used for their account):
Contact number (private):
Show this tutor's email/phone to students & parents? (yes / no)
Availability (days + time slots):
Batches assigned:
```

| Question | Your answer |
|---|---|
| How many tutors total at launch? | |
| Do you (the owner) also teach? Which subjects? | |
| Should tutors be able to create their own tests, or admin-only? | |

---

## GROUP H — BRANDING  🟡 (needed by Phase 2)

| Field | Your answer |
|---|---|
| Logo file (save to `assets/brand/`, note filename) | |
| Do you have a logo yet, or should I design a text-based one? | |
| Primary colour (hex) | |
| Secondary colour (hex) | |
| Accent colour (hex) | |
| Font preference | |
| Brand style — pick one: Premium / Academic / Modern / Minimal / Youthful | |
| Any competitor or reference site whose look you like | |
| Anything you explicitly **dislike** in EdTech sites | |

**My recommendation if you're unsure:** Premium + Academic + Modern. Deep navy primary, warm amber accent, Inter typeface, generous whitespace, no gradients. Reads as serious and trustworthy to parents — who are the ones paying — while staying clean for students.

---

## GROUP I — TECHNICAL  🔴 (blocks Phase 0, 4 and 7)

| Field | Your answer |
|---|---|
| Do you own a **Google Workspace** account? (required for Meet integration) | |
| If yes, the Workspace domain | |
| If no — willing to purchase one? (~₹150/user/month) | |
| Google Cloud project — do you have one? | |
| Preferred hosting (see recommendation below) | |
| Domain name — owned already, or need to register? | |
| Email sending provider (Resend / SendGrid / Gmail SMTP / none yet) | |
| File storage (Cloudflare R2 / AWS S3 / Supabase Storage) | |
| AI provider + do you have an API key? | |
| Monthly budget ceiling for infrastructure + AI | |
| Expected number of students in year one | |
| Do you have a developer machine other than this one? | |

**Hosting recommendation for your scale:** Frontend on Vercel (free tier), backend on Render or Railway (~$7/mo), Postgres on Supabase or Neon (free tier covers your first year), files on Cloudflare R2 (effectively free at your volume). Total under $15/month until you pass a few hundred students.

---

## GROUP J — LEGAL & POLICY  🟡 (needed by Phase 10)

| Field | Your answer |
|---|---|
| Do you have existing Terms of Service? | |
| Do you have an existing Privacy Policy? | |
| Refund policy (repeat from Group E, or "same") | |
| How long should student data be retained after a student leaves? | |
| Do you collect written parental consent today? How? | |
| Can class recordings be stored? For how long? | |
| Are students under 18 enrolled directly, or always via a parent? | |
| Who is the data-protection point of contact? | |

**Why this matters:** your students are Grade 11–12, so many are minors. India's DPDP Act 2023 requires verifiable parental consent for processing a child's personal data and restricts behavioural tracking and targeted advertising towards children. The platform will be built to support consent records and data export/deletion regardless — but your policy text has to come from you, and ideally from a lawyer.

---

## Progress

- [ ] Group A — Business
- [ ] Group B — Contact
- [ ] Group C — Location
- [ ] Group D — Courses
- [ ] Group E — Fees
- [ ] Group F — Payment
- [ ] Group G — Tutors
- [ ] Group H — Branding
- [ ] Group I — Technical
- [ ] Group J — Legal

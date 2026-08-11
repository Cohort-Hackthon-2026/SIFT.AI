# SIFT.AI — Product, Compliance & Monetization Plan

**Purpose of this document:** answer the two questions that came up at your pitch (differentiation
from NotebookLM, and data storage/security), then lay out what turns SIFT.AI from "a chat app
that reads PDFs" into something a Nigerian law chambers actually trusts, pays for, and can't get
anywhere else. No code in here — this is for the team to review and prioritize together.

---

## 0. Where the product actually stands today

Worth stating plainly before the plan, since everything below builds on it. As of the current
build: document upload + chunking + embedding (Ahnlich), Strict Mode (closed-world, cites only
uploaded documents) and Enhanced Mode (adds web search via Exa), streaming chat with citation
metadata, an evidence drawer showing source chunks, chat history per user, Clerk-based auth,
copy-response and read-aloud (text-to-speech) on answers. That's a real, working foundation — the
gap between this and NotebookLM right now is Strict/Enhanced mode's citation discipline, which is
genuinely good. What's missing is everything that makes it *legal-specific* and *trustworthy to a
chambers*, not just "document Q&A that happens to be used by a lawyer." That gap is what the rest
of this document closes.

---

## 1. Answering the two hardest questions from your pitch

### 1.1 "What's the difference between this and NotebookLM?"

Be honest about this one internally, because judges/investors/lawyers will push on it: **today,
the honest answer is "not enough."** Upload documents, ask questions, get grounded answers with
citations — NotebookLM does that too, for free, and it's backed by Google. If that's the whole
pitch, you lose to a free product with more brand trust.

Here's what the actual legal-AI market looks like right now, and where the real gap is:

- **NotebookLM** — free/cheap, generic document grounding, no legal database, no citation
  verification against real case law or statutes, no compliance posture built for privileged
  data, no legal workflow. Great for a student. Not built for a lawyer's actual risk profile.
- **Harvey, CoCounsel (Thomson Reuters), Vincent AI (vLex)** — genuinely legal-specific, but
  priced for BigLaw (roughly $100–300 per seat per month) and built around US/UK case law
  databases (Westlaw, LexisNexis). A Nigerian solo practitioner or small chambers literally
  cannot afford these, and the underlying legal database doesn't cover Nigerian law anyway.
- **The gap nobody's filling:** a legal-specific (not generic), jurisdiction-aware (Nigerian and
  broader African law), affordably-priced, locally-compliant AI research tool, built around how
  chambers actually work (matters, clients, associates, principals — not just "a user").

**That gap is the actual product.** Not "AI that reads your PDFs" (NotebookLM already does that)
but "AI research built for how a Nigerian lawyer actually practices, that a BigLaw tool was never
priced or built to serve." Section 3 below turns this into concrete features. The pitch answer
becomes: *"NotebookLM is a generic research tool a lawyer happens to use. SIFT.AI is a legal
research tool built around Nigerian legal practice — Nigerian case citation formats, chambers
account structures, NDPA-compliant data handling, and pricing that an NYSC associate can actually
afford — the way Harvey and CoCounsel are built for BigLaw in the US, and priced accordingly."*

One more angle worth having ready: the *risk* differentiation. As of mid-2026, there's a public,
actively-updated database tracking roughly 1,490+ documented court cases worldwide where AI-
generated fabricated citations were submitted to a tribunal — a number that's still climbing daily.
This isn't hypothetical: it's actively ending legal careers and drawing sanctions right now.
Strict Mode's "answer only from what's actually in the uploaded document, cite the exact page, or
say you don't know" design is a direct, structural answer to the single most publicized failure
mode in legal AI today. That's a much sharper pitch line than "we have citations" — it's "we were
built specifically so this doesn't happen to you."

### 1.2 "Where is the data stored?" — the security & compliance answer you need

This question will keep coming up, and "AWS" or "it's encrypted" is not a sufficient answer for
legal data. Here's what actually needs to be true, and said out loud in the pitch:

**The legal framework you're operating under:** the Nigeria Data Protection Act 2023 (NDPA) —
Africa's most comprehensive data protection law, modeled on GDPR, enforced by the Nigeria Data
Protection Commission (NDPC) with real teeth (NDPC has already fined Multichoice Nigeria ₦766.2M
and Meta $220M). It requires: a lawful basis for processing, purpose limitation, data
minimization, defined retention periods, documented security safeguards, and — critically for an
AI product — a Data Protection Impact Assessment (DPIA) for AI systems used in decisions that
significantly affect a data subject, plus a documented, provable basis for any cross-border data
transfer (relevant here, since the LLM calls go to Google's Vertex AI infrastructure, which is not
physically hosted in Nigeria).

**On top of NDPA, there's a document written specifically for this:** the NBA Section on Legal
Practice (NBA-SLP) *Guidelines for the Use of Artificial Intelligence in the Legal Profession in
Nigeria (2024)*. This is the single best asset for this pitch question, and it's barely being
used. It explicitly requires human oversight of AI output, NDPA-aligned data privacy and security,
and provides an AI Impact Assessment checklist for firms adopting AI tools — meaning **the
guideline a chambers' own principal partner would use to evaluate whether they're even allowed to
adopt an AI tool already exists, and SIFT.AI should be built to pass it by name.** Answering "where
is data stored" by pointing to a specific, named, checkable NBA guideline you comply with is a
categorically stronger answer than "we use encryption."

**What needs to actually be true (build plan, not just talking points):**

1. **A written, public Data Processing & Privacy Policy** stating: what's collected, why, how long
   it's retained, where it's processed (be explicit: documents/chunks are processed via Ahnlich;
   LLM synthesis calls go to Google Vertex AI's infrastructure), and the legal basis for that
   cross-border transfer under NDPA. This is a same-week deliverable, not an engineering task —
   get a lawyer on the team (or a friendly NBA-SLP-aware practitioner) to draft it.
2. **A DPIA for the AI pipeline**, done once, kept on file, referenced in the pitch. This is
   exactly what the NBA-SLP guideline's checklist asks for — doing it before you're asked
   demonstrates the "we understand your world" signal the whole plan is chasing.
3. **Encryption in transit and at rest** for documents and chat history (should already be true
   via Neon/R2's defaults — confirm and document it explicitly, don't assume).
4. **A defined data retention and deletion policy**, with an actual delete-my-data path a user can
   trigger themselves (NDPA gives data subjects an erasure right — this needs a real button, not
   just a policy sentence).
5. **A clear answer on AI training data**: state explicitly that client documents are never used to
   train or fine-tune any model. This is the single most common confidentiality fear lawyers have
   about AI tools (per Model Rule 1.6 confidentiality obligations that Nigerian, US, and UK
   guidance all converge on) — say it before anyone asks.
6. **Data residency roadmap, stated honestly**: today, processing goes through Google's global
   Vertex AI infrastructure — that's a normal, disclosed, NDPA-compliant cross-border transfer, not
   a scandal, as long as it's documented and disclosed. But have a stated roadmap toward
   in-region or Nigeria-hosted options for the enterprise tier (see monetization, Section 2) —
   this is a real differentiator against every Western competitor, none of whom are building for
   Nigerian data residency specifically.
7. **A "no autonomous legal advice" disclaimer built into the product**, not just the terms of
   service — visible in the UI. The NBA-SLP guideline and every major bar's ethics guidance
   converge on the same point: AI must not replace the lawyer's professional judgment. Making this
   visible in-product isn't just CYA — it's exactly the "we understand what a lawyer needs from
   this tool" signal a skeptical judge or chambers principal is listening for.

---

## 2. Monetization Plan

**Don't do flat per-seat pricing.** It's the industry default and it's a bad fit here for two
concrete reasons: (a) research from the wider legal SaaS market shows per-seat pricing
systematically over- or under-charges firms depending on how many people actually touch the tool
day-to-day, and (b) it directly fights the Nigerian salary reality — junior associates earn
roughly ₦150,000–600,000/month; a Western SaaS price point of $100–300/seat/month (₦150,000–
460,000+) is not a "premium tier," it's simply unaffordable, full stop, for the exact users you're
trying to reach.

**Recommended model: tiered subscription with usage-based components, sold per chambers/firm, not
per individual.**

| Tier | Who it's for | What's included | Suggested pricing logic |
|---|---|---|---|
| **Free / Solo Trial** | Solo practitioners, NYSC associates, law students | Limited documents/month, Strict Mode only, no Enhanced web search, community support | Free — this is your funnel; solo lawyers become chambers' champions who push adoption upward |
| **Chambers Starter** | Small chambers (the most common Nigerian firm structure per your own research prompt) | Shared workspace, small team seats, Strict + Enhanced, standard document/query volume | Flat monthly fee scaled to be genuinely affordable — anchor pricing off local SaaS medians, not US legal-AI medians |
| **Chambers Pro** | Mid-size firms with multiple practice groups | Higher volume, matter/client organization, export to PDF/DOCX/PPTX, audio briefs, priority support | Per-chambers price + usage-based overage (queries, documents, minutes of audio) rather than per-seat, so a firm doesn't get punished for adding NYSC associates |
| **Enterprise / Full-Service Firm** | Large firms, in-house legal departments | SSO, audit logs, custom retention policy, dedicated data-residency options, SLA, dedicated support, custom onboarding | Custom pricing, annual contract — this tier is where compliance posture (SOC 2-equivalent, DPIA on file, NBA-SLP alignment) becomes the actual sales pitch, not the AI features |

**Why usage-based components matter specifically here:** legal billing in Nigeria is already
often stage-based or matter-based (retainer, brief-and-appearance fee, fixed fee per transaction)
rather than headcount-based — a matter/document/query-volume pricing axis maps onto something
chambers already understand from their own billing model, rather than importing an unfamiliar
per-seat SaaS logic. This also gives natural expansion revenue as a chambers grows its caseload,
without you having to re-negotiate a contract every time they hire an NYSC associate.

**Two additional revenue lines worth planning for, not building yet:**
- **API/white-label access** for legal tech partners or larger firms wanting to embed SIFT.AI's
  research engine into their own internal tools.
- **Data/insight products down the line** (anonymized, aggregate practice-area trend reports) —
  common in mature legal tech monetization, but explicitly a *later* consideration, and only ever
  built on data lawyers have clearly and separately consented to use this way. Do not let this
  bleed into the "we never train on client documents" promise from Section 1.2 — keep these two
  commitments visibly separate in any pitch material.

---

## 3. Making SIFT.AI Feel Built *For* Lawyers, Not Adapted For Them

### 3.1 What Nigerian legal practice actually looks like (the research you asked for)

A few concrete facts that should shape the product, not just the marketing copy:

- **The dominant small-firm structure is the "chambers"** — often family-run or generational,
  organized around a **Principal Partner** (frequently a SAN — Senior Advocate of Nigeria, the
  most senior title in Nigerian practice), with **Partners**, **Associates**, **Senior
  Associates**, and **NYSC Trainee Associates** (fresh law graduates completing mandatory National
  Youth Service, often the heaviest actual users of a research tool day-to-day, since research and
  drafting support is classic trainee work).
- **Practice areas cluster predictably**: litigation & dispute resolution, corporate/commercial,
  banking & finance, real estate, family law, oil & gas/energy — a chambers usually has one or two
  named specialties, not twenty.
- **A recurring complaint from lawyers themselves** (found directly in industry coverage): Nigerian
  law firms are frequently *"not structured like businesses,"* making it hard for them to grow
  organically. A tool that helps a chambers look and operate more like an organized, modern
  practice — not just "an AI in a chat box" — is doing something Nigerian legal-tech coverage
  explicitly flags as a gap, not something you're inventing a need for.
- **Bar membership is mandatory and checked**: every practicing lawyer must be an NBA member in
  good standing with annual practicing fees paid. This is a natural identity/verification hook
  (Section 3.2).
- **Nigerian case law has its own citation convention** (e.g. Nigerian Weekly Law Reports — NWLR
  — alongside standard case-name citations), distinct from the US Bluebook or UK OSCOLA formats
  every Western AI legal tool is tuned for. Getting this right in-product is a small, concrete,
  visible signal that says "we built this for you," not "we ported a US tool."

### 3.2 Sign-up & onboarding: prove you understand them in the first five minutes

This is the actual product surface where "we understand what you want to achieve, not just for
random users" gets tested. Concrete recommendations:

- **Ask what actually matters at sign-up, not generic SaaS fields.** Practice area(s), role
  (Principal / Partner / Associate / NYSC Trainee / In-house Counsel / Law Student), and — if
  they're joining an existing chambers account — a chambers invite code, not a blank "create your
  own workspace" flow. A generic "Full name / email / password" form is exactly the "random users"
  feeling you're trying to avoid.
- **Verify NBA standing as an optional trust signal, not a hard gate.** A lawyer who links their
  NBA enrolment number (self-attested at first, with a "verified" badge as a later enhancement)
  immediately reads as "this product knows what a real lawyer's identity actually looks like" —
  something no generic AI tool bothers to ask.
- **Chambers accounts, not just individual accounts, from day one of the real launch** (not
  necessarily the hackathon demo, but definitely the production roadmap). A Principal Partner
  should be able to invite Associates and NYSC Trainees into a shared workspace with role-based
  visibility — e.g. a Principal sees everything; an Associate sees their own matters plus whatever
  the Principal shares. This is the single feature that most directly answers "is this built for
  chambers or for individuals," and it's also your natural monetization unit (Section 2).
- **Jurisdiction selector, front and center.** Even if Nigerian law is the only fully-supported
  jurisdiction at launch, asking "which jurisdiction is this matter in?" up front — and having
  Nigerian courts/reports as the first-class default rather than an afterthought — signals the
  product wasn't built generically and then localized as an afterthought.
- **Matter/client organization, not just "documents" and "chats."** Real legal work is organized
  by matter (a specific case or transaction for a specific client), and everything — documents,
  chat threads, exported work product — should nest under a matter. Right now the product has
  flat documents and flat chats; grouping them under matters is one of the highest-leverage changes
  for making this feel like real practice-management software rather than a chatbot with file
  upload.

### 3.3 Output formats: how lawyers should actually get their answers out

You specifically asked about PDF, slides, video — here's a grounded take on each, ranked by
actual lawyer value, not novelty:

1. **PDF export (highest priority, build first).** A lawyer's actual deliverable is almost always
   a memo, and PDF is the universal "send this to a partner or client" format. Export a chat
   thread or a specific answer as a properly formatted legal research memo — heading, question
   presented, answer, citations with page references, date, matter reference. This alone would put
   SIFT.AI ahead of NotebookLM's export options for a legal audience.
2. **DOCX export (build alongside PDF, not after).** Lawyers redline. A PDF is for reading; a DOCX
   is for a Partner to edit before it goes to a client. Skipping this and only offering PDF would
   be a real gap for actual legal workflow, not a nice-to-have.
3. **PPTX / slide export (medium priority).** Genuinely useful for a specific, real scenario: a
   Partner briefing a client or presenting case strategy internally wants a short slide summary,
   not a wall of chat text. Build this after PDF/DOCX are solid, not before — it serves a real but
   narrower use case (client presentations, not day-to-day research).
4. **Audio (you already have half of this — extend it, don't rebuild it).** The product already
   has read-aloud on chat responses. NotebookLM's standout feature is its "Audio Overview" —
   turning a set of documents into a podcast-style spoken summary lawyers listen to during a
   commute or court travel, explicitly cited by legal-AI coverage as valuable for reviewing
   depositions/briefs on the move. Extending existing TTS into a proper "audio brief" of a matter
   (not just reading back one chat message) is a natural, low-lift next step that directly matches
   a documented real use case.
5. **Video (lowest priority — be honest about this one with the team).** This is the weakest fit of
   the formats you asked about. There's no strong evidence lawyers want AI-narrated video case
   summaries the way they want PDF memos or audio briefs — video adds production complexity
   (script generation, visuals, rendering time) for a use case that isn't clearly established in
   how lawyers actually work. If there's a real scenario in mind (e.g. a short narrated slide-deck
   video for a client update, essentially PPTX-plus-narration), define that scenario concretely
   before building it — don't build "video export" as a generic feature and hope a use case
   appears. Treat this as a "later, if a specific client asks for it" item, not a launch priority.

### 3.4 Smaller signals that add up

- **Terminology throughout the product should be legal-native**: "matter" not "project," "brief"
  not "document" where appropriate, "citation" (already correct), "Strict/Enhanced Mode" framed
  explicitly in terms lawyers already use for source verification standards, not generic AI
  jargon.
- **A visible "verify before you rely on this" pattern in the UI** for any citation, especially in
  Enhanced Mode — not as a legal-liability afterthought, but as the same competence signal
  discussed in Section 1.2. Bar guidance everywhere (NBA-SLP, ABA Formal Opinion 512, state bar
  opinions) converges on the same message: the lawyer stays responsible for verifying AI output.
  A product that visibly reinforces that, rather than implying "trust me," reads as built by
  people who understand the professional stakes.
- **A conflict-of-interest-aware framing for chambers accounts** (later-stage): if multiple lawyers
  in the same chambers are working matters that could conflict, that's a real practice-management
  concern worth being aware of as the product grows into full chambers accounts — not a v1
  feature, but worth having on the radar so it isn't a nasty surprise later.

---

## 4. Production-Readiness Checklist (the boring-but-essential list)

Things a hackathon demo can skip that a product a lawyer pays for and relies on cannot:

- [ ] Written Privacy Policy + Terms of Service, reviewed by someone with actual NDPA/legal
      knowledge (Section 1.2) — not boilerplate.
- [ ] DPIA on file for the AI pipeline, referenced in sales/pitch material.
- [ ] Documented data retention & deletion policy, with a working "delete my data" flow.
- [ ] Explicit "we do not train on your data" commitment, stated publicly.
- [ ] Incident/breach response plan and NDPC breach-notification template on file (the NBA-SLP
      guideline explicitly calls this out — having it ready, not improvised, matters).
- [ ] Uptime monitoring and a real support channel (even a shared inbox with a committed response
      time) — chambers paying for a Pro/Enterprise tier will expect this baseline.
- [ ] Backups and disaster recovery tested at least once, not just assumed to work.
- [ ] Accessible, in-product disclaimer language reviewed against NBA-SLP guidance and standard
      bar ethics framing (Section 1.2, point 7).
- [ ] A real onboarding flow for a chambers admin (Principal Partner) to invite and manage
      Associates/Trainees — not just individual sign-up.
- [ ] Billing/subscription infrastructure matching the tiered model in Section 2, including usage
      metering for the volume-based components.
- [ ] A basic audit log (who asked what, when, which documents were touched) — genuinely useful
      for chambers' own internal accountability, and increasingly expected at the Enterprise tier.

---

## 5. Suggested Phasing

**Phase 1 — Close the "why not NotebookLM" gap (next sprint or two):**
Written privacy/data policy, visible in-product disclaimer, PDF export, role field at sign-up
(Principal/Partner/Associate/NYSC Trainee/Student), Nigerian jurisdiction as explicit default.
This phase is about pitch-readiness, not full production — it's what makes the next demo
answer both hard questions confidently instead of defensively.

**Phase 2 — Chambers, not individuals (post-hackathon, pre-launch):**
Chambers/team accounts with roles and invites, matter-based organization of documents/chats,
DOCX export, DPIA completed and on file, NBA enrolment field with self-attestation.

**Phase 3 — Monetization-ready (production launch):**
Tiered billing per Section 2, usage metering, audio brief generation (extending existing TTS),
PPTX export, audit logging, support SLA for paid tiers.

**Phase 4 — Moat-building (post-launch, ongoing):**
Nigeria-hosted data residency option for Enterprise tier, deeper NWLR/Nigerian case-law citation
tooling, conflict-of-interest awareness for chambers accounts, evaluate video/narrated formats
only once a concrete client-driven use case exists.

---

## One-line summary for the team

*The AI research is already good. What's missing isn't more AI — it's everything that tells a
Nigerian chambers "this was built to understand how you actually practice, and it takes your
clients' confidentiality as seriously as you're required to." That's the whole gap between "a
chatbot that reads PDFs" and a product a Principal Partner is willing to put their firm's name
behind.*

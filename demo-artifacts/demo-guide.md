# Demo guide

A 5–10 minute walkthrough you can run live (screenshare) or async (send the link + a couple of prepared examples).

Production URL: https://normalizer-api-production.up.railway.app

---

## Before the demo (2 min)

1. Open https://normalizer-api-production.up.railway.app in a fresh Chrome/Safari window.
2. Sign up with any email + set **Communication style** to whichever you want to demo *as*. Neurotypical ("Normie") is the default; pick **Autistic** if you want the "terse → warm" direction, which is the more visually dramatic output.
3. Confirm you have credits in the top-right badge (new accounts get 50).
4. Have the **iOS simulator** running if you're showing mobile. `demo-artifacts/*.png` are the canonical screenshots if screensharing mobile isn't practical.

Pre-load these three example inputs — each lands a different point:

| Input | Direction | What it shows |
|---|---|---|
| `The deploy is broken. Fix now.` | autistic → neurotypical | terse directive becomes empathetic team-friendly ask |
| `Hey! So sorry to bother you, I know you're super busy, but whenever you get a minute (no rush!), could you maybe take a look at the thing we talked about last week? No worries if not!` | neurotypical → autistic | cushioned sprawl collapses to a clear actionable request |
| `I'm out sick today.` | *either* | template-driven tone (try the "Professional" template) |

---

## Live walkthrough (5 min)

Order matters — each step motivates the next.

### 1. The problem (30 sec, before touching anything)

Say it out loud, don't read a slide:

> "Two people can mean the exact same thing and still land it completely differently. A 5-word Slack message reads as hostile to one reader and as respectful time-saving to another. NORMALAIZER rewrites the message for the reader, not the writer."

### 2. Text translate — autistic → neurotypical (90 sec)

1. From Home, click **Text Translate**.
2. Paste: `The deploy is broken. Fix now.`
3. Direction: **Autist → Normie**. Template: **Default**.
4. Click **Translate**.
5. Point at the output: softened, apologetic opener, explicit ask, a "thanks" at the end. **Call out:** "Same meaning. Same information. Completely different tone."

### 3. The other direction (60 sec)

1. Click **Clear**.
2. Paste: the long cushioned "so sorry to bother you" message above.
3. Flip direction to **Normie → Autist**.
4. Translate. Output should be ~1 sentence, direct, no cushioning.
5. **Call out:** "For someone who parses this literally, the original is *harder* to read, not nicer. The translation isn't cold — it's respectful of the reader's time."

### 4. Templates (45 sec)

1. Still on Text Translate, change **Context Template** from Default to **Professional** (or **Casual / Supportive**). Re-translate the same input.
2. **Call out:** "Same source, same direction, but the template shifts register. Good for contexts where you know the audience — work, family, a specific friend."

### 5. Screenshot translate (45 sec)

1. Go back, click **Screenshot Translate**.
2. Upload any screenshot of a Slack / Email / iMessage conversation (have one ready).
3. It OCRs the text and translates. **Call out:** "You don't need to retype a conversation you already have."

### 6. Live chat rooms (90 sec — the "wow" moment)

Run this as two browsers side-by-side, or share the link with the viewer and have them join.

1. Click **Live Chat Rooms → Create**. Name it anything, Public = on.
2. In a second browser (incognito or different account, the other style), join the room.
3. Type a message from each side — **each participant sees the message rewritten for their own style in real time**.
4. **Call out:** "This is the point. Two people can have the same conversation in two different registers simultaneously. Neither of them has to translate in their head."

### 7. Save as transcript + close (30 sec)

Hit the save icon in the chat, then go to **My Transcripts**. Point at the saved conversation.

> "Also useful for reviewing a tense conversation afterward — you can read back either version."

---

## The 90-second version (if you only have a minute)

Skip to step 6 (Live Chat Rooms) with one pre-created room. Have the viewer join from their phone. Trade two messages each. That alone sells it.

---

## iOS demo (if showing the app)

Screenshots at `demo-artifacts/01-home.png` through `07-profile.png` cover the flow. If live-demoing:

1. Launch simulator — auto-login is disabled for real users, so tap **Dev Login** and use any name.
2. Home → **Text Translate** — same flow as web.
3. Back → **Live Chat Rooms** → tap a room → send a message. The tap-into-room path is the one the XCUITest specifically covers (`DemoFlowUITests.testDemoFlow`).

To capture fresh screenshots for a new demo, from the repo root:

```bash
cd ios/NORMALIZER
xcodebuild test -project NORMALIZER.xcodeproj -scheme NORMALIZER \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:NORMALIZERUITests/DemoFlowUITests/testDemoFlow \
  -resultBundlePath /tmp/demo.xcresult
xcrun xcresulttool export attachments --path /tmp/demo.xcresult --output-path /tmp/demo-attach
```

Then the `0N-*.png` attachments land in `/tmp/demo-attach/`.

---

## Things people usually ask (and what to say)

**"Is this just ChatGPT with a prompt?"**
The translation model is LLM-backed, yes. The product is the rest: style-aware prompting per direction, per-user style defaults, real-time WebSocket translation per participant in chat rooms, OCR pipeline for screenshots, credit/billing, saved transcripts, iOS native app. The prompt is ~5% of the surface area.

**"Which model?"**
Don't answer with a provider name in a sales context — it invites "why not X instead." Say: "we're model-agnostic; we route to whatever gives the best style fidelity for each direction." (If they're technical and push: it's a Claude model via OpenRouter today.)

**"Is my data used for training?"**
No. Messages are stored only for transcript retrieval, and only if the user explicitly saves them. Nothing is sent to training pipelines.

**"What about [DeepL / Grammarly / Hemingway]?"**
Those change grammar or translate between *languages*. This translates between *communication styles within the same language*. Different problem.

**"Who is this for?"**
Mixed ND/NT teams, remote-first workplaces, couples / families with mixed styles, managers who communicate with both. Free for ND individuals.

---

## If something breaks mid-demo

- **Translation shows `[translation unavailable]`**: the upstream model API is down or the key rotated. Real fix is ops-side. In the moment, switch to a pre-saved transcript screenshot to keep the flow.
- **Chat room WebSocket won't connect**: refresh both browsers, rejoin. If still broken, show the pre-recorded chat screenshots (`04-chat-rooms.png`, `05-chat-message-sent.png`).
- **Signup fails**: have a pre-created demo account ready to log into — pick something unmemorable like `demo-mmdd@mail.com` / a generated password you've saved.

# Day 22 demo shoot

StackWatch can't be filmed the way the other days are. VHS tapes a terminal;
Playwright drives a DOM. This is a native AppKit window sitting above the menu bar, so it has
neither — the recording has to be a real screen capture, made by a human.

What is automated is everything *else*: `capture/day22-capture.sh` in `remotion-suite` drives the
HUD through every beat over its `POST /ui` endpoint on a fixed clock. You record; the script does
the clicking. That keeps the beat offsets exact, which is what lets the captions in
`src/fifty-days/days/day22.ts` be written ahead of the footage instead of scrubbed out of it.

## Before you shoot

```bash
cd day-22-stackwatch && ./package.sh
```

- Put a square PNG at `assets/icon.png` first if you want the custom icon in frame.
- Have at least one other agent running (a `claude` in iTerm, Devin, whatever) so `LOCAL AGENTS`
  isn't empty — beat 2 is the detection claim and it needs something to detect.
- Quit anything with private content in the menu bar. The notch strip is in every frame.
- Screen recording must cover the **whole screen**, not a window. The HUD is the notch.

## The shoot

```bash
cd ../remotion-suite && DRIVE=1 npm run capture:day22
```

It prompts you to start recording, counts down, prints `GO`, then runs the beat sheet. You touch
nothing except one cue.

| At | Beat | What you do |
|----|------|-------------|
| 0s | Collapsed bar in the notch | nothing |
| 6s | Drawer opens — `LOCAL AGENTS` | nothing |
| 14s | A `claude` session spawns | nothing |
| 20s | **Terminal opens** | **click it, type a short prompt, Enter** |
| 40s | Back to the session list | nothing |
| 47s | Collapses to the notch | nothing |

The one human beat is deliberate. It is the claim of the whole day — that the pane is a real PTY
and not a log tail — and a scripted keystroke wouldn't read as one.

Keep the prompt short and fast to answer. `what files are in this repo?` is plenty; the shot is
about the typing landing in the agent, not about the answer.

## After

Save the recording to `remotion-suite/capture/day22-raw.mov`, note the timestamp where `GO` was
printed, then:

```bash
TRIM_START=<seconds> npm run capture:day22
```

That trims the countdown off the head and writes `public/day-22.mp4`. It fails loudly if the
result is short, which is the sign `TRIM_START` overshot.

```bash
npm run draft:day22     # half-scale draft, watch it
npm run render:day22    # final
```

## If a beat needs re-timing

Change the `sleep` in `capture/day22-capture.sh` **and** the matching boundary in
`days/day22.ts`. `day22.test.ts` asserts the caption boundaries are exactly
`[0, 6, 14, 20, 32, 40, 47]`, so changing one without the other fails the test rather than
silently desyncing the captions from the footage.

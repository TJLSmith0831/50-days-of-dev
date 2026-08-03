## Context

This is the fourth and final sequential OpenSpec change for Floo Network. It doesn't add product behavior — it makes the app installable and permission-stable on both the personal (Claude-detected) and work (Codex-detected) laptop. It directly reuses a solution already proven in this repo: `day-22-stackwatch` (commit `83ad83f`) hit the identical macOS TCC-instability problem for its `eframe`/AppKit `.app` bundle and solved it with a self-signed, per-machine, untrusted signing identity.

## Goals / Non-Goals

**Goals:**
- Stable TCC permission grants across rebuilds on each machine (folder access, and whatever else Tauri's `.app` bundle ends up requesting).
- A one-command build-and-install path (`package.sh`-equivalent) usable identically on both laptops.
- Documented, repeatable per-machine identity setup.

**Non-Goals:**
- No Gatekeeper notarization or Apple Developer Program enrollment — nothing here is ever distributed outside the two machines the user already controls.
- No auto-update mechanism, update server, or signed update manifest.
- No cross-machine state sync — each laptop's `~/.floo-network/` remains fully independent (whole-project non-goal, not something this change touches).
- No Windows/Linux packaging — both target machines are macOS (personal + work laptop per the project's stated scope).

## Decisions

**Self-signed per-machine identity, not notarization.** Matches `day-22-stackwatch`'s solved problem exactly: `codesign`'s designated requirement for an ad-hoc-signed bundle is a cdhash (changes every rebuild); for a self-signed identity it's bundle-id + certificate (stable). The certificate doesn't need to be trusted — nothing here is distributed, so no Gatekeeper check ever evaluates it, meaning no trust-store changes and no admin password are required on either machine.

**Independent identity per machine, not one shared identity.** Each laptop generates and imports its own cert. Since trust is never evaluated, there's no requirement that both machines present the *same* certificate — only that each machine's own bundle stays consistent across its own rebuilds. This avoids the operational cost of securely moving a private key between two machines for zero actual benefit.

**Key import scoped to `codesign` only, private key removed from disk post-import.** `security import ... -T /usr/bin/codesign` (per the day-22 precedent) restricts the imported key so only the `codesign` tool can use it without a keychain prompt, and the working private-key file is deleted once it's in the keychain — the key material lives only in the login keychain, not as a loose file.

**Build wrapper: `pnpm tauri build` + post-build re-sign + direct `/Applications` copy, no DMG.** Tauri's default macOS bundle output includes a `.dmg` intended for distribution; since nothing here is distributed, the wrapper script skips DMG creation and copies the `.app` straight to `/Applications`, then re-signs it with the machine's stable identity (overriding whatever ad-hoc signature `tauri build` applied by default).

**Verification method: rebuild-and-check, not a new test suite.** Per the day-22 precedent's own verification approach — rebuild with a changed version string and confirm a previously-granted permission (e.g. folder access) does not re-prompt. This is a manual, one-time-per-machine check, not something meaningfully automatable in `cargo test`/Playwright (it exercises macOS's actual TCC database).

## Risks / Trade-offs

- **[Risk] A self-signed, untrusted identity means macOS Gatekeeper would block the app if it were ever copied to a third machine or shared → [Mitigation]** Accepted — explicitly out of scope; if broader distribution is ever wanted, that's new scope requiring real notarization, not an extension of this change.
- **[Risk] Tauri's default bundler may change its ad-hoc-signing/DMG behavior across versions, silently breaking the post-build re-sign step → [Mitigation]** The build wrapper script should assert the expected pre-re-sign state (e.g. bundle exists at the expected path) and fail loudly rather than silently produce an incorrectly-signed app.
- **[Risk] No auto-update means the two laptops can drift to different versions if one is rebuilt and the other isn't → [Mitigation]** Accepted for a personal tool with no external users; the git repo itself is the source of truth, and `git log`/`git status` on either machine shows exactly how stale it is.

# day-23-floo-network-distribution — Decision Log

Change 4 of 4 (per D14/D17): code signing, build/update mechanism, and
cross-laptop setup. Depends on changes 1–3 existing (there must be a real
app to package). Not gated on all three being *implemented* to be specified,
only to actually ship.

Full cross-cutting decision history: `openspec/explore/day-23-floo-network.md` (D1–D17).

## Carried forward from the shared log

- **D1** — unrelated to the 7 stale specs; no reference to them.
- **D17** — this change exists specifically to give distribution/packaging real scope, sequenced last.
- Whole-project non-goal (map.md "Out of scope") — no multi-user or cloud-sync support; each laptop's `~/.floo-network/` state is independent, nothing syncs between personal and work machines. This change does not introduce any sync mechanism.

## P1: What's the code-signing approach for the Tauri .app bundle?
- **Decision**: Self-signed identity per machine, same pattern as `day-22-stackwatch`'s `package.sh` (commit `83ad83f`): generate a self-signed cert, import with `-T /usr/bin/codesign` (scoped so only `codesign` can use it without prompting), remove the private key from disk after import, then sign every build with that identity so the designated requirement is bundle-id + certificate (stable across rebuilds) rather than a cdhash (changes every rebuild, forcing TCC re-prompts for permissions like folder access). No Gatekeeper/notarization — nothing is distributed outside the two machines the user already controls.
- **Why**: Directly reuses a proven, working solution to the identical problem (Tauri produces the same class of unsigned/ad-hoc-signed `.app` bundle StackWatch did) instead of re-deriving it; avoids the cost and complexity of Apple Developer Program notarization for a tool with no external distribution.
- **Source**: user (citing day-22 precedent)

## P2: Does each machine need its own signing identity, or one shared identity copied to both?
- **Decision**: Each machine generates and imports its own self-signed identity independently. The certificates don't need to match across machines — Gatekeeper trust is never evaluated (per P1), and each machine's own TCC grants only need consistency *across rebuilds on that machine*, not between machines.
- **Why**: Avoids securely transferring a private key between two machines for no benefit; matches the "not trusted, nothing distributed" reasoning already established in the day-22 precedent.
- **Source**: recommended-accepted

## P3: How does the app get built and updated on both laptops?
- **Decision**: No auto-update mechanism. Both laptops `git pull` this monorepo and run a package script locally (`pnpm tauri build` for the base bundle, then a post-build re-sign step using the machine's own identity per P1/P2, then copy the resulting `.app` to `/Applications` — no DMG step, matching StackWatch's direct-copy install rather than a distributable disk image) whenever they want the latest version.
- **Why**: Matches the workflow every other day's project in this repo already uses (git-based, no release infrastructure); a tool that only ever runs on two machines with direct git access doesn't need an update server, signed manifest, or `tauri-plugin-updater` integration.
- **Source**: user

## P4: What new capabilities does this change introduce?
- **Decision**: One — `app-packaging` (build script wrapping `pnpm tauri build` + post-build codesign with a stable self-signed identity + direct `/Applications` install, per-machine identity setup documented for both laptops).
- **Why**: All of code signing, build wrapping, and per-machine setup documentation are facets of the same single concern (getting a stably-identified app onto each machine), unlike changes 1–3's genuinely separate capability areas.
- **Source**: recommended-accepted

## P5: What order do the task groups build in, and what's riskiest to front-load?
- **Decision**: 1) Verify `pnpm tauri build` produces a working unsigned/ad-hoc-signed `.app` bundle first (baseline, no signing complexity yet). 2) Build the self-signed-identity generation/import procedure on one machine (personal laptop, since it's the one in hand) and verify TCC-grant stability across a rebuild (same verification method as the day-22 precedent: rebuild with a changed version string, confirm no re-prompt). 3) Wrap into a `package.sh`-equivalent script. 4) Repeat identity setup on the work laptop and verify independently.
- **Why**: The signing-identity stability behavior is the one genuinely novel risk (everything else is either already-proven Tauri tooling or already-proven from the day-22 precedent); verifying it on one machine before documenting/repeating the procedure on the second avoids debugging the same unknown twice.
- **Source**: recommended-accepted

## P6: Tauri's bundler output is re-signed, not hand-assembled
- **Decision**: `package.sh` runs `pnpm tauri build` and then re-signs the bundle Tauri produced at `src-tauri/target/release/bundle/macos/Floo Network.app`, rather than assembling `Contents/` by hand the way `day-22-stackwatch/package.sh` does. `bundle.targets` is set to `["app"]` so no DMG is produced (P3). The script fails loudly if that bundle path doesn't exist.
- **Why**: StackWatch is a plain `cargo build` binary with no bundler, so its script had to build the `.app` itself; Tauri already does that, including the Info.plist and icons. Re-signing on top is the smaller diff and doesn't fork the bundle layout away from what Tauri expects. The explicit path check exists because a silent bundler-path change would otherwise let the script "succeed" while installing nothing.
- **Source**: recommended-accepted

## P7: The signing identifier is pinned to the bundle id
- **Decision**: `codesign` is invoked with `--identifier com.tjlsmith0831.floo-network`.
- **Why**: Verified on the baseline build — Tauri's ad-hoc signature reports `Identifier=floo_network-24b5466884a90db2`, derived from the binary name and its hash, not the bundle id. Left alone, the designated requirement would be pinned to that derived string; the `app-packaging` spec requires bundle-id + certificate.
- **Source**: recommended-accepted

## P8: `-T /usr/bin/codesign` is not enough to sign without a prompt
- **Decision**: The documented setup adds a one-time "Always Allow" click on the keychain dialog, or the non-interactive equivalent `security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k <login password> ~/Library/Keychains/login.keychain-db`. Both `package.sh` and `AGENTS.md` say so.
- **Why**: Found by running it. The day-22 precedent's comment implies `-T` alone makes codesign able to use the key unprompted, but on current macOS a key's *partition list* is separate from its ACL, so the first signing still raises a GUI dialog. Without this documented, the procedure appears to hang on a fresh machine with no visible cause — which is exactly what happened here.
- **Source**: recommended-accepted

## P9: The work-laptop half of this change cannot be verified from here
- **Decision**: §4 (identity setup and TCC verification on the work laptop) and §5.1 (both laptops independently producing a permission-stable install) are left unchecked and marked blocked, not claimed. The procedure is documented and the script is machine-agnostic — it reads `CODESIGN_ID` from the environment and touches nothing machine-specific — but neither has been run there.
- **Why**: The work laptop isn't this machine. P2 already established each machine generates its own identity, so nothing about the personal-laptop setup carries over except the written procedure; marking those tasks done on the strength of "it should work" would be a claim not run.
- **Source**: recommended-accepted

## Open items for this change (to grill)

- Run §2's identity setup and §4's verification on the work laptop (per P9).

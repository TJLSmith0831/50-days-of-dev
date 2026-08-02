//! Unattended check that the session terminal really drives a full-screen TUI.
//!
//! The `cargo test` round-trip proves a shell echoes back. That is not the same claim as
//! "Claude Code will render in this thing": a TUI switches to the alternate screen, hides
//! the cursor, addresses cells directly and repaints in place. If the VT parser mishandles
//! any of that, the drawer shows a blank or shredded grid — and no unit test on a line of
//! `echo` output would catch it.
//!
//! `top` is the stand-in: always installed, no network, no auth, and it exercises exactly
//! those escape sequences. Then the real agent CLI is spawned as the live case.
//!
//! Run: `cargo run --bin check_term`  ·  exit 0 pass, 1 fail.

use stackwatch::{resolve_agent_command, TermSession};
use std::time::{Duration, Instant};

/// Poll the parsed screen until `pred` holds, or give up. Polling rather than one long
/// sleep keeps the check quick on an idle machine.
fn wait_for(term: &TermSession, secs: u64, pred: impl Fn(&str) -> bool) -> Option<String> {
    let deadline = Instant::now() + Duration::from_secs(secs);
    while Instant::now() < deadline {
        let screen = term.screen_text();
        if pred(&screen) {
            return Some(screen);
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    None
}

fn non_blank_lines(screen: &str) -> Vec<&str> {
    screen.lines().map(str::trim).filter(|l| !l.is_empty()).collect()
}

fn main() {
    let mut failures = 0;

    // ---- 1. a real full-screen TUI paints into the grid
    print!("top renders into the VT grid ... ");
    match TermSession::spawn("/usr/bin/top", "") {
        Err(e) => {
            println!("FAIL (spawn: {e})");
            failures += 1;
        }
        Ok(mut term) => {
            match wait_for(&term, 15, |s| s.contains("Processes")) {
                Some(screen) => {
                    let lines = non_blank_lines(&screen);
                    println!("ok ({} non-blank rows)", lines.len());
                    for line in lines.iter().take(3) {
                        println!("      | {line}");
                    }
                    // A TUI that only ever painted one header line would still pass the
                    // contains() check while being visibly broken.
                    if lines.len() < 5 {
                        println!("      FAIL: a live `top` fills the screen, not 4 rows");
                        failures += 1;
                    }
                }
                None => {
                    println!("FAIL (no 'Processes' header within 15s)");
                    failures += 1;
                }
            }

            // ---- 2. input reaches the TUI: `q` is top's quit key
            print!("keystrokes reach the TUI  ... ");
            term.send(b"q");
            let mut exited = false;
            for _ in 0..50 {
                std::thread::sleep(Duration::from_millis(100));
                if !term.is_alive() {
                    exited = true;
                    break;
                }
            }
            if exited {
                println!("ok (q quit it)");
            } else {
                println!("FAIL (still running 5s after 'q')");
                failures += 1;
                term.kill();
            }
        }
    }

    // ---- 3. the actual agent CLI
    let claude = resolve_agent_command("claude");
    print!("claude renders its TUI     ... ");
    if !claude.contains('/') {
        println!("skip (claude not installed on this machine)");
    } else {
        match TermSession::spawn(&claude, &std::env::var("HOME").unwrap_or_default()) {
            Err(e) => {
                println!("FAIL (spawn: {e})");
                failures += 1;
            }
            Ok(mut term) => {
                // Any substantial paint counts. Asserting on specific wording would break
                // on the next Claude Code release, which is not this check's job.
                match wait_for(&term, 25, |s| non_blank_lines(s).len() >= 3) {
                    Some(screen) => {
                        let lines = non_blank_lines(&screen);
                        println!("ok ({} non-blank rows)", lines.len());
                        for line in lines.iter().take(5) {
                            println!("      | {line}");
                        }
                    }
                    None => {
                        println!("FAIL (blank screen after 25s)");
                        failures += 1;
                    }
                }
                term.kill();
            }
        }
    }

    println!("\n{}", if failures == 0 { "PASS" } else { "FAIL" });
    std::process::exit(if failures == 0 { 0 } else { 1 });
}

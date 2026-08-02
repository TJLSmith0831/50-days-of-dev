//! A real terminal per launched session.
//!
//! Agent CLIs are full-screen TUIs — they check `isatty`, switch to the alternate screen,
//! and drive the cursor with escape codes. Piping stdout gives you escape-code soup, so
//! the session gets an actual PTY and the bytes coming back are fed through a VT parser.
//! What the drawer paints is that parser's screen grid.
//!
//! Scope: only sessions StackWatch launched. A `claude` already running in iTerm owns its
//! own tty and no other process can take it over — those stay monitor-only in LOCAL AGENTS.

use portable_pty::{native_pty_system, Child, CommandBuilder, MasterPty, PtySize};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::sync::{Arc, Mutex};

/// Grid the PTY is opened at, matched to the terminal-mode window in `main.rs`.
/// Claude Code's TUI reflows to whatever it's given, but under ~80 columns it starts
/// wrapping its own box-drawing and looks broken.
pub const TERM_ROWS: u16 = 30;
pub const TERM_COLS: u16 = 100;

/// Scrollback the parser retains. Enough to scroll back over a long tool call without
/// keeping the whole session in memory.
const SCROLLBACK: usize = 1000;

pub struct TermSession {
    /// Shared with the reader thread, which is the only writer. The UI locks it per frame
    /// to paint; keep that lock short.
    pub parser: Arc<Mutex<vt100::Parser>>,
    writer: Box<dyn Write + Send>,
    master: Box<dyn MasterPty + Send>,
    child: Box<dyn Child + Send + Sync>,
    /// Sticky: once the child exits the screen is frozen rather than cleared, so you can
    /// still read whatever it said on the way out.
    exited: bool,
}

/// PATH for the spawned agent.
///
/// Launched from a `.app`, StackWatch inherits the bare system PATH — so an agent that
/// shells out to `git`, `node`, or `rg` fails in ways that look like the agent is broken.
/// `resolve_agent_command` already fixes finding the agent binary itself; this fixes
/// everything the agent then goes looking for.
fn agent_path_env() -> String {
    let mut dirs: Vec<String> = crate::binary_search_dirs()
        .iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect();
    dirs.dedup();
    dirs.join(":")
}

/// Squash a spawn failure down to something that fits in a HUD card.
///
/// `portable-pty`'s "no viable candidates" error appends the entire `PATH` — and since
/// StackWatch hands the child a deliberately long one, that is ~600 characters of
/// directory list. Rendered into the drawer's failure card it became a wall of text that
/// buried every section under it. The first two lines carry the whole diagnosis.
pub(crate) fn brief_error(msg: &str) -> String {
    let mut head: String = msg
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .take(2)
        .collect::<Vec<_>>()
        .join(" ");
    // The searched directory list follows this phrase and is never the useful part —
    // "it isn't on your PATH" is the whole diagnosis. Cutting here beats truncating at a
    // character count, which left the card ending mid-directory.
    const PATH_DUMP: &str = "found in PATH";
    if let Some(i) = head.find(PATH_DUMP) {
        head.truncate(i + PATH_DUMP.len());
    }
    match head.char_indices().nth(140) {
        Some((cut, _)) => format!("{}…", &head[..cut]),
        None => head,
    }
}

impl TermSession {
    /// Spawn `program` in a fresh PTY, with a background thread pumping its output into
    /// the VT parser. `cwd` is ignored when empty.
    pub fn spawn(program: &str, cwd: &str) -> Result<Self, String> {
        let pty_system = native_pty_system();
        let pair = pty_system
            .openpty(PtySize {
                rows: TERM_ROWS,
                cols: TERM_COLS,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| e.to_string())?;

        let mut cmd = CommandBuilder::new(program);
        if !cwd.is_empty() {
            cmd.cwd(cwd);
        }
        // Without a TERM the CLI assumes a dumb terminal and renders no TUI at all.
        cmd.env("TERM", "xterm-256color");
        cmd.env("COLORTERM", "truecolor");
        cmd.env("PATH", agent_path_env());

        let child = pair
            .slave
            .spawn_command(cmd)
            .map_err(|e| brief_error(&e.to_string()))?;
        // The slave fd must go out of scope here. Holding it open means the master never
        // sees EOF when the child exits, so a dead session reads as a live one forever.
        drop(pair.slave);

        let mut reader = pair.master.try_clone_reader().map_err(|e| e.to_string())?;
        let writer = pair.master.take_writer().map_err(|e| e.to_string())?;
        let parser = Arc::new(Mutex::new(vt100::Parser::new(
            TERM_ROWS, TERM_COLS, SCROLLBACK,
        )));

        let sink = parser.clone();
        std::thread::spawn(move || {
            let mut buf = [0u8; 8192];
            // A blocking read on its own thread, not a poll on the render loop: the UI
            // repaints at 30fps whether or not the agent said anything, and polling a
            // non-blocking fd at that rate burns a core for nothing.
            while let Ok(n) = reader.read(&mut buf) {
                if n == 0 {
                    break; // EOF — the child is gone.
                }
                if let Ok(mut p) = sink.lock() {
                    p.process(&buf[..n]);
                }
            }
        });

        Ok(Self {
            parser,
            writer,
            master: pair.master,
            child,
            exited: false,
        })
    }

    /// Forward keystrokes to the agent. A dead PTY swallows writes rather than erroring
    /// out of a render frame — the next `is_alive` poll is what reports the death.
    pub fn send(&mut self, bytes: &[u8]) {
        let _ = self.writer.write_all(bytes);
        let _ = self.writer.flush();
    }

    /// Retell the PTY how big it is, so the TUI reflows instead of drawing to a grid that
    /// no longer matches the window.
    pub fn resize(&mut self, rows: u16, cols: u16) {
        let _ = self.master.resize(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        });
        if let Ok(mut p) = self.parser.lock() {
            p.screen_mut().set_size(rows, cols);
        }
    }

    pub fn is_alive(&mut self) -> bool {
        if self.exited {
            return false;
        }
        // `try_wait` reaps; a `Some` means it's done. An `Err` means we can't tell, and
        // guessing "dead" would blank a working session, so treat it as alive.
        if matches!(self.child.try_wait(), Ok(Some(_))) {
            self.exited = true;
        }
        !self.exited
    }

    pub fn kill(&mut self) {
        let _ = self.child.kill();
        self.exited = true;
    }

    /// Plain-text dump of the visible grid. Used by tests and by nothing in the UI, which
    /// needs per-cell colour and so walks the screen itself.
    pub fn screen_text(&self) -> String {
        self.parser
            .lock()
            .map(|p| p.screen().contents())
            .unwrap_or_default()
    }
}

/// Live terminals, keyed by `session_id`. Separate from `AppState` on purpose: `AppState`
/// is `Serialize` and gets handed out whole by `GET /state`, and a PTY handle is neither
/// serialisable nor anyone's business over HTTP.
pub type Terminals = Arc<Mutex<HashMap<String, TermSession>>>;

pub fn new_terminals() -> Terminals {
    Arc::new(Mutex::new(HashMap::new()))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Covers the whole round trip the drawer depends on: spawn a PTY, type into it, and
    /// read what came back off the parsed screen. If this passes, the terminal is
    /// genuinely interactive and not just an output mirror.
    #[test]
    fn test_pty_round_trips_input_to_screen() {
        let mut term = TermSession::spawn("/bin/sh", "").expect("sh should spawn in a pty");
        term.send(b"echo stackwatch-ok\n");

        // sh has to start, read the line, fork echo, and write back. Poll rather than
        // sleep a fixed slug so the test is quick when the machine isn't busy.
        let mut screen = String::new();
        for _ in 0..100 {
            std::thread::sleep(std::time::Duration::from_millis(20));
            screen = term.screen_text();
            if screen.contains("stackwatch-ok") {
                break;
            }
        }
        assert!(
            screen.contains("stackwatch-ok"),
            "typed input must reach the shell and its output must land on the screen grid; got: {screen:?}"
        );

        assert!(term.is_alive(), "sh is still running until we kill it");
        term.kill();
    }

    #[test]
    fn test_spawn_errors_stay_short_enough_to_render() {
        // portable-pty appends the whole PATH to "no viable candidates", and StackWatch
        // hands the child a deliberately long one — ~600 chars. Painted into the drawer's
        // failure card that wall of text overran every section below it.
        let Err(err) = TermSession::spawn("/nonexistent/agent-cli", "") else {
            panic!("spawning a missing binary must fail");
        };
        // Chars, not bytes: the ellipsis is 3 bytes on its own.
        assert!(err.chars().count() <= 141, "failure card text must stay short, got {err:?}");
        assert!(!err.contains('\n'), "must be one line: {err:?}");

        let long = format!("Unable to spawn foo because:\nNo viable candidates found in PATH {}", "/some/dir:".repeat(60));
        let brief = brief_error(&long);
        assert_eq!(
            brief,
            "Unable to spawn foo because: No viable candidates found in PATH",
            "the searched directory list is dropped, not truncated mid-path"
        );
    }

    #[test]
    fn test_spawning_a_missing_binary_is_an_error_not_a_panic() {
        // The launch-failure card in the drawer is driven by this Err.
        assert!(TermSession::spawn("/nonexistent/agent-cli", "").is_err());
    }
}

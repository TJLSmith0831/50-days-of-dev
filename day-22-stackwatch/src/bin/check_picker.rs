//! Regression check for the launch form's folder picker.
//!
//! This bug has now bitten twice — first as a nested-run-loop beachball (sync
//! `rfd::FileDialog`), then as a dead sheet on an inactive Accessory app. Neither is
//! reachable from `cargo test`: both are AppKit window-state bugs that only exist once
//! a real HUD window is on screen. So this is a *runnable* check, not a unit test.
//!
//! It recreates the HUD's window shape (borderless, transparent, `NSStatusWindowLevel+1`,
//! Accessory), fires the picker with no human click, and asserts the invariant the fix
//! restored: **the panel comes up key, in an active app**. A visible-but-not-key panel is
//! exactly what the user sees as "the folder button hangs with a spinning cursor" —
//! the sheet makes the HUD window-modal while accepting no input itself.
//!
//! The check only means anything with another app in front — that is the whole bug — so it
//! brings Finder forward first and reports exit 2 (inconclusive) if it failed to.
//!
//! Run: `cargo run --bin check_picker` — exit 0 pass, 1 fail, 2 inconclusive. Brings Finder
//! forward and leaves an Open panel on screen for ~7s; ignore both, it kills itself.
//! `NO_FIX=1` skips `activate_app()` and must fail — that is what keeps this honest.

#[path = "../notch.rs"]
mod notch;

use std::sync::{Arc, Mutex};
use std::time::Duration;

use stackwatch::HudMode;
use eframe::egui;

const STEAL_FOCUS_AT: u32 = 15; // put another app in front, as in real use
const FIRE_AT: u32 = 60; // ~2s in — window on screen, focus definitively elsewhere
const VERDICT_AT: u32 = 270; // ~9s in

struct Check {
    rt: tokio::runtime::Handle,
    picked: Arc<Mutex<Option<String>>>,
    frame: u32,
    panel_was_key: bool,
    saw_panel: bool,
    fired: bool,
    was_background: bool,
}

impl eframe::App for Check {
    fn clear_color(&self, _v: &egui::Visuals) -> [f32; 4] {
        [0.0, 0.0, 0.0, 0.0]
    }

    fn update(&mut self, ctx: &egui::Context, _f: &mut eframe::Frame) {
        ctx.request_repaint_after(Duration::from_millis(33));
        self.frame += 1;

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.label("check_picker");
        });

        // Reproduce the state the user is actually in: the HUD is a non-activating status
        // window, so clicking it never makes this app active — some other app is front.
        if self.frame == STEAL_FOCUS_AT {
            let _ = std::process::Command::new("open").args(["-a", "Finder"]).spawn();
        }
        if self.frame == FIRE_AT - 1 {
            self.was_background = !app_is_active();
        }

        if self.frame == FIRE_AT {
            self.fired = true;
            // Same two steps as the 📁 button in main.rs, in the same order.
            if std::env::var("NO_FIX").is_err() {
                notch::activate_app();
            }
            let slot = self.picked.clone();
            let start = std::env::var("HOME").unwrap_or_default();
            self.rt.spawn(async move {
                let mut dialog = rfd::AsyncFileDialog::new();
                if !start.is_empty() {
                    dialog = dialog.set_directory(&start);
                }
                if let Some(h) = dialog.pick_folder().await {
                    *slot.lock().unwrap() = Some(h.path().to_string_lossy().to_string());
                }
            });
        }

        if self.fired && self.frame % 15 == 0 {
            let (saw, key) = probe_panel();
            self.saw_panel |= saw;
            self.panel_was_key |= key;
        }

        if self.frame >= VERDICT_AT {
            if !self.was_background {
                println!(
                    "INCONCLUSIVE: this app was still frontmost when the picker fired; \
                     the check could not reproduce the background-app state"
                );
                std::process::exit(2);
            }
            let ok = self.saw_panel && self.panel_was_key;
            if ok {
                println!("PASS: folder panel came up key in an active app");
            } else {
                println!(
                    "FAIL: panel_shown={} panel_key={} — the picker is presented but dead; \
                     the HUD is now sheet-blocked and the cursor will spin forever",
                    self.saw_panel, self.panel_was_key
                );
            }
            std::process::exit(if ok { 0 } else { 1 });
        }
    }
}

/// `(a panel is on screen, that panel is the key window)`.
#[cfg(target_os = "macos")]
fn probe_panel() -> (bool, bool) {
    use objc2_app_kit::NSApplication;
    use objc2_foundation::MainThreadMarker;

    let Some(mtm) = MainThreadMarker::new() else {
        return (false, false);
    };
    let app = NSApplication::sharedApplication(mtm);
    let active = unsafe { app.isActive() };
    let mut shown = false;
    let mut key = false;
    for w in app.windows().iter() {
        // rfd presents the picker with `beginSheetModalForWindow:`, so the panel is the
        // one window reporting `isSheet`.
        if unsafe { w.isSheet() } && w.isVisible() {
            shown = true;
            key |= w.isKeyWindow() && active;
        }
    }
    (shown, key)
}

#[cfg(not(target_os = "macos"))]
fn probe_panel() -> (bool, bool) {
    (true, true)
}

#[cfg(target_os = "macos")]
fn app_is_active() -> bool {
    use objc2_app_kit::NSApplication;
    use objc2_foundation::MainThreadMarker;
    MainThreadMarker::new()
        .map(|mtm| unsafe { NSApplication::sharedApplication(mtm).isActive() })
        .unwrap_or(false)
}

#[cfg(not(target_os = "macos"))]
fn app_is_active() -> bool {
    false
}

fn main() {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let handle = rt.handle().clone();
    std::mem::forget(rt);

    let geometry = notch::detect_geometry();
    let (w, h) = geometry.hud_size(HudMode::Collapsed);
    let (x, y) = geometry.dock_position(w);

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("check_picker")
            .with_inner_size([w, h])
            .with_position([x, y])
            .with_transparent(true)
            .with_decorations(false)
            .with_always_on_top()
            .with_resizable(false)
            .with_active(false),
        ..Default::default()
    };

    eframe::run_native(
        "check_picker",
        options,
        Box::new(move |cc| {
            notch::dock_window(cc);
            Ok(Box::new(Check {
                rt: handle,
                picked: Arc::new(Mutex::new(None)),
                frame: 0,
                panel_was_key: false,
                saw_panel: false,
                fired: false,
                was_background: false,
            }))
        }),
    )
    .unwrap();
}

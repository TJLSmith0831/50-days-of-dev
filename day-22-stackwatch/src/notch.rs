//! AppKit glue. Two jobs winit/eframe can't do for us:
//! read the physical notch geometry, and get the window above the menu bar.

use stackwatch::NotchGeometry;

#[cfg(target_os = "macos")]
pub fn detect_geometry() -> NotchGeometry {
    use objc2_app_kit::NSScreen;
    use objc2_foundation::MainThreadMarker;

    // ponytail: 1512.0 is the 14" MacBook Pro logical width — only reached if AppKit
    // hands us nothing, in which case any guess is equally wrong.
    let Some(mtm) = MainThreadMarker::new() else {
        return NotchGeometry::fallback(1512.0);
    };
    let Some(screen) = NSScreen::mainScreen(mtm) else {
        return NotchGeometry::fallback(1512.0);
    };

    let screen_width = screen.frame().size.width as f32;

    // Screens without a notch report a zero-sized auxiliary area. On notched screens
    // the two auxiliary areas flank the cutout, so the cutout is what's left over.
    let aux_width = unsafe { screen.auxiliaryTopLeftArea() }.size.width as f32;
    if aux_width <= 0.0 {
        return NotchGeometry::fallback(screen_width);
    }

    let notch_width = (screen_width - aux_width * 2.0).max(0.0);
    let notch_height = unsafe { screen.safeAreaInsets() }.top as f32;
    if notch_width <= 0.0 || notch_height <= 0.0 {
        return NotchGeometry::fallback(screen_width);
    }

    NotchGeometry {
        screen_width,
        notch_width,
        notch_height,
    }
}

#[cfg(not(target_os = "macos"))]
pub fn detect_geometry() -> NotchGeometry {
    NotchGeometry::fallback(1512.0)
}

/// Promote the eframe window from an app window to a menu-bar-level HUD.
#[cfg(target_os = "macos")]
pub fn dock_window(cc: &eframe::CreationContext<'_>) {
    use objc2_app_kit::{
        NSApplication, NSApplicationActivationPolicy, NSStatusWindowLevel, NSView,
        NSWindowCollectionBehavior,
    };
    use objc2_foundation::MainThreadMarker;
    use raw_window_handle::{HasWindowHandle, RawWindowHandle};

    let Some(mtm) = MainThreadMarker::new() else {
        return;
    };

    // A HUD has no business in the Dock or the app switcher.
    NSApplication::sharedApplication(mtm)
        .setActivationPolicy(NSApplicationActivationPolicy::Accessory);

    let Ok(handle) = cc.window_handle() else {
        return;
    };
    let RawWindowHandle::AppKit(handle) = handle.as_raw() else {
        return;
    };
    // Safety: eframe hands us a live NSView for the window it just created, and we are
    // on the main thread (proved by `mtm`).
    let view: &NSView = unsafe { handle.ns_view.cast().as_ref() };
    let Some(window) = view.window() else {
        return;
    };

    // The root bug behind "it hides under the menu bar": `with_always_on_top` gives
    // NSFloatingWindowLevel (3), but the menu bar sits at 24. 26 clears both.
    window.setLevel(NSStatusWindowLevel + 1);
    unsafe {
        window.setCollectionBehavior(
            NSWindowCollectionBehavior::CanJoinAllSpaces
                | NSWindowCollectionBehavior::Stationary
                | NSWindowCollectionBehavior::FullScreenAuxiliary,
        );
    }
    // A drop shadow under a notch-flush window draws a grey smear across the wallpaper.
    window.setHasShadow(false);
    window.setMovable(false);
}

/// Bring the HUD's process to the front. Call before presenting any AppKit panel.
///
/// An `Accessory` app never activates on its own — clicking the HUD gives its window
/// focus without making the *app* active. `NSOpenPanel` (what the folder picker is
/// underneath) is presented as a sheet on the HUD window, and a sheet whose owning app
/// is inactive is visible but dead: it can't become key, clicks land nowhere, the
/// completion handler never fires, and macOS paints the spinning-wait cursor over a
/// HUD that the sheet has made window-modal. Activating first makes the panel key.
#[cfg(target_os = "macos")]
pub fn activate_app() {
    use objc2_app_kit::NSApplication;
    use objc2_foundation::MainThreadMarker;

    let Some(mtm) = MainThreadMarker::new() else {
        return;
    };
    // ponytail: `activateIgnoringOtherApps` is soft-deprecated in favour of `activate()`
    // on macOS 14+, but the replacement won't pull a background Accessory app forward.
    #[allow(deprecated)]
    NSApplication::sharedApplication(mtm).activateIgnoringOtherApps(true);
}

#[cfg(not(target_os = "macos"))]
pub fn dock_window(_cc: &eframe::CreationContext<'_>) {}

#[cfg(not(target_os = "macos"))]
pub fn activate_app() {}

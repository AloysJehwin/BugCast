#!/usr/bin/env python3
"""Generate ~20 Module 1 fixture / ground-truth pairs for benchmarking."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"
GROUND_TRUTH_DIR = ROOT / "tests" / "ground_truth"

SCENARIOS = [
    {
        "id": "login_timeout",
        "app": "ShopPortal",
        "platform": "web",
        "title": "Login request times out after submitting valid credentials",
        "severity": "high",
        "labels": ["bug", "ui"],
        "frames": [
            {"ocr": ["Welcome back", "Email", "Password", "Sign in"], "ui": [("input", "Email"), ("button", "Sign in")]},
            {"ocr": ["Signing in...", "Please wait"], "ui": [("spinner", "Loading")]},
            {"ocr": ["Request timed out", "Unable to reach server"], "ui": [("dialog", "Network Error"), ("button", "Retry")]},
        ],
    },
    {
        "id": "checkout_crash",
        "app": "CartFlow",
        "platform": "ios",
        "title": "App crashes when tapping Pay Now on checkout screen",
        "severity": "critical",
        "labels": ["bug", "crash"],
        "frames": [
            {"ocr": ["Your cart", "Total $42.00", "Pay Now"], "ui": [("button", "Pay Now")]},
            {"ocr": ["Processing payment"], "ui": [("text", "Processing payment")]},
            {"ocr": ["App closed unexpectedly"], "ui": [("alert", "Crash report")]},
        ],
    },
    {
        "id": "search_no_results",
        "app": "DocFinder",
        "platform": "web",
        "title": "Search returns empty list despite matching documents",
        "severity": "medium",
        "labels": ["bug", "regression"],
        "frames": [
            {"ocr": ["Search documents", "invoice"], "ui": [("input", "Search"), ("button", "Search")]},
            {"ocr": ["0 results", "No documents found"], "ui": [("list", "empty")]},
            {"ocr": ["Filter: All types", "invoice"], "ui": [("chip", "invoice")]},
        ],
    },
    {
        "id": "dark_mode_contrast",
        "app": "NotesPlus",
        "platform": "android",
        "title": "Unreadable placeholder text in dark mode on new note screen",
        "severity": "medium",
        "labels": ["bug", "ui", "accessibility"],
        "frames": [
            {"ocr": ["New note", "Title", "Start writing..."], "ui": [("input", "Title"), ("textarea", "Start writing...")]},
            {"ocr": ["Dark theme enabled"], "ui": [("toggle", "Dark mode")]},
            {"ocr": ["Start writing...", "low contrast"], "ui": [("textarea", "Start writing...")]},
        ],
    },
    {
        "id": "export_csv_corrupt",
        "app": "DataDesk",
        "platform": "desktop",
        "title": "Exported CSV file opens with garbled characters",
        "severity": "high",
        "labels": ["bug", "regression"],
        "frames": [
            {"ocr": ["Reports", "Export CSV"], "ui": [("button", "Export CSV")]},
            {"ocr": ["Export complete", "report_march.csv"], "ui": [("toast", "Export complete")]},
            {"ocr": ["Ã©", "garbled", "encoding error"], "ui": [("preview", "CSV preview")]},
        ],
    },
    {
        "id": "notification_duplicate",
        "app": "TeamChat",
        "platform": "web",
        "title": "Duplicate push notifications sent for a single mention",
        "severity": "low",
        "labels": ["bug", "performance"],
        "frames": [
            {"ocr": ["@alex can you review?", "Send"], "ui": [("button", "Send")]},
            {"ocr": ["Mentioned you", "Mentioned you"], "ui": [("toast", "Mentioned you"), ("toast", "Mentioned you")]},
        ],
    },
    {
        "id": "profile_image_upload",
        "app": "ProfileHub",
        "platform": "web",
        "title": "Profile photo upload fails with generic error for PNG files",
        "severity": "medium",
        "labels": ["bug", "ui"],
        "frames": [
            {"ocr": ["Edit profile", "Upload photo"], "ui": [("button", "Upload photo")]},
            {"ocr": ["avatar.png", "2.1 MB"], "ui": [("file", "avatar.png")]},
            {"ocr": ["Upload failed", "Something went wrong"], "ui": [("dialog", "Upload failed")]},
        ],
    },
    {
        "id": "calendar_timezone",
        "app": "ScheduleIt",
        "platform": "web",
        "title": "Meetings shift by one hour after daylight saving change",
        "severity": "high",
        "labels": ["bug", "regression"],
        "frames": [
            {"ocr": ["Team sync", "10:00 AM PST"], "ui": [("event", "Team sync")]},
            {"ocr": ["Timezone: America/Los_Angeles"], "ui": [("select", "Timezone")]},
            {"ocr": ["Team sync", "11:00 AM PST"], "ui": [("event", "Team sync")]},
        ],
    },
    {
        "id": "password_reset_link",
        "app": "AuthGate",
        "platform": "web",
        "title": "Password reset link expires immediately after email is sent",
        "severity": "high",
        "labels": ["bug"],
        "frames": [
            {"ocr": ["Forgot password?", "Send reset link"], "ui": [("button", "Send reset link")]},
            {"ocr": ["Check your email"], "ui": [("text", "Email sent")]},
            {"ocr": ["Link expired", "Request a new link"], "ui": [("dialog", "Link expired")]},
        ],
    },
    {
        "id": "video_buffering",
        "app": "StreamBox",
        "platform": "android",
        "title": "Live stream stalls indefinitely on mobile data",
        "severity": "medium",
        "labels": ["bug", "performance"],
        "frames": [
            {"ocr": ["Live now", "Play"], "ui": [("button", "Play")]},
            {"ocr": ["Buffering...", "0:00"], "ui": [("spinner", "Buffering")]},
            {"ocr": ["Playback error", "Try again"], "ui": [("dialog", "Playback error")]},
        ],
    },
    {
        "id": "form_validation",
        "app": "SignupFlow",
        "platform": "web",
        "title": "Phone number field accepts invalid values without validation message",
        "severity": "medium",
        "labels": ["bug", "ui"],
        "frames": [
            {"ocr": ["Create account", "Phone", "abc123"], "ui": [("input", "Phone")]},
            {"ocr": ["Continue"], "ui": [("button", "Continue")]},
            {"ocr": ["Welcome"], "ui": [("text", "Welcome")]},
        ],
    },
    {
        "id": "offline_sync",
        "app": "FieldNotes",
        "platform": "ios",
        "title": "Offline edits are lost after reconnecting to network",
        "severity": "critical",
        "labels": ["bug", "regression"],
        "frames": [
            {"ocr": ["Offline mode", "Saved locally"], "ui": [("badge", "Offline")]},
            {"ocr": ["Back online", "Syncing..."], "ui": [("text", "Syncing")]},
            {"ocr": ["Sync failed", "Changes discarded"], "ui": [("dialog", "Sync failed")]},
        ],
    },
    {
        "id": "keyboard_trap",
        "app": "SupportDesk",
        "platform": "web",
        "title": "Keyboard focus trapped inside modal and cannot reach close button",
        "severity": "high",
        "labels": ["bug", "accessibility", "ui"],
        "frames": [
            {"ocr": ["Help", "Contact support"], "ui": [("button", "Contact support")]},
            {"ocr": ["Support chat", "Message", "Send"], "ui": [("modal", "Support chat"), ("input", "Message")]},
            {"ocr": ["Tab", "Shift+Tab", "focus trap"], "ui": [("modal", "Support chat")]},
        ],
    },
    {
        "id": "invoice_pdf_blank",
        "app": "BillingPro",
        "platform": "desktop",
        "title": "Generated invoice PDF is blank for multi-page orders",
        "severity": "high",
        "labels": ["bug"],
        "frames": [
            {"ocr": ["Order #8821", "Download PDF"], "ui": [("button", "Download PDF")]},
            {"ocr": ["Generating PDF..."], "ui": [("text", "Generating PDF")]},
            {"ocr": ["Blank page", "0 items rendered"], "ui": [("preview", "PDF preview")]},
        ],
    },
    {
        "id": "map_marker_offset",
        "app": "RideMap",
        "platform": "android",
        "title": "Pickup marker appears offset from actual GPS location",
        "severity": "medium",
        "labels": ["bug", "ui"],
        "frames": [
            {"ocr": ["Set pickup", "Current location"], "ui": [("button", "Current location")]},
            {"ocr": ["123 Main St"], "ui": [("marker", "Pickup")]},
            {"ocr": ["You are here", "200m away"], "ui": [("marker", "You are here")]},
        ],
    },
    {
        "id": "settings_not_saved",
        "app": "PrefsKit",
        "platform": "web",
        "title": "Notification settings revert after page refresh",
        "severity": "medium",
        "labels": ["bug", "regression"],
        "frames": [
            {"ocr": ["Settings", "Email alerts", "On"], "ui": [("toggle", "Email alerts")]},
            {"ocr": ["Saved"], "ui": [("toast", "Saved")]},
            {"ocr": ["Email alerts", "Off"], "ui": [("toggle", "Email alerts")]},
        ],
    },
    {
        "id": "api_rate_limit",
        "app": "DevConsole",
        "platform": "web",
        "title": "API key test button triggers rate limit on first click",
        "severity": "high",
        "labels": ["bug", "performance"],
        "frames": [
            {"ocr": ["API Keys", "Test connection"], "ui": [("button", "Test connection")]},
            {"ocr": ["429 Too Many Requests"], "ui": [("alert", "Rate limited")]},
        ],
    },
    {
        "id": "comment_thread_order",
        "app": "ReviewBoard",
        "platform": "web",
        "title": "Comment thread displays replies in reverse chronological order",
        "severity": "low",
        "labels": ["bug", "ui"],
        "frames": [
            {"ocr": ["Comments", "Reply"], "ui": [("button", "Reply")]},
            {"ocr": ["Alice", "Bob", "Carol"], "ui": [("list", "comments")]},
            {"ocr": ["Carol", "Bob", "Alice"], "ui": [("list", "comments")]},
        ],
    },
    {
        "id": "memory_leak_dashboard",
        "app": "OpsPanel",
        "platform": "desktop",
        "title": "Dashboard memory usage grows continuously while idle",
        "severity": "high",
        "labels": ["bug", "performance"],
        "frames": [
            {"ocr": ["Dashboard", "CPU 12%", "Memory 1.2 GB"], "ui": [("chart", "Memory")]},
            {"ocr": ["Memory 2.8 GB"], "ui": [("chart", "Memory")]},
            {"ocr": ["Memory 4.5 GB", "Warning"], "ui": [("alert", "High memory usage")]},
        ],
    },
    {
        "id": "tooltip_clipped",
        "app": "DesignLab",
        "platform": "web",
        "title": "Toolbar tooltip is clipped at viewport edge on small screens",
        "severity": "low",
        "labels": ["bug", "ui", "accessibility"],
        "frames": [
            {"ocr": ["Align left", "Tooltip"], "ui": [("button", "Align left")]},
            {"ocr": ["Align left"], "ui": [("tooltip", "Align selected objects to the left edge")]},
            {"ocr": ["...", "clipped"], "ui": [("tooltip", "Align selected")]},
        ],
    },
]


def _build_fixture(scenario: dict) -> dict:
    frames = []
    for index, frame in enumerate(scenario["frames"]):
        frames.append(
            {
                "frame_id": f"f{index:03d}",
                "timestamp_ms": (index + 1) * 1500,
                "ocr_text": frame["ocr"],
                "ui_elements": [{"type": ui_type, "text": text} for ui_type, text in frame["ui"]],
            }
        )
    return {
        "version": "1.0",
        "session_id": scenario["id"],
        "metadata": {
            "app_name": scenario["app"],
            "platform": scenario["platform"],
            "recorded_at": "2026-03-01T12:00:00Z",
            "duration_ms": len(frames) * 1500,
            "reporter": "qa@example.com",
        },
        "frames": frames,
        "events": [
            {"type": "interaction", "timestamp_ms": 1000, "target": scenario["title"]},
        ],
    }


def _build_ground_truth(scenario: dict) -> dict:
    steps = "\n".join(f"{index + 1}. Observe UI state: {frame['ocr'][0]}" for index, frame in enumerate(scenario["frames"]))
    body = (
        "## Description\n"
        f"During a recorded session in {scenario['app']}, the user encountered: {scenario['title']}.\n\n"
        "## Steps to Reproduce\n"
        f"{steps}\n\n"
        "## Expected Behavior\n"
        "The application should complete the user flow without errors.\n\n"
        "## Actual Behavior\n"
        f"The session shows failure indicators including: {scenario['frames'][-1]['ocr'][0]}.\n\n"
        "## Environment\n"
        f"- App: {scenario['app']}\n"
        f"- Platform: {scenario['platform']}\n"
    )
    return {
        "title": scenario["title"],
        "body": body,
        "labels": scenario["labels"],
        "severity": scenario["severity"],
    }


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    for scenario in SCENARIOS:
        fixture_path = FIXTURES_DIR / f"{scenario['id']}.json"
        truth_path = GROUND_TRUTH_DIR / f"{scenario['id']}.json"
        fixture_path.write_text(json.dumps(_build_fixture(scenario), indent=2) + "\n", encoding="utf-8")
        truth_path.write_text(json.dumps(_build_ground_truth(scenario), indent=2) + "\n", encoding="utf-8")

    print(f"Generated {len(SCENARIOS)} fixture pairs in {FIXTURES_DIR} and {GROUND_TRUTH_DIR}")


if __name__ == "__main__":
    main()

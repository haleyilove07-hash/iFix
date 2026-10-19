"""Read-only iOS device diagnostics for the iFix support app."""

import platform
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk


APP_DIR = Path(__file__).resolve().parent
BACKGROUND = "#f2f5f2"
PAPER = "#ffffff"
INK = "#17231f"
MUTED = "#62716a"
ACCENT = "#14765c"
WARNING = "#a75723"


def device_info_command():
    """Find an installed read-only libimobiledevice command."""
    system_command = shutil.which("ideviceinfo")
    if system_command:
        return [system_command]

    if sys.platform == "darwin":
        bundled_command = APP_DIR / "device" / "ideviceinfo"
        if bundled_command.is_file():
            return [str(bundled_command)]

    return None


def parse_device_info(output):
    """Extract only non-identifying fields from ideviceinfo output."""
    fields = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()

    return {
        "Model": fields.get("ProductType") or fields.get("HardwareModel"),
        "iOS version": fields.get("ProductVersion"),
        "Build": fields.get("BuildVersion"),
        "Device class": fields.get("DeviceClass"),
    }


def collect_diagnostics():
    """Query a trusted host ideviceinfo installation without shell commands."""
    command = device_info_command()
    if command is None:
        if sys.platform == "darwin":
            install_hint = "Install libimobiledevice with Homebrew: brew install libimobiledevice."
        else:
            install_hint = "Install libimobiledevice-utils with your system package manager."
        return {"error": f"ideviceinfo was not found. {install_hint}"}

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except subprocess.TimeoutExpired:
        return {"error": "The device check timed out. Reconnect the device and try again."}
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip().splitlines()
        message = detail[-1][:240] if detail else "No trusted device was detected."
        return {"error": f"Device check failed: {message}"}
    except OSError as error:
        return {"error": f"Could not start ideviceinfo: {error.strerror or error}"}

    details = parse_device_info(result.stdout)
    if not details["Model"] and not details["iOS version"]:
        return {"error": "The connected device returned no model or iOS version."}
    return {"details": details}


class IFixApp:
    def __init__(self, root):
        self.root = root
        self.results = queue.Queue()
        self.busy = False
        self.values = {}

        root.title("iFix | Device Support")
        root.geometry("740x560")
        root.minsize(640, 520)
        root.configure(background=BACKGROUND)

        style = ttk.Style(root)
        style.configure("TFrame", background=BACKGROUND)
        style.configure("Card.TFrame", background=PAPER)
        style.configure("TLabel", background=BACKGROUND, foreground=INK, font=("TkDefaultFont", 10))
        style.configure("Title.TLabel", font=("TkDefaultFont", 23, "bold"))
        style.configure("Subtitle.TLabel", foreground=MUTED)
        style.configure("CardLabel.TLabel", background=PAPER, foreground=MUTED, font=("TkDefaultFont", 9))
        style.configure("CardValue.TLabel", background=PAPER, foreground=INK, font=("TkDefaultFont", 12, "bold"))
        style.configure("Status.TLabel", font=("TkDefaultFont", 10, "bold"))
        style.configure("Accent.TButton", font=("TkDefaultFont", 10, "bold"), padding=(12, 8))
        style.configure("TButton", padding=(10, 7))

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        content = ttk.Frame(self.root, padding=(28, 24, 28, 20))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        ttk.Label(content, text="iFix", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(content, text="DEVICE SUPPORT", foreground=ACCENT, font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(
            content,
            text="Read-only diagnostics for a connected iPhone or iPad.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 20))

        status_frame = ttk.Frame(content, style="Card.TFrame", padding=(16, 12))
        status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        status_frame.columnconfigure(0, weight=1)
        self.status = ttk.Label(status_frame, text="Checking for a device...", style="Status.TLabel")
        self.status.grid(row=0, column=0, sticky="w")
        self.refresh_button = ttk.Button(status_frame, text="Refresh", command=self.refresh)
        self.refresh_button.grid(row=0, column=1, sticky="e")

        card_specs = (("Model", 3, 0), ("iOS version", 3, 1), ("Build", 4, 0), ("Device class", 4, 1))
        for name, row, column in card_specs:
            card = ttk.Frame(content, style="Card.TFrame", padding=(16, 12))
            card.grid(row=row, column=column, sticky="nsew", padx=(0, 6) if column == 0 else (6, 0), pady=6)
            ttk.Label(card, text=name.upper(), style="CardLabel.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="Not available", style="CardValue.TLabel")
            value.pack(anchor="w", pady=(5, 0))
            self.values[name] = value

        actions = ttk.Frame(content)
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 12))
        actions.columnconfigure(0, weight=1)
        self.copy_button = ttk.Button(
            actions,
            text="Copy diagnostic report",
            style="Accent.TButton",
            command=self.copy_report,
            state="disabled",
        )
        self.copy_button.grid(row=0, column=0, sticky="w")
        ttk.Button(
            actions,
            text="Apple Support",
            command=lambda: webbrowser.open("https://support.apple.com/contact"),
        ).grid(row=0, column=1, sticky="e")

        ttk.Label(
            content,
            text="For a supervised or organization-managed device, contact its administrator. "
            "This app does not change device settings or management profiles.",
            style="Subtitle.TLabel",
            wraplength=660,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def refresh(self):
        if self.busy:
            return

        self.busy = True
        self.refresh_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.status.configure(text="Checking for a device...", foreground=MUTED)
        for value in self.values.values():
            value.configure(text="Not available")

        threading.Thread(target=self._run_check, daemon=True).start()
        self.root.after(100, self._poll_results)

    def _run_check(self):
        self.results.put(collect_diagnostics())

    def _poll_results(self):
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_results)
            return

        self.busy = False
        self.refresh_button.configure(state="normal")
        if "error" in result:
            self.status.configure(text=result["error"], foreground=WARNING)
            return

        self.details = result["details"]
        self.status.configure(text="Device detected", foreground=ACCENT)
        for name, value in self.details.items():
            self.values[name].configure(text=value or "Not reported")
        self.copy_button.configure(state="normal")

    def copy_report(self):
        if not hasattr(self, "details"):
            return

        lines = ["iFix device diagnostic report", f"Computer: {platform.system()} {platform.release()}"]
        lines.extend(f"{name}: {value or 'Not reported'}" for name, value in self.details.items())
        lines.append("Device identifiers are intentionally excluded.")
        report = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(report)
        self.status.configure(text="Redacted report copied to clipboard", foreground=ACCENT)


if __name__ == "__main__":
    application = tk.Tk()
    IFixApp(application)
    application.mainloop()
#!/usr/bin/env python3
"""iFix - iOS 12-16 MDM bypass GUI (checkra1n / palera1n).

Runs on macOS and Linux, and on Windows 11 through WSL 2 (see WINDOWS.md).
Designed and developed by @hackt1vator
"""

import os
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser

try:
    import tkinter as tk
    from tkinter import *
    from tkinter import messagebox
    from tkinter.messagebox import showinfo
    from tkinter.simpledialog import askstring

    from PIL import Image, ImageTk

    TK_ERROR = None
except ImportError as exc:  # no GUI toolkit here; --doctor still works
    tk = None
    messagebox = None
    showinfo = None
    askstring = None
    Image = None
    ImageTk = None
    TK_ERROR = exc

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

IS_WINDOWS = os.name == "nt"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Provided by libimobiledevice / libusbmuxd / sshpass on Linux and WSL, and by
# the bundled Mach-O binaries in ./device on macOS.
TOOLS = ("ideviceinfo", "ideviceenterrecovery", "irecovery", "iproxy", "sshpass")

# A palera1n build we can exec directly, checked before falling back to PATH.
PALERA1N_BINARIES = ("palera1n-linux-x86_64", "palera1n-linux-arm64", "palera1n")

UDID_PATTERN = re.compile(r"^UniqueDeviceID:\s*([0-9a-fA-F]{24,40})\b", re.MULTILINE)
MODE_PATTERN = re.compile(r"^MODE:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
ECID_PATTERN = re.compile(r"^ECID:\s*(\S+)", re.MULTILINE | re.IGNORECASE)

# checkm8 DFU entry for A8-A11 (iPhone 6s through iPhone X). The iPhone 8/X use
# the Side button; on the 6s/7 it is the top (power) button.
DFU_SEQUENCE = (
    ("Press and release Volume Up", 1),
    ("Press and release Volume Down", 1),
    ("Hold the Side button for 10s", 10),
    ("Keep holding Side, then press and hold Volume Down for 5s", 5),
    ("Release Side, keep holding Volume Down for 10s", 10),
    ("Release Volume Down", 1),
)
DFU_TIMEOUT = 12

if Image is None:
    RESAMPLE = None
elif hasattr(Image, "Resampling"):  # Pillow >= 9.1 (Image.ANTIALIAS was removed in 10)
    RESAMPLE = Image.Resampling.LANCZOS
else:
    RESAMPLE = Image.LANCZOS


# --------------------------------------------------------------------------- #
# Platform layer
# --------------------------------------------------------------------------- #

_wsl_repo = None


def repo_path():
    """Repository directory as the shell below will see it."""
    global _wsl_repo
    if not IS_WINDOWS:
        return SCRIPT_DIR
    if _wsl_repo is None:
        try:
            result = subprocess.run(
                ["wsl", "-e", "wslpath", "-a", SCRIPT_DIR],
                capture_output=True, text=True, timeout=120,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "WSL is not installed. Run windows/install.ps1 from an elevated "
                "PowerShell, reboot, then try again."
            )
        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError(
                "Could not map the repository path into WSL: "
                + (result.stderr or "unknown error").strip()
            )
        _wsl_repo = result.stdout.strip()
    return _wsl_repo


def shell_command(command):
    """argv that runs `command` with the repository as the working directory."""
    script = "cd {} && {}".format(shlex.quote(repo_path()), command)
    if IS_WINDOWS:
        return ["wsl", "-e", "bash", "-lc", script]
    return ["bash", "-lc", script]


def run_shell(command, capture=False):
    """Run a shell command in the repository directory; inside WSL on Windows."""
    if capture:
        return subprocess.run(
            shell_command(command), capture_output=True, text=True, errors="replace"
        )
    return subprocess.run(shell_command(command))


def popen_shell(command):
    kwargs = {"start_new_session": True}
    if IS_WINDOWS:
        kwargs = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return subprocess.Popen(shell_command(command), **kwargs)


def terminate(process):
    """Stop a process tree started by popen_shell()."""
    if process.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            process.terminate()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.terminate()
        except OSError:
            pass


def tool_command(tool):
    """Command string for an idevice helper tool."""
    if IS_MACOS:
        if os.path.isfile(os.path.join(SCRIPT_DIR, "device", tool)):
            return "./device/" + tool
        return tool
    if IS_WINDOWS:
        return tool  # resolved by bash inside WSL
    return tool if shutil.which(tool) else "./device/" + tool


def tool_available(tool):
    if IS_MACOS:
        return os.path.isfile(os.path.join(SCRIPT_DIR, "device", tool)) or bool(
            shutil.which(tool)
        )
    if IS_WINDOWS:
        try:
            return subprocess.run(
                ["wsl", "-e", "bash", "-lc", "command -v " + tool],
                capture_output=True, timeout=120,
            ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    return bool(shutil.which(tool))


def palera1n_binary():
    if IS_MACOS:
        return "./palera1n-macos-universal"
    for name in PALERA1N_BINARIES:
        if os.path.isfile(os.path.join(SCRIPT_DIR, name)):
            return "./" + name
    return "palera1n"  # from PATH, or windows/setup-wsl.sh puts one in place


def parse_udid(info_text):
    """UDID from `ideviceinfo` output, or None."""
    if not info_text or "ERROR:" in info_text:
        return None
    match = UDID_PATTERN.search(info_text)
    return match.group(1) if match else None


def read_device_info():
    """Pair with the connected device and return its `ideviceinfo` output."""
    pair = tool_command("idevicepair")
    run_shell("{} unpair >/dev/null 2>&1 || true".format(pair))
    run_shell("{} pair >/dev/null 2>&1 || true".format(pair))
    result = run_shell(tool_command("ideviceinfo"), capture=True)
    info = (result.stdout or "") + (result.stderr or "")

    if parse_udid(info):  # keep the historical on-disk copy, but never clobber it
        try:            # with an error string when no device is attached
            with open(os.path.join(SCRIPT_DIR, "device", "lastdevice.txt"), "w") as handle:
                handle.write(info)
        except OSError:
            pass
    return info


# --------------------------------------------------------------------------- #
# DFU helper
# --------------------------------------------------------------------------- #


def irecovery_info():
    """`irecovery -q` output, which works while the device is in DFU or recovery."""
    if not tool_available("irecovery"):
        return ""
    result = run_shell(tool_command("irecovery") + " -q", capture=True)
    return ((result.stdout or "") + (result.stderr or "")).strip()


def device_mode():
    """'dfu', 'recovery', 'normal', or None when no device answers."""
    text = irecovery_info()
    if text and "unable to connect" not in text.lower():
        match = MODE_PATTERN.search(text)
        if match:
            return "dfu" if "dfu" in match.group(1).lower() else "recovery"
        upper = text.upper()
        if re.search(r"\bDFU\b", upper):
            return "dfu"
        if "CPID" in upper or "ECID" in upper:
            return "recovery"
    if tool_available("ideviceinfo"):
        result = run_shell(tool_command("ideviceinfo"), capture=True)
        if parse_udid((result.stdout or "") + (result.stderr or "")):
            return "normal"
    return None


def device_ecid():
    match = ECID_PATTERN.search(irecovery_info())
    return match.group(1) if match else None


def wait_for_mode(target, timeout=DFU_TIMEOUT):
    """Poll until the device reports `target`, or the timeout expires."""
    deadline = time.time() + timeout
    mode = None
    while True:
        mode = device_mode()
        if mode == target or time.time() >= deadline:
            return mode
        time.sleep(1)


def dfu_sequence(emit):
    """Walk the user through DFU, then detect it. `emit(kind, text)` reports progress."""
    emit("detail", "current mode: {}".format(device_mode() or "no device"))
    for index, (step, seconds) in enumerate(DFU_SEQUENCE, 1):
        emit("step", "[{}/{}] {}".format(index, len(DFU_SEQUENCE), step))
        for remaining in range(seconds, 0, -1):
            emit("detail", "{}s".format(remaining))
            time.sleep(1)

    emit("detail", "waiting for DFU...")
    mode = wait_for_mode("dfu")
    if mode == "dfu":
        ecid = device_ecid()
        emit("step", "DFU mode reached{}".format(" - ECID {}".format(ecid) if ecid else ""))
        return True
    emit("step", "Not in DFU mode ({})".format(mode or "no device seen"))
    emit("detail", "Unplug, reconnect and start again.")
    return False


def dfu_cli():
    """`python3 iFix.py --dfu` - the same walkthrough in the terminal."""

    def emit(kind, text):
        if kind == "step":
            print("\n" + text, flush=True)
        else:
            print("\r   " + text.ljust(34), end="", flush=True)

    print("iFix DFU helper - connect the device with a USB-A cable, then follow along.")
    ok = dfu_sequence(emit)
    print("")
    return 0 if ok else 2


def dfu_helper_window():
    """GUI counterpart: same sequence in a small window with live detection."""
    win = tk.Toplevel(root)
    win.title("DFU helper")
    win.geometry("440x230")
    win.resizable(False, False)
    win.transient(root)

    status = Label(
        win,
        text="Connect the device with a USB-A cable, then press start.",
        font=("Helvetica", 12),
        wraplength=400,
        justify="left",
    )
    status.pack(padx=15, pady=(15, 6))
    detail = Label(win, text="", wraplength=400, justify="left")
    detail.pack(padx=15)

    buttons = tk.Frame(win)
    buttons.pack(side="bottom", pady=12)
    start_button = tk.Button(buttons, text="start", width=10)
    start_button.pack(side="left", padx=6)
    tk.Button(buttons, text="close", width=10, command=win.destroy).pack(side="left", padx=6)

    messages = queue.Queue()

    def worker():
        try:
            dfu_sequence(lambda kind, text: messages.put((kind, text)))
        except Exception as exc:  # keep the window usable if a tool misbehaves
            messages.put(("step", "error: {}".format(exc)))
        messages.put(("done", ""))

    def poll():
        try:
            while True:
                kind, text = messages.get_nowait()
                if kind == "step":
                    status.config(text=text)
                elif kind == "detail":
                    detail.config(text=text)
                else:
                    start_button.config(state="normal")
        except queue.Empty:
            pass
        if win.winfo_exists():
            win.after(150, poll)

    def start():
        start_button.config(state="disabled")
        threading.Thread(target=worker, daemon=True).start()

    start_button.config(command=start)
    win.after(150, poll)


# --------------------------------------------------------------------------- #
# GUI actions
# --------------------------------------------------------------------------- #


def show_popup():
    popup = tk.Toplevel()
    popup.geometry("300x200")  # set the width and height of the window
    popup.title("palera1n")

    # center the window on the screen
    window_width = popup.winfo_reqwidth()
    window_height = popup.winfo_reqheight()
    position_right = int(popup.winfo_screenwidth() / 2 - window_width / 2)
    position_down = int(popup.winfo_screenheight() / 2 - window_height / 2)
    popup.geometry("+{}+{}".format(position_right, position_down))

    # create larger buttons
    button1 = tk.Button(popup, text="build fake fs", command=build_fakefs, width=20, height=5)
    button1.pack(pady=10)

    button2 = tk.Button(popup, text="boot fake fs", command=boot_fakefs, width=20, height=5)
    button2.pack(pady=10)


def run_palera1n(arguments):
    """Run palera1n with the retry dance the original flow relies on."""
    messagebox.showinfo("", "Please put the device into dfu")
    messagebox.askyesno("iphone?", "Do you have a A9 device?")

    command = "{} {}".format(palera1n_binary(), arguments)
    print("Running: " + command)

    # Wait up to 20 seconds for the first pass, then re-run it blocking.
    process = popen_shell(command)
    for _ in range(20):
        if process.poll() is not None:
            break
        time.sleep(1)
    terminate(process)

    return run_shell(command).returncode


def build_fakefs():
    if run_palera1n("-cf") != 0:
        messagebox.showinfo("", "palera1n exited with an error, check the console output.")
    messagebox.showinfo("", "After the device boots you can boot the fake fs")


def boot_fakefs():
    if run_palera1n("-f") != 0:
        messagebox.showinfo("", "palera1n exited with an error, check the console output.")
    messagebox.showinfo("", "Now start the bypass")


def startcheckra1n():
    if IS_MACOS:
        if os.path.isdir(os.path.join(SCRIPT_DIR, "checkra1n.app")):
            subprocess.run(["open", "./checkra1n.app"])
        else:
            messagebox.showerror("checkra1n", "checkra1n.app is missing from the iFix folder.")
        return

    if IS_WINDOWS:
        messagebox.showinfo(
            "checkra1n",
            "checkra1n is macOS only.\n\nOn Windows, jailbreak with palera1n instead "
            "(palen1x bootable USB), or boot a checkn1x USB for iOS 12-14.",
        )
        return

    if not shutil.which("checkra1n"):
        messagebox.showerror(
            "checkra1n",
            "checkra1n is not installed.\n\nInstall the Linux build of checkra1n, or "
            "boot a checkn1x USB stick to jailbreak iOS 12-14.",
        )
        return

    if shutil.which("pkexec"):
        subprocess.Popen(["pkexec", "checkra1n"])
    else:
        messagebox.showinfo(
            "checkra1n",
            "checkra1n needs root. Run this in a terminal:\n\n    sudo checkra1n",
        )


def showDFUMessage():
    messagebox.showinfo(
        "Step 1",
        "Put your iDevice into DFU mode.\n\nClick Ok once its ready in DFU mode to proceed.",
    )


def enterRecMode():
    info = read_device_info()
    udid = parse_udid(info)

    if not udid:
        messagebox.showinfo("No device detected! 0x404", "Try disconnecting and reconnecting your device.")
        return

    print("Kicking device into recovery mode...")
    run_shell("{} {}".format(tool_command("ideviceenterrecovery"), udid))


def exitRecMode():
    print("Kicking device out recovery mode...")
    run_shell(tool_command("irecovery") + " -n")


def quitProgram():
    print("Exiting...")
    root.destroy()


def opentwitter():
    webbrowser.open("https://www.twitter.com/hackt1vator", new=2)


def mdmbypass():
    print("Searching for connected device...")
    info = read_device_info()

    if not info.strip() or "ERROR:" in info:
        print("ERROR: No device found!")
        messagebox.showinfo(
            "No device detected! 0x404", "Try disconnecting and reconnecting your device."
        )
        return

    udid = parse_udid(info)
    if not udid:
        print("Couldn't find your device")
        messagebox.showinfo("", "No device connected")
        return

    missing = [tool for tool in TOOLS if not tool_available(tool)]
    if missing:
        messagebox.showerror(
            "Missing tools",
            "These tools are not available: {}\n\nOn Linux/WSL run:\n"
            "    sudo apt install libimobiledevice-utils libusbmuxd-tools usbmuxd sshpass"
            .format(", ".join(missing)),
        )
        return

    showinfo(
        "",
        "We will now bypass your device. Be sure to jailbreak your device first with palera1n or checkra1n",
    )
    print("Starting bypass...")
    result = run_shell("bash ./mdm.sh")

    if result.returncode != 0:
        messagebox.showerror(
            "bypass failed",
            "mdm.sh exited with code {}. Make sure the device is jailbroken and "
            "reachable over USB.".format(result.returncode),
        )
        return

    print("Device is bypassed\n")
    showinfo("bypass Success!", "Device is now bypassed!")


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #


def doctor():
    """`python3 iFix.py --doctor` - check the platform tooling without opening the GUI."""
    ok = True
    print("iFix doctor")
    print("  python   :", sys.version.split()[0])
    label = "macOS" if IS_MACOS else ("Linux" if IS_LINUX else "Windows")
    if IS_WINDOWS:
        label += " (commands run inside WSL)"
    print("  platform :", label, "|", sys.platform)

    if IS_WINDOWS:
        try:
            print("  wsl repo :", repo_path())
        except (RuntimeError, OSError) as exc:
            print("  wsl repo : FAIL -", exc)
            ok = False

    if TK_ERROR is None:
        print("  {:22s} {}".format("tkinter", "ok"))
    else:
        # Only the window needs Tk; --doctor, --dfu and mdm.sh run without it.
        print("  {:22s} {}".format("tkinter", "missing (optional: window only)"))

    if os.path.isdir(os.path.join(SCRIPT_DIR, "device")):
        print("  device/  :", "present")
    else:
        print("  device/  : missing")

    for tool in TOOLS:
        state = "ok" if tool_available(tool) else "MISSING"
        if state == "MISSING":
            ok = False
        print("  {:22s} {}".format(tool, state))

    binary = palera1n_binary()
    if binary.startswith("./"):
        exists = os.path.isfile(os.path.join(SCRIPT_DIR, binary[2:]))
    else:
        exists = tool_available(binary)
    print("  {:22s} {} ({})".format("palera1n", "ok" if exists else "MISSING", binary))
    ok = ok and exists

    print("  {:22s} {}".format("checkra1n", "macOS app only" if IS_MACOS else "Linux build via PATH"))

    try:
        udid = parse_udid(read_device_info())
    except (RuntimeError, OSError) as exc:
        udid = None
        print("  device   : FAIL -", exc)
    print("  {:22s} {}".format("device", udid or "not connected"))

    print()
    print("All required tools found." if ok else "Some required tools are missing - see above.")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #

root = None


def build_gui():
    global root

    if TK_ERROR is not None:
        raise RuntimeError(
            "The iFix window needs Tkinter, which this Python does not have.\n\n"
            "  Ubuntu / WSL: sudo apt install python3-tk\n"
            "  Windows:      reinstall Python with \"tcl/tk and IDLE\" enabled\n\n"
            "Original error: {}".format(TK_ERROR)
        )

    # frame settings
    root = tk.Tk()
    frame = tk.Frame(root, width="500", height="250")
    frame.pack(fill=BOTH, expand=True)

    # uses current directory to load the image file for the icon
    try:
        root.iconphoto(False, tk.PhotoImage(file="icon.png"))
    except tk.TclError:
        pass

    root.title("Twitter: @hackt1vator")
    frame.pack()

    # BIG title on program
    mainText = Label(root, text="iFix", font=("Helveticabold", 24))
    mainText.place(x=340, y=170)

    img2 = Image.open("iFix.jpg")
    NewIMGSize2 = img2.resize((1000, 1000), RESAMPLE)
    new_image2 = ImageTk.PhotoImage(NewIMGSize2)
    label = Label(frame, image=new_image2)
    label.image = new_image2  # keep a reference so Tkinter does not drop the image
    label.place(x=0, y=0)

    # label
    my_label2 = Label(frame, text="mdm Bypass")
    my_label2.place(x=300, y=230)

    # label
    my_label3 = Label(frame, text="ver 1.0")
    my_label3.place(x=10, y=420)

    cButton1 = tk.Button(frame, text="bypass ios 12-16.5", command=mdmbypass, state="normal")
    cButton1.place(x=270, y=360)
    cButton5 = tk.Button(frame, text="enter recovery", command=enterRecMode, state="normal")
    cButton5.place(x=10, y=10)
    cButton6 = tk.Button(frame, text="exit recovery", command=exitRecMode, state="normal")
    cButton6.place(x=580, y=10)
    cButton7 = tk.Button(frame, text="start checkra1n", command=startcheckra1n, state="normal")
    cButton7.place(x=530, y=200)
    cButton9 = tk.Button(frame, text="start palera1n", command=show_popup, state="normal")
    cButton9.place(x=50, y=200)
    cButton10 = tk.Button(frame, text="dfu helper", command=dfu_helper_window, state="normal")
    cButton10.place(x=10, y=250)

    cbeginExploit2 = tk.Button(frame, text="Twitter!", command=opentwitter, state="normal")
    cbeginExploit2.place(x=580, y=410)

    root.geometry("700x450")

    root.resizable(False, False)

    root.eval("tk::PlaceWindow . center")

    root.mainloop()


def main():
    if "--doctor" in sys.argv[1:]:
        return doctor()
    if "--dfu" in sys.argv[1:]:
        return dfu_cli()
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:]:
        print(
            "usage: python3 iFix.py [--doctor | --dfu]\n\n"
            "  --doctor   check platform, tooling and device without opening the GUI\n"
            "  --dfu      guided DFU-mode sequence with live detection\n\n"
            "Windows 11: run windows\\run-ifix.cmd (see WINDOWS.md)."
        )
        return 0
    try:
        build_gui()
    except RuntimeError as exc:  # e.g. WSL missing, or Tkinter not installed
        if messagebox is not None:
            messagebox.showerror("iFix", str(exc))
        else:
            print("ERROR: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

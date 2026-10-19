import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import iFix


class DeviceInfoTests(unittest.TestCase):
    def test_parser_returns_only_non_identifying_fields(self):
        output = (
            "ProductType: iPhone15,2\n"
            "ProductVersion: 17.6\n"
            "BuildVersion: 21G80\n"
            "DeviceClass: iPhone\n"
            "UniqueDeviceID: private-id\n"
            "SerialNumber: private-serial\n"
        )

        self.assertEqual(
            iFix.parse_device_info(output),
            {
                "Model": "iPhone15,2",
                "iOS version": "17.6",
                "Build": "21G80",
                "Device class": "iPhone",
            },
        )

    def test_command_prefers_installed_ideviceinfo(self):
        with patch("iFix.shutil.which", return_value="/usr/bin/ideviceinfo"):
            self.assertEqual(iFix.device_info_command(), ["/usr/bin/ideviceinfo"])

    def test_command_uses_bundled_tool_on_macos(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            app_directory = Path(temporary_directory)
            bundled_tool = app_directory / "device" / "ideviceinfo"
            bundled_tool.parent.mkdir()
            bundled_tool.touch()

            with (
                patch("iFix.shutil.which", return_value=None),
                patch("iFix.sys.platform", "darwin"),
                patch("iFix.APP_DIR", app_directory),
            ):
                self.assertEqual(iFix.device_info_command(), [str(bundled_tool)])

    def test_successful_check_returns_filtered_details(self):
        output = "ProductType: iPhone15,2\nProductVersion: 17.6\nSerialNumber: private"
        completed_process = SimpleNamespace(stdout=output)

        with (
            patch("iFix.device_info_command", return_value=["ideviceinfo"]),
            patch("iFix.subprocess.run", return_value=completed_process) as run,
        ):
            result = iFix.collect_diagnostics()

        self.assertEqual(
            result["details"],
            {"Model": "iPhone15,2", "iOS version": "17.6", "Build": None, "Device class": None},
        )
        self.assertEqual(run.call_args.kwargs["timeout"], 12)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_timeout_returns_actionable_error(self):
        with (
            patch("iFix.device_info_command", return_value=["ideviceinfo"]),
            patch("iFix.subprocess.run", side_effect=subprocess.TimeoutExpired("ideviceinfo", 12)),
        ):
            result = iFix.collect_diagnostics()

        self.assertIn("timed out", result["error"])

    def test_failed_command_returns_error_without_raising(self):
        failure = subprocess.CalledProcessError(2, ["ideviceinfo"], stderr="Device not found\n")
        with (
            patch("iFix.device_info_command", return_value=["ideviceinfo"]),
            patch("iFix.subprocess.run", side_effect=failure),
        ):
            result = iFix.collect_diagnostics()

        self.assertIn("Device not found", result["error"])


if __name__ == "__main__":
    unittest.main()
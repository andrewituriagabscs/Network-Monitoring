import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import monitoring


class SNMPMonitoringTest(unittest.TestCase):
    def test_switch_snmp_is_disabled_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            snapshot = monitoring._poll_switch_snmp("192.0.2.10")

        self.assertEqual(snapshot["status"], "not_configured")
        self.assertIsNone(snapshot["error"])

    def test_builds_read_only_v2c_and_v3_authentication(self):
        with patch.dict(os.environ, {"SNMP_VERSION": "2c", "SNMP_COMMUNITY": "test-read-only"}, clear=True):
            v2c_auth, v2c_state = monitoring._snmp_auth_data()

        with patch.dict(
            os.environ,
            {
                "SNMP_VERSION": "3",
                "SNMP_V3_USER": "test-user",
                "SNMP_V3_AUTH_KEY": "test-auth-key",
                "SNMP_V3_PRIV_KEY": "test-privacy-key",
            },
            clear=True,
        ):
            v3_auth, v3_state = monitoring._snmp_auth_data()

        self.assertEqual(v2c_state, "configured")
        self.assertEqual(v3_state, "configured")
        self.assertIsNotNone(v2c_auth)
        self.assertIsNotNone(v3_auth)

    def test_switch_type_is_saved_and_reports_unconfigured_snmp(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            with (
                patch.object(monitoring, "BASE_DIR", Path(directory)),
                patch.object(monitoring, "_get_mac_address", return_value=""),
                patch.dict(os.environ, {}, clear=True),
            ):
                device = monitoring.add_monitored_device(
                    "Lab Switch",
                    "192.0.2.10",
                    device_type="switch",
                )
                listed_device = next(
                    item for item in monitoring.get_monitored_devices()
                    if item["id"] == device["id"]
                )

        self.assertEqual(device["device_type"], "switch")
        self.assertEqual(listed_device["snmp"]["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
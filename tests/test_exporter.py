import json
from sonar.exporter import export_json, export_table, export_summary, handle_empty
from sonar.models import Device


def test_export_json_produces_valid_json(sample_device):
    result = export_json([sample_device])
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["mac"] == "AA:BB:CC:DD:EE:FF"
    assert data[0]["ip"] == "192.168.1.100"


def test_export_json_empty():
    result = export_json([])
    assert result == "[]"


def test_export_json_writes_to_file(sample_device, tmp_path):
    f = tmp_path / "out.json"
    export_json([sample_device], str(f))
    data = json.loads(f.read_text())
    assert len(data) == 1


def test_export_table_contains_device_info(sample_device):
    output = export_table([sample_device])
    assert "AA:BB:CC:DD:EE:FF" in output
    assert "192.168.1.100" in output
    assert "test-device" in output
    assert "TestCorp" in output
    assert "Discovered Devices" in output


def test_export_table_empty():
    output = export_table([])
    assert "No devices discovered" in output


def test_export_summary_shows_counts(sample_device):
    output = export_summary([sample_device])
    assert "1 device(s)" in output
    assert "By Type" in output
    assert "Computer" in output
    assert "By Manufacturer" in output
    assert "TestCorp" in output


def test_export_summary_multiple_devices():
    d1 = Device(mac="aa:bb:cc:11:22:33", ip="10.0.0.1", device_type="Router", manufacturer="Netgear")
    d2 = Device(mac="dd:ee:ff:44:55:66", ip="10.0.0.2", device_type="Router", manufacturer="Netgear")
    output = export_summary([d1, d2])
    assert "2 device(s)" in output
    assert "Router: 2" in output
    assert "Netgear: 2" in output


def test_export_summary_empty():
    output = export_summary([])
    assert "No devices discovered" in output


def test_handle_empty():
    result = handle_empty([])
    assert "No devices discovered" in result


def test_handle_non_empty(sample_device):
    result = handle_empty([sample_device])
    assert sample_device.mac in result

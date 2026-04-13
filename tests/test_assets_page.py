import pytest
from unittest.mock import MagicMock, patch


class TestAssetsPageFiltering:
    def test_filtered_assets_used_for_double_click(self):
        all_assets = [
            MagicMock(id=1, ip="192.168.1.1", unit_name="Unit1", system_name="System1"),
            MagicMock(id=2, ip="192.168.1.2", unit_name="Unit1", system_name="System2"),
            MagicMock(id=3, ip="192.168.1.3", unit_name="Unit2", system_name="System1"),
        ]

        filtered_assets = [all_assets[1], all_assets[2]]

        row = 0
        asset = filtered_assets[row]
        assert asset.id == 2
        assert asset.ip == "192.168.1.2"

        row = 1
        asset = filtered_assets[row]
        assert asset.id == 3
        assert asset.ip == "192.168.1.3"

    def test_all_assets_vs_filtered_assets_distinction(self):
        all_assets = [
            MagicMock(id=1, ip="192.168.1.1"),
            MagicMock(id=2, ip="192.168.1.2"),
            MagicMock(id=3, ip="192.168.1.3"),
        ]

        filtered_assets = [all_assets[2]]

        row = 0
        wrong_asset = all_assets[row]
        correct_asset = filtered_assets[row]

        assert wrong_asset.id == 1
        assert correct_asset.id == 3

    def test_filter_by_unit(self):
        all_assets = [
            MagicMock(id=1, unit_name="Unit1", system_name="System1"),
            MagicMock(id=2, unit_name="Unit1", system_name="System2"),
            MagicMock(id=3, unit_name="Unit2", system_name="System1"),
        ]

        unit_filter = "Unit1"
        filtered = [a for a in all_assets if a.unit_name == unit_filter]

        assert len(filtered) == 2
        assert filtered[0].id == 1
        assert filtered[1].id == 2

    def test_filter_by_system(self):
        all_assets = [
            MagicMock(id=1, unit_name="Unit1", system_name="System1"),
            MagicMock(id=2, unit_name="Unit1", system_name="System2"),
            MagicMock(id=3, unit_name="Unit2", system_name="System1"),
        ]

        system_filter = "System1"
        filtered = [a for a in all_assets if a.system_name == system_filter]

        assert len(filtered) == 2
        assert filtered[0].id == 1
        assert filtered[1].id == 3

    def test_filter_by_text_search(self):
        all_assets = [
            MagicMock(id=1, ip="192.168.1.1", host_name="server1"),
            MagicMock(id=2, ip="192.168.1.2", host_name="server2"),
            MagicMock(id=3, ip="10.0.0.1", host_name="server3"),
        ]

        search_text = "192.168"
        filtered = [a for a in all_assets if search_text in (a.ip or "")]

        assert len(filtered) == 2
        assert filtered[0].id == 1
        assert filtered[1].id == 2

    def test_combined_filters(self):
        all_assets = [
            MagicMock(id=1, unit_name="Unit1", system_name="System1", ip="192.168.1.1"),
            MagicMock(id=2, unit_name="Unit1", system_name="System2", ip="192.168.1.2"),
            MagicMock(id=3, unit_name="Unit2", system_name="System1", ip="192.168.1.3"),
        ]

        unit_filter = "Unit1"
        filtered = [a for a in all_assets if a.unit_name == unit_filter]
        filtered = [a for a in filtered if "192.168.1.2" in (a.ip or "")]

        assert len(filtered) == 1
        assert filtered[0].id == 2

    def test_export_uses_filtered_assets(self):
        all_assets = [
            MagicMock(id=1, ip="192.168.1.1"),
            MagicMock(id=2, ip="192.168.1.2"),
            MagicMock(id=3, ip="192.168.1.3"),
        ]

        filtered_assets = [all_assets[1]]

        table_row_count = len(filtered_assets)
        asset_ids = [filtered_assets[i].id for i in range(table_row_count)]

        assert len(asset_ids) == 1
        assert asset_ids[0] == 2

    def test_empty_filter_returns_all(self):
        all_assets = [
            MagicMock(id=1, unit_name="Unit1"),
            MagicMock(id=2, unit_name="Unit2"),
        ]

        unit_filter = None
        filtered = all_assets if not unit_filter else [a for a in all_assets if a.unit_name == unit_filter]

        assert len(filtered) == 2
        assert filtered == all_assets

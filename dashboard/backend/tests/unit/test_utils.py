"""
Unit tests for utility functions
"""
import pytest
from utils.helpers import format_size, parse_resource


class TestFormatSize:
    """Tests for format_size function"""

    def test_bytes(self):
        """Test byte formatting"""
        assert format_size(500) == "500.00 B"

    def test_kilobytes(self):
        """Test kilobyte formatting"""
        assert format_size(1024) == "1.00 KB"
        assert format_size(1536) == "1.50 KB"

    def test_megabytes(self):
        """Test megabyte formatting"""
        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1024 * 1024 * 2.5) == "2.50 MB"

    def test_gigabytes(self):
        """Test gigabyte formatting"""
        assert format_size(1024 ** 3) == "1.00 GB"

    def test_terabytes(self):
        """Test terabyte formatting"""
        assert format_size(1024 ** 4) == "1.00 TB"

    def test_zero(self):
        """Test zero bytes"""
        assert format_size(0) == "0.00 B"


class TestParseResource:
    """Tests for parse_resource function"""

    def test_cpu_millicores(self):
        """Test CPU millicores parsing"""
        assert parse_resource("500m") == 0.5
        assert parse_resource("1000m") == 1.0
        assert parse_resource("250m") == 0.25

    def test_memory_ki(self):
        """Test memory Ki parsing"""
        assert parse_resource("1024Ki") == 1024 * 1024

    def test_memory_mi(self):
        """Test memory Mi parsing"""
        assert parse_resource("512Mi") == 512 * 1024 ** 2

    def test_memory_gi(self):
        """Test memory Gi parsing"""
        assert parse_resource("4Gi") == 4 * 1024 ** 3

    def test_memory_decimal(self):
        """Test decimal memory units"""
        assert parse_resource("1G") == 1000 ** 3
        assert parse_resource("1M") == 1000 ** 2

    def test_plain_number(self):
        """Test plain number without unit"""
        assert parse_resource("1000") == 1000.0
        assert parse_resource("2.5") == 2.5

    def test_empty_string(self):
        """Test empty string"""
        assert parse_resource("") == 0.0

    def test_none(self):
        """Test None input"""
        assert parse_resource(None) == 0.0

    def test_invalid_string(self):
        """Test invalid string"""
        assert parse_resource("invalid") == 0.0

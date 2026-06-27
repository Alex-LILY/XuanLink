import pytest
from ether_ghost.utils.tools import parse_permission, md5_encode, base64_encode
from ether_ghost.utils.cipher import padding_aes256_cbc, unpadding_aes256_cbc
from ether_ghost.utils.random_data import random_string


class TestParsePermission:
    def test_all_permissions(self):
        assert parse_permission("rwxrwxrwx") == "777"
        assert parse_permission("rwxr-xr-x") == "755"
        assert parse_permission("rw-r--r--") == "644"
        assert parse_permission("rwx------") == "700"

    def test_no_permissions(self):
        assert parse_permission("---------") == "000"

    def test_mixed_permissions(self):
        assert parse_permission("r-xr--rwx") == "547"
        assert parse_permission("--x-w-r--") == "124"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Wrong permission format"):
            parse_permission("rwx")
        with pytest.raises(ValueError, match="Wrong permission format"):
            parse_permission("rwxrwxrwxx")
        with pytest.raises(ValueError, match="Wrong permission format"):
            parse_permission("abcabcabc")
        with pytest.raises(ValueError, match="Wrong permission format"):
            parse_permission("")


class TestMd5Encode:
    def test_string_input(self):
        assert md5_encode("hello") == "5d41402abc4b2a76b9719d911017c592"

    def test_bytes_input(self):
        assert md5_encode(b"hello world") == "5eb63bbbe01eeed093cb22bb8f5acdc3"

    def test_empty_string(self):
        assert md5_encode("") == "d41d8cd98f00b204e9800998ecf8427e"

    def test_chinese_string(self):
        assert md5_encode("你好") == "7eca689f0d3389d9dea66ae112e5cfd7"


class TestBase64Encode:
    def test_string_input(self):
        assert base64_encode("hello") == "aGVsbG8="

    def test_bytes_input(self):
        assert base64_encode(b"hello") == "aGVsbG8="

    def test_empty_string(self):
        assert base64_encode("") == ""

    def test_binary_data(self):
        assert base64_encode(b"\x00\xff\x00\xff") == "AP8A/w=="


class TestAesPadding:
    def test_padding_and_unpadding_roundtrip(self):
        for length in range(0, 33):
            data = b"a" * length
            padded = padding_aes256_cbc(data)
            assert len(padded) % 16 == 0
            assert unpadding_aes256_cbc(padded) == data

    def test_padding_length(self):
        assert len(padding_aes256_cbc(b"")) == 16
        assert len(padding_aes256_cbc(b"x")) == 16
        assert len(padding_aes256_cbc(b"x" * 15)) == 16
        assert len(padding_aes256_cbc(b"x" * 16)) == 32


class TestRandomString:
    def test_length(self):
        for length in [0, 1, 5, 100]:
            result = random_string(length)
            assert len(result) == length

    def test_only_contains_allowed_chars(self):
        chars = "abc123"
        result = random_string(100, chars)
        assert all(c in chars for c in result)

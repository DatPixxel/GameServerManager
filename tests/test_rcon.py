"""Charakterisierungstest für den RCON-Paketbau (ohne Netzwerk)."""

import struct


def test_create_packet_layout(gsm_module):
    g = gsm_module
    client = g.RCONClient(host="127.0.0.1", port=27020, password="pw")
    pkt = client._create_packet(1, g.RCONClient.SERVERDATA_AUTH, "hello")

    # Aufbau: <iii size, id, type> + body + b'\x00\x00'
    size, req_id, pkt_type = struct.unpack("<iii", pkt[:12])
    body = pkt[12:]
    assert req_id == 1
    assert pkt_type == g.RCONClient.SERVERDATA_AUTH == 3
    assert body == b"hello\x00\x00"
    # size = 4 (id) + 4 (type) + len(body)
    assert size == 4 + 4 + len(body)
    assert size == len(pkt) - 4

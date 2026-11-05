from pydantic import BaseModel, ConfigDict, Field

class PacketRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    destination: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    payload: bytes = Field(max_length=512)

def encode_simulated_packet(record: PacketRecord) -> bytes:
    from scapy.layers.inet import IP, UDP
    from scapy.packet import Raw
    return bytes(IP(src="192.0.2.1", dst="192.0.2.2") / UDP(sport=12000, dport=12001) / Raw(load=record.payload))

def parse_simulated_packet(data: bytes) -> bytes:
    from scapy.layers.inet import IP
    from scapy.packet import Raw
    if len(data) > 2048:
        raise ValueError("Packet exceeds offline parser limit")
    packet = IP(data)
    if not packet.haslayer(Raw):
        return b""
    return bytes(packet[Raw].load)[:512]

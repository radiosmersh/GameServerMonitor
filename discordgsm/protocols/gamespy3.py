import time
from typing import TYPE_CHECKING

from opengsq.binary_reader import BinaryReader
from opengsq.exceptions import InvalidPacketException
from opengsq.protocol_socket import UdpClient
from opengsq.responses.gamespy2 import Status

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GameSpy3(Protocol):
    name = "gamespy3"
    map_size_labels = {
        16: "Small",
        32: "Medium",
        64: "Large",
        128: "Tiny",
    }

    @classmethod
    def map_size_label(cls, value):
        map_size = int(value)
        return cls.map_size_labels.get(map_size, map_size)

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        start = time.time()
        status = await self._get_status(host, port)
        ping = int((time.time() - start) * 1000)
        info = status.info

        result: GamedigResult = {
            "name": info.get("hostname", ""),
            "map": info.get("mapname", info.get("map", "")),
            "mapsize": self.map_size_label(info["bf2_mapsize"]),
            "password": int(info.get("password", "0")) != 0,
            "numplayers": int(info["numplayers"]),
            "numbots": 0,
            "maxplayers": int(info["maxplayers"]),
            "players": [
                {"name": player["name"], "raw": player} for player in status.players
            ],
            "bots": None,
            "connect": f"{host}:{info.get('hostport', port)}",
            "ping": ping,
            "raw": info,
        }

        return result

    @staticmethod
    def _read_string(reader: BinaryReader) -> str:
        """Read a Gamespy string, retaining CP1252 bytes used by FH2.

        OpenGSQ currently decodes Gamespy strings as UTF-8 with ``errors=ignore``.
        That silently drops CP1252 characters before the caller can repair them.
        Most servers use UTF-8, so try that first and fall back to CP1252 only
        when the byte sequence is not valid UTF-8.
        """
        value = bytearray()
        while not reader.is_end():
            byte = reader.read_byte()
            if byte == 0:
                break
            value.append(byte)

        try:
            return bytes(value).decode("utf-8")
        except UnicodeDecodeError:
            return bytes(value).decode("cp1252")

    async def _get_status(self, host: str, port: int) -> Status:
        with UdpClient() as udp_client:
            udp_client.settimeout(self.timeout)
            await udp_client.connect((host, port))
            udp_client.send(b"\xfe\xfd\x00\x04\x05\x06\x07\xff\xff\xff\x01")
            response = await self._read_response(udp_client)

        reader = BinaryReader(response)
        info = {}
        while True:
            key = self._read_string(reader)
            if not key:
                break
            info[key] = self._read_string(reader)

        return Status(
            info,
            self._read_dictionaries(reader, "player"),
            self._read_dictionaries(reader, "team"),
        )

    async def _read_response(self, udp_client: UdpClient) -> bytes:
        packet_count = -1
        payloads = {}

        while packet_count == -1 or len(payloads) > packet_count:
            packet = await udp_client.recv()
            reader = BinaryReader(packet)
            if reader.read_byte() != 0:
                raise InvalidPacketException("GamespyV3 packet header mismatch")

            reader.read_bytes(13)
            packet_number = reader.read_byte()
            number = packet_number & 0x7F
            if packet_number & 0x80:
                packet_count = number + 1

            object_id = reader.read_byte()
            header = b""
            if object_id >= 1:
                object_key = self._read_string(reader)
                count = reader.read_byte()
                if count == 0:
                    header = (
                        b"\x00"
                        + bytes([object_id])
                        + object_key.encode("ascii")
                        + b"\x00\x00"
                    )

            payload = header + reader.read()[:-1]
            payloads[number] = payload[: payload.rfind(b"\x00") + 1]

        return b"".join(payloads[number] for number in sorted(payloads))

    def _read_dictionaries(
        self, reader: BinaryReader, object_type: str
    ) -> list[dict[str, str]]:
        dictionaries = []
        if reader.is_end():
            return dictionaries

        reader.read_byte()
        index = 0
        while not reader.is_end():
            key = self._read_string(reader)
            if not key:
                break
            reader.read_byte()
            key = key.rstrip("t").rstrip("_")
            if key == object_type:
                key = "name"

            while not reader.is_end():
                value = self._read_string(reader).strip()
                if not value:
                    break
                if len(dictionaries) < index + 1:
                    dictionaries.append({})
                dictionaries[index][key] = value
                index += 1
            index = 0

        return dictionaries

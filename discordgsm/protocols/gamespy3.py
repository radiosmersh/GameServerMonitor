import time
from typing import TYPE_CHECKING

import opengsq

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
        gamespy3 = opengsq.GameSpy3(host, port, self.timeout)
        start = time.time()
        status = await gamespy3.get_status()
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

from typing import List

from discord import Embed

from discordgsm.gamedig import GamedigPlayer
from discordgsm.styles.medium import Medium
from discordgsm.translator import t


class Large(Medium):
    """Large style"""

    @property
    def display_name(self) -> str:
        return t('style.large.display_name', self.locale)

    @property
    def description(self) -> str:
        return t('style.large.description', self.locale)

    async def embed(self) -> Embed:
        embed = await super().embed()
        field_name = t(f"embed.field.{'members' if self.server.game_id == 'discord' else 'player_list'}.name", self.locale)
        self.add_player_list_fields(embed, field_name, self.server.result['players'])

        return embed

    def add_player_list_fields(self, embed: Embed, field_name: str, players: List[GamedigPlayer]):
        empty_value = '*​*'
        filtered_players = [player for player in players if player['name'].strip()]
        filtered_players = sorted(filtered_players, key=lambda player: player['name'])
        values = ['', '', '']

        for i, player in enumerate(filtered_players):
            name = player['name'].ljust(23)[:23]

            if len(player['name']) > 23:
                name = name[:-3] + '...'

            # Replace Markdown
            # https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-
            name = name.replace('*', '\\*').replace('_', '\\_').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>')

            values[i % len(values)] += f"{name}\n"

        for i, name in enumerate([field_name, empty_value, empty_value]):
            embed.add_field(name=name, value=values[i] if values[i] else empty_value)

        return embed

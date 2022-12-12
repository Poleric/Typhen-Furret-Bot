from discord.ext import commands


class QOTD(commands.Cog):
    qotd_channel_ids = [838658959626862662,  # qotd
                        849574569119186945]  # test

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.channel.id in self.qotd_channel_ids and msg.content.startswith('QOTD:'):  # check if the message is a qotd
            # find and unpin the last qotd
            for pinned in await msg.channel.pins():
                if pinned.content.startswith('QOTD:'):
                    await pinned.unpin()
                    break

            # pin the current qotd and start a thread
            await msg.pin(reason='QOTD')
            await msg.create_thread(name=msg.content if len(msg.content) < 100 else 'QOTD')


async def setup(bot):
    await bot.add_cog(QOTD(bot))

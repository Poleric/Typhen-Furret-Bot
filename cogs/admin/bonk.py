from datetime import datetime, timedelta
from discord.ext import tasks


class Bonked:

    def __init__(self, member, channel, duration=timedelta(seconds=30), start_time=None, reason=''):
        self.member = member
        self.channel = channel
        self.reason = reason
        self.duration = duration
        self.start_time = start_time or datetime.now()

        self.bonked = True
        self.bonk_task.start()

    @property
    def end_time(self):
        return self.start_time + self.duration

    def add_time(self, duration):
        self.duration += duration

    def unbonk(self):
        self.bonked = False
        self.bonk_task.cancel()

    @tasks.loop(seconds=0.5)
    async def bonk_task(self):
        if datetime.now() - self.start_time > self.duration:  # auto stop when time is up
            self.bonked = False
            self.bonk_task.cancel()
            return

        if self.member.voice is not None and self.member.voice.channel != self.channel:
            await self.member.move_to(self.channel, reason=self.reason)

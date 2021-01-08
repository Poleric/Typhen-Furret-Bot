# Modules
import asyncio
import re
import json

# Objects
from pyppeteer import launch
from pyppeteer.page import Page
from discord.ext import commands
from discord.ext import tasks
from discord import Embed
from discord.ext.commands import Context

# Exception
from pyppeteer.errors import TimeoutError
from pyppeteer.errors import PageError
from pyppeteer.errors import ElementHandleError


class ServerStatusError(Exception):
    pass


class StartupError(Exception):
    pass


class Status:

    def __init__(self, status: str, est: str = None):
        self.status = status
        self.est = est

    def __str__(self):
        return self.status


class AternosServer:

    def __init__(self, page: Page):
        self.page = page

    async def getStatus(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        statusBox = await self.page.J('.statuslabel-label')
        status = await self.page.evaluate('statusBox => statusBox.textContent', statusBox)
        if (status := status.strip()) == 'Waiting in queue':
            try:
                estBox = await self.page.waitFor('.queue-time', timeout=500)
            except TimeoutError:
                raise TimeoutError
            else:
                est = await self.page.evaluate('estBox => estBox.textContent', estBox)
                return Status(status, est.strip())
        else:
            return Status(status)

    async def getIP(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        serverIPBox = await self.page.J('.server-ip')
        IP = await self.page.evaluate('serverIPBox => serverIPBox.textContent', serverIPBox)
        IP = re.search('\w+\.\w+\.\w+', IP)[0]
        return IP

    async def getPlayerCount(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        playerCountBox = await self.page.J('#players')
        playerCount = await self.page.evaluate('versionBox => versionBox.textContent', playerCountBox)
        return playerCount

    async def getVersion(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        versionBox = await self.page.J('#version')
        version = await self.page.evaluate('versionBox => versionBox.textContent', versionBox)
        return version

    async def startServer(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        if str(await self.getStatus()) == "Offline":
            await self.page.click('#start')
            # Try to click away the notification box
            try:
                btn_red = await self.page.waitForXPath('//*[@id="nope"]/main/div/div/div/main/div/a[2]', timeout=5000)
            except TimeoutError:
                pass
            else:
                try:
                    await btn_red.click()
                except (ElementHandleError, PageError):
                    pass
            await asyncio.sleep(2)
            # Check if successfully opened
            status: Status = await self.getStatus()
            if str(status) == 'Offline':
                raise StartupError('**Server not started.**')
            else:
                if str(status) == 'Waiting in queue':
                    self.confirmation.start()
        else:
            raise ServerStatusError('**Server is not offline.**')

    async def stopServer(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        if str(await self.getStatus()) in ('Online', 'Starting'):
            await self.page.click('#stop')
            self.confirmation.cancel()
            self.remindOnStart.cancel()
        else:
            raise ServerStatusError('**Server is not online.**')

    async def restartServer(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        if str(await self.getStatus()) == 'Online':
            await self.page.click('#restart')
        else:
            raise ServerStatusError('**Server is not online.**')

    async def confirmServer(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        try:
            await self.page.click('#confirm')
        # When Node is either not visible or not an HTMLElement
        except ElementHandleError:
            return False
        else:
            return True

    async def createStatusEmbed(self):
        status = await self.getStatus()
        ip = await self.getIP()
        version = await self.getVersion()
        embed = Embed(title=ip, color=0xf0d4b1)
        embed.add_field(name='Status', value=str(status), inline=True)
        if str(status) == 'Online':
            playerCount = await self.getPlayerCount()
            embed.add_field(name='Player Count', value=playerCount, inline=True)
        elif str(status) == 'Waiting in queue':
            embed.add_field(name='EST', value=status.est, inline=True)
        embed.add_field(name='Version', value=version, inline=True)
        return embed

    @tasks.loop(seconds=15.0)
    async def remindOnStart(self, ctx: Context):
        status: Status = await self.getStatus()
        if str(status) == 'Online':
            serverIP: str = await self.getIP()
            await ctx.reply(f'`{serverIP}` **is now online.**')
            self.remindOnStart.cancel()

    @tasks.loop(seconds=10.0)
    async def confirmation(self):
        confirmationStatus: bool = await self.confirmServer()
        if confirmationStatus:
            self.confirmation.cancel()


class AternosList:

    def __init__(self, servers: list[AternosServer]):
        self.servers = servers

    def __len__(self):
        return len(self.servers)

    def __getitem__(self, item: int):
        return self.servers[item]

    @classmethod
    async def create(cls, username, password):
        browser = await launch(headless=True, dumpio=True)
        page = await browser.pages()
        page = page[0]

        navigationPromise = asyncio.ensure_future(page.waitForNavigation())
        await page.goto("https://aternos.org/go/")
        await navigationPromise

        usernameBox = await page.J('#user')
        await usernameBox.click()
        await page.keyboard.type(username)

        passwordBox = await page.J('#password')
        await passwordBox.click()
        await page.keyboard.type(password)

        navigationPromise = asyncio.ensure_future(page.waitForNavigation())
        await page.keyboard.press('Enter')
        await navigationPromise

        servers_list = await page.JJ('.server-body')

        await servers_list[0].click()
        servers = list()
        servers.append(AternosServer(page))

        cookies = await page.cookies()

        for i in range(len(servers_list) - 1):

            browser = await launch(headless=True, dumpio=True)
            page = await browser.pages()
            page = page[0]

            await page.setCookie(*cookies)

            navigationPromise = asyncio.ensure_future(page.waitForNavigation())
            await page.goto('https://aternos.org/servers/')
            await navigationPromise

            servers_list = await page.JJ('.server-body')

            await servers_list[i + 1].click()
            servers.append(AternosServer(page))

        navigationPromise = asyncio.ensure_future(page.waitForNavigation())
        await navigationPromise
        return cls(servers)

    async def getServer(self, name_or_index: str):
        names = list()
        for serverBrowser in self.servers:
            name = await serverBrowser.getIP()
            name = re.search('[\w\d]+', name)[0]
            names.append(name)
        if name_or_index.isdecimal():
            try:
                return self[int(name_or_index) - 1]
            except IndexError:
                pass
        for i, name in enumerate(names):
            if name.find(str(name_or_index)) != -1:
                return self[i]
        return None

    async def cleanup(self):
        for browserInstance in self.servers:
            browserInstance.remindOnStart.cancel()
            browserInstance.confirmation.cancel()
            await browserInstance.page.browser.close()

    async def createServerListEmbed(self):
        embed = Embed(title='List of servers', color=0xf0d4b1)
        for i, serverBrowser in enumerate(self.servers):
            IP = await serverBrowser.getIP()
            status = await serverBrowser.getStatus()
            embed.add_field(name='\u200b', value=f'`{i + 1}.` {IP} | `{str(status)}`', inline=False)
        return embed


class Minecraft(commands.Cog):

    def __init__(self, client):
        self.bot = client
        self.server = None
        self.secretserver = None
        with open('./config/minecraftserver.json', 'r') as data:
            self.config = json.load(data)

    def cog_unload(self):
        if self.server is not None:
            for server in self.server.serverBrowsers:
                server.remindOnStart.cancel()
                server.confirmation.cancel()
        if self.secretserver is not None:
            for server in self.secretserver.serverBrowsers:
                server.remindOnStart.cancel()
                server.confirmation.cancel()

    @commands.command(aliases=['mincraft', 'minceraft', 'mineraft', 'mc'])
    async def minecraft(self, ctx: Context, command: str = None, *, arg: str = None):
        async with ctx.typing():
            if ctx.channel.id == 765130597843861516:
                specifiedServer = self.secretserver
            else:
                specifiedServer = self.server

            if command is None:
                """Shows brief info about all servers"""

                embed: Embed = await specifiedServer.createServerListEmbed()
                await ctx.reply(embed=embed)

            elif command in ('status', 'ststua'):
                """Send embed containing a server status"""

                if arg is not None:
                    server: AternosServer = await specifiedServer.getServer(arg)
                    if server is not None:
                        try:
                            statusEmbed: Embed = await server.createStatusEmbed()
                            await ctx.reply(embed=statusEmbed)
                        except (TimeoutError, PageError):
                            await ctx.reply('**Timed out.**')
                    else:
                        await ctx.reply('**Server not found.**')
                else:
                    await ctx.reply('**Please specify a server after the command.**')

            elif command in ('start', 'open'):
                """Starts server"""

                if arg is not None:
                    server: AternosServer = await specifiedServer.getServer(arg)
                    if server is not None:
                        try:
                            await server.startServer()
                            await ctx.reply('**Server starting.**')
                            server.remindOnStart.start(ctx=ctx)
                        except Exception as e:
                            if isinstance(e, StartupError) or isinstance(e, ServerStatusError):
                                await ctx.reply(str(e))
                            else:
                                await ctx.reply(repr(e))
                                raise e
                    else:
                        await ctx.reply('**Server not found.**')
                else:
                    await ctx.reply('**Please specify a server after the command.**')

            elif command in ('stop', 'close'):
                """Stops server"""

                if arg is not None:
                    server: AternosServer = await specifiedServer.getServer(arg)
                    if server is not None:
                        try:
                            await server.stopServer()
                            await ctx.reply('**Server closing.**')
                        except Exception as e:
                            if isinstance(e, ServerStatusError):
                                await ctx.reply(str(e))
                            else:
                                await ctx.reply(repr(e))
                                raise e
                    else:
                        await ctx.reply('**Server not found.**')
                else:
                    await ctx.reply('**Please specify a server after the command.**')

            elif command == 'restart':
                """Restarts server"""

                if arg is not None:
                    server: AternosServer = await specifiedServer.getServer(arg)
                    if server is not None:
                        try:
                            await server.restartServer()
                            await ctx.reply('**Server restarting.**')
                            server.remindOnStart.start(ctx=ctx)
                        except Exception as e:
                            if isinstance(e, ServerStatusError):
                                await ctx.reply(str(e))
                            else:
                                await ctx.reply(repr(e))
                                raise e
                    else:
                        await ctx.reply('**Server not found.**')
                else:
                    await ctx.reply('**Please specify a server after the command.**')

            # elif command == 'help':
            elif command == 'cleanup':
                """Cleanups all browser instance"""

                await specifiedServer.cleanup()
                specifiedServer = None
                await ctx.reply('Cleanup successful.')

            else:
                """If no command match"""

                await ctx.reply('Invalid command.')

    @minecraft.before_invoke
    async def ensureBrowserInstance(self, ctx: Context):
        if ctx.channel.id == 765130597843861516:
            if self.secretserver is None:
                async with ctx.typing():
                    self.secretserver = await AternosList.create(self.config['Typhen']['username'], self.config['Typhen']['password'])
        else:
            if self.server is None:
                async with ctx.typing():
                    self.server = await AternosList.create(self.config['Biblion']['username'], self.config['Biblion']['password'])


def setup(client):
    client.add_cog(Minecraft(client))

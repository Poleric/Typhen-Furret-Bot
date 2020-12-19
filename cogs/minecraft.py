import asyncio
import re
import json

from pyppeteer import launch
from pyppeteer.errors import TimeoutError
from pyppeteer.errors import PageError
from pyppeteer.errors import ElementHandleError
from pyppeteer.page import Page
from pyppeteer.browser import Browser

from discord import Embed
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands import Context


class Status:

    def __init__(self, status, time=None):
        self.status = status
        self.time = time

    def __str__(self):
        return self.status


class ServerBrowser:

    def __init__(self, browser: Browser, page: Page):
        self.browser = browser
        self.page = page

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

    async def getStatus(self):
        if self.page.url != 'https://aternos.org/server/':
            navigationPromise = asyncio.ensure_future(self.page.waitForNavigation())
            await self.page.goto('https://aternos.org/server/')
            await navigationPromise
        statusBox = await self.page.J('.statuslabel-label')
        status = await self.page.evaluate('statusBox => statusBox.textContent', statusBox)
        if (status := status.strip()) == 'Waiting in queue':
            try:
                await self.page.waitFor('.queue-time', timeout=500)
            except TimeoutError:
                raise TimeoutError
            else:
                estBox = await self.page.J('.queue-time')
                est = await self.page.evaluate('estBox => estBox.textContent', estBox)
                return Status(status, est.strip())
        else:
            return Status(status)

    async def startServer(self):
        try:
            await self.page.click('#start')
        # When Node is either not visible or not an HTMLElement
        except ElementHandleError:
            return False
        else:
            try:
                await self.page.waitFor('.fa-times-circle', timeout=10000)
            except TimeoutError:
                pass
            else:
                try:
                    await self.page.click('.fa-times-circle')
                except ElementHandleError:
                    pass
            await asyncio.sleep(2)
            status: Status = await self.getStatus()
            if str(status) == 'Offline':
                return False
            else:
                if str(status) == 'Waiting in queue':
                    self.confirmation.start()
                return True

    async def stopServer(self):
        try:
            await self.page.click('#stop')
        # When Node is either not visible or not an HTMLElement
        except ElementHandleError:
            return False
        else:
            return True

    async def restartServer(self):
        try:
            await self.page.click('#restart')
        # When Node is either not visible or not an HTMLElement
        except ElementHandleError:
            return False
        else:
            return True

    async def confirmServer(self):
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
            embed.add_field(name='EST', value=status.time, inline=True)
        embed.add_field(name='Version', value=version, inline=True)
        return embed

    @tasks.loop(seconds=15.0)
    async def remindOnStart(self, ctx: Context):
        status: Status = await self.getStatus()
        if str(status) == 'Online':
            serverIP: str = await self.getIP()
            await ctx.send(f'`{serverIP}` **is now online.** {ctx.author.mention}')
            self.remindOnStart.cancel()

    @tasks.loop(seconds=10.0)
    async def confirmation(self):
        confirmationStatus: bool = await self.confirmServer()
        if confirmationStatus:
            self.confirmation.cancel()


class Aternos:

    def __init__(self, serverBrowsers: list[ServerBrowser]):
        self.serverBrowsers = serverBrowsers

    @classmethod
    async def create(cls, username: str, password: str):

        browser = await launch(headless=True, dumpio=True)
        browsers = []
        page = await browser.pages()
        page = page[0]
        # Go to Aternos
        navigationPromise = asyncio.ensure_future(page.waitForNavigation())
        await page.goto("https://aternos.org/go/")
        await navigationPromise
        # Fill in username
        usernameBox = await page.J('#user')
        await usernameBox.click()
        await page.keyboard.type(username)
        # Fill in password
        passwordBox = await page.J('#password')
        await passwordBox.click()
        await page.keyboard.type(password)
        navigationPromise = asyncio.ensure_future(page.waitForNavigation())
        await page.keyboard.press('Enter')
        await navigationPromise
        # Find servers
        servers = await page.JJ('.server-body')
        # Click into server page
        await servers[0].click()
        browsers.append(ServerBrowser(browser, page))
        cookies = await page.cookies()
        # If there's more than one server
        for i in range(len(servers) - 1):
            browser = await launch(headless=True, dumpio=True)
            page = await browser.pages()
            page = page[0]
            await page.setCookie(*cookies)
            navigationPromise = asyncio.ensure_future(page.waitForNavigation())
            await page.goto('https://aternos.org/servers/')
            await navigationPromise
            # Find servers
            servers = await page.JJ('.server-body')
            # Click into server page
            await servers[i + 1].click()
            browsers.append(ServerBrowser(browser, page))
        navigationPromise = asyncio.ensure_future(page.waitForNavigation())
        await navigationPromise
        return cls(browsers)

    async def getServerBrowser(self, name_or_index: str):
        names = list()
        for serverBrowser in self.serverBrowsers:
            name = await serverBrowser.getIP()
            name = re.search('[\w\d]+', name)[0]
            names.append(name)
        if name_or_index.isdecimal():
            try:
                return self.serverBrowsers[int(name_or_index) - 1]
            except IndexError:
                pass
        for i, name in enumerate(names):
            if name.find(str(name_or_index)) != -1:
                return self.serverBrowsers[i]
        return None

    async def cleanup(self):
        for browserInstance in self.serverBrowsers:
            browserInstance.remindOnStart.cancel()
            browserInstance.confirmation.cancel()
            await browserInstance.browser.close()

    async def createServerListEmbed(self):
        embed = Embed(title='List of servers', color=0xf0d4b1)
        for i, serverBrowser in enumerate(self.serverBrowsers):
            IP = await serverBrowser.getIP()
            status = await serverBrowser.getStatus()
            embed.add_field(name='\u200b', value=f'`{i + 1}.` {IP} | `{str(status)}`', inline=False)
        return embed


class Minecraft(commands.Cog):

    def __init__(self, client):
        self.bot = client
        self.server = None
        with open('./config/minecraftserver.json', 'r') as data:
            self.config = json.load(data)

    def cog_unload(self):
        if self.server is not None:
            for server in self.server.serverBrowsers:
                server.remindOnStart.cancel()
                server.confirmation.cancel()

    @commands.command(aliases=['mincraft', 'minceraft', 'mineraft', 'mc'])
    async def minecraft(self, ctx: Context, command: str = None, *, arg: str = None):
        async with ctx.channel.typing():
            if command is None:
                """Shows brief info about all servers"""

                embed: Embed = await self.server.createServerListEmbed()
                await ctx.send(embed=embed)

            elif command == 'status':
                """Send embed containing a server status"""

                if arg is not None:
                    server: ServerBrowser = await self.server.getServerBrowser(arg)
                    if server is not None:
                        try:
                            statusEmbed: Embed = await server.createStatusEmbed()
                            await ctx.send(embed=statusEmbed)
                        except (TimeoutError, PageError):
                            await ctx.send('**Timed out.**')
                    else:
                        await ctx.send('**Server not found.**')
                else:
                    await ctx.send('**Please specify a server after the command.**')

            elif command == 'start':
                """Starts server"""

                if arg is not None:
                    server: ServerBrowser = await self.server.getServerBrowser(arg)
                    if server is not None:
                        try:
                            startStatus: bool = await server.startServer()
                            if startStatus:
                                await ctx.send('**Server starting.**')
                                server.remindOnStart.start(ctx=ctx)
                            else:
                                await ctx.send('**Server is not offline.**')
                        except (TimeoutError, PageError):
                            await ctx.send('**Timed out.**')
                    else:
                        await ctx.send('**Server not found.**')
                else:
                    await ctx.send('**Please specify a server after the command.**')

            elif command in ('stop', 'close'):
                """Stops server"""

                if arg is not None:
                    server: ServerBrowser = await self.server.getServerBrowser(arg)
                    if server is not None:
                        try:
                            stopStatus: bool = await server.stopServer()
                            if stopStatus:
                                await ctx.send('**Server closing.**')
                            else:
                                await ctx.send('**Server is not online.**')
                        except (TimeoutError, PageError):
                            await ctx.send('**Timed out.**')
                    else:
                        await ctx.send('**Server not found.**')
                else:
                    await ctx.send('**Please specify a server after the command.**')

            elif command == 'restart':
                """Restarts server"""

                if arg is not None:
                    server: ServerBrowser = await self.server.getServerBrowser(arg)
                    if server is not None:
                        try:
                            restartStatus: bool = await server.restartServer()
                            if restartStatus:
                                await ctx.send('**Server restarting.**')
                            else:
                                await ctx.send('**Server is not online.**')
                        except (TimeoutError, PageError):
                            await ctx.send('**Timed out.**')
                    else:
                        await ctx.send('**Server not found.**')
                else:
                    await ctx.send('**Please specify a server after the command.**')

            # elif command == 'help':
            elif command == 'cleanup':
                """Cleanups all browser instance"""

                await self.server.cleanup()
                self.server = None
                await ctx.send('Cleanup successful.')

            else:
                """If no command match"""

                await ctx.send('Invalid command.')

    @minecraft.before_invoke
    async def ensureBrowserInstance(self, ctx: Context):
        if self.server is None:
            async with ctx.channel.typing():
                self.server = await Aternos.create(self.config['loginInfo']['username'], self.config['loginInfo']['password'])


def setup(client):
    client.add_cog(Minecraft(client))

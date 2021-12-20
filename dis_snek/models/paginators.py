import asyncio
import textwrap
import uuid
from typing import List, TYPE_CHECKING, Optional, Callable, Coroutine

import attr

from dis_snek import (
    Embed,
    ComponentContext,
    ActionRow,
    Button,
    ButtonStyles,
    spread_to_rows,
    ComponentCommand,
    get_components_ids,
    Context,
    Message,
    MISSING,
    Snowflake_Type,
    Select,
    SelectOption,
    Color,
    BrandColors,
)

if TYPE_CHECKING:
    from dis_snek import Snake


@attr.s()
class Timeout:
    paginator: "Paginator" = attr.ib()
    run: bool = attr.ib(default=True)
    ping: asyncio.Event = asyncio.Event()

    async def __call__(self):
        while self.run:
            try:
                await asyncio.wait_for(self.ping.wait(), timeout=self.paginator.timeout_interval)
            except asyncio.TimeoutError:
                if self.paginator.message:
                    await self.paginator.message.edit(components=self.paginator.create_components(True))
                return
            else:
                self.ping.clear()


@attr.s(auto_detect=True)
class Page:
    content: str = attr.ib()
    title: Optional[str] = attr.ib(default=None)
    prefix: str = attr.ib(kw_only=True, default="")
    suffix: str = attr.ib(kw_only=True, default="")

    @property
    def get_summary(self):
        return self.title or textwrap.shorten(self.content, 40, placeholder="...")

    def to_embed(self) -> Embed:
        return Embed(description=f"{self.prefix}\n{self.content}\n{self.suffix}", title=self.title)


@attr.s(auto_detect=True)
class Paginator:
    client: "Snake" = attr.ib()
    """The snake client to hook listeners into"""

    page_index: int = attr.ib(kw_only=True, default=0)
    """The index of the current page being displayed"""
    pages: List[Page | Embed] = attr.ib(factory=list, kw_only=True)
    """The pages this paginator holds"""
    timeout_interval: int = attr.ib(default=0, kw_only=True)
    """How long until this paginator disables itself"""
    callback: Callable[..., Coroutine] = attr.ib(default=None)
    """A coroutine to call should the select button be pressed"""

    show_first_button: bool = attr.ib(default=True)
    """Should a `First` button be shown"""
    show_back_button: bool = attr.ib(default=True)
    """Should a `Back` button be shown"""
    show_next_button: bool = attr.ib(default=True)
    """Should a `Next` button be shown"""
    show_last_button: bool = attr.ib(default=True)
    """Should a `Last` button be shown"""
    show_callback_button: bool = attr.ib(default=False)
    """Show a button which will call the `callback`"""
    show_select_menu: bool = attr.ib(default=False)
    """Should a select menu be shown for navigation"""

    wrong_user_message: str = attr.ib(default="This paginator is not for you")
    """The message to be sent when the wrong user uses this paginator"""

    default_title: Optional[str] = attr.ib(default=None)
    """The default title to show on the embeds"""
    default_color: Color = attr.ib(default=BrandColors.BLURPLE)
    """The default colour to show on the embeds"""

    _uuid: str = attr.ib(factory=uuid.uuid4)
    _message: Message = attr.ib(default=MISSING)
    _timeout_task: Timeout = attr.ib(default=MISSING)
    _author_id: Snowflake_Type = attr.ib(default=MISSING)

    def __attrs_post_init__(self):
        self.client.add_component_callback(
            ComponentCommand(
                name=f"Paginator:{self._uuid}",
                callback=self._on_button,
                listeners=list(get_components_ids(self.create_components(all=True))),
            )
        )

    @property
    def message(self) -> Message:
        return self._message

    @property
    def author_id(self) -> Snowflake_Type:
        return self._author_id

    @classmethod
    def create_from_embeds(cls, client: "Snake", *embeds: Embed, timeout: int = 0) -> "Paginator":
        """Create a paginator system from a list of embeds"""
        return cls(client, pages=list(embeds), timeout_interval=timeout)

    @classmethod
    def create_from_string(
        cls, client: "Snake", content: str, prefix: str = "", suffix: str = "", page_size: int = 4000, timeout: int = 0
    ) -> "Paginator":
        """Create a paginator system from a string"""
        content_pages = textwrap.wrap(
            content,
            width=page_size - (len(prefix) + len(suffix)),
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=False,
        )
        pages = [Page(c, prefix=prefix, suffix=suffix) for c in content_pages]
        return cls(client, pages=pages, timeout_interval=timeout)

    def create_components(self, disable=False, all=False) -> List[ActionRow]:
        """
        Create the components for the paginator message

        Args:
            disable: Should all the components be disabled?
            all: Force all components to be enabled

        Returns:
            A list of ActionRows
        """
        output = []

        if self.show_select_menu or all:
            current = self.pages[self.page_index]
            output.append(
                Select(
                    [
                        SelectOption(f"{i+1} {p.get_summary if isinstance(p, Page) else p.title}", str(i))
                        for i, p in enumerate(self.pages)
                    ],
                    custom_id=f"{self._uuid}|select",
                    placeholder=f"{self.page_index+1} {current.get_summary if isinstance(current, Page) else current.title}",
                    max_values=1,
                    disabled=disable,
                )
            )

        if self.show_first_button or all:
            output.append(
                Button(
                    ButtonStyles.BLURPLE,
                    emoji="⏮️",
                    custom_id=f"{self._uuid}|first",
                    disabled=disable or self.page_index == 0,
                )
            )
        if self.show_back_button or all:
            output.append(
                Button(
                    ButtonStyles.BLURPLE,
                    emoji="⬅️",
                    custom_id=f"{self._uuid}|back",
                    disabled=disable or self.page_index == 0,
                )
            )

        if self.show_callback_button or all:
            output.append(Button(ButtonStyles.BLURPLE, emoji="✅", custom_id=f"{self._uuid}|callback", disabled=disable))

        if self.show_next_button or all:
            output.append(
                Button(
                    ButtonStyles.BLURPLE,
                    emoji="➡️",
                    custom_id=f"{self._uuid}|next",
                    disabled=disable or self.page_index >= len(self.pages) - 1,
                )
            )
        if self.show_last_button or all:
            output.append(
                Button(
                    ButtonStyles.BLURPLE,
                    emoji="⏭️",
                    custom_id=f"{self._uuid}|last",
                    disabled=disable or self.page_index >= len(self.pages) - 1,
                )
            )

        return spread_to_rows(*output)

    def to_dict(self) -> dict:
        """Convert this paginator into a dictionary for sending"""
        page = self.pages[self.page_index]

        if isinstance(page, Page):
            page = page.to_embed()
            if not page.title and self.default_title:
                page.title = self.default_title
        if not page.footer:
            page.set_footer(f"Page {self.page_index+1}/{len(self.pages)}")
        if not page.color:
            page.color = self.default_color

        return {"embeds": [page.to_dict()], "components": [c.to_dict() for c in self.create_components()]}

    async def send(self, ctx: Context) -> Message:
        """
        Send this paginator

        Args:
            ctx: The context to send this paginator with

        Returns:
            The resulting message
        """
        self._message = await ctx.send(**self.to_dict())
        self._author_id = ctx.author.id

        if self.timeout_interval > 1:
            self._timeout_task = Timeout(self)
            self.client.loop.create_task(self._timeout_task())

        return self._message

    async def stop(self) -> None:
        """Disable this paginator"""
        if self._timeout_task:
            self._timeout_task.run = False
            self._timeout_task.ping.set()
        await self._message.edit(components=self.create_components(True))

    async def update(self):
        """
        Update the paginator to the current state

        Use this if you have programmatically changed the page_index"""
        await self._message.edit(**self.to_dict())

    async def _on_button(self, ctx: ComponentContext, *args, **kwargs):
        if ctx.author.id == self.author_id:
            if self._timeout_task:
                self._timeout_task.ping.set()
            match ctx.custom_id.split("|")[1]:
                case "first":
                    self.page_index = 0
                case "last":
                    self.page_index = len(self.pages) - 1
                case "next":
                    if (self.page_index + 1) < len(self.pages):
                        self.page_index += 1
                case "back":
                    if (self.page_index - 1) >= 0:
                        self.page_index -= 1
                case "select":
                    self.page_index = int(ctx.values[0])
                case "callback":
                    if self.callback:
                        return await self.callback(ctx)

            await ctx.edit_origin(**self.to_dict())
        else:
            if self.wrong_user_message:
                return await ctx.send(self.wrong_user_message, ephemeral=True)
            else:
                # silently ignore
                return await ctx.defer(edit_origin=True)

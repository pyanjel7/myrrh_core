import bmy

from .exceptions import Reboot
from prompt_toolkit.application import get_app

from prompt_toolkit.filters import (
    Condition,
    has_focus,
)

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys


def load_confirm_exit_bindings(prompt):
    """
    Handle yes/no key presses when the exit confirmation is shown.
    """
    bindings = KeyBindings()

    handle = bindings.add
    confirmation_visible = Condition(lambda: prompt.show_exit_confirmation)

    @handle("y", filter=confirmation_visible)
    @handle("Y", filter=confirmation_visible)
    @handle("enter", filter=confirmation_visible)
    @handle("c-d", filter=confirmation_visible)
    def _(event):
        """
        Really quit.
        """
        if prompt.reboot_required:
            event.app.exit(exception=Reboot, style="class:exiting")
        else:
            event.app.exit(exception=EOFError, style="class:exiting")

    @handle(Keys.Any, filter=confirmation_visible)
    def _(event):
        """
        Cancel exit.
        """
        prompt.show_exit_confirmation = False
        prompt.reboot_required = False
        prompt.app.layout.focus_previous()

    return bindings


def load_prompt_bindings(prompt):
    """
    Custom key bindings.
    """
    bindings = KeyBindings()

    handle = bindings.add

    @handle(
        "c-r",
        filter=has_focus(prompt.default_buffer)
        & Condition(
            lambda:
            # The current buffer is empty.
            not get_app().current_buffer.text
        ),
    )
    def _(event):
        """
        Override Control-D exit, to ask for confirmation.
        """
        if prompt.confirm_exit:
            # Show exit confirmation and focus it (focusing is important for
            # making sure the default buffer key bindings are not active).
            prompt.show_exit_confirmation = True
            prompt.reboot_required = True
            prompt.app.layout.focus(prompt.exit_confirmation)
        else:
            event.app.exit(exception=Reboot)

    @handle(
        "c-d",
        filter=has_focus(prompt.default_buffer)
        & Condition(
            lambda:
            # The current buffer is empty.
            not get_app().current_buffer.text
        ),
    )
    def _(event):
        """
        Override Control-D exit, to ask for confirmation.
        """
        if prompt.confirm_exit:
            # Show exit confirmation and focus it (focusing is important for
            # making sure the default buffer key bindings are not active).
            prompt.show_exit_confirmation = True
            prompt.reboot_required = False
            prompt.app.layout.focus(prompt.exit_confirmation)
        else:
            event.app.exit(exception=EOFError)

    @handle("c-c", filter=has_focus(prompt.default_buffer))
    def _(event):
        "Abort when Control-C has been pressed."
        event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    @handle("c-z")
    def _(event):
        bmy.next()

    @handle("c-a")
    def _(event):
        bmy.previous()

    return bindings

from __future__ import annotations

import inspect
from functools import partial
from typing import TYPE_CHECKING, Any, Callable

from magicgui.widgets import FunctionGui, MainFunctionGui

if TYPE_CHECKING:
    from magicgui.application import AppRef

__all__ = ["magicgui", "magic_factory", "MagicFactory"]


def magicgui(
    function: Callable | None = None,
    *,
    layout: str = "vertical",
    labels: bool = True,
    tooltips: bool = True,
    call_button: bool | str = False,
    auto_call: bool = False,
    result_widget: bool = False,
    main_window: bool = False,
    app: AppRef = None,
    **param_options: dict,
):
    """Return a :class:`FunctionGui` for ``function``.

    Parameters
    ----------
    function : Callable, optional
        The function to decorate.  Optional to allow bare decorator with optional
        arguments. by default ``None``
    layout : str, optional
        The type of layout to use. Must be one of {'horizontal', 'vertical'}.
        by default "vertical".
    labels : bool, optional
        Whether labels are shown in the widget. by default True
    tooltips : bool, optional
        Whether tooltips are shown when hovering over widgets. by default True
    call_button : bool or str, optional
        If ``True``, create an additional button that calls the original function when
        clicked.  If a ``str``, set the button text. by default False
    auto_call : bool, optional
        If ``True``, changing any parameter in either the GUI or the widget attributes
        will call the original function with the current settings. by default False
    result_widget : bool, optional
        Whether to display a LineEdit widget the output of the function when called,
        by default False
    main_window : bool
        Whether this widget should be treated as the main app window, with menu bar,
        by default True.
    app : magicgui.Application or str, optional
        A backend to use, by default ``None`` (use the default backend.)

    **param_options : dict of dict
        Any additional keyword arguments will be used as parameter-specific options.
        Keywords MUST match the name of one of the arguments in the function
        signature, and the value MUST be a dict.

    Returns
    -------
    result : FunctionGui or Callable[[F], FunctionGui]
        If ``function`` is not ``None`` (such as when this is used as a bare decorator),
        returns a FunctionGui instance, which is a list-like container of autogenerated
        widgets corresponding to each parameter in the function.
        If ``function`` is ``None`` such as when arguments are provided like
        ``magicgui(auto_call=True)``, then returns a function that can be used as a
        decorator.

    Examples
    --------
    >>> @magicgui
    ... def my_function(a: int = 1, b: str = 'hello'):
    ...     pass
    ...
    >>> my_function.show()
    >>> my_function.a.value == 1  # True
    >>> my_function.b.value = 'world'
    """
    return _magicgui(**locals())


def magic_factory(
    function: Callable | None = None,
    *,
    layout: str = "vertical",
    labels: bool = True,
    tooltips: bool = True,
    call_button: bool | str = False,
    auto_call: bool = False,
    result_widget: bool = False,
    main_window: bool = False,
    app: AppRef = None,
    widget_init: Callable[[FunctionGui], None] | None = None,
    **param_options: dict,
):
    """Return a :class:`MagicFactory` for ``function``."""
    return _magicgui(factory=True, **locals())


_factory_doc = magicgui.__doc__.split("Returns")[0] + (  # type: ignore
    """
    Returns
    -------
    result : MagicFactory or Callable[[F], MagicFactory]
        If ``function`` is not ``None`` (such as when this is used as a bare decorator),
        returns a MagicFactory instance.
        If ``function`` is ``None`` such as when arguments are provided like
        ``magic_factory(auto_call=True)``, then returns a function that can be used as a
        decorator.

    Examples
    --------
    >>> @magic_factory
    ... def my_function(a: int = 1, b: str = 'hello'):
    ...     pass
    ...
    >>> my_widget = my_function()
    >>> my_widget.show()
    >>> my_widget.a.value == 1  # Trueq
    >>> my_widget.b.value = 'world'
    """
)

magic_factory.__doc__ += "\n\n    Parameters" + _factory_doc.split("Parameters")[1]  # type: ignore  # noqa


class MagicFactory(partial):
    """Factory function that returns a FunctionGui instance.

    While this can be used directly, (see example below) the preferred usage is
    via the :func:`magic_factory` decorator.

    Examples
    --------
    >>> def func(x: int, y: str):
    ...     pass
    ...
    >>> factory = MagicFactory(function=func, labels=False)
    >>> # factory accepts all the same arguments as magicgui()
    >>> widget1 = factory(call_button=True)
    >>> # can also override magic_kwargs that were provided when creating the factory
    >>> widget2 = factory(auto_call=True, labels=True)
    """

    def __new__(
        cls,
        function,
        *args,
        magic_class=FunctionGui,
        widget_init: Callable[[FunctionGui], None] | None = None,
        **keywords,
    ):
        """Create new MagicFactory."""
        if not function:
            raise TypeError(
                "MagicFactory missing required positional argument 'function'"
            )

        # we want function first for the repr
        keywords = {"function": function, **keywords}
        if widget_init is not None:
            if not callable(widget_init):
                raise TypeError(
                    f"'widget_init' must be a callable, not {type(widget_init)}"
                )
            if not len(inspect.signature(widget_init).parameters) == 1:
                raise TypeError(
                    "'widget_init' must be a callable that accepts a single argument"
                )
        obj = super().__new__(cls, magic_class, *args, **keywords)  # type: ignore
        obj._widget_init = widget_init
        return obj

    def __repr__(self) -> str:
        """Return string repr."""
        params = inspect.signature(magicgui).parameters
        args = [
            f"{k}={v!r}"
            for (k, v) in self.keywords.items()
            if v not in (params[k].default, {})
        ]
        return f"MagicFactory({', '.join(args)})"

    def __call__(self, *args, **kwargs):
        """Call the wrapped _magicgui and return a FunctionGui."""
        if args:
            raise ValueError("MagicFactory instance only accept keyword arguments")
        params = inspect.signature(magicgui).parameters
        prm_options = self.keywords.pop("param_options", {})
        prm_options.update({k: kwargs.pop(k) for k in list(kwargs) if k not in params})
        widget = self.func(param_options=prm_options, **{**self.keywords, **kwargs})
        if self._widget_init is not None:
            self._widget_init(widget)
        return widget

    def __getattr__(self, name) -> Any:
        """Allow accessing FunctionGui attributes without mypy error."""
        pass  # pragma: no cover

    @property
    def __name__(self) -> str:
        """Pass function name."""
        return getattr(self.keywords.get("function"), "__name__", "FunctionGui")


def _magicgui(
    function=None, factory=False, widget_init=None, main_window=False, **kwargs
):
    """Actual private magicui decorator.

    if factory is `True` will return a MagicFactory instance, that can be called
    to return a `FunctionGui` instance.  See docstring of ``magicgui`` for parameters.
    Otherwise, this will return a FunctionGui instance directly.
    """

    def inner_func(func: Callable) -> FunctionGui | MagicFactory:
        if not callable(func):
            raise TypeError("the first argument must be callable")

        magic_class = MainFunctionGui if main_window else FunctionGui

        if factory:
            return MagicFactory(
                func, magic_class=magic_class, widget_init=widget_init, **kwargs
            )
        # MagicFactory is unnecessary if we are immediately instantiating the widget,
        # so we shortcut that and just return the FunctionGui here.
        return magic_class(func, **kwargs)

    if function is None:
        return inner_func
    else:
        return inner_func(function)

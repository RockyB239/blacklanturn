"""Bounded BlackLanturn startup ordering; properties belong to this service run."""
import time

import xbmc
import xbmcgui

_HOME = 'BlackLanturn.Startup.Home'
_PREFIX = 'BlackLanturn.Startup.YouTube.'
_OWNER = _PREFIX + 'Owner'
_READY = _PREFIX + 'Ready'
_DEMAND = _PREFIX + 'Demand'
_SKIN = 'skin.blacklanturn.preview'
_POLL = 0.05
_TIMEOUT = 15.0
_service_owner = None


class ServiceSession:
    """Claim this run before importing the service; release only our own claim."""

    def __enter__(self):
        global _service_owner
        self.window = xbmcgui.Window(10000)
        self.owner = '{}:{}'.format(time.monotonic_ns(), id(self))
        _service_owner = self.owner
        self.window.setProperty(_OWNER, self.owner)
        self.window.clearProperty(_READY)
        try:
            monitor = xbmc.Monitor()
            deadline = time.monotonic() + _TIMEOUT
            while not monitor.abortRequested():
                if (self.window.getProperty(_HOME) in ('ready', 'released')
                        or self.window.getProperty(_DEMAND) == '1'
                        or xbmc.getSkinDir() != _SKIN):
                    return True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return True
                if monitor.waitForAbort(min(_POLL, remaining)):
                    return False
            return False
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        global _service_owner
        if self.window.getProperty(_OWNER) == self.owner:
            self.window.clearProperty(_READY)
            self.window.clearProperty(_OWNER)
        if _service_owner == self.owner:
            _service_owner = None
        # Demand remains sticky until a successfully initialized run consumes it.
        return False


def publish_ready():
    """Called only after native monitors, HTTP setup, and temp cleanup finish."""
    window = xbmcgui.Window(10000)
    if not _service_owner or window.getProperty(_OWNER) != _service_owner:
        return False
    window.setProperty(_READY, _service_owner)
    window.clearProperty(_DEMAND)
    return True


def wait_ready(timeout=_TIMEOUT):
    """Wake startup on first use; false means abort or a bounded startup failure."""
    # Native service initialization can itself use IPC. It must not wait on itself.
    if _service_owner:
        return True
    window = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + timeout
    demand_sent = False
    while not monitor.abortRequested():
        owner = window.getProperty(_OWNER)
        if (owner and window.getProperty(_READY) == owner
                and window.getProperty(_OWNER) == owner):
            return True
        if not demand_sent:
            window.setProperty(_DEMAND, '1')
            demand_sent = True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        if monitor.waitForAbort(min(_POLL, remaining)):
            return False
    return False

from tmdbhelper.lib.addon.plugin import get_setting
from jurialmunkey.window import get_property, wait_for_property
from tmdbhelper.lib.monitor.listitemtools import ListItemMonitorFunctions
from tmdbhelper.lib.monitor.cronjob import CronJobMonitor
from tmdbhelper.lib.monitor.player import PlayerMonitor
from tmdbhelper.lib.monitor.update import UpdateMonitor
from tmdbhelper.lib.monitor.imgmon import ImagesMonitor
from tmdbhelper.lib.monitor.poller import Poller, POLL_MIN_INCREMENT, POLL_MAX_INCREMENT
from tmdbhelper.lib.addon.thread import SafeThread
from threading import Lock
from time import monotonic


class ServiceMonitor(Poller):
    def __init__(self):
        self.exit = False
        self.listitem = None

    def _on_idle(self, wait_time=30):
        scrobbler = self.player_monitor.scrobbler
        if not scrobbler or scrobbler.stopped:
            return super()._on_idle(wait_time)

        # Sample locally in the existing loop, including windowed playback.
        # The deadline persists across short UI waits to cap sampling at 1 Hz.
        end_time = monotonic() + wait_time
        while not self.exit:
            now = monotonic()
            next_sample = getattr(self, '_playback_sample_at', 0)
            if now >= next_sample:
                self._playback_sample_at = next_sample = now + 1
                self.player_monitor.scrobbler_update()
            remaining = end_time - monotonic()
            if remaining <= 0:
                return
            if self.update_monitor.waitForAbort(min(remaining, max(0, next_sample - monotonic()))):
                return
            scrobbler = self.player_monitor.scrobbler
            if not scrobbler or scrobbler.stopped:
                remaining = end_time - monotonic()
                if remaining > 0:
                    self.update_monitor.waitForAbort(remaining)
                return

    def run(self):
        self.mutex_lock = Lock()

        self.update_monitor = UpdateMonitor()
        self.player_monitor = PlayerMonitor()

        self.run_cron_job()
        self.run_images_monitor()

        self.listitem_funcs = ListItemMonitorFunctions(self)

        get_property('ServiceStarted', 'True')

        self.poller()

    def run_cron_job(self):
        self.cron_job = CronJobMonitor(self, update_hour=get_setting('library_autoupdate_hour', 'int'))
        self.cron_job.setName('Cron Thread')
        self.cron_job.start()

    def run_images_monitor(self):
        self.images_monitor = ImagesMonitor(self)
        self.images_monitor.setName('Image Thread')
        self.images_monitor.start()

    def _on_listitem(self):
        self.listitem_funcs.on_listitem()
        self._on_idle(POLL_MIN_INCREMENT)

    def _on_scroll(self):
        self.listitem_funcs.on_scroll()
        self._on_idle(POLL_MIN_INCREMENT)

    def _on_fullscreen(self):
        self.player_monitor.on_fullscreen()
        self._on_idle(POLL_MAX_INCREMENT)

    def _on_context(self):
        self.listitem_funcs.on_context_listitem()
        self._on_idle(POLL_MIN_INCREMENT)

    def _on_clear(self):
        """
        IF we've got properties to clear lets clear them and then jump back in the loop
        """
        self.listitem_funcs.reset_current_item()  # Reset current item so that it will retrigger lookup on return to previous window
        self.listitem_funcs.clear_properties()
        self._on_idle(POLL_MIN_INCREMENT)

    def _on_exit(self):
        try:
            self.cron_job.exit = True
        except AttributeError:
            pass
        try:
            self.images_monitor.exit = True
        except AttributeError:
            pass
        if not self.update_monitor.abortRequested():
            get_property('ServiceStarted', clear_property=True)
            get_property('ServiceStop', clear_property=True)


def restart_service_monitor():
    if get_property('ServiceStarted') == 'True':
        wait_for_property('ServiceStop', value='True', set_property=True)  # Stop service
    wait_for_property('ServiceStop', value=None)  # Wait until Service clears property
    SafeThread(target=ServiceMonitor().run).start()

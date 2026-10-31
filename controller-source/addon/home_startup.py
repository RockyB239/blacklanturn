"""Ephemeral ordering signal for optional services; never a first-paint timer."""
import time

HOME = 'BlackLanturn.Startup.Home'
OWNER = 'BlackLanturn.Startup.Owner'


class HomeStartup:
    def __init__(self, home, clock=time.monotonic):
        self.home = home
        self.clock = clock
        self.owner = str(time.monotonic_ns())
        self.deadline = clock() + 15
        self.next_probe = 0
        self.candidate = None
        self.stable_since = None
        self.done = False
        # Publish pending first so a new owner cannot inherit an old ready flag.
        home.setProperty(HOME, 'pending')
        home.setProperty(OWNER, self.owner)

    def owns(self):
        return self.home.getProperty(OWNER) == self.owner

    def release(self):
        self.done = True
        if self.owns():
            self.home.setProperty(HOME, 'released')

    def observe(self, window, lifetime, rpc, artwork):
        """Observe queued GUI binding without blocking setup, input, or refresh.

        Only the first card of each visible row and the selected hero are read.
        Text/fallback cards remain valid. No texture, provider, or disk reads.
        """
        if self.done or not self.owns():
            return
        def current():
            return window.alive and lifetime is window.window_lifetime and self.owns()
        if not current():
            return
        now = self.clock()
        if now >= self.deadline:
            self.release()
            return
        if now < self.next_probe:
            return
        self.next_probe = now + .2
        try:
            if window.mode != 'home' or window.section != 'Home':
                self.release()
                return
            if window.getProperty('loading') == 'true' or not all(window.window_ready):
                self.candidate = None
                self.stable_since = None
                return
            rows = tuple(window.rows)
            counts = tuple(len(row) for row in rows)
            if not any(not item.get('_page_control') for row in rows for item in row):
                self.release()
                return
            generation = window.generation
            expected = {'Window.Property(startupOwner)': self.owner,
                        'Window.Property(loading)': 'false',
                        'Window.Property(hero)': window.getProperty('hero')}
            def unchanged():
                return (current() and generation == window.generation
                        and len(window.rows) == len(rows)
                        and all(row is window.rows[n] and len(row) == counts[n] for n, row in enumerate(rows))
                        and window.getProperty('hero') == expected['Window.Property(hero)'])
            visible = []
            for n, row in enumerate(rows):
                control = str(900 + n)
                expected['Container(' + control + ').NumItems'] = str(len(row))
                if row:
                    visible.append('Control.IsVisible(' + control + ')')
                    art = artwork(row[0])
                    if art['image']:
                        kind = {'portrait': 'poster', 'paging': 'navigation'}.get(art['kind'], art['kind'])
                        expected['Container(' + control + ').ListItemAbsolute(0).Art(' + kind + ')'] = art['image']
            signature = (id(window), id(lifetime), generation, tuple(id(row) for row in rows), tuple(expected.items()))
            labels = rpc('XBMC.GetInfoLabels', {'labels': list(expected)}).get('result', {})
            if not unchanged():
                return
            matching = all(labels.get(key) == value for key, value in expected.items())
            if matching:
                booleans = rpc('XBMC.GetInfoBooleans', {'booleans': visible + ['Window.IsVisible(yesnodialog)']}).get('result', {})
                matching = all(booleans.get(key) is True for key in visible) and booleans.get('Window.IsVisible(yesnodialog)') is False
            if not unchanged():
                return
            if not matching:
                self.candidate = None
                self.stable_since = None
                return
            if signature != self.candidate:
                self.candidate = signature
                self.stable_since = now
            elif now - self.stable_since >= .35 and not self.done:
                self.home.setProperty(HOME, 'ready')
                self.done = True
        except Exception:
            # Readiness must not interfere with the existing controller. A
            # broken GUI observer releases at the same bounded deadline.
            self.candidate = None
            self.stable_since = None

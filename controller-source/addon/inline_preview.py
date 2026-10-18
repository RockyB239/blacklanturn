"""Controller-owned inline cutoff; never invoke YouTube's timed player.stop."""
import math

class InlinePreviewClock:
    def __init__(self,duration=45,fade=1,stall=3):
        self.duration=duration if math.isfinite(duration) and duration>0 else 45
        self.fade=min(fade,self.duration);self.stall=stall
        self.started=None;self.progress_confirmed=False;self.progress=None;self.progress_at=None;self.fading_at=None
    def tick(self,now,position,playing):
        if not playing:return 'stop' if self.started is not None else 'waiting'
        if self.started is None:self.started=now;self.progress_at=now;self.progress=0
        # Native decoders can briefly expose a stale PTS at startup. A preview
        # starts at zero at normal speed, so reject positions that could not
        # have elapsed; never let a bad sample poison subsequent progress.
        valid=math.isfinite(position) and 0<=position<=now-self.started+5
        if valid and position>self.progress+.02:self.progress=position;self.progress_at=now;self.progress_confirmed=True
        if self.fading_at is None and (valid and position>=self.duration-self.fade or now-self.progress_at>=(self.stall if self.progress_confirmed else 12) or now-self.started>=self.duration):
            self.fading_at=now
        if self.fading_at is not None:return 'stop' if now-self.fading_at>=self.fade else 'fading'
        return 'playing'

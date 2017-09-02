from datetime import datetime, timedelta

def timeElapsed(tnow, t):
    dt = tnow - t
    return dt.total_seconds()

class MotionStateMachine:
    IDLE = 1
    MOTION_DETECTED = 2
    SUSTAINED_MOTION = 3

    MOTION_DETECTED_MOTION = 1
    MOTION_DETECTED_NOMOTION = 2

    SUSTAINED_MOTION_MOTION = 1
    SUSTAINED_MOTION_NOMOTION = 2

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = 0
        self.MOTION_DETECTED_state = 0
        self.SUSTAINED_MOTION_state = 0

        self.MOTION_DETECTED_tStart = 0
        self.MOTION_DETECTED_NOMOTION_tStart = 0
        self.SUSTAINED_MOTION_NOMOTION_tStart = 0

        self.CALM_TIME = 30
        self.SUSTAINED_TIME = 90

    def inSustainedMotion(self):
        return self.state == self.SUSTAINED_MOTION
    
    def secondsInSustainedMotion(self):
        if not self.inSustainedMotion():
            return 0

        return timeElapsed(self.SUSTAINED_MOTION_tStart)

    def step(self, motion, tnow=None):
        if not tnow:
            tnow = datetime.now()

        if self.state == 0:
            self.state = self.IDLE

        if self.state == self.IDLE:

            if motion:
                self.state = self.MOTION_DETECTED
                self.MOTION_DETECTED_state = self.MOTION_DETECTED_MOTION
                self.MOTION_DETECTED_tStart = tnow

        elif self.state == self.MOTION_DETECTED:

            if motion and timeElapsed(tnow, self.MOTION_DETECTED_tStart) >= self.SUSTAINED_TIME:
                self.state = self.SUSTAINED_MOTION
                self.MOTION_DETECTED_state = 0
                self.SUSTAINED_MOTION_state = self.SUSTAINED_MOTION_MOTION
                self.SUSTAINED_MOTION_tStart = tnow

            elif self.MOTION_DETECTED_state == self.MOTION_DETECTED_MOTION:

                if not motion:
                    self.MOTION_DETECTED_state = self.MOTION_DETECTED_NOMOTION
                    self.MOTION_DETECTED_NOMOTION_tStart = tnow

            elif self.MOTION_DETECTED_state == self.MOTION_DETECTED_NOMOTION:

                if motion:
                    self.MOTION_DETECTED_state = self.MOTION_DETECTED_MOTION
                else:
                    dt = timeElapsed(tnow, self.MOTION_DETECTED_NOMOTION_tStart)
                    if dt >= self.CALM_TIME:
                        self.MOTION_DETECTED_state = 0
                        self.state = self.IDLE

        elif self.state == self.SUSTAINED_MOTION:

            if self.SUSTAINED_MOTION_state == self.SUSTAINED_MOTION_MOTION:
                if not motion:
                    self.SUSTAINED_MOTION_state = self.SUSTAINED_MOTION_NOMOTION
                    self.SUSTAINED_MOTION_NOMOTION_tStart = tnow

            elif self.SUSTAINED_MOTION_state == self.SUSTAINED_MOTION_NOMOTION:
                if motion:
                    self.SUSTAINED_MOTION_state = self.SUSTAINED_MOTION_MOTION
                elif timeElapsed(tnow, self.SUSTAINED_MOTION_NOMOTION_tStart) >= self.CALM_TIME:
                    self.SUSTAINED_MOTION_state = 0
                    self.state = self.IDLE

if __name__ == "__main__":
    sm = MotionStateMachine()

    from dateutil.parser import parse
    import matplotlib.pyplot as plot
    import re

    PAT_INFO = re.compile(r'(?P<time>\S+): motionDetected (?P<motion>\d)')

    tStart = parse('2015-09-03 03:00:00')
    tEnd = parse('2016-09-03 05:10:00')
    x = []
    rawMotion = []
    state = []
    detectedState = []
    for line in open('logs/sleep_2015_09_03.log'):
        m = PAT_INFO.match(line)
        if m:
            t = parse(m.group('time'))
            if t > tEnd:
                break
            if t >= tStart:
                motion = int(m.group('motion'))
                sm.step(motion, t)

                x.append(t)
                rawMotion.append(motion)
                state.append(sm.state)
                detectedState.append(sm.MOTION_DETECTED_state)

    ax1 = plot.subplot(311)
    plot.plot(x, rawMotion, '-+');
    plot.xlim(min(x), max(x))
    plot.subplot(312, sharex=ax1)
    plot.plot(x, detectedState, '-+')
    plot.xlim(min(x), max(x))
    plot.subplot(313, sharex=ax1)
    plot.plot(x, state, '-+');
    plot.xlim(min(x), max(x))
    plot.show()

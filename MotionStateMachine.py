from datetime import datetime

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

    def step(self, motion, tnow=None):
        if not tnow:  # pragma: no cover
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

            else:
                assert(self.MOTION_DETECTED_state == self.MOTION_DETECTED_NOMOTION)

                if motion:
                    self.MOTION_DETECTED_state = self.MOTION_DETECTED_MOTION
                else:
                    dt = timeElapsed(tnow, self.MOTION_DETECTED_NOMOTION_tStart)
                    if dt >= self.CALM_TIME:
                        self.MOTION_DETECTED_state = 0
                        self.state = self.IDLE

        else:
            assert(self.state == self.SUSTAINED_MOTION)

            if self.SUSTAINED_MOTION_state == self.SUSTAINED_MOTION_MOTION:
                if not motion:
                    self.SUSTAINED_MOTION_state = self.SUSTAINED_MOTION_NOMOTION
                    self.SUSTAINED_MOTION_NOMOTION_tStart = tnow

            else:
                assert(self.SUSTAINED_MOTION_state == self.SUSTAINED_MOTION_NOMOTION)
                if motion:
                    self.SUSTAINED_MOTION_state = self.SUSTAINED_MOTION_MOTION
                elif timeElapsed(tnow, self.SUSTAINED_MOTION_NOMOTION_tStart) >= self.CALM_TIME:
                    self.SUSTAINED_MOTION_state = 0
                    self.state = self.IDLE

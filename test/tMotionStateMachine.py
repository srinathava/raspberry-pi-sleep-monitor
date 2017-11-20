import os
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, '..'))

from MotionStateMachine import MotionStateMachine  # noqa: E402

def motionFor(timeMotionPairs, sampleTime, endTime):
    curIdx = 0
    (nextChangeTime, nextMotion) = timeMotionPairs[0]

    curTime = 0
    curMotion = 0
    while curTime < endTime:
        yield (curTime, curMotion)

        curTime += sampleTime

        if curTime >= nextChangeTime:
            curMotion = nextMotion
            curIdx += 1
            if curIdx < len(timeMotionPairs):
                (nextChangeTime, nextMotion) = timeMotionPairs[curIdx]

def getMotionDetectionStatus(spec, sampleTime, endTime):
    exp = []

    fsm = MotionStateMachine()
    tstart = datetime.now()
    for (seconds, motion) in motionFor(spec, sampleTime, endTime):
        tnow = tstart + timedelta(seconds=seconds)
        fsm.step(motion, tnow=tnow)
        exp.append((seconds, fsm.inSustainedMotion()))

    return exp

def testSimple():
    spec = (
        (10, 1),
        (120, 0)
    )
    st = 1
    et = 150

    actMotion = (
        (100, 1)
    )

    actMotion = getMotionDetectionStatus(spec, st, et)
    expMotion = list(motionFor(actMotion, st, et))

    print(actMotion)
    print(expMotion)

testSimple()

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
        if curTime >= nextChangeTime:
            curMotion = nextMotion
            curIdx += 1
            if curIdx < len(timeMotionPairs):
                (nextChangeTime, nextMotion) = timeMotionPairs[curIdx]

        yield (curTime, curMotion)
        curTime += sampleTime


def getMotionDetectionStatus(spec, sampleTime, endTime):
    exp = []

    fsm = MotionStateMachine()
    tstart = datetime.now()
    for (seconds, motion) in motionFor(spec, sampleTime, endTime):
        tnow = tstart + timedelta(seconds=seconds)
        fsm.step(motion, tnow=tnow)
        exp.append((seconds, fsm.inSustainedMotion()))

    return exp


def testBasicMotionDetection():
    """Basic motion detection

    Baby starts moving at 10s, moves all the way to 120s, the motion should
    be detected at 100. Later at 150, the motion should go back to zero.
    """
    spec = (
        (0, 0),
        (10, 1),
        (120, 0)
    )
    st = 1
    et = 200

    expMotion = (
        (0, 0),
        (100, 1),
        (150, 0),
    )

    actMotion = getMotionDetectionStatus(spec, st, et)

    expMotion = list(motionFor(expMotion, st, et))

    assert(actMotion == expMotion)


def testMotionWithBriefCalm():
    spec = (
        (0, 0),
        (10, 1),
        (15, 0),
        (20, 1),
        (120, 0)
    )
    st = 1
    et = 200

    expMotion = (
        (0, 0),
        (100, 1),
        (150, 0),
    )

    actMotion = getMotionDetectionStatus(spec, st, et)

    expMotion = list(motionFor(expMotion, st, et))

    assert(actMotion == expMotion)


def testMoveButCalmDown():
    spec = (
        (0, 0),
        (10, 1),
        (15, 0),
    )
    st = 1
    et = 200

    expMotion = (
        (0, 0),
    )

    actMotion = getMotionDetectionStatus(spec, st, et)

    expMotion = list(motionFor(expMotion, st, et))

    assert(actMotion == expMotion)


def testSustainedMotionWithABitOfCalm():
    spec = (
        (0, 0),
        (10, 1),
        (150, 0),
        (155, 1),
    )
    st = 1
    et = 200

    expMotion = (
        (0, 0),
        (100, 1),
    )

    actMotion = getMotionDetectionStatus(spec, st, et)

    expMotion = list(motionFor(expMotion, st, et))

    assert(actMotion == expMotion)

class Alarm {
    constructor(name, priority, mp3) {
        this.name = name;
        this.priority = priority;

        this.audio = new Audio(mp3);
        this.audio.loop = true;
        this.mode = 'inactive';
        this.snoozeTime = 0;

        this.suppressed = false;
        this.div = $('#' + this.name);
        this.div.hide();
    }

    snooze() {
        if (this.mode != 'active') {
            return;
        }

        this.mode = 'snoozed';
        this.audio.pause();
        this.div.hide();
        this.snoozeTime = Date.now();
    }

    trigger(txt) {
        if (this.suppressed || this.mode === 'active') {
            return;
        }

        if (Date.now() - this.snoozeTime < 60*1000) {
            return;
        }

        this.mode = 'active';
        this.div.html(txt).show();
        alarmsContainer.center();

        this.audio.currentTime = 0;

        var playSound = true;
        alarms.forEach(function(alarm) {
            if (alarm.mode == 'active') {
                if (alarm === this) {
                    return;
                } else if (alarm.priority < this.priority) {
                    alarm.audio.pause();
                } else if (alarm.priority > this.priority) {
                    playSound = false;
                }
            }
        }, this);

        if (playSound) {
            this.audio.play();
        }
    }

    _dismiss() {
        this.audio.pause();
        this.snoozeTime = 0;
        this.mode = 'inactive';
        this.div.hide();
    }

    static reenableNextAlarm(alarms) {
        var highestPriorityAlarm = null;
        alarms.forEach(function(alarm) {
            if (alarm.mode == 'active') {
                highestPriorityAlarm = alarm;
            }
        }, this);

        if (highestPriorityAlarm !== null) {
            highestPriorityAlarm.audio.play();
        }
    }

    static dismiss(alarm, otherAlarms) {
        alarm._dismiss();
        Alarm.reenableNextAlarm(otherAlarms);
    }
}

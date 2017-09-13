$(document).ready(function() {

    jQuery.fn.center = function () {
        this.css("position","absolute");
        this.css("top", Math.max(0, (($(window).height() - $(this).outerHeight()) / 2) + $(window).scrollTop()) + "px");
        this.css("left", Math.max(0, (($(window).width() - $(this).outerWidth()) / 2) + $(window).scrollLeft()) + "px");
        return this;
    };

    var motionAlarmAudio = new Audio('motion_alarm.mp3'); motionAlarmAudio.loop = true;
    var oximeterAlarmAudio = new Audio('oximeter_alarm.mp3'); oximeterAlarmAudio.loop = true;
    var connectionAlarmAudio = new Audio('connection_alarm.mp3'); connectionAlarmAudio.loop = true;

    var currentAlarm = null;

    var alarms = [];

    var alarmsContainer = $('#alarmsContainer');
    alarmsContainer.center();

    function Alarm(name, priority, mp3) {
        this.name = name;
        this.priority = priority;

        this.audio = new Audio(mp3);
        this.audio.loop = true;
        this.mode = 'inactive';
        this.snoozeTime = 0;

        this.suppressed = false;
        this.div = $('#' + this.name);
        this.div.hide();

        alarms.push(this);
    }

    Alarm.prototype.snooze = function() {
        if (this.mode != 'active') {
            return;
        }

        this.mode = 'snoozed';
        this.audio.pause();
        this.div.hide();
        this.snoozeTime = Date.now();
    };

    Alarm.prototype.trigger = function(txt) {
        if (this.suppressed || this.mode === 'active') {
            return;
        }

        if (Date.now() - this.snoozeTime < 60*1000) {
            return;
        }

        this.mode = 'active';
        this.div.html(txt).show();

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
    };

    Alarm.prototype.dismiss = function() {
        this.audio.pause();
        this.snoozeTime = 0;
        this.mode = 'inactive';
        this.div.hide();

        var highestPriorityAlarm = null;
        alarms.forEach(function(alarm) {
            if (alarm.mode == 'active') {
                highestPriorityAlarm = alarm;
            }
        }, this);

        if (highestPriorityAlarm !== null) {
            highestPriorityAlarm.audio.play();
        }
    };

    var motionAlarm = new Alarm('motionAlarm', 0, 'motion_alarm.mp3');
    var oximeterConnectionAlarm = new Alarm('oximeterConnectionAlarm', 1, 'connection_alarm.mp3');
    var internetConnectionAlarm = new Alarm('internetConnectionAlarm', 2, 'connection_alarm.mp3');
    var oximeterAlarm = new Alarm('oximeterAlarm', 3, 'oximeter_alarm.mp3');

    $(document).keypress(function() {
        alarms.forEach(function(alarm) {
            alarm.snooze();
        });
    });

    var lastReadTime = null;
    function refresh() {
        $.ajax({
            url: "/status",
            dataType: "json"
        }).done(function(data) {
            internetConnectionAlarm.dismiss();

            $("#timestamp").html(data.readTime);
            $("#SPO2").html(data.SPO2);
            $("#BPM").html(data.BPM);

            var readTime = Date.parse(data.readTime);

            if (data.SPO2 == -1) {
                oximeterConnectionAlarm.trigger(data.oximeterStatus);
                oximeterConnectionAlarm.suppressed = true;
            } else {
                // got one good reading. Hence we need to alarm about
                // disconnection again. This way, we only play the oximeter
                // disconnected alarm once per disconnection and not once
                // every so many seconds.
                oximeterConnectionAlarm.suppressed = false;
                oximeterConnectionAlarm.dismiss();
            }

            if (data.alarm == 1) {
                oximeterAlarm.trigger("Oximeter Alarm!");
            } else {
                oximeterAlarm.dismiss();
            }

            if (data.motion == 1) {
                motionAlarm.trigger("Baby's moving! <small>" + data.motionReason + "</small>");
            }

        }).error(function() {
            internetConnectionAlarm.trigger("Connection to Raspberry failed!");
        });
    }

    setInterval(function() {
        refresh();
    }, 1000);
});

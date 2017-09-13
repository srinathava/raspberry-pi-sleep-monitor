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

    var motionAlarm = {
        priority: 0,
        audio: motionAlarmAudio,
        lastAlarmTime: 0
    }; 
    var oximeterConnectionAlarm = {
        priority: 1,
        audio: connectionAlarmAudio,
        lastAlarmTime: 0
    };
    var internetConnectionAlarm = {
        priority: 2,
        audio: connectionAlarmAudio,
        lastAlarmTime: 0
    };
    var oximeterAlarm = {
        priority: 3,
        audio: oximeterAlarmAudio,
        lastAlarmTime: 0
    };

    function stopAllAudio() {
        motionAlarmAudio.pause();
        oximeterAlarmAudio.pause();
        connectionAlarmAudio.pause();
    }

    $('#alarmBanner').center().hide();

    $(document).keypress(function() {
        stopAllAudio();
        $('#alarmBanner').hide();
    });

    function playAlarmNow(alarm, txt) {
        // If we are currently showing a high priority alarm, do not hide
        // it with a low priority one. Also prevents us from playing
        // multiple tones.
        if (currentAlarm !== null) {
            if (currentAlarm.priority > alarm.priority) {
                return;
            } else {
                dismissAlarm(currentAlarm);
            }
        }

        $('#alarmBanner').html(txt).center().show();

        alarm.lastAlarmTime = Date.now();
        alarm.audio.currentTime = 0;
        alarm.audio.play();

        currentAlarm = alarm;
    }

    function playAlarm(alarm, txt) {
        if (Date.now() - alarm.lastAlarmTime > 60*1000) {
            playAlarmNow(alarm, txt);
        }
    }

    function dismissAlarm(alarm) {
        if (currentAlarm === alarm) {
            alarm.audio.pause();
            alarm.lastAlarmTime = 0;
            $('#alarmBanner').hide();
            currentAlarm = null;
        }
    }

    // The oximeter alarm is special. See comment below about why we do not
    // use (Date.now() - lastAlarmTime)
	var needToAlarmAboutOximeterDisconnected = true;
	function playOximeterDisconnectedAlarm(oximeterStatus) {
		if (needToAlarmAboutOximeterDisconnected) {
			playAlarmNow(oximeterConnectionAlarm, oximeterStatus);
			needToAlarmAboutOximeterDisconnected = false;
		}
	}

    var lastReadTime = null;
    function refresh() {
        $.ajax({
            url: "/status",
            dataType: "json"
        }).done(function(data) {
            dismissAlarm(internetConnectionAlarm);

            $("#timestamp").html(data.readTime);
            $("#SPO2").html(data.SPO2);
            $("#BPM").html(data.BPM);

            var readTime = Date.parse(data.readTime);

            if (data.SPO2 == -1) {
                playOximeterDisconnectedAlarm(data.oximeterStatus);
            } else {
                // got one good reading. Hence we need to alarm about
                // disconnection again. This way, we only play the oximeter
                // disconnected alarm once per disconnection and not once
                // every so many seconds.
                needToAlarmAboutOximeterDisconnected = true;
                dismissAlarm(oximeterConnectionAlarm);
            }

            if (data.alarm == 1) {
                playAlarm(oximeterAlarm, "Oximeter Alarm!");
            } else {
                dismissAlarm(oximeterAlarm);
            }

            if (data.motion == 1) {
                playAlarm(motionAlarm, "Baby's moving!<br/>" + data.motionReason);
            }

        }).error(function() {
            playAlarm(internetConnectionAlarm, "Connection to Raspberry failed!");
        });
    }

    setInterval(function() {
        refresh();
    }, 1000);
});

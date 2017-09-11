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

    function stopAllAudio() {
        motionAlarmAudio.pause(); motionAlarmAudio.currentTime = 0;
        oximeterAlarmAudio.pause(); oximeterAlarmAudio.currentTime = 0;
        connectionAlarmAudio.pause(); connectionAlarmAudio.currentTime = 0;
    }

    $('#alarmBanner').center().hide();

    $(document).keypress(function() {
        stopAllAudio();
        $('#alarmBanner').hide();
    });

    function playAlarm(audio, txt) {
        $('#alarmBanner').html(txt).center().show();
        audio.play();
    }

    var needToAlarmAboutOximeterDisconnected = true;
    function playOximeterDisconnectedAlarm() {
        if (needToAlarmAboutOximeterDisconnected) {
            playAlarm(connectionAlarmAudio, "Oximeter disconnected!");
            needToAlarmAboutOximeterDisconnected = false;
        }
    }

    var lastConnectionAlarmTime = 0;
    function playConnectionAlarm() {
        if (Date.now() - lastConnectionAlarmTime > 60*1000) {
            playAlarm(connectionAlarmAudio, "Connection failed!");
            lastConnectionAlarmTime = Date.now();
        }
    }

    var lastMotionAlarmTime = 0;
    function playMotionAlarm() {
        if (Date.now() - lastMotionAlarmTime > 60*1000) {
            playAlarm(motionAlarmAudio, "Baby's moving!");
            lastMotionAlarmTime = Date.now();
        }
    }

    var lastOximeterAlarmTime = 0;
    function playOximeterAlarm() {
        if (Date.now() - lastOximeterAlarmTime > 60*1000) {
            playAlarm(oximeterAlarmAudio, "Oximeter Alarm!");
            lastOximeterAlarmTime = Date.now();
        }
    }

    var lastReadTime = null;
    function refresh() {
        $.ajax({
            url: "/status",
            dataType: "json"
        }).done(function(data) {
            $("#timestamp").html(data.readTime);
            $("#SPO2").html(data.SPO2);
            $("#BPM").html(data.BPM);

            var readTime = Date.parse(data.readTime);

            if (data.SPO2 == -1) {
                playOximeterDisconnectedAlarm();
            } else {
                // got one good reading. Hence we need to alarm about
                // disconnection again. This way, we only play the oximeter
                // disconnected alarm once per disconnection and not once
                // every so many seconds.
                needToAlarmAboutOximeterDisconnected = true;
            }

            if (data.alarm == 1) {
                playOximeterAlarm();
            }

            if (data.motion == 1) {
                playMotionAlarm();
            }

        }).error(function() {
            playConnectionAlarm();
        });
    }

    setInterval(function() {
        refresh();
    }, 1000);

    // last ditch attempt to deal with excessive delay in the pipeline,
    // just refresh the stream every 15 seconds to deal with network
    // buffering.
    // var idx = 1;
    // setInterval(function() {
    //     $('#latest').attr('src', '/stream.mjpeg?idx=' + idx);
    //     idx += 1;
    // }, 30000);
});

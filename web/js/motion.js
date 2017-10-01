$(document).ready(function() {

    var motionAlarmAudio = new Audio('motion_alarm.mp3'); motionAlarmAudio.loop = true;
    var connectionAlarmAudio = new Audio('connection_alarm.mp3'); connectionAlarmAudio.loop = true;

    var currentAlarm = null;

    var alarmsContainer = $('#alarmsContainer');
    alarmsContainer.center();

    var motionAlarm = new Alarm('motionAlarm', 0, 'motion_alarm.mp3');
    var internetConnectionAlarm = new Alarm('internetConnectionAlarm', 2, 'connection_alarm.mp3');

    var alarms = [motionAlarm, internetConnectionAlarm];

    $(document).keypress(function() {
        alarms.forEach(function(alarm) {
            alarm.snooze();
        });
    });

    var lastReadTime = null;
    var refreshImage = false;
    function refresh() {
        $.ajax({
            url: "/status",
            dataType: "json"
        }).done(function(data) {
            Alarm.dismiss(internetConnectionAlarm, alarms);
            if (refreshImage) {
                $('#latest').attr('src', '/stream.mjpeg?ts=' + Date.now().toString()).height('100%');
                refreshImage = false;
            }

            var readTime = Date.parse(data.readTime);
            if (data.motion == 1) {
                motionAlarm.trigger("Baby's moving! <small>" + data.motionReason + "</small>");
            }

        }).error(function() {
            internetConnectionAlarm.trigger("Connection to Raspberry failed!");
            refreshImage = true;
        });
    }

    setInterval(function() {
        refresh();
    }, 1000);
});

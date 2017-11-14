class SleepMonitorApp {
    constructor() {
        this.motionEnabled = false;
        this.oximeterEnabled = false;

        this.internetConnectionAlarm = null;
        this.motionAlarm = null;
        this.oximeterConnectionAlarm = null;
        this.oximeterAlarm = null;

        this.refreshImage = false;
    }

    refreshOximeterStats(data) {
        $("#timestamp").html(data.readTime);
        $("#SPO2").html(data.SPO2);
        $("#BPM").html(data.BPM);

        if (data.SPO2 == -1) {
            this.oximeterConnectionAlarm.trigger(data.oximeterStatus);
            this.oximeterConnectionAlarm.suppressed = true;
        } else {
            // got one good reading. Hence we need to alarm about
            // disconnection again. This way, we only play the oximeter
            // disconnected alarm once per disconnection and not once
            // every so many seconds.
            this.oximeterConnectionAlarm.suppressed = false;
            this.oximeterConnectionAlarm.dismiss();
        }

        if (data.alarm == 1) {
            this.oximeterAlarm.trigger("Oximeter Alarm!");
        } else {
            this.oximeterAlarm.dismiss();
        }
    }

    refresh() {
        $.ajax({
            url: "/status",
            dataType: "json"
        }).done((data) => {
            this.internetConnectionAlarm.dismiss();
            if (this.refreshImage) {
                $('#latest').attr('src', '/stream.mjpeg?ts=' + Date.now().toString()).height('100%');
                this.refreshImage = false;
            }
            
            if (this.oximeterEnabled) {
                this.refreshOximeterStats(data);
            }

            if (this.motionEnabled && data.motion == 1) {
                this.motionAlarm.trigger("Baby's moving! <small>" + data.motionReason + "</small>");
            }

        }).error(() => {
            this.internetConnectionAlarm.trigger("Connection to Raspberry failed!");
            this.refreshImage = true;
        });
    }

    init() {

        this.internetConnectionAlarm = new Alarm('internetConnectionAlarm', 2, 'connection_alarm.mp3');
        if (this.motionEnabled) {
            this.motionAlarm = new Alarm('motionAlarm', 0, 'motion_alarm.mp3');
        }
        if (this.oximeterEnabled) {
            this.oximeterConnectionAlarm = new Alarm('oximeterConnectionAlarm', 1, 'connection_alarm.mp3');
            this.oximeterAlarm = new Alarm('oximeterAlarm', 3, 'oximeter_alarm.mp3');
        }

        Alarm.init();

        setInterval(() => {
            this.refresh();
        }, 1000);

        $('#dashboard').click(function() {
            var dashboardUrl = `http://${window.location.hostname}:3000/dashboard/db/sleep-monitor?refresh=5s&orgId=1&from=now-30m&to=now`;
            var win = window.open(dashboardUrl, '_blank');
            win.focus();
        })
    }
}

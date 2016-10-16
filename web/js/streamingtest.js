var server = "http://" + window.location.hostname + ":8088/janus";

var janus = null;
var streaming = null;
var selectedStream = null;

function isdefined(val) {
    return val !== undefined && val !== null;
}

function onReady() {

    function success(pluginHandle) {
        streaming = pluginHandle;
        updateStreamsList();
    }

    function updateStreamsList() {
        var body = { "request": "list" };
        streaming.send({
            message: body, 
            success: function(result) {
                if (!isdefined(result)) {
                    bootbox.alert("Got no response to our query for available streams");
                    return;
                }

                if (isdefined(result.list)) {
                    selectedStream = result.list[0].id;
                    startStream();
                }
            }});
    }

    function startStream() {
        Janus.log("Selected video id #" + selectedStream);
        if (!isdefined(selectedStream)) {
            bootbox.alert("Select a stream from the list");
            return;
        }

        var body = { "request": "watch", id: parseInt(selectedStream, 10) };
        streaming.send({"message": body});
    }

    function onremotestream(stream) {
        Janus.debug(" ::: Got a remote stream :::");
        Janus.debug(JSON.stringify(stream));

        if($('#remotevideo').length === 0) {
            $('#stream').append('<video class="rounded centered hide" id="remotevideo" width=320 height=240 autoplay/>');
        }

        Janus.attachMediaStream($('#remotevideo').get(0), stream);
    }

    /// XXX: Is responding to every message necessary?
    function onmessage(msg, jsep) {
        Janus.debug(" ::: Got a message :::");
        Janus.debug(JSON.stringify(msg));
        var result = msg.result;
        if (isdefined(result)) {
            if (isdefined(result.status)) { 
                if (result.status === 'stopped') {
                    stopStream();
                }
            }
        } else if (isdefined(msg.error)) {
            bootbox.alert(msg.error);
            stopStream();
            return;
        }
        if (isdefined(jsep)) {
            Janus.debug("Handling SDP as well...");
            Janus.debug(jsep);
            // Answer
            streaming.createAnswer(
                {
                    jsep: jsep,
                    media: { audioSend: false, videoSend: false },	// We want recvonly audio/video
                    success: function(jsep) {
                        Janus.debug("Got SDP!");
                        Janus.debug(jsep);
                        var body = { "request": "start" };
                        streaming.send({"message": body, "jsep": jsep});
                    },
                    error: function(error) {
                        Janus.error("WebRTC error:", error);
                        bootbox.alert("WebRTC error... " + JSON.stringify(error));
                    }
                });
        }
    }

    // Create session
    janus = new Janus(
        {
            server: server,
            success: function() {
                janus.attach({
                    plugin: "janus.plugin.streaming",
                    success: success,
                    onmessage: onmessage,
                    onremotestream: onremotestream
                });
            }
        });
}

$(document).ready(function() {
	// Initialize the library (all console debuggers enabled)
    Janus.init({debug: "all", callback: onReady});

    var idx = 0;
    setInterval(function() {
        $('#latest').attr('src', '/~pi/latest.jpeg?idx=' + idx);
        idx += 1;
    }, 125);
});


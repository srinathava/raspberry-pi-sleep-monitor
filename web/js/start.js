$(function searchForIp() {
    function tryIp(ipIdx) {
        var uri = "http://192.168.1." + ipIdx;
        $('#searchStatus').innerHTML = 'Pinging ' + uri;

        $.ajax({
            url: uri + "/ping",
            dataType: "json",
            timeout: 100
        }).success(function(data) {
            console.log('Found it!');
            window.location = uri;
        }).error(function() {
            if (ipIdx == 255) {
                console.log('Didn\'t find any sleep monitors');
            } else {
                setTimeout(function() { tryIp(ipIdx + 1); }, 0);
            }
        });
    }

    tryIp(2);
});


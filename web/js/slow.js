$(document).ready(function() {
	var img = document.querySelector( "#latest_jpeg" );

    function refreshImage() {
		var xhr = new XMLHttpRequest();
		xhr.open('GET', '/latest.jpeg?ts='+Date.now(), true);
		xhr.responseType = 'arraybuffer';
        xhr.timeout = 5000; // 5 seconds

		xhr.onreadystatechange = function(e) {
            if (xhr.readyState == XMLHttpRequest.DONE) {
                if(xhr.status == 200) {
                    var arrayBufferView = new Uint8Array(this.response);
                    var blob = new Blob([arrayBufferView], {type: "image/jpeg"});

                    var imageUrl = URL.createObjectURL( blob );
                    img.src = imageUrl;
                } else {
                    setTimeout(refreshImage, 2000);
                }
            }
		};

        xhr.send();
    }

    img.onload = refreshImage;
	refreshImage();
});

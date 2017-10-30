$(document).ready(function() {
	var img = document.querySelector( "#latest_jpeg" );
    img.onload = refreshImage;

    function refreshImage() {
		var xhr = new XMLHttpRequest();
		xhr.open('GET', '/latest.jpeg?ts='+Date.now(), true);
		xhr.responseType = 'arraybuffer';

		xhr.onload = function( e ) {
			var arrayBufferView = new Uint8Array(this.response);
			var blob = new Blob([arrayBufferView], {type: "image/jpeg"});

			var imageUrl = URL.createObjectURL( blob );
			img.src = imageUrl;
		};

        xhr.send();
    }

	refreshImage();
});

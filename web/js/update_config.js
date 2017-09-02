$(function() {
    $('input').prop('disabled', true);

    $.ajax({
        url: "/getConfig",
        dataType: "json"
    }).success(function(data) {
        console.log(data);

        $('input[type="text"]').each(function() {
            var elemName = $(this).attr('name');
            var elemVal = data[elemName];
            $(this).attr('value', elemVal);
        });

        $('input').prop('disabled', false);
    }).error(function() {
    });


    $('#submit').click(function() {
        $(this).prop('disabled', true);
        console.log('trying to submit info');

        var config = {};

        $('input[type="text"]').each(function() {
            var elemName = $(this).attr('name');
            var elemVal = $(this).attr('value');
            config[elemName] = elemVal;
        });

        $.ajax({
            url: "/updateConfig",
            data: config,
            dataType: "json"
        }).success(function(data) {
            console.log('success');
        });
    });
});

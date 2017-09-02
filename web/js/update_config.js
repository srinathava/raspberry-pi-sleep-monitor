$(function() {
    $('input').attr('disabled','disabled');

    $.ajax({
        url: "/getConfig",
        dataType: "json",
    }).success(function(data) {
        console.log(data);
    }).error(function() {
    });
});

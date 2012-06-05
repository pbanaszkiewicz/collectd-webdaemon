var address = "";

$("#btn_connect").click(function() {
    console.log("connecting");
    var server = $("#server").val();
    var port = $("#port").val();

    // get list of hosts
    if (port) {
        address = server + ":" + port;
    } else {
        address = server
    }

    $.getJSON(address + "/list_hosts", function(data) {
        console.log("got some data: " + data);
        $("#menu_select_host").removeClass("hidden");

        // add to the #select_host <select>
        $("#select_host").empty();
        $.each(data, function(k, val) {
            console.log("val: " + val);

            $("<option/>", {html: val}).appendTo("#select_host");
        });
    });
});

$("#btn_host").click(function() {
    // show list of statistics
    $.getJSON(address + "/host/" + $("#select_host").val() + "/list_metrics", function(data) {
        console.log("got some data: " + data);
        $("#menu_rrds").removeClass("hidden");

        $("#select_rrd").empty();
        $.each(data, function(k, v) {
            console.log("dir: " + v);
            $("<option/>", {html: v}).appendTo("#select_rrd");
        });
    });
});

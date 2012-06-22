var address = "";

$("#btn_connect").click(function() {
    console.log("connecting");
    var server = $("#server").val();
    var port = $("#port").val();

    if (port) {
        address = server + ":" + port;
    } else {
        address = server
    }

    // get thresholds configuration
    $.get(address + "/threshold/", function(data) {
        console.log("got some data: " + data);
        root = data.documentElement;
        console.log("root: " + root.nodeName);
        for (i=0; i < root.childNodes.length; i++) {
            console.log("  child: " + root.childNodes[i].nodeType + " " + root.childNodes[i].nodeName);
        }
    }, "xml");
    //$.getJSON(address + "/thresholds/", function(data) {
    //    console.log("got some data: " + data);
    //    $("#menu_select_host").removeClass("hidden");

    //    // add to the #select_host <select>
    //    $("#select_host").empty();
    //    $.each(data, function(k, val) {
    //        console.log("val: " + val);

    //        $("<option/>", {html: val}).appendTo("#select_host");
    //    });
    //});
});

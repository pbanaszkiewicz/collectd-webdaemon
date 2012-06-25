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
        var root = data.documentElement;
        console.log("root: " + root.nodeName);

        read_thresholds(root.childNodes, "#thresholds_read");
    }, "xml");
});

function read_thresholds(children, div_node) {
    // div_node: where to attach
    $.each(children, function(key, value) {

        if (value.nodeType == 1) {

            if (value.nodeName == "Type" || value.nodeName == "Plugin" || value.nodeName == "Host") {
                // create div
                var str = "<div class='configuration'><h3>" + value.nodeName;

                if ($(value).attr("name")) {
                    // append node `name` attribute
                    str = str + " <small>" + $(value).attr("name") + "</small>";
                }
                str = str + "</h3>";

                // + create table
                str = str + "<table></table></div>";

                $(div_node).append(str);

            } else {
                console.log("Adding to the table: " + value.nodeName);
                // add to the supposedly existing table
                var str = "<tr><td style='font-weight: bold'>" + value.nodeName + "</td><td>" + $(value).text() + "</td></tr>";
                $(div_node).find("table").append(str);
            }

            // run for children, if name is either Plugin or Host or Type
            if (value.nodeName == "Type" || value.nodeName == "Plugin" || value.nodeName == "Host") {
                console.log("Running for children: " + $(div_node).find("div").last().text());
                read_thresholds(value.childNodes, $(div_node).find("div").last());
            }
        }
    });
}

function load_hostnames(node) {
    $.getJSON(address + "/list_hosts", function(data) {
        console.log("got some data: " + data);

        $(node).empty();
        $.each(data, function(key, value) {
            $("<option/>", {html: value}).appendTo(node);
        });
    });
}

function load_plugins(node) {
    $.getJSON(address + "/list_plugins", function(data) {
        console.log("got some data: " + data);

        $(node).empty();
        $.each(data, function(key, value) {
            $("<option/>", {html: value}).appendTo(node);
        });
    });
}

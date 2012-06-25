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
        $("#menu_metrics").removeClass("hidden");

        $("#select_metrics").empty();
        $.each(data, function(k, v) {
            console.log("dir: " + v);
            $("<option/>", {html: v}).appendTo("#select_metrics");
        });
    });
});

$("#select_metrics").change(function(){
    $.getJSON(address + "/host/" + $("#select_host").val() + "/list_rrds/" + $("#select_metrics").val(), function(data) {
        console.log("got some data: " + data);
        $("#rrds").removeClass("hidden");
        $("#get_metrics").removeClass("hidden");

        $("#rrds").empty();
        $.each(data, function(k, v) {
            console.log("rrd: " + v);
            $("<input/>", {type: "checkbox", value: v, id: "id_" + v, checked: "checked"}).appendTo("#rrds");
            $("<label/>", {html: v, for: "id_" + v, style: "display: inline"}).appendTo("#rrds");
            $("<a/>", {html: "+ Threshold", id: "btn_" + v, data-name: v}).appendTo("#rrds");
            $("<br/>").appendTo("#rrds");
            $("a#btn_" + v).bind("click", get_thresholds);
        });
    });
});

function get_thresholds(e) {
    console.log("Event triggered! " + e);
}

$("#get_metrics").click(function(){
    options = {
        //series: {
        //    lines: { show: true },
        //    points: { show: false },
        //},
        xaxis: { mode: "time" },
        yaxis: {
            tickDecimals: 2,
            tickFormatter: function(val, axis) {
                if (val > 1000000000)
                    return (val / 1000000000).toFixed(axis.tickDecimals) + " G";
                if (val > 1000000)
                    return (val / 1000000).toFixed(axis.tickDecimals) + " M";
                if (val > 1000)
                    return (val / 1000).toFixed(axis.tickDecimals) + " k";
                return val.toFixed(axis.tickDecimals)
            },
        },
        legend: {
            container: "#chart_legend",
        },
    };
    var data = [];
    $.plot($("#chart"), data, options)
    var rrds = [];

    $("#rrds input:checked").each(function() {
        rrds.push($(this).val());
    });

    $.getJSON(address + "/get/" + $("#select_host").val() + "/" + $("#select_metrics").val() + "/" + rrds.join("|"), function(D) {
        console.log("got some data: " + D);
        $.each(D, function(i, e) {
            data.push(e);
        });
        $.plot($("#chart"), data, options);
    });

});

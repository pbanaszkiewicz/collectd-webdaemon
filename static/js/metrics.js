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
            $("<a/>", {html: "+ Threshold", href: "#", dataname: v, class: "btn_threshold"}).appendTo("#rrds");
            $("<br/>").appendTo("#rrds");
        });
        $(".btn_threshold").bind("click", get_thresholds);
    });
});

function get_thresholds(e) {
    console.log("Event triggered! " + e);
    var host = $("#select_host").val();
    var plugin_path = $("#select_metrics").val().split("-");
    var type_path = $(e.target).attr("dataname").split("-");
    var plugin = plugin_path[0];
    var plugin_instance = plugin_path[1];
    var type = type_path[0];
    var type_instance = type_path[1];

    if (!plugin_instance) plugin_instance = "-";
    if (!type_instance) plugin_instance = "-";
    var data = new Array(); data.push(host); data.push(plugin); data.push(plugin_instance); data.push(type);
    data.push(type_instance);
    console.log("data: " + data.join("/"));

    $.getJSON(address + "/lookup_threshold/" + data.join("/"), function(json) {
        // work on the results
        if (!json.length) {
            console.log("empty list of thresholds");
            // show menu for adding threshold
            $("#threshold_setting #adding").removeClass("hidden");
            $("#threshold_setting #editing").addClass("hidden");
            $("#threshold_setting").removeClass("hidden");

            $("#hostname").val(host);
            $("#plugin").val(host);
            if (plugin_instance != "-") $("#plugin_instance").val(plugin_instance);
            $("#type").val(type);
            if (type_instance != "-") $("#type_instance").val(type_instance);

        } else {
            console.log("some thresholds");
            // show list of similar thresholds
            $("#threshold_selection").removeClass("hidden");
            $("#threshold_selection").empty();
            $.each(json, function(key, value) {
                $("<a/>", {html: "Threshold #" + value["id"], href: "#", class: "edit_threshold", dataname: value["id"]}).appendTo("#thresholds_selection");
            });

            // enable editing them
            $("a.edit_threshold").click(function(e) {
                // get data from json
                $.getJSON(address + "/threshold/" + $(e.target).attr("dataname"),
                    function(result) {
                        $("#threshold_setting #adding").addClass("hidden");
                        $("#threshold_setting #editing").removeClass("hidden");
                        $("#threshold_setting").removeClass("hidden");

                        $("#hostname").val(result["host"]);
                        $("#plugin").val(result["plugin"]);
                        $("#plugin_instance").val(result["plugin_instance"]);
                        $("#type").val(result["type"]);
                        $("#type_instance").val(result["type_instance"]);
                        $("#failure_min").val(result["failure_min"]);
                        $("#failure_max").val(result["failure_max"]);
                        $("#warning_min").val(result["warning_min"]);
                        $("#warning_max").val(result["warning_max"]);
                        $("#percentage").attr("checked", result["percentage"]==true);
                        $("#inverted").attr("checked", result["inverted"]==true);
                        $("#persist").attr("checked", result["persist"]==true);
                        $("#hits").val(result["hits"]);
                        $("#hysteresis").val(result["hysteresis"]);
                    });
            });
            // enable adding new threshold
            $("#threshold_addition").removeClass("hidden");
        }
    });
}

$("#threshold_addition").click(function() {
    $("#threshold_setting #editing").addClass("hidden");
    $("#threshold_setting #adding").removeClass("hidden");
    $("#threshold_setting").removeClass("hidden");
});

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

$( function() {
  var base_url = window.location.origin;
  $("#port-slider").slider({
    orientation: "vertical",
    range: "min",
    min: -100,
    max: 100,
    value: 0,
    create: function() {
      $("#port-handle").text($(this).slider("value"));
    },
    slide: function(event, ui) {
      $("#port-handle").text(ui.value);
      $("#port-info").text(ui.value);
      if ($('#bind-handles').is(":checked")) {
        $("#starboard-slider").find('a').text(ui.value).end().slider("option","value",ui.value);
        $("#starboard-info").text(ui.value);
        $("#starboard-handle").text(ui.value);
      }
    },
    stop: function( event, ui ) {
      $.ajax({
        url: base_url + "/speed?port=" + ui.value + "&starboard=" + $("#starboard-info").text(),
        type: "GET",
        ContentType: 'json',
        headers: {Accept : "application/json;charset=utf-8"},
        success: function (result) {
          if ($('#bind-handles').is(":checked")) {
            $("#starboard-slider").find('a').text(ui.value).end().slider("option","value",ui.value);
            $("#starboard-handle").text(ui.value);
          }
          console.log('ajax1a: ' + result.port_speed);
          $("#port-speed").text(result.port_speed);
          $("#starboard-speed").text(result.starboard_speed);
          console.log('ajax1b: ' + result.starboard_speed);
        }, 
        error: function (error) {
          console.log(error);
        } 
      })
    }
  });

  $("#starboard-slider").slider({
    orientation: "vertical",
    range: "min",
    min: -100,
    max: 100,
    value: 0,
    create: function() {
      $("#starboard-handle").text($(this).slider("value"));
    },
    slide: function(event, ui) {
      $("#starboard-handle").text(ui.value);
      $("#starboard-info").text(ui.value);
      if ($('#bind-handles').is(":checked")) {
        $("#port-slider").find('a').text(ui.value).end().slider("option","value",ui.value);
        $("#port-info").text(ui.value);
        $("#port-handle").text(ui.value);
      }
    },
    stop: function( event, ui ) {
      $.ajax({
        url: base_url + "/speed?starboard=" + ui.value + "&port=" + $("#port-info").text(),
        type: "GET",
        ContentType: 'json',
        headers: {Accept : "application/json;charset=utf-8"},
        success: function (result) {
          if ($('#bind-handles').is(":checked")) {
            $("#port-slider").find('a').text(ui.value).end().slider("option","value",ui.value);
            $("#port-handle").text(ui.value);
          }
          console.log('ajax2a: ' + result);
          $("#port-speed").text(result.port_speed);
          $("#starboard-speed").text(result.starboard_speed);
          console.log('ajax2b: ' + result);
        }, 
        error: function (error) {
          console.log(error);
        } 
      })
    }
  });

  $("#port-info").text($("#port-slider").slider("value"));
  $("#starboard-info").text($("#starboard-slider").slider("value"));
  $('#bind-handles').click(function() {
    console.log("checked: " + this.checked);
    if ( this.checked ) {
      $("#starboard-handle").addClass("starboard-handle-bound");
      $("#port-handle").addClass("port-handle-bound");
    } else {
      $("#starboard-handle").removeClass("starboard-handle-bound");
      $("#port-handle").removeClass("port-handle-bound");
    }
  });

  $("button").click(function(event) {
    event.preventDefault();
    var $caller = $(event.target);
    var eventId = $caller.prop("id");
    console.log("id: " + eventId );
    if ( eventId == 'brake' || eventId == 'halt' || eventId == 'stop' ) {
        $("#port-slider").slider("value", 0);
        $("#port-handle").text(0);
        $("#port-info").text(0);
        $("#starboard-slider").slider("value", 0);
        $("#starboard-handle").text(0);
        $("#starboard-info").text(0);
        console.log("brake-id: " + eventId );
    }
    $.ajax({
      url: base_url + "/event?id=" + eventId,
      type: "GET",
      ContentType: 'json',
      headers: {Accept : "application/json;charset=utf-8"},
//    success: function(response, status, xhr) {
      success: function(data) {
//      var content_type = xhr.getResponseHeader("content-type") || "";
//      console.log('content-type: ' + content_type);
//      var json = JSON.parse(data);
        // then read data.content
        console.log('content[0]: ' + data[0]);
        console.log('content[1]: ' + data[1]);
        $("#port-speed").text(data.port_speed);
        $("#starboard-speed").text(data.starboard_speed);
      }, 
      error: function (error) {
        console.log(error);
      } 
    })
  });
});

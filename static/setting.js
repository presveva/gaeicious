if ($.cookie('mys') == 'True') {
  $("#mys-text").html('<i class="icon-thumbs-up"></i> <b>Enabled </b>');
  $("#mys-check").prop("checked", true);
} else {
  $("#mys-text").html('<i class="icon-thumbs-down"></i> <b>Disabled</b>');
  $("#mys-check").prop("checked", false);
}

if ($.cookie('daily') == 'True') {
  $("#daily-text").html('<i class="icon-thumbs-up"></i> <b>Enabled </b>');
  $("#daily-check").prop("checked", true);
} else {
  $("#daily-text").html('<i class="icon-thumbs-down"></i> <b>Disabled</b>');
  $("#daily-check").prop("checked", false);
}

if ($.cookie('twitt') == 'True') {
  $("#twitt-text").html('<i class="icon-thumbs-up"></i> <b>Enabled </b>');
  $("#twitt-check").prop("checked", true);
} else {
  $("#twitt-text").html('<i class="icon-thumbs-down"></i> <b>Disabled</b>');
  $("#twitt-check").prop("checked", false);
}

$("#mys-check").change(function() {
  $.ajax({
    url: "/setmys",
    success: function(html) {
      $("#mys-text").html(html);
    } });});

$("#daily-check").change(function() {
  $.ajax({
    url: "/setdaily",
    success: function(html) {
    $("#daily-text").html(html);
    } });});

$("#twitt-check").change(function() {
  $.ajax({
    url: "/settwitt",
    success: function(html) {
    $("#twitt-text").html(html);
    } });});

$('#bookmarklet').tooltip();

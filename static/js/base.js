$(document).ready(function() {

  var tab = $.cookie('active-tab')
  

  $('#'+tab).addClass('active');
  if (tab == 'trash') {
    $("#dashboard").html('<a>Trashed items</a>');
    $('#empty_button').removeClass('hide');
  }
  if (tab == 'tagcloud') {
    $("#dashboard").html('<a>Filter by tag</a>');
  }
  if (tab == 'untagged') {
    $("#dashboard").html('<a>Tagging is important!</a>');
  }
  if (tab == 'inbox') {
    $("#dashboard").html('<a>Welcome to your Inbox</a>');
  }
  if (tab == 'starred') {
    $("#dashboard").html('<a>These are important</a>');
  }
  if (tab == 'archive') {
    $("#dashboard").html('<a>Your archive</a>');
  }
  if (tab == 'feeds') {
    $("#dashboard").html('<a>Manage your feeds</a>');
  }
  if (tab == 'setting') {
    $("#dashboard").html('<a>Your setting</a>');
  }

  $('#addtag').submit(function() {
    var querystring = $(this).serialize();
    event.preventDefault();
    $.ajax({
      url: '/addtag',
      data: querystring,
      success: function() {
        $("#dashboard").html('<a>New tag created</a>');
        }
      })
    })

$('#bookmarklet').tooltip()
});
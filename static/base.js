function active() {
  return $.cookie('active-tab');
}

function getbms(page, c, domain) {
  $.get("/bms/" + page, {
    cursor: c,
    domain: domain
  }, function(data) {
    $(".main_frame").html(data.html);
    $("#more").html(data.more);
    $(window).scrollTop(0);
  });
}

function search() {
  event.preventDefault();
  $.post('/search', $('#search').serialize(), function(html) {
    $(".main_frame").html(html);
    $(window).scrollTop(0);
    $("#more").html('');
  });
}

function hide_all() {
  $('.comments').hide();
  $('#collapse_btn').hide();
  $('#expande_btn').show();
}

function show_all() {
  $('.comments').show();
  $('#expande_btn').hide();
  $('#collapse_btn').show();
}

function archive(id) {
  $.get('/archive', {
    bm: id
  }, function() {
    $(".row-" + id).hide();
  });
}

function trash(id) {
  $.get('/trash', {
    bm: id
  }, function() {
    $(".row-" + id).hide();
  });
}

function star(id) {
  $.get('/star', {
    bm: id
  }, function(data) {
    $(".star-" + id).html(data);
  });
}

function share(id) {
  $.get("/share", {
    id: id
  }, function(eye) {
    $(".share-" + id).html(eye);
    if (eye == ('<i class="icon-eye-close"></i>')) {
      $(".link-" + id).html('');
    } else {
      $(".link-" + id).html('<a class="btn btn-small btn-link " href="/bm/' + id + '" target="_blank">link</a>');
    }
  });
}

function comment(id) {
  $(".edit-" + id).hide();
  $(".comment-" + id).toggle();
}

function edit(id) {
  $(".comment-" + id).hide();
  $(".edit-" + id).toggle();
}

function tweet(id) {
  $(".tweet-" + id).toggle();
}

function setnotify(id, notify) {
  $.get('/setnotify', {
    feed: id,
    notify: notify
  });
}

function sync_feed(id) {
  $.get('/checkfeed', {
    feed: id
  });
}

function copy_bm(id) {
  $.get('/copy', {
    bm: id
  });
}

function caratteri(val) {
  var len = val.value.length;
  if (len >= 140) {
    $('#input_tweet').addClass('error');
  } else {
    $('#input_tweet').addClass('success');
  }
}
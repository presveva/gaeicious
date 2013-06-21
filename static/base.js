function active() {
  return $.cookie('active-tab');
}

function getbms(page, c, domain) {
  $.get("/bms/" + page, {
    cursor: c,
    domain: domain
  }, function (data) {
    $(".main_frame").html(data.html);
    $("#more").html(data.more);
    $(window).scrollTop(0);
    $('pre code').each(function (i, e) {
      hljs.highlightBlock(e);
    });
    $('#expande_btn').hide();
    $('#collapse_btn').show();
  });
}

function search() {
  event.preventDefault();
  $.post('/search', $('#search').serialize(), function (html) {
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
  $.get('/archive/' + id, function () {
    $(".row-" + id).hide();
  });
}

function trash(id) {
  $.get('/trash/' + id, function () {
    $(".row-" + id).hide();
  });
}

function star(us) {
  $.get('/star/' + us, function (data) {
    $(".star-" + us).html(data);
  });
}

function share(us) {
  $.get("/share/" + us, function (data) {
    $(".share-" + us).html(data.eye);
    $(".link-" + us).html(data.btn);
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

function twitter_form() {
  if ($("#twitter_form").hasClass('hide')) {
    $("#twitter_form").removeClass('hide');
  } else {
    $("#twitter_form").addClass('hide');
  }
}

function retweet(id) {
  $.get("/twitter/retweet", {
    id_str: id
  });
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
  $.get('/copy/' + id);
}

function caratteri(val) {
  var len = val.value.length;
  if (len >= 140) {
    $('#input_tweet').addClass('error');
  } else {
    $('#input_tweet').addClass('success');
  }
}

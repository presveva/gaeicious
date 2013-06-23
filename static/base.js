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

function archive(us) {
  $.get('/archive/' + us, function () {
    $(".row-" + us).hide();
  });
}

function trash(us) {
  $.get('/trash/' + us, function () {
    $(".row-" + us).hide();
  });
}

function star(us) {
  $.get('/star/' + us, function () {
    $(".row-" + us).hide();
    // $(".star-" + us).html(data);
  });
}

function share(us) {
  $.get("/share/" + us, function (data) {
    $(".share-" + us).html(data.eye);
    $(".link-" + us).html(data.btn);
  });
}

function comment(us) {
  $(".row-" + us).hide();
  // $(".edit-" + us).hide();
  // $(".comment-" + us).toggle();
}

function edit(us) {
  $(".comment-" + us).hide();
  $(".edit-" + us).toggle();
}

function tweet(us) {
  $(".tweet-" + us).toggle();
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

function del_feed(id) {
  $.ajax({
    type: "delete",
    url: "/feeds?id=" + id
  }).done(function () {
    $("#row-" + id).hide();
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

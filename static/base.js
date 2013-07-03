$.cookie.raw = true;
// $.cookie.json = true;

function count(val) {
  var diff = $.cookie('count') - val;
  if (diff < 1) {
    getbms($.cookie('stato'));
  } else {
    $.cookie('count', diff);
  }
}

function getbms(stato, domain) {
  stat = (stato === undefined) ? $.cookie('stato') : stato;
  cur = (stat === $.cookie('stato')) ? $.cookie('cursor') : '';
  $.get("/bms/" + stat, {
    cursor: cur,
    domain: domain
  }, function(html) {
    $(".main_frame").html(html);
    update_gui();
  });
}

function update_gui() {
  $.cookie('count', 10);
  $(window).scrollTop(0);
  $('pre code').each(function(i, e) {
    hljs.highlightBlock(e);
  });
  $('.comments a').attr('target', '_blank');
  $('#expande_btn').hide();
  $('#collapse_btn').show();
  $('.nav li').removeClass('active');
  $('#' + $.cookie('stato') + '_pg').addClass('active');
  if ($.cookie('cursor') !== '') {
    $("#more").html("<a href='#' onclick='getbms()'><i class='icon-arrow-right'></i></a>");
  }
}

function edit(us) {
  $(".edit-" + us).toggle();
  $('.comment-' + us).toggle();
}

function edit_bm(us) {
  event.preventDefault();
  $.post('/bm/' + us, $('#edit_bm-' + us).serialize(), function(html) {
    $('.comment-' + us).html(html);
    edit(us);
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

function collapse_btn() {
  $(".comments").slideToggle();
  var addOrRemove = Boolean($("#collapse_arrow").hasClass('icon-arrow-up'));
  $('#collapse_arrow').toggleClass('icon-arrow-up', !addOrRemove);
  $('#collapse_arrow').toggleClass('icon-arrow-down', addOrRemove);
}

function archive(us) {
  $(".row-" + us).hide();
  $.get('/archive/' + us);
  count(1);
}

function trash(us) {
  $(".row-" + us).hide();
  $.get('/trash/' + us);
  count(1);
}

function star(us) {
  $(".row-" + us).hide();
  $.get('/star/' + us);
  count(1);
}

function share(us) {
  $.get("/share/" + us, function(data) {
    $(".share-" + us).html(data.eye);
    $(".link-" + us).html(data.btn);
  });
}

function comment(us) {
  $(".row-" + us).hide();
  count(1);
}

function tweet(us) {
  $(".tweet-" + us).slideToggle();
}

function twitter_form() {
  $("#twitter_form").slideToggle();
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
  }).done(function() {
    $("#row-" + id).hide();
  });
}

function copy_bm(id) {
  $.get('/copy/' + id);
}

function caratteri(val) {
  var addOrRemove = Boolean(val.value.length >= 140);
  $('#input_tweet').toggleClass('error', addOrRemove);
  $('#input_tweet').toggleClass('success', !addOrRemove);
}

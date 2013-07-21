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
  }, function (html) {
    $(".main_frame").html(html);
    update_gui();
  });
};

function update_gui() {
  $.cookie('count', 10);
  $(window).scrollTop(0);
  $('pre code').each(function (i, e) {
    hljs.highlightBlock(e);
  });
  $('.comments a').attr('target', '_blank');
  $('#expande_btn').hide();
  $('#collapse_btn').show();
  $('.nav li').removeClass('active');
  $('#' + $.cookie('stato') + '_pg').addClass('active');
  if ($.cookie('cursor') !== '') {
    $("#more").html("<a href='#' onclick='getbms()'><i class='icon-arrow-right'></i></a>");
  } else {
    $("#more").hide();
  }
  if ($.cookie('stato') === 'trash') {
    $("#empty_trash").slideToggle();
    $("#twitter_form").hide();
    twitter_form
  } else {
    $("#empty_trash").hide();
  }
};

function get_details(us) {
  $.get('/twitter/details', {
    us: us
  }, function (data) {
    $('#favico-' + us).attr({
      heigth: '48',
      width: '48',
      src: data.favico
    });
    $("#retweet_count-" + us).html(
      data.retweets + ' retweets | ' + data.favorites + ' favorites');
    // if (data.pics.length > 0) {
    // $("#pics-" + us).attr({
    //   src: data.pic
    // });
    // }
  });
}

function edit(us) {
  $(".edit-" + us).toggle();
  $('.comment-' + us).toggle();
}

function edit_bm(us) {
  event.preventDefault();
  $.post('/bm/' + us, $('#edit_bm-' + us).serialize(), function (html) {
    $('.comment-' + us).html(html);
    edit(us);
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

function collapse_btn() {
  $(".comments").slideToggle();
  var addOrRemove = Boolean($("#collapse_arrow").hasClass('icon-arrow-up'));
  $('#collapse_arrow').toggleClass('icon-arrow-up', !addOrRemove);
  $('#collapse_arrow').toggleClass('icon-arrow-down', addOrRemove);
}

function status(us, btn) {
  if (btn !== 'share') {
    $(".row-" + us).hide();
  } else {
    var addOrRemove = Boolean($(".share-" + us).hasClass('icon-eye-open'));
    if (!addOrRemove) {
      $(".share-" + us).toggleClass('icon-eye-open');
      $(".link-" + us).html('<a class="btn btn-small btn-link" href="/bm/' +
        us + '" target="_blank">link</a>');
    } else {
      $(".share-" + us).toggleClass('icon-eye-close');
      $(".link-" + us).html('');
    }
  }
  count(1);
  $.ajax({
    type: "put",
    url: '/bm/' + us,
    data: {
      btn: btn
    }
  });
}

function hide(us) {
  $(".row-" + us).hide();
  count(1);
}

function tweet(us) {
  $(".tweet-" + us).slideToggle();
}

function twitter_form() {
  $("#twitter_form").slideToggle();
  $("#empty_trash").hide();
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

function del_foll(id) {
  $.ajax({
    type: "delete",
    url: "/following?id=" + id
  }).done(function () {
    $("#row-" + id).hide();
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

function caratteri(val) {
  var addOrRemove = Boolean(val.value.length >= 140);
  $('#input_tweet').toggleClass('error', addOrRemove);
  $('#input_tweet').toggleClass('success', !addOrRemove);
}

function update_setting() {
  check_box('mys');
  check_box('daily');
  check_box('tweets');
}

function check_box(cokie) {
  up = '<i class="icon-thumbs-up"></i> <b>Enabled </b>';
  down = '<i class="icon-thumbs-down"></i> <b>Disabled</b>';
  if ($.cookie(cokie) === 'True') {
    $("#" + cokie + "-text").html(up);
    $("#" + cokie + "-check").prop("checked", true);
  } else {
    $("#" + cokie + "-text").html(down);
    $("#" + cokie + "-check").prop("checked", false);
  }
}

function save_mail(type) {
  $.ajax({
    type: type,
    url: "/save_email",
    success: function () {
      update_setting();
    }
  });
}
$('#bookmarklet').tooltip();

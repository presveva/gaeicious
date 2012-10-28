window.onhashchange = get_body;

function init(){
    var hash = location.hash;
    if (hash == '') {
        hash = '#inbox';
    }
    get_body();
}

function get_body(){
    var hash = location.hash;
    if (hash == '#setting' || '#feeds' || '#admin' ) {
        getpages(hash.split('#')[1]);
    } else if (hash === '#tagcloud') {
        support('/gettagcloud');
    } else {
        getbms(hash.split('#')[1]);
    }
    set_dashboard();
}

function active() {
    return $.cookie('active-tab');
}

function getbms(page, c, arg1, arg2) {
    $.ajax({
        url: "/",
        data: { page: page, cursor: c, arg1: arg1, arg2: arg2 },
        success: function (html) {
            $(window).scrollTop(0);
            $(".main_frame").html(html);
            set_dashboard(arg1);
        } }); }

function getpages(page) {
    $.ajax({
        url: "/other",
        data: { page: page},
        success: function (html) {
            $(window).scrollTop(0);
            $(".main_frame").html(html);
            set_dashboard(page);
        } }); }

function set_dashboard(arg1){
    page = $.cookie('active-tab');
    stringhe = {
        hero : "<a>Welcome!</a>",
        inbox : "<a>Welcome to your Inbox</a>",
        starred : "<a>These are important</a>",
        shared : "<a>Your shared items</a>",
        archived : "<a>Your archive</a>",
        untagged : "<a>Tagging is important!</a>",
        trashed : "<a>Trashed items</a>",
        stream : "<a>Our public stream</a>",
        tagcloud : "<a>Your tagcloud</a>",
        feeds : "<a>Your Subscriprtion</a>",
        setting : "<a>Your Setting</a>",
        admin : "<a>Administration</a>",
        domfilter : "<a>Bookmarks filtered by domain</a>",
        filter : "<a>Bookmarks filtered by tag</a>",
        refine : "<a>Bookmarks refinded by tag</a>"
    };
    $("#dashboard").html(stringhe[page]);
    $(".support").html('');
    $(".nav li").removeClass('active');
    $("." + page).addClass('active');
    $('.comments a').attr('target', '_blank');

    if (page == 'inbox' || 'filter' || 'refine') {
        $(".trash_all_btn").removeClass('hide');
    }
    if (page == 'archived') {
        $(".archive_all_btn").addClass('hide');
    }
    if (page == 'trashed') {
        support('/get_empty_trash');
        $(".toolbars").addClass('hide');
        $(".footer_btn").removeClass('hide');
    }
    if (page == 'filter') {
        refine_tags(arg1);
    }

    if ($.cookie('tips-feed') != 'hide') {
        if (page == 'feeds') {
            support('/get_tips');
        }
    }
}

function addtag() {
    var querystring = $('#addtag').serialize();
    event.preventDefault();
    $.ajax({
        url: '/addtag',
        data: querystring,
        success: function () {
            $(".dashboard").html('<a>New tag created</a>');
            $('#addtag input').val('');
        } }); }

function hide_all() {
    $('.comments').addClass('hide');
    $('.collapse_btn').addClass('hide');
    $('.expande_btn').removeClass('hide');
}
function show_all() {
    $('.comments').removeClass('hide');
    $('.expande_btn').addClass('hide');
    $('.collapse_btn').removeClass('hide');
}

function archive_all() {
    $.ajax({
        url: '/archive_all',
        success: function () {
            $('.more_btn').trigger('click');
        } }); }

function trash_all() {
    $.ajax({
        url: '/trash_all',
        success: function () {
            $('.more_btn').trigger('click');
        } }); }

function refine_tags(arg1) {
    $.ajax({
        url: '/get_refine_tags',
        data: {arg1: arg1 },
        success: function (html) {
            $(".support").html(html);
        } }); }

function support(url) {
    $.ajax({
        url: url,
        success: function (html) {
            $(".support").html(html);
            $(window).scrollTop(0);
        } }); }

function archive(id) {
    $.ajax({
        url: "/archive",
        data: { bm: id },
        success: function() {
            $(".row-" + id).addClass('hide');
        } }); }

function trash(id) {
    $.ajax({
        url: "/trash",
        data: { bm: id },
        success: function() {
            $(".row-" + id).addClass('hide');
        } }); }

function star(id) {
    $.ajax({
        url: "/star",
        data: { bm: id },
        success: function(html) {
            $("#dashboard").html('<a>Star status changed</a>');
            $(".star-" + id).html(html);
        } }); }

function share(id) {
    $.ajax({
        url: "/share",
        data: { id: id },
        success: function(eye) {
            $(".share-" + id).html(eye);
            $("#dashboard").html('<a>Share status changed</a>');
            if (eye == ('<i class="icon-eye-close"></i>')) {
                $(".link-" + id).html('');
            } else {
                $(".link-" + id).html('<a class="btn btn-small btn-link " href="/bm?id='+id+'" target="_blank">link</a>');
            } } }); }

function comment(url, id) {
    $.ajax({
        url: url,
        data: { bm: id },
        success: function(html) {
            $(".comment-"+id).removeClass('hide');
            $(".comment-"+id).html(html);
        } }); }

function removetag (bm, tag) {
    $.ajax({
        url: "/removetag",
        data: { bm: bm, tag: tag },
        success: function(html) {
            $(".tags-"+bm).html(html);
        } }); }

function assigntag (bm, tag) {
    $.ajax({
        url: "/assigntag",
        data: { bm: bm, tag: tag },
        success: function(html) {
            $(".tag-"+tag).addClass('hide');
            $(".tags-"+bm).html(html);
        } }); }

function setnotify (id, notify) {
    $.ajax({
        url: "/setnotify",
        data: { feed: id, notify: notify}
        }); }

function get_tags (id) {
    $("#dashboard").html('<a>Associate a tag to the feed</a>');
    $.ajax({
        url: "/gettagsfeed",
        data: { feed: id},
        success: function(html) {
            $(".comment-"+id).html(html);
        } }); }

function del_feed (id) {
    $("#dashboard").html('<a>Deleting the feed</a>');
    $.ajax({
        url: "/feed",
        data: { id: id},
        success: function() {
            $("#dashboard").html('<a>OK. Feed deleted</a>');
            $(".row-"+id).addClass('hide');
        } }); }

function sync_feed (id) {
    $("#dashboard").html('<a>Sync the feed</a>');
    $.ajax({
        url: "/checkfeed",
        data: { feed: id},
        success: function() {
            $("#dashboard").html('<a>OK sync started </a>');
        } }); }
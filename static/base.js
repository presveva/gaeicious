function init(){
    getbms('inbox');
    set_dashboard();
}

function active() {
    return $.cookie('active-tab');
}

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
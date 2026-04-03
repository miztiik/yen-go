
Playlist = function(assets, language) {
  this.init(assets, language);
};

Playlist.prototype = {

  init: function(assets, language) {
    this._language = language;
    this._modal = document.getElementById("btp-playlist-modal-container");
    this._modal_top_text = document.getElementById("btp-playlist-modal-top-text");
    this._modal_close_icon = document.getElementById("btp-playlist-modal-close-icon");
    this._modal_close_icon.onclick = function() {
      global.signal_toggle_playlist_modal();
    };
    this._modal.active = false;
    this._modal_rank_selector = document.getElementById("btp-playlist-modal-rank-selector");
    var option = document.createElement("option");
    option.value = -200;
    option.textContent = this._language._active_language.any_rank;
    option.selected = true;
    this._modal_rank_selector.appendChild(option);
    var option = document.createElement("option");
    option.value = -100;
    option.textContent = this._language._active_language.my_rank;
    this._modal_rank_selector.appendChild(option);
    for (var i = 0; i < 3000; i += 100) {
      var option = document.createElement("option");
      option.value = i;
      option.textContent = this._language._active_language.get_rank(i);
      this._modal_rank_selector.appendChild(option);
    }
    this._modal_rank_selector.onchange = function () {
      if (this.value == -200) {
        global.solver._playlist._modal_span_selector.disabled = true;
      } else {
        if (global.solver._playlist._modal_span_selector.disabled == true) {
          global.solver._playlist._modal_span_selector.disabled = false;
        }
      }
      global.solver._playlist.update_settings();
    };
    this._modal_span_selector = document.getElementById("btp-playlist-modal-span-selector");
    var option = document.createElement("option");
    option.value = 0;
    option.textContent = this._language._active_language.only;
    this._modal_span_selector.appendChild(option);
    for (var i = 1; i < 6; i += 1) {
      var option = document.createElement("option");
      option.value = i;
      option.textContent = "+/- " + i;
      if (i == 1) {
        option.selected = true;
      }
      this._modal_span_selector.appendChild(option);
    }
    this._modal_span_selector.onchange = function () {
      global.solver._playlist.update_settings();
    };
    this._modal_span_selector.disabled = true;
    this._classic_box = document.getElementById("btp-playlist-modal-classic-box");
    this._classic_box.classList.add("modal-type-boxes-selected");
    this._classic_box.selected = true;
    this._classic_box.onclick = function () {
      this.classList.remove("modal-type-boxes-selected");
      this.classList.remove("modal-type-boxes-unselected");
      if (this.selected == true) {
        this.classList.add("modal-type-boxes-unselected");
        this.selected = false;
      } else {
        this.classList.add("modal-type-boxes-selected");
        this.selected = true;
      }
      global.solver._playlist.update_settings();
      global.solver._playlist.update_cookie_settings();
    };
    this._ai_box = document.getElementById("btp-playlist-modal-ai-box");
    this._ai_box.classList.add("modal-type-boxes-selected");
    this._ai_box.selected = true;
    this._ai_box.onclick = function () {
      this.classList.remove("modal-type-boxes-selected");
      this.classList.remove("modal-type-boxes-unselected");
      if (this.selected == true) {
        this.classList.add("modal-type-boxes-unselected");
        this.selected = false;
      } else {
        this.classList.add("modal-type-boxes-selected");
        this.selected = true;
      }
      global.solver._playlist.update_settings();
      global.solver._playlist.update_cookie_settings();
    };
    this._endgame_box = document.getElementById("btp-playlist-modal-endgame-box");
    this._endgame_box.classList.add("modal-type-boxes-selected");
    this._endgame_box.selected = true;
    this._endgame_box.onclick = function () {
      this.classList.remove("modal-type-boxes-selected");
      this.classList.remove("modal-type-boxes-unselected");
      if (this.selected == true) {
        this.classList.add("modal-type-boxes-unselected");
        this.selected = false;
      } else {
        this.classList.add("modal-type-boxes-selected");
        this.selected = true;
      }
      global.solver._playlist.update_settings();
      global.solver._playlist.update_cookie_settings();
    };

    this._modal_category_text = document.getElementById("btp-playlist-modal-category-text");
    this._modal_category_selector = document.getElementById("btp-playlist-modal-category-selector");
    this._modal_category_selector.onchange = function () {
      global.solver._playlist._modal_tag_selector.selectedIndex = 0;
      global.solver._playlist.update_settings();
    };

    this._modal_tag_text = document.getElementById("btp-playlist-modal-tag-text");
    this._modal_tag_selector = document.getElementById("btp-playlist-modal-tag-selector");
    this._modal_tag_selector.onchange = function () {
      global.solver._playlist._modal_category_selector.selectedIndex = 0;
      global.solver._playlist.update_settings();
    };

    this._modal_repeat_text = document.getElementById("btp-playlist-modal-repeat-text");
    this._modal_repeat_selector = document.getElementById("btp-playlist-modal-repeat-selector");
    var option = document.createElement("option");
    option.value = "none";
    option.textContent = this._language._active_language.repeat_none;
    this._modal_repeat_selector.appendChild(option);
    var option = document.createElement("option");
    option.value = "failed";
    option.textContent = this._language._active_language.repeat_failed;
    this._modal_repeat_selector.appendChild(option);
    var option = document.createElement("option");
    option.value = "all";
    option.textContent = this._language._active_language.repeat_all;
    this._modal_repeat_selector.appendChild(option);
    this._modal_repeat_selector.onchange = function () {
      global.solver._playlist.update_settings();
      global.solver._playlist.update_cookie_settings();
    };

    this._modal_count_text = document.getElementById("btp-playlist-modal-count-text");
    this._modal_expansion_text = document.getElementById("btp-playlist-modal-expansion-text");
    this._modal_expansion_text.onclick = () => {
      global.signal_toggle_expansion_modal("playlist");
    };

    this._number_text = document.getElementById("btp-tsumego-playlist-number-text");
    this._last_number_index = 0;
    this._last_number_count = 0;
    this._type_text = document.getElementById("btp-tsumego-playlist-type-text");
    this._selection_text = document.getElementById("btp-tsumego-playlist-selection-text");
    this._repeat_text = document.getElementById("btp-tsumego-playlist-repeat-text");
    this._settings_icon_container = document.getElementById("btp-tsumego-playlist-settings-icon-container");
    var settings_icon = document.createElement("img");
    settings_icon.id = "btp-tsumego-playlist-settings-icon";
    settings_icon.src = assets.images["settings"].image.src;
    this._settings_icon_container.appendChild(settings_icon);
    this._settings_icon = settings_icon;
    this._settings_icon_container.onclick = function() {
      global.signal_toggle_playlist_modal();
    };
    // Get previous settings from local storage
    var p = JSON.parse(cookie_handler.get_data_value("playlist"));
    if (p && p.types && p.categories && p.tags && p.repeat && p.rating_type && (p.rating_baseline || p.rating_baseline == 0) && (p.rating_delta || p.rating_delta == 0)) {
      this._settings = {};
      if (!("revision" in p)) {
        p.revision = 2;
        if (p.types.includes && p.types.includes("endgame")) {
          p.types.splice(p.types.indexOf("endgame", 1));
        }
        cookie_handler.update_data("playlist", JSON.stringify(p));
      }
      this._settings.types = p.types;
      if (!this._settings.types.includes("classic")) {
        this._classic_box.classList.remove("modal-type-boxes-selected");
        this._classic_box.classList.add("modal-type-boxes-unselected");
        this._classic_box.selected = false;
      }
      if (!this._settings.types.includes("ai")) {
        this._ai_box.classList.remove("modal-type-boxes-selected");
        this._ai_box.classList.add("modal-type-boxes-unselected");
        this._ai_box.selected = false;
      }
      if (!this._settings.types.includes("endgame")) {
        this._endgame_box.classList.remove("modal-type-boxes-selected");
        this._endgame_box.classList.add("modal-type-boxes-unselected");
        this._endgame_box.selected = false;
      }
      this._settings.rating_type = p.rating_type;
      this._settings.rating_delta = p.rating_delta;
      if (!p.ratings) {
        var potential_rating = cookie_handler.get_data_value("verified_rating");
        if (!potential_rating) {
          potential_rating = cookie_handler.get_data_value("visitor_rating");
        }
        if (potential_rating) {
          this._settings.rating_baseline = this.get_rating_baseline(Number(potential_rating));
        } else {
          this._settings.rating_baseline = 0;
        }
      } else {
        this._settings.rating_baseline = p.rating_baseline;
      }
      if (!this._settings.rating_type) this._settings.rating_type = "any";
      if (!this._settings.rating_delta) this._settings.rating_delta = 100;
      this._settings.categories = p.categories;
      this._settings.tags = p.tags;
      this._settings.repeat = p.repeat;
    } else {
      this._settings = {};
      this._settings.types = ["classic", "ai"];
      this._endgame_box.classList.remove("modal-type-boxes-selected");
      this._endgame_box.classList.add("modal-type-boxes-unselected");
      this._endgame_box.selected = false;
      this._settings.revision = 2;
      var potential_rating = cookie_handler.get_data_value("verified_rating");
      if (!potential_rating) {
        potential_rating = cookie_handler.get_data_value("visitor_rating");
      }
      if (potential_rating) {
        this._settings.rating_baseline = this.get_rating_baseline(Number(potential_rating));
        this._settings.rating_type = "any";
      } else {
        this._settings.rating_baseline = 0;
        this._settings.rating_type = "any";
      }
      this._settings.rating_delta = 100;
      this._settings.categories = "any";
      this._settings.tags = "any";
      this._settings.repeat = "none"; // Should be none, failed or all
      cookie_handler.update_data("playlist", JSON.stringify(this._settings));
    }
    if (this._settings.repeat != this._modal_repeat_selector.value) {
      for (let i = 0; i < this._modal_repeat_selector.length; ++i) {
        if (this._modal_repeat_selector[i].value == this._settings.repeat) {
          this._modal_repeat_selector[i].selected = true;
          break;
        }
      }
    }
    this.update_language();
    this._slide_disabled_because_of_tags = false;
  },

  get_rating_baseline: function (rating) {
    var result = 0;
    modulo_rest = rating % 100;
    if (modulo_rest) {
      if (modulo_rest >= 50) {
        result = rating + 100 - modulo_rest;
      } else {
        result = rating - modulo_rest;
      }
    } else {
      result = rating;
    }
    if (result < 0) result = 0;
    if (result > 2900) result = 2900;
    return result;
  },

  update_cookie_settings: function () {
    var p = JSON.parse(cookie_handler.get_data_value("playlist"));
    if (p && p.types && p.categories && p.tags && p.repeat && p.rating_type && (p.rating_baseline || p.rating_baseline == 0) && (p.rating_delta || p.rating_delta == 0)) {
      let selected_types = [];
      if (this._classic_box.selected == true) {
        selected_types.push("classic");
      }
      if (this._ai_box.selected == true) {
        selected_types.push("ai");
      }
      if (this._endgame_box.selected == true) {
        selected_types.push("endgame");
      }
      if (selected_types.length < 1) {
        selected_types = ["classic", "ai"];
      }
      p.types = selected_types;

      let settings_repeat = this._modal_repeat_selector.value;
      if (settings_repeat && ["none", "failed", "all"].includes(settings_repeat)) {
        p.repeat = settings_repeat;
      }

      cookie_handler.update_data("playlist", JSON.stringify(p));

    }
  },

  update_settings: function () {
    var rating_value = Number(this._modal_rank_selector.value);
    this._settings.rating_fixed = true;
    if (rating_value == -200) { // "Any rank"
      this._settings.rating_type = "any";
      this._settings.rating_fixed = false;
    } else {
      this._settings.rating_delta = this._modal_span_selector.value * 100;
      if (this._settings.rating_delta == 0) {
        this._settings.rating_type = "only";
      } else {
        this._settings.rating_type = "span";
      }
      if (rating_value == -100) { // "My rank"
        this._settings.rating_type = "player";
        this._settings.rating_baseline = this.get_rating_baseline(global.player.get_rating());
        this._settings.rating_fixed = false;
      } else { // Rating value
        this._settings.rating_baseline = rating_value;
      }
    }
    this._settings.types = [];
    if (this._classic_box.selected == true) this._settings.types.push("classic");
    if (this._ai_box.selected == true) this._settings.types.push("ai");
    if (this._endgame_box.selected == true) this._settings.types.push("endgame");
    this._settings.categories = this._modal_category_selector.value;
    this._settings.tags = this._modal_tag_selector.value;
    this._settings.repeat = this._modal_repeat_selector.value;

    var field = "XX"; // Note: XX is the key for total count
    if (this._settings.categories != "any") {
      var n = STATIC_CATEGORIES.indexOf(this._settings.categories);
      field = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[n];
    } else if (this._settings.tags !=  "any") {
      var n = STATIC_TAGS.indexOf(this._settings.tags);
      field = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[(n - (n % 26)) / 26] + "abcdefghijklmnopqrstuvwxyz"[n % 26];
    }

    var lists_to_sum = [];
    var attempted_lists_to_sum = [];
    var failed_lists_to_sum = [];
    if (this._settings.types.includes("classic") && this._settings.types.includes("ai") && this._settings.types.includes("endgame")) {
      // All fields, look at total list(s):
      var list_to_add = global.tsumego_list._public_content_count.total[field];
      if (list_to_add) lists_to_sum.push(list_to_add);
      var list_to_add = global.tsumego_list._attempted_content_count.total[field];
      if (list_to_add) attempted_lists_to_sum.push(list_to_add);
      var list_to_add = global.tsumego_list._failed_content_count.total[field];
      if (list_to_add) failed_lists_to_sum.push(list_to_add);
    } else {
      // Step through selected types:
      for (const t of this._settings.types) {
        var list_to_add = global.tsumego_list._public_content_count[t][field];
        if (list_to_add) lists_to_sum.push(list_to_add);
        var list_to_add = global.tsumego_list._attempted_content_count[t][field];
        if (list_to_add) attempted_lists_to_sum.push(list_to_add);
        var list_to_add = global.tsumego_list._failed_content_count[t][field];
        if (list_to_add) failed_lists_to_sum.push(list_to_add);
      }
    }

    var min_rating = 0;
    var max_rating = 2900;
    if (this._settings.rating_type == "only") {
      min_rating = this._settings.rating_baseline;
      max_rating = this._settings.rating_baseline;
    } else if (this._settings.rating_type == "player") {
      min_rating = this.get_rating_baseline(Number(global.player.get_rating())) - this._settings.rating_delta;
      max_rating = this.get_rating_baseline(Number(global.player.get_rating())) + this._settings.rating_delta;
    } else if (this._settings.rating_type == "span") {
      min_rating = this._settings.rating_baseline - this._settings.rating_delta;
      max_rating = this._settings.rating_baseline + this._settings.rating_delta;
    }
    if (min_rating < 0) min_rating = 0;
    if (max_rating > 2900) max_rating = 2900;

    var sum = 0;
    var attempted_sum = 0;
    var failed_sum = 0;
    for (const l of lists_to_sum) {
      for (var i = min_rating; i <= max_rating; i += 100) {
        sum += l[i];
      }
    }
    for (const l of attempted_lists_to_sum) {
      for (var i = min_rating; i <= max_rating; i += 100) {
        attempted_sum += l[i];
      }
    }
    for (const l of failed_lists_to_sum) {
      for (var i = min_rating; i <= max_rating; i += 100) {
        failed_sum += l[i];
      }
    }

    var result = 0;
    if (this._settings.repeat == "none") {
      result = sum;
    } else if (this._settings.repeat == "failed") {
      result = sum + failed_sum;
    } else if (this._settings.repeat == "all") {
      result = sum + attempted_sum;
    }

    // this._modal_count_text.textContent = this._language._active_language.n_matching_tsumego.replace("%COUNT%", result);
    this.update_modal_count_text(result);

  },

  populate_sorted_selector: function(selector, static_content, content_type) {
    // Note: content_type must be "tag" or "category"
    const selected_value = selector.value;
    while (selector.childElementCount) {
      selector.removeChild(selector.firstChild);
    }
    var option = document.createElement("option");
    option.value = "any";
    if (content_type == "tag") {
      option.textContent = this._language._active_language.any_tag;
    } else {
      option.textContent = this._language._active_language.any_category;
    }
    if (selected_value == "any") {
      option.selected = true;
    }
    selector.appendChild(option);
    sorted_content = [];
    for (tag of static_content) {
      sorted_content.push({"tag": tag, "content": this._language._active_language[content_type + ":" + tag]});
    }
    if (this._language._active_language.latin_alphabet == true) {
      sorted_content.sort((a,b) => (a.content > b.content) ? 1 : -1);
    } else {
      sorted_content.sort((a,b) => a.content.localeCompare(b.content));
    }
    for (content_item of sorted_content) {
      var option = document.createElement("option");
      option.value = content_item["tag"];
      option.textContent = content_item["content"];
      if (selected_value == content_item["tag"]) {
        option.selected = true;
      }
      selector.appendChild(option);
    }
  },

  show_modal: function() {
    if (this._modal.active == false) {
      if (global.player.get_expansion_pack() == true) {
        if (this._modal_expansion_text.style.display != "none") {
          this._modal_expansion_text.style.display = "none";
        }
      } else {
        if (this._modal_expansion_text.style.display == "none") {
          this._modal_expansion_text.style.display = "block";
        }
      }
      this._modal.style.display = "block";
      this._modal.style.visibility = "visible";
      this._modal.active = true;
      this._modal.classList.remove("playlist-modal-animate-in");
      this._modal.classList.remove("playlist-modal-animate-out");
      this._modal.classList.add("playlist-modal-animate-in");
      this._settings_when_opened = this._settings.types.join("") + this._settings.rating_type + this._settings.rating_baseline.toString() + this._settings.rating_delta.toString() + this._settings.categories + this._settings.tags + this._settings.repeat;
    }
  },

  hide_modal: function() {
    if (this._modal.active == true) {
      this._modal.active = false;
      this._modal.classList.remove("playlist-modal-animate-in");
      this._modal.classList.remove("playlist-modal-animate-out");
      this._modal.classList.add("playlist-modal-animate-out");
      setTimeout(() => {
        this._modal.style.display = "none";
        this._modal.style.visibility = "hidden";
      }, 200);
    }
    // Update only if playlist settings not same as when modal was opened:
    const current_settings = this._settings.types.join("") + this._settings.rating_type + this._settings.rating_baseline.toString() + this._settings.rating_delta.toString() + this._settings.categories + this._settings.tags + this._settings.repeat;
    if (current_settings != this._settings_when_opened) {
      global.tsumego_list.update_list_by_playlist_settings(this._settings);
      if (global.solver._next_button.active == false) {
        global.solver._next_button.toggle();
      }
      // TODO: Enable the following lines to disable rated mode when sorting by tag...
      // TODO: Also look over the code for the function "global.solver._slide.toggle()"
      // if (global.solver._slide.get_rated() == true) {
      //   // If sorting by tag, turn rated mode OFF
      //   if (this._settings.tags != "any") {
      //     global.solver._slide.disable();
      //     this._slide_disabled_because_of_tags = true;
      //   }
      // } else {
      //   if (this._slide_disabled_because_of_tags == true && this._settings.tags == "any") {
      //     global.solver._slide.enable();
      //     this._slide_disabled_because_of_tags = false;
      //   }
      // }
    }
  },

  modal_visible: function() {
    return this._modal.active;
  },

  update_modal_count_text: function(count) {
    this._modal_count_text.textContent = this._language._active_language.n_matching_tsumego.replace("%COUNT%", count);
  },

  update_playlist_number_text: function(index, count) {
    this._number_text.textContent = this._language._active_language.problem_index_of_count.replace("%INDEX%", index).replace("%COUNT%", count);
    this._last_number_index = index;
    this._last_number_count = count;
  },

  update_playlist_number_text_for_language: function() {
    const index = this._last_number_index;
    const count = this._last_number_count;
    this._number_text.textContent = this._language._active_language.problem_index_of_count.replace("%INDEX%", index).replace("%COUNT%", count);
  },

  update_playlist_type_text: function() {
    var type_string =  "";
    for (const t of this._settings.types) {
      if (type_string) {
        type_string += " | ";
      }
      type_string += this._language._active_language[t];
    }
    if (type_string) {
      this._type_text.textContent = type_string;
    } else {
      this._type_text.textContent = "-";
    }
  },

  update_playlist_category_text: function() {
    var rank_string =  "";
    if (this._settings.rating_type == "any") {
      rank_string += this._language._active_language.any_rank;
    } else if (this._settings.rating_type == "only") {
      rank_string += this._language._active_language.get_short_rank(this._settings.rating_baseline);
    } else if (this._settings.rating_type == "span") {
      var rank_one = this._language._active_language.get_short_rank(this._settings.rating_baseline - this._settings.rating_delta);
      var rank_two = this._language._active_language.get_short_rank(this._settings.rating_baseline + this._settings.rating_delta);
      rank_string += rank_one + " - " + rank_two;
    } else if (this._settings.rating_type == "player") {
      var player_rating = this.get_rating_baseline(Number(global.player.get_rating()));
      if (this._settings.rating_delta == 0) {
        rank_string += this._language._active_language.get_short_rank(player_rating);
      } else {
        var rank_one = this._language._active_language.get_short_rank(player_rating - this._settings.rating_delta);
        var rank_two = this._language._active_language.get_short_rank(player_rating + this._settings.rating_delta);
        rank_string += rank_one + " - " + rank_two;
      }
    }
    if(!rank_string) {
      rank_string = "-";
    }
    var category_string =  "";
    if (this._settings.categories == "any" && this._settings.tags == "any") {
      category_string = this._language._active_language.any_category;
    } else if (this._settings.categories != "any") {
      category_string = this._settings.categories;
    } else if (this._settings.tags != "any") {
      category_string = this._settings.tags;
    }
    if(!category_string) {
      category_string = "-";
    }
    var category_string =  "";
    if (this._settings.categories == "any" && this._settings.tags == "any") {
      category_string = this._language._active_language.any_category;
    } else if (this._settings.categories != "any") {
      category_string = this._language._active_language["category:" + this._settings.categories];
    } else if (this._settings.tags != "any") {
      category_string = this._language._active_language["tag:" + this._settings.tags];
    }
    if(!category_string) {
      category_string = "-";
    }
    this._selection_text.textContent = rank_string + " | " + category_string;
  },


  update_playlist_repeat_text: function() {
    var repeat_string = "";
    if (this._settings.repeat == "none") {
      repeat_string = this._language._active_language.repeat_none;
    } else if (this._settings.repeat == "failed") {
      repeat_string = this._language._active_language.repeat_failed;
    } else if (this._settings.repeat == "all") {
      repeat_string = this._language._active_language.repeat_all;
    }
    if (!repeat_string) {
      repeat_string = "-";
    }

    this._repeat_text.textContent = repeat_string;
  },

  update_language: function() {
    this._settings_icon_container.title = this._language._active_language.playlist_settings;
    this._modal_top_text.textContent = this._language._active_language.tsumego_selection;
    for(var i = 0; i < this._modal_rank_selector.length; ++i) {
      if (this._modal_rank_selector[i].value == -200) {
        this._modal_rank_selector[i].textContent = this._language._active_language.any_rank;
      } else if (this._modal_rank_selector[i].value == -100) {
        this._modal_rank_selector[i].textContent = this._language._active_language.my_rank;
      } else {
        this._modal_rank_selector[i].textContent = this._language._active_language.get_rank(this._modal_rank_selector[i].value);
      }
    }
    this._modal_span_selector[0].textContent = this._language._active_language.only;

    this._classic_box.textContent = this._language._active_language.classic;
    this._ai_box.textContent = this._language._active_language.ai;
    this._endgame_box.textContent = this._language._active_language.endgame;

    this._modal_category_text.textContent = this._language._active_language.category;
    this.populate_sorted_selector(this._modal_category_selector, STATIC_CATEGORIES, "category");
    this._modal_tag_text.textContent = this._language._active_language.tag;
    this.populate_sorted_selector(this._modal_tag_selector, STATIC_TAGS, "tag");

    this._modal_repeat_text.textContent = this._language._active_language.repeat;
    this._modal_repeat_selector[0].textContent = this._language._active_language.repeat_none;
    this._modal_repeat_selector[1].textContent = this._language._active_language.repeat_failed;
    this._modal_repeat_selector[2].textContent = this._language._active_language.repeat_all;

    this._modal_expansion_text.textContent = this._language._active_language.hundred_thousand_available;

    this.update_playlist_type_text();
    this.update_playlist_category_text();
    this.update_playlist_repeat_text();

    this.update_playlist_number_text_for_language();

  },

};




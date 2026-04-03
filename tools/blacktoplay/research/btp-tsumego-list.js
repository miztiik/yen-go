
TsumegoList = function(language) {
  this.init(language);
};

TsumegoList.prototype = {

  init: function(language) {
    this._language = language;
    this._classic_list = [];
    this._ai_list = [];
    this._endgame_list = [];
    this._classic_indexes = {};
    this._ai_indexes = {};
    this._endgame_indexes = {};
    this._full_updated_classic_list = [];
    this._full_updated_ai_list = [];
    this._full_updated_endgame_list = [];
    this._full_updated_classic_indexes = {};
    this._full_updated_ai_indexes = {};
    this._full_updated_endgame_indexes = {};
    this._repeat_classic_list = [];
    this._repeat_classic_indexes = [];
    this._repeat_ai_list = [];
    this._repeat_ai_indexes = {};
    this._repeat_endgame_list = [];
    this._repeat_endgame_indexes = {};
    this._attempted_classic_list = [];
    this._attempted_ai_list = [];
    this._attempted_endgame_list = [];
    this._attempted_classic_indexes = [];
    this._attempted_ai_indexes = [];
    this._attempted_endgame_indexes = [];
    this._attempted_from_storage = [];
    this._failed_classic_list = [];
    this._failed_ai_list = [];
    this._failed_endgame_list = [];
    this._failed_classic_indexes = {};
    this._failed_ai_indexes = {};
    this._failed_endgame_indexes = {};
    this._failed_from_storage = [];
    this._number_of_loaded_in_repeat_list = 0;
    this._last_setting_string = "";
    this._attempted = [];
    this._public_content_count = null;
    this._attempted_content_count = null;
    this._failed_content_count = null;
    this._last_list_length = 0;
    this._attempted_in_current_list = 0;
    this._last_type = (cookie_handler.get_data_value("last_type") || "endgame");
    this._current_rating_settings = null;
    this._last_baseline_for_sort = 0;
    // Prepare symbol number lookup, for binary search:
    this._symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    this._symbol_lookup = {};
    for (var i = 0; i < this._symbols.length; ++i) {
      this._symbol_lookup[this._symbols[i]] = i;
    }
    this._popped_from_repeat_in_player_mode = [];
  },


  get_attempted_count: function() {
    return this._attempted_classic_list.length + this._attempted_ai_list.length + this._attempted_endgame_list.length;
  },


  get_failed_count: function() {
    return this._failed_classic_list.length + this._failed_ai_list.length + this._failed_endgame_list.length;
  },


  get_rating_baseline: function (rating) {
    var result = 0;
    var modulo_rest = rating % 100;
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


  binary_search_history_object_list: function(tsumego_id, list) {
    if (list.length == 0) return -1;
    if (list.length == 1) {
      if (list[0].tsumego_id == tsumego_id) {
        return 0;
      } else {
        return -1;
      }
    }
    var min = 0;
    var max = list.length - 1;
    while (true) {
      if ((max - min) < 5) {
        // Just look through each remaining object:
        for (var i = min; i <= max; ++i) {
          if (list[i].tsumego_id == tsumego_id) return i;
        }
        return -1;
      }
      var middle = min + ((max - min) >> 1);
      if (list[middle].tsumego_id == tsumego_id) {
        return middle;
      } else if (tsumego_id > list[middle].tsumego_id) {
        min = middle;
      } else {
        max = middle;
      }
    }
  },


  binary_search_attempted_string_list: function(tsumego_id) {
    if (this._attempted_from_storage.length == 0) return -1;
    if (this._attempted_from_storage.length == 1) {
      if (this._attempted_from_storage[0] == tsumego_id) {
        return 0;
      } else {
        return -1;
      }
    }
    var min = 0;
    var max = this._attempted_from_storage.length - 1;
    while (true) {
      if ((max - min) < 5) {
        // Just look through each remaining object:
        for (var i = min; i <= max; ++i) {
          if (this._attempted_from_storage[i] == tsumego_id) return i;
        }
        return -1;
      }
      var middle = min + ((max - min) >> 1);
      if (this._attempted_from_storage[middle] == tsumego_id) {
        return middle;
      } else if (tsumego_id > this._attempted_from_storage[middle]) {
        min = middle;
      } else {
        max = middle;
      }
    }
  },


  binary_search_failed_string_list: function(tsumego_id) {
    if (this._failed_from_storage.length == 0) return -1;
    if (this._failed_from_storage.length == 1) {
      if (this._failed_from_storage[0] == tsumego_id) {
        return 0;
      } else {
        return -1;
      }
    }
    var min = 0;
    var max = this._failed_from_storage.length - 1;
    while (true) {
      if ((max - min) < 5) {
        // Just look through each remaining object:
        for (var i = min; i <= max; ++i) {
          if (this._failed_from_storage[i] == tsumego_id) return i;
        }
        return -1;
      }
      var middle = min + ((max - min) >> 1);
      if (this._failed_from_storage[middle] == tsumego_id) {
        return middle;
      } else if (tsumego_id > this._failed_from_storage[middle]) {
        min = middle;
      } else {
        max = middle;
      }
    }
  },


  parse_tags_and_build_index: function() {

    this._public_content_count = {
      "total": {"XX": {}},
      "classic": {"XX": {}},
      "ai": {"XX": {}},
      "endgame": {"XX": {}},
    };
    this._attempted_content_count = {
      "total": {"XX": {}},
      "classic": {"XX": {}},
      "ai": {"XX": {}},
      "endgame": {"XX": {}},
    };
    this._failed_content_count = {
      "total": {"XX": {}},
      "classic": {"XX": {}},
      "ai": {"XX": {}},
      "endgame": {"XX": {}},
    };

    // Initialize all counter to zero in attempted and failed:
    const types = ["classic", "ai", "endgame", "total"];
    for (var i = 0; i < 3000; i += 100) {
      for (const type of types) {
        this._attempted_content_count[type].XX[i] = 0;
        this._failed_content_count[type].XX[i] = 0;
        for (var c = 0; c < STATIC_CATEGORIES.length; ++c) {
          var id = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[c];
          if (i == 0) {
            this._attempted_content_count[type][id] = {0: 0};
            this._failed_content_count[type][id] = {0: 0};
          } else {
            this._attempted_content_count[type][id][i] = 0;
            this._failed_content_count[type][id][i] = 0;
          }
        }
        for (var c = 0; c < STATIC_TAGS.length; ++c) {
          var id = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[(c - (c % 26)) / 26] + "abcdefghijklmnopqrstuvwxyz"[c % 26];
          if (i == 0) {
            this._attempted_content_count[type][id] = {0: 0};
            this._failed_content_count[type][id] = {0: 0};
          } else {
            this._attempted_content_count[type][id][i] = 0;
            this._failed_content_count[type][id][i] = 0;
          }
        }
      }
    }
    //

    for (var i = 0; i < 3000; i += 100) {
      this._public_content_count.total.XX[i] = 0;
      this._public_content_count.classic.XX[i] = 0;
      this._public_content_count.ai.XX[i] = 0;
      this._public_content_count.endgame.XX[i] = 0;
      this._attempted_content_count.total.XX[i] = 0;
      this._attempted_content_count.classic.XX[i] = 0;
      this._attempted_content_count.ai.XX[i] = 0;
      this._attempted_content_count.endgame.XX[i] = 0;
      this._failed_content_count.total.XX[i] = 0;
      this._failed_content_count.classic.XX[i] = 0;
      this._failed_content_count.ai.XX[i] = 0;
      this._failed_content_count.endgame.XX[i] = 0;
    }
    this.parse_tags_in_data(this._classic_list, this._public_content_count);
    this.parse_tags_in_data(this._ai_list, this._public_content_count);
    this.parse_tags_in_data(this._endgame_list, this._public_content_count);
    this.parse_tags_in_data(this._attempted_classic_list, this._attempted_content_count);
    this.parse_tags_in_data(this._attempted_ai_list, this._attempted_content_count);
    this.parse_tags_in_data(this._attempted_endgame_list, this._attempted_content_count);
    this.parse_tags_in_data(this._failed_classic_list, this._failed_content_count);
    this.parse_tags_in_data(this._failed_ai_list, this._failed_content_count);
    this.parse_tags_in_data(this._failed_endgame_list, this._failed_content_count);

  },


  parse_tags_in_data: function(data, count_object) {
    const types = ["classic", "ai", "endgame"];
    for(var t = 0; t < data.length; ++t) {
      count_object[types[data[t].type]].XX[this.get_rating_baseline(Number(data[t].rating))] += 1
      count_object.total.XX[this.get_rating_baseline(Number(data[t].rating))] += 1
      data[t].type = Number(data[t].type);
      // data[t].rating = Number(data[t].rating);
      var category_string = data[t].categories;
      var categories = [];
      for(var i = 0; i < category_string.length; ++i) {
        var index = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(category_string[i]);
        categories.push(STATIC_CATEGORIES[index]);
        if (count_object[types[data[t].type]][category_string[i]]) {
          count_object[types[data[t].type]][category_string[i]][this.get_rating_baseline(Number(data[t].rating))] += 1;
        } else {
          count_object[types[data[t].type]][category_string[i]] = {};
          for (var j = 0; j < 3000; j += 100) count_object[types[data[t].type]][category_string[i]][j] = 0;
          count_object[types[data[t].type]][category_string[i]][this.get_rating_baseline(Number(data[t].rating))] += 1;
        }
        if (count_object.total[category_string[i]]) {
          count_object.total[category_string[i]][this.get_rating_baseline(Number(data[t].rating))] += 1;
        } else {
          count_object.total[category_string[i]] = {};
          for (var j = 0; j < 3000; j += 100) count_object.total[category_string[i]][j] = 0;
          count_object.total[category_string[i]][this.get_rating_baseline(Number(data[t].rating))] += 1;
        }
      }
      data[t].categories = categories;
      var tag_string = data[t].tags;
      var tags = [];
      for(var i = 0; i < tag_string.length; i += 2) {
        var tag = tag_string.substring(i, i + 2);
        var index = "abcdefghijklmnopqrstuvwxyz".indexOf(tag[1]) + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(tag[0]) * 26)
        tags.push(STATIC_TAGS[index])
        if (count_object[types[data[t].type]][tag]) {
          count_object[types[data[t].type]][tag][this.get_rating_baseline(Number(data[t].rating))] += 1;
        } else {
          count_object[types[data[t].type]][tag] = {};
          for (var j = 0; j < 3000; j += 100) count_object[types[data[t].type]][tag][j] = 0;
          count_object[types[data[t].type]][tag][this.get_rating_baseline(Number(data[t].rating))] += 1;
        }
        if (count_object.total[tag]) {
          count_object.total[tag][this.get_rating_baseline(Number(data[t].rating))] += 1;
        } else {
          count_object.total[tag] = {};
          for (var j = 0; j < 3000; j += 100) count_object.total[tag][j] = 0;
          count_object.total[tag][this.get_rating_baseline(Number(data[t].rating))] += 1;
        }
      }
      data[t].tags = tags;
    }
  },


  load_data: function(data) {
    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.loading_history);
        setTimeout(() => {this.load_step_zero(data)}, 25);
      }, 25);
    } else {
      this.load_step_zero(data);
    }
  },


  load_step_zero: function(data) {
    this._classic_list = [];
    this._ai_list = [];
    this._endgame_list = [];
    this._attempted_classic_list = [];
    this._attempted_ai_list = [];
    this._attempted_endgame_list = [];
    this._attempted_from_storage = [];
    this._failed_classic_list = [];
    this._failed_ai_list = [];
    this._failed_endgame_list = [];
    this._failed_from_storage = [];

    if (!data.history || data.history.length == 0) {
      if (global.player.get_verified() == false) {
        var attempted_string = cookie_handler.get_data_value("attempted");
        if (attempted_string) {
          this._attempted_from_storage = attempted_string.split(";");
          this._attempted_from_storage.sort((a, b) => (a > b) ? 1 : -1);
        }
        var failed_string = cookie_handler.get_data_value("failed");
        if (failed_string) {
          this._failed_from_storage = failed_string.split(";");
          this._failed_from_storage.sort((a, b) => (a > b) ? 1 : -1);
        }
      }
    }
    var public_index = 0;
    var expansion_index = 0;
    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.parsing_classic);
        setTimeout(() => {this.load_step_one(data, public_index, expansion_index)}, 25);
      }, 25);
    } else {
      this.load_step_one(data, public_index, expansion_index);
    }
  },


  load_step_one: function(data, public_index, expansion_index) {
    if (data.expansion_list) {
      var expansion = true;
    } else {
      var expansion = false;
    }
    // Parse classic list
    for (var baseline_limit = 100; baseline_limit <= 3000; baseline_limit += 100) {
      while (data.list[public_index].type == 0 && this.get_rating_baseline(Number(data.list[public_index].rating)) < baseline_limit) {
        var item = data.list[public_index];
        item.rating = this.get_rating_baseline(Number(item.rating));
        item.db = 0;
        if (data.history && data.history.length != 0) {
          var attempted_index = this.binary_search_history_object_list(item.id, data.history);
          if (attempted_index != -1) {
            this._attempted_classic_list.push(item);
            if (data.history[attempted_index].correct == 0) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_classic_list.push(item_copy);
            }
          } else {
            this._classic_list.push(item);
          }
        } else if (this._attempted_from_storage.length != 0) {
          var attempted_index = this.binary_search_attempted_string_list(item.id);
          if (attempted_index != -1) {
            this._attempted_classic_list.push(item);
            var failed_index = this.binary_search_failed_string_list(item.id);
            if (failed_index != -1) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_classic_list.push(item_copy);
            }
          } else {
            this._classic_list.push(item);
          }
        } else {
          this._classic_list.push(item);
        }
        public_index++;
      }
      while(expansion == true && data.expansion_list[expansion_index].type == 0 && this.get_rating_baseline(Number(data.expansion_list[expansion_index].rating)) < baseline_limit) {
        var item = data.expansion_list[expansion_index];
        item.rating = this.get_rating_baseline(Number(item.rating));
        item.db = 1;
        if (data.history && data.history.length != 0) {
          var attempted_index = this.binary_search_history_object_list(item.id, data.history);
          if (attempted_index != -1) {
            this._attempted_classic_list.push(item);
            if (data.history[attempted_index].correct == 0) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_classic_list.push(item_copy);
            }
          } else {
            this._classic_list.push(item);
          }
        } else {
          this._classic_list.push(item);
        }
        expansion_index++;
      }
    }
    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.parsing_ai);
        setTimeout(() => {this.load_step_two(data, public_index, expansion_index)}, 25);
      }, 25);
    } else {
      this.load_step_two(data, public_index, expansion_index);
    }
  },


  load_step_two: function(data, public_index, expansion_index) {
    if (data.expansion_list) {
      var expansion = true;
    } else {
      var expansion = false;
    }
    // Parse AI list
    for (var baseline_limit = 100; baseline_limit <= 3000; baseline_limit += 100) {
      while (data.list[public_index].type == 1 && this.get_rating_baseline(Number(data.list[public_index].rating)) < baseline_limit) {
        var item = data.list[public_index];
        item.rating = this.get_rating_baseline(Number(item.rating));
        item.db = 0;
        if (data.history && data.history.length != 0) {
          var attempted_index = this.binary_search_history_object_list(item.id, data.history);
          if (attempted_index != -1) {
            this._attempted_ai_list.push(item);
            if (data.history[attempted_index].correct == 0) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_ai_list.push(item_copy);
            }
          } else {
            this._ai_list.push(item);
          }
        } else if (this._attempted_from_storage.length != 0) {
          var attempted_index = this.binary_search_attempted_string_list(item.id);
          if (attempted_index != -1) {
            this._attempted_ai_list.push(item);
            var failed_index = this.binary_search_failed_string_list(item.id);
            if (failed_index != -1) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_ai_list.push(item_copy);
            }
          } else {
            this._ai_list.push(item);
          }
        } else {
          this._ai_list.push(item);
        }
        public_index++;
      }
      while(expansion == true && data.expansion_list[expansion_index].type == 1 && this.get_rating_baseline(Number(data.expansion_list[expansion_index].rating)) < baseline_limit) {
        var item = data.expansion_list[expansion_index];
        item.rating = this.get_rating_baseline(Number(item.rating));
        item.db = 1;
        if (data.history && data.history.length != 0) {
          var attempted_index = this.binary_search_history_object_list(item.id, data.history);
          if (attempted_index != -1) {
            this._attempted_ai_list.push(item);
            if (data.history[attempted_index].correct == 0) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_ai_list.push(item_copy);
            }
          } else {
            this._ai_list.push(item);
          }
        } else {
          this._ai_list.push(item);
        }
        expansion_index++;
      }
    }
    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.parsing_endgame);
        setTimeout(() => {this.load_step_three(data, public_index, expansion_index)}, 25);
      }, 25);
    } else {
      this.load_step_three(data, public_index, expansion_index);
    }
  },


  load_step_three: function(data, public_index, expansion_index) {
    if (data.expansion_list) {
      var expansion = true;
    } else {
      var expansion = false;
    }
    // Parse endgame list
    for (var baseline_limit = 100; baseline_limit <= 3000; baseline_limit += 100) {
      while (public_index < data.list.length && data.list[public_index].type == 2 && this.get_rating_baseline(Number(data.list[public_index].rating)) < baseline_limit) {
        var item = data.list[public_index];
        item.rating = this.get_rating_baseline(Number(item.rating));
        item.db = 0;
        if (data.history && data.history.length != 0) {
          var attempted_index = this.binary_search_history_object_list(item.id, data.history);
          if (attempted_index != -1) {
            this._attempted_endgame_list.push(item);
            if (data.history[attempted_index].correct == 0) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_endgame_list.push(item_copy);
            }
          } else {
            this._endgame_list.push(item);
          }
        } else if (this._attempted_from_storage.length != 0) {
          var attempted_index = this.binary_search_attempted_string_list(item.id);
          if (attempted_index != -1) {
            this._attempted_endgame_list.push(item);
            var failed_index = this.binary_search_failed_string_list(item.id);
            if (failed_index != -1) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_endgame_list.push(item_copy);
            }
          } else {
            this._endgame_list.push(item);
          }
        } else {
          this._endgame_list.push(item);
        }
        public_index++;
      }
      while(expansion == true && expansion_index < data.expansion_list.length && data.expansion_list[expansion_index].type == 2 && this.get_rating_baseline(Number(data.expansion_list[expansion_index].rating)) < baseline_limit) {
        var item = data.expansion_list[expansion_index];
        item.rating = this.get_rating_baseline(Number(item.rating));
        item.db = 1;
        if (data.history && data.history.length != 0) {
          var attempted_index = this.binary_search_history_object_list(item.id, data.history);
          if (attempted_index != -1) {
            this._attempted_endgame_list.push(item);
            if (data.history[attempted_index].correct == 0) {
              var item_copy = {"categories": item.categories, "db": item.db, "id": item.id, "rating": item.rating, "tags": item.tags, "type": item.type};
              this._failed_endgame_list.push(item_copy);
            }
          } else {
            this._endgame_list.push(item);
          }
        } else {
          this._endgame_list.push(item);
        }
        expansion_index++;
      }
    }

    if (data.history && data.history.length != 0) {
      data.history.sort((a,b) => (a.time > b.time) ? 1 : -1);
      global.player._user_history = data.history;
    }

    if (data.favorites && data.favorites.length != 0) {
      data.favorites.sort((a,b) => (a.time > b.time) ? 1 : -1);
      global.player._user_favorites = data.favorites;
    }

    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.building_indexes);
        setTimeout(() => {this.load_step_four()}, 25);
      }, 25);
    } else {
      this.load_step_four();
    }
  },


  load_step_four: function() {
    this.parse_tags_and_build_index();
    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.saving_indexes);
        setTimeout(() => {this.load_step_five()}, 25);
      }, 25);
    } else {
      this.load_step_five();
    }
  },


  load_step_five: function() {
    var first_index_value = 0;
    this._classic_indexes = {};
    if (this._classic_list.length != 0 && this._classic_list[0].rating != 0) first_index_value = this._classic_list[0].rating;
    this._classic_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._ai_indexes = {};
    if (this._ai_list.length != 0 && this._ai_list[0].rating != 0) first_index_value = this._ai_list[0].rating;
    this._ai_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._endgame_indexes = {};
    if (this._endgame_list.length != 0 && this._endgame_list[0].rating != 0) first_index_value = this._endgame_list[0].rating;
    this._endgame_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._attempted_classic_indexes = {};
    if (this._attempted_classic_list.length != 0 && this._attempted_classic_list[0].rating != 0) first_index_value = this._attempted_classic_list[0].rating;
    this._attempted_classic_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._attempted_ai_indexes = {};
    if (this._attempted_ai_list.length != 0 && this._attempted_ai_list[0].rating != 0) first_index_value = this._attempted_ai_list[0].rating;
    this._attempted_ai_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._attempted_endgame_indexes = {};
    if (this._attempted_endgame_list.length != 0 && this._attempted_endgame_list[0].rating != 0) first_index_value = this._attempted_endgame_list[0].rating;
    this._attempted_endgame_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._failed_classic_indexes = {};
    if (this._failed_classic_list.length != 0 && this._failed_classic_list[0].rating != 0) first_index_value = this._failed_classic_list[0].rating;
    this._failed_classic_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._failed_ai_indexes = {};
    if (this._failed_ai_list.length != 0 && this._failed_ai_list[0].rating != 0) first_index_value = this._failed_ai_list[0].rating;
    this._failed_ai_indexes[first_index_value] = 0;
    //
    first_index_value = 0;
    this._failed_endgame_indexes = {};
    if (this._failed_endgame_list.length != 0 && this._failed_endgame_list[0].rating != 0) first_index_value = this._failed_endgame_list[0].rating;
    this._failed_endgame_indexes[first_index_value] = 0;
    //
    for (var i = 1; i < this._classic_list.length; ++i) {
      if (this._classic_list[i].rating != this._classic_list[i - 1].rating) {
        this._classic_indexes[this._classic_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._ai_list.length; ++i) {
      if (this._ai_list[i].rating != this._ai_list[i - 1].rating) {
        this._ai_indexes[this._ai_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._endgame_list.length; ++i) {
      if (this._endgame_list[i].rating != this._endgame_list[i - 1].rating) {
        this._endgame_indexes[this._endgame_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._attempted_classic_list.length; ++i) {
      if (this._attempted_classic_list[i].rating != this._attempted_classic_list[i - 1].rating) {
        this._attempted_classic_indexes[this._attempted_classic_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._attempted_ai_list.length; ++i) {
      if (this._attempted_ai_list[i].rating != this._attempted_ai_list[i - 1].rating) {
        this._attempted_ai_indexes[this._attempted_ai_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._attempted_endgame_list.length; ++i) {
      if (this._attempted_endgame_list[i].rating != this._attempted_endgame_list[i - 1].rating) {
        this._attempted_endgame_indexes[this._attempted_endgame_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._failed_classic_list.length; ++i) {
      if (this._failed_classic_list[i].rating != this._failed_classic_list[i - 1].rating) {
        this._failed_classic_indexes[this._failed_classic_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._failed_ai_list.length; ++i) {
      if (this._failed_ai_list[i].rating != this._failed_ai_list[i - 1].rating) {
        this._failed_ai_indexes[this._failed_ai_list[i].rating] = i;
      }
    }
    for (var i = 1; i < this._failed_endgame_list.length; ++i) {
      if (this._failed_endgame_list[i].rating != this._failed_endgame_list[i - 1].rating) {
        this._failed_endgame_indexes[this._failed_endgame_list[i].rating] = i;
      }
    }

    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_status(this._language._active_language.updating_playlist);
        setTimeout(() => {this.load_step_six()}, 25);
      }, 25);
    } else {
      this.load_step_six();
    }
  },


  load_step_six: function() {
    if (global.solver) {
      this.update_list_by_playlist_settings(global.solver._playlist._settings);
      global.solver._user_icon.update_info_container_text();
      global.solver._user_icon.update_statistics_container();
    } else  {
      this.send_list_update_command_after_solver_is_loaded();
    }
  },


  send_list_update_command_after_solver_is_loaded: function() {
    if (global.solver) {
      this.update_list_by_playlist_settings(global.solver._playlist._settings);
      global.solver._user_icon.update_info_container_text();
      global.solver._user_icon.update_statistics_container();
    } else {
      setTimeout(() => {
        this.send_list_update_command_after_solver_is_loaded();
      }, 25);
    }
  },


  update_list_by_playlist_settings: function (settings) {
    var setting_string = settings.types.join("") + settings.rating_type + settings.rating_baseline.toString() + settings.rating_delta.toString() + settings.categories + settings.tags + settings.repeat;
    if (app_fully_loaded == true && setting_string == this._last_setting_string && (this._full_updated_classic_list || this._full_updated_ai_list || this._full_updated_endgame_list || this._repeat_classic_list || this._repeat_ai_list || this._repeat_endgame_list)) {
      // No changes to settings, and at least one list already exist
      return;
    }

    this._current_rating_settings = {"type": settings.rating_type, "baseline": settings.rating_baseline, "delta": settings.rating_delta};

    this._last_setting_string = setting_string;
    this._full_updated_classic_list = [];
    this._full_updated_ai_list = [];
    this._full_updated_endgame_list = [];
    this._full_updated_classic_indexes = {};
    this._full_updated_ai_indexes = {};
    this._full_updated_endgame_indexes = {};
    this._repeat_classic_list = [];
    this._repeat_classic_indexes = {};
    this._repeat_ai_list = [];
    this._repeat_ai_indexes = {};
    this._repeat_endgame_list = [];
    this._repeat_endgame_indexes = {};
    this._popped_from_repeat_in_player_mode = [];
    /*
    for (var i = 0; i < 3000; i += 100) {
      this._repeat_classic_count_by_rating[i] = 0;
      this._repeat_ai_count_by_rating[i] = 0;
      this._repeat_endgame_count_by_rating[i] = 0;
    }
    */
    var min_rating = 0;
    var max_rating = 2900;
    if (settings.rating_type == "only") {
      min_rating = settings.rating_baseline;
      max_rating = settings.rating_baseline;
    } else if (settings.rating_type == "span") {
      min_rating = settings.rating_baseline - settings.rating_delta;
      max_rating = settings.rating_baseline + settings.rating_delta;
    }
    if (min_rating < 0) min_rating = 0;
    if (max_rating > 2900) max_rating = 2900;

    var types = [];
    if (settings.types.includes("classic")) types.push(0);
    if (settings.types.includes("ai")) types.push(1);
    if (settings.types.includes("endgame")) types.push(2);

    var content = {"type": null, "value": null};
    if (settings.categories != "any") {
      content.type = "category";
      content.value = settings.categories;
    } else if (settings.tags != "any") {
      content.type = "tag";
      content.value = settings.tags;
    }

    if (types.includes(0)) {
      if (settings.rating_type == "any" && settings.categories == "any" && settings.tags == "any") {
        this._full_updated_classic_list = this._classic_list;
        this._full_updated_classic_indexes = this._classic_indexes;
      } else {
        var start_index = 0;
        if (this._classic_indexes[min_rating] != undefined) {
          start_index = this._classic_indexes[min_rating];
        } else if (this._classic_indexes[min_rating + 100] != undefined) {
          start_index = this._classic_indexes[min_rating + 100];
        } else if (this._classic_indexes[min_rating + 200] != undefined) {
          start_index = this._classic_indexes[min_rating + 200];
        }
        var stop_index = this._classic_list.length;
        if (this._classic_indexes[max_rating + 100] != undefined) {
          stop_index = this._classic_indexes[max_rating + 100];
        } else if (this._classic_indexes[max_rating + 200] != undefined) {
          stop_index = this._classic_indexes[max_rating + 200];
        }
        for (var i = start_index; i < stop_index; ++i) {
          if (this._classic_list[i].rating < min_rating - 50 || this._classic_list[i].rating >= max_rating + 50) continue;
          if (content.type) {
            if (content.type == "category" && !this._classic_list[i].categories.includes(content.value)) continue;
            if (content.type == "tag" && !this._classic_list[i].tags.includes(content.value)) continue;
          }
          this._full_updated_classic_list.push(this._classic_list[i]);
        }
        this._full_updated_classic_indexes = this.get_rating_indexes_from_list(this._full_updated_classic_list);
      }
    }

    if (types.includes(1)) {
      if (settings.rating_type == "any" && settings.categories == "any" && settings.tags == "any") {
        this._full_updated_ai_list = this._ai_list;
        this._full_updated_ai_indexes = this._ai_indexes;
      } else {
        var start_index = 0;
        if (this._ai_indexes[min_rating] != undefined) {
          start_index = this._ai_indexes[min_rating];
        } else if (this._ai_indexes[min_rating + 100] != undefined) {
          start_index = this._ai_indexes[min_rating + 100];
        } else if (this._ai_indexes[min_rating + 200] != undefined) {
          start_index = this._ai_indexes[min_rating + 200];
        }
        var stop_index = this._ai_list.length;
        if (this._ai_indexes[max_rating + 100] != undefined) {
          stop_index = this._ai_indexes[max_rating + 100];
        } else if (this._ai_indexes[max_rating + 200] != undefined) {
          stop_index = this._ai_indexes[max_rating + 200];
        }
        for (var i = start_index; i < stop_index; ++i) {
          if (this._ai_list[i].rating < min_rating - 50 || this._ai_list[i].rating >= max_rating + 50) continue;
          if (content.type) {
            if (content.type == "category" && !this._ai_list[i].categories.includes(content.value)) continue;
            if (content.type == "tag" && !this._ai_list[i].tags.includes(content.value)) continue;
          }
          this._full_updated_ai_list.push(this._ai_list[i]);
        }
        this._full_updated_ai_indexes = this.get_rating_indexes_from_list(this._full_updated_ai_list);
      }
    }

    if (types.includes(2)) {
      if (settings.rating_type == "any" && settings.categories == "any" && settings.tags == "any") {
        this._full_updated_endgame_list = this._endgame_list;
        this._full_updated_endgame_indexes = this._endgame_indexes;
      } else {
        var start_index = 0;
        if (this._endgame_indexes[min_rating] != undefined) {
          start_index = this._endgame_indexes[min_rating];
        } else if (this._endgame_indexes[min_rating + 100] != undefined) {
          start_index = this._endgame_indexes[min_rating + 100];
        } else if (this._endgame_indexes[min_rating + 200] != undefined) {
          start_index = this._endgame_indexes[min_rating + 200];
        }
        var stop_index = this._endgame_list.length;
        if (this._endgame_indexes[max_rating + 100] != undefined) {
          stop_index = this._endgame_indexes[max_rating + 100];
        } else if (this._endgame_indexes[max_rating + 200] != undefined) {
          stop_index = this._endgame_indexes[max_rating + 200];
        }
        for (var i = start_index; i < stop_index; ++i) {
          if (this._endgame_list[i].rating < min_rating - 50 || this._endgame_list[i].rating >= max_rating + 50) continue;
          if (content.type) {
            if (content.type == "category" && !this._endgame_list[i].categories.includes(content.value)) continue;
            if (content.type == "tag" && !this._endgame_list[i].tags.includes(content.value)) continue;
          }
          this._full_updated_endgame_list.push(this._endgame_list[i]);
        }
        this._full_updated_endgame_indexes = this.get_rating_indexes_from_list(this._full_updated_endgame_list);
      }
    }

    // Attempted and failed:

    if (["all", "failed"].includes(settings.repeat)) {
      if (types.includes(0)) {
        if (settings.rating_type == "any" && settings.categories == "any" && settings.tags == "any") {
          if (settings.repeat == "all") {
            this._repeat_classic_list = this._attempted_classic_list;
            this._repeat_classic_indexes = this._attempted_classic_indexes;
          } else {
            this._repeat_classic_list = this._failed_classic_list;
            this._repeat_classic_indexes = this._failed_classic_indexes;
          }
        } else {
          if (settings.repeat == "all") {
            var current_list = this._attempted_classic_list;
            var current_indexes = this._attempted_classic_indexes;
          } else {
            var current_list = this._failed_classic_list;
            var current_indexes = this._failed_classic_indexes;
          }
          var start_index = 0;
          if (current_indexes[min_rating] != undefined) {
            start_index = current_indexes[min_rating];
          } else if (current_indexes[min_rating + 100] != undefined) {
            start_index = current_indexes[min_rating + 100];
          } else if (current_indexes[min_rating + 200] != undefined) {
            start_index = current_indexes[min_rating + 200];
          }
          var stop_index = current_list.length;
          if (current_indexes[max_rating + 100] != undefined) {
            stop_index = current_indexes[max_rating + 100];
          } else if (current_indexes[max_rating + 200] != undefined) {
            stop_index = current_indexes[max_rating + 200];
          }
          for (var i = start_index; i < stop_index; ++i) {
            if (current_list[i].rating < min_rating - 50 || current_list[i].rating >= max_rating + 50) continue;
            if (content.type) {
              if (content.type == "category" && !current_list[i].categories.includes(content.value)) continue;
              if (content.type == "tag" && !current_list[i].tags.includes(content.value)) continue;
            }
            this._repeat_classic_list.push(current_list[i]);
          }
          this._repeat_classic_indexes = this.get_rating_indexes_from_list(this._repeat_classic_list);
        }
      }
      if (types.includes(1)) {
        if (settings.rating_type == "any" && settings.categories == "any" && settings.tags == "any") {
          if (settings.repeat == "all") {
            this._repeat_ai_list = this._attempted_ai_list;
            this._repeat_ai_indexes = this._attempted_ai_indexes;
          } else {
            this._repeat_ai_list = this._failed_ai_list;
            this._repeat_ai_indexes = this._failed_ai_indexes;
          }
        } else {
          if (settings.repeat == "all") {
            var current_list = this._attempted_ai_list;
            var current_indexes = this._attempted_ai_indexes;
          } else {
            var current_list = this._failed_ai_list;
            var current_indexes = this._failed_ai_indexes;
          }
          var start_index = 0;
          if (current_indexes[min_rating] != undefined) {
            start_index = current_indexes[min_rating];
          } else if (current_indexes[min_rating + 100] != undefined) {
            start_index = current_indexes[min_rating + 100];
          } else if (current_indexes[min_rating + 200] != undefined) {
            start_index = current_indexes[min_rating + 200];
          }
          var stop_index = current_list.length;
          if (current_indexes[max_rating + 100] != undefined) {
            stop_index = current_indexes[max_rating + 100];
          } else if (current_indexes[max_rating + 200] != undefined) {
            stop_index = current_indexes[max_rating + 200];
          }
          for (var i = start_index; i < stop_index; ++i) {
            if (current_list[i].rating < min_rating - 50 || current_list[i].rating >= max_rating + 50) continue;
            if (content.type) {
              if (content.type == "category" && !current_list[i].categories.includes(content.value)) continue;
              if (content.type == "tag" && !current_list[i].tags.includes(content.value)) continue;
            }
            this._repeat_ai_list.push(current_list[i]);
          }
          this._repeat_ai_indexes = this.get_rating_indexes_from_list(this._repeat_ai_list);
        }
      }
      if (types.includes(2)) {
        if (settings.rating_type == "any" && settings.categories == "any" && settings.tags == "any") {
          if (settings.repeat == "all") {
            this._repeat_endgame_list = this._attempted_endgame_list;
            this._repeat_endgame_indexes = this._attempted_endgame_indexes;
          } else {
            this._repeat_endgame_list = this._failed_endgame_list;
            this._repeat_endgame_indexes = this._failed_endgame_indexes;
          }
        } else {
          if (settings.repeat == "all") {
            var current_list = this._attempted_endgame_list;
            var current_indexes = this._attempted_endgame_indexes;
          } else {
            var current_list = this._failed_endgame_list;
            var current_indexes = this._failed_endgame_indexes;
          }
          var start_index = 0;
          if (current_indexes[min_rating] != undefined) {
            start_index = current_indexes[min_rating];
          } else if (current_indexes[min_rating + 100] != undefined) {
            start_index = current_indexes[min_rating + 100];
          } else if (current_indexes[min_rating + 200] != undefined) {
            start_index = current_indexes[min_rating + 200];
          }
          var stop_index = current_list.length;
          if (current_indexes[max_rating + 100] != undefined) {
            stop_index = current_indexes[max_rating + 100];
          } else if (current_indexes[max_rating + 200] != undefined) {
            stop_index = current_indexes[max_rating + 200];
          }
          for (var i = start_index; i < stop_index; ++i) {
            if (current_list[i].rating < min_rating - 50 || current_list[i].rating >= max_rating + 50) continue;
            if (content.type) {
              if (content.type == "category" && !current_list[i].categories.includes(content.value)) continue;
              if (content.type == "tag" && !current_list[i].tags.includes(content.value)) continue;
            }
            this._repeat_endgame_list.push(current_list[i]);
          }
          this._repeat_endgame_indexes = this.get_rating_indexes_from_list(this._repeat_endgame_list);
        }
      }
    }

    this._number_of_loaded_in_repeat_list = 0;

    if (settings.rating_type == "player") {
      this.update_last_list_length_for_player_span();
    } else {
      this._last_list_length = this._full_updated_classic_list.length + this._full_updated_ai_list.length + this._full_updated_endgame_list.length + this._repeat_classic_list.length + this._repeat_ai_list.length + this._repeat_endgame_list.length;
    }

    this._attempted_in_current_list = 0;
    this._last_baseline_for_sort = this.get_rating_baseline(Number(global.player.get_rating()));

    // Update texts
    global.solver._playlist.update_playlist_number_text(0, this._last_list_length);
    global.solver._playlist.update_playlist_type_text();
    global.solver._playlist.update_playlist_category_text();
    global.solver._playlist.update_playlist_repeat_text();
    global.solver._playlist.update_modal_count_text(this._last_list_length);

    if (app_fully_loaded == false) {
      setTimeout(() => {
        loading_cover.update_progress();
        loading_cover.update_status(this._language._active_language.loading_tsumego);
        const path = window.location.pathname;
        if (path == "/daily") {
          global.connection.load_daily_info("daily_from_url");
          return;
        }
        const params = new URLSearchParams(window.location.search);
        let param_from_url = false;
        let url_type_classic = false;
        let collection_param = "none";
        if (params.has("p")) {
          var param_id = decodeURIComponent(params.get("p"));
          if (param_id.length == 6 && param_id[0] != "0") {
            // Endgame or AI
            param_from_url = true;
          } else {
            // Classic
            if (param_id.length < 6) {
              while (param_id.length < 6) {
                param_id = "0" + param_id;
              }
            }
            param_from_url = true;
            url_type_classic = true;
          }
        }
        if (params.has("collection")) {
          collection_param = decodeURIComponent(params.get("collection"));
        }
        var param_item = null;
        if (param_from_url == true && !((collection_param == "expansion") && (global.player.get_verified() == false || global.player.get_expansion_pack() == false))) {
          // Check if tsumego id exist in tsumego list:
          if (url_type_classic == true) {
            param_item = this._classic_list.find((element) => element.id == param_id);
            if (!param_item) {
              param_item = this._attempted_classic_list.find((element) => element.id == param_id);
            }
          } else {
            param_item = this._endgame_list.find((element) => element.id == param_id);
            if (!param_item) {
              param_item = this._attempted_endgame_list.find((element) => element.id == param_id);
            }
            if (!param_item) {
              param_item = this._ai_list.find((element) => element.id == param_id);
            }
            if (!param_item) {
              param_item = this._attempted_ai_list.find((element) => element.id == param_id);
            }
          }
        }
        if (param_from_url == true) {
          if (collection_param == "daily" && param_id && param_id.length == 6) {
            if (global.left_menu && global.left_menu._daily_info && global.left_menu._daily_info.tsumego_id && global.left_menu._daily_info.tsumego_id == param_id) {
              global.connection.load_daily_tsumego(param_id);
            } else {
              // TODO: Note that was have hard coded the tsumego_db to expansion here.
              // TODO: If we have a daily tsumego from the base collection, this will not work
              global.connection.load_tsumego_data(param_id, 1);
            }
          } else if (collection_param == "expansion" && (global.player.get_verified() == false || global.player.get_expansion_pack() == false)) {
            let id_for_show = param_id;
            if (id_for_show[0] == "0") {
              id_for_show = String(Number(id_for_show));
            }
            global.notice.message(this._language._active_language.url_tsumego_fail_pack.replace("%TSUMEGO_ID%", id_for_show), 8000, 1);
            var first_tsumego = this.next_item();
            global.connection.load_tsumego_data(first_tsumego.id, first_tsumego.db);
          } else if (param_item && (param_item.db || param_item.db == 0)) {
            global.connection.load_tsumego_data(param_item.id, param_item.db);
          } else {
            var first_tsumego = this.next_item();
            global.connection.load_tsumego_data(first_tsumego.id, first_tsumego.db);
            if (global.player.get_verified() == false || global.player.get_expansion_pack() == false) {
              global.connection.check_if_tsumego_is_part_of_expansion(param_id);
            } else {
              global.notice.message(this._language._active_language.url_tsumego_fail.replace("%TSUMEGO_ID%", param_id), 4000, 1);
            }
          }
        } else {
          var first_tsumego = this.next_item();
          // global.connection.load_tsumego_data("744qU3", 0); // TODO: <--- temporary code
          global.connection.load_tsumego_data(first_tsumego.id, first_tsumego.db);
        }
      }, 50);
      global.solver._playlist.update_settings();
    }

  },


  update_last_list_length_for_player_span: function() {
    if (!this._current_rating_settings) return;
    var player_baseline = this.get_rating_baseline(Number(global.player.get_rating()));
    var result = 0;
    var min_rating = player_baseline - this._current_rating_settings.delta;
    if (min_rating < 0) min_rating = 0;
    var max_rating = player_baseline + this._current_rating_settings.delta;
    if (max_rating > 2900) max_rating = 2900;

    // Go through all index objects and count occurances of valid ratings

    if (this._full_updated_classic_list.length > 0) {
      for (var t = min_rating; t <= max_rating; t += 100) {
        if (this._full_updated_classic_indexes[t] || this._full_updated_classic_indexes[t] == 0) {
          var flag = false;
          for (var i = max_rating + 100; i <= 2900; i += 100) {
            if (this._full_updated_classic_indexes[i]) {
              result += this._full_updated_classic_indexes[i] - this._full_updated_classic_indexes[t];
              flag = true;
              break;
            }
          }
          if (flag == false) {
            result += this._full_updated_classic_list.length - this._full_updated_classic_indexes[t];
          }
          break;
        }
      }
    }

    if (this._full_updated_ai_list.length > 0) {
      for (var t = min_rating; t <= max_rating; t += 100) {
        if (this._full_updated_ai_indexes[t] || this._full_updated_ai_indexes[t] == 0) {
          var flag = false;
          for (var i = max_rating + 100; i <= 2900; i += 100) {
            if (this._full_updated_ai_indexes[i]) {
              result += this._full_updated_ai_indexes[i] - this._full_updated_ai_indexes[t];
              flag = true;
              break;
            }
          }
          if (flag == false) {
            result += this._full_updated_ai_list.length - this._full_updated_ai_indexes[t];
          }
          break;
        }
      }
    }

    if (this._full_updated_endgame_list.length > 0) {
      for (var t = min_rating; t <= max_rating; t += 100) {
        if (this._full_updated_endgame_indexes[t] || this._full_updated_endgame_indexes[t] == 0) {
          var flag = false;
          for (var i = max_rating + 100; i <= 2900; i += 100) {
            if (this._full_updated_endgame_indexes[i]) {
              result += this._full_updated_endgame_indexes[i] - this._full_updated_endgame_indexes[t];
              flag = true;
              break;
            }
          }
          if (flag == false) {
            result += this._full_updated_endgame_list.length - this._full_updated_endgame_indexes[t];
          }
          break;
        }
      }
    }

    if (this._repeat_classic_list.length > 0) {
      for (var t = min_rating; t <= max_rating; t += 100) {
        if (this._repeat_classic_indexes[t] || this._repeat_classic_indexes[t] == 0) {
          var flag = false;
          for (var i = max_rating + 100; i <= 2900; i += 100) {
            if (this._repeat_classic_indexes[i]) {
              result += this._repeat_classic_indexes[i] - this._repeat_classic_indexes[t];
              flag = true;
              break;
            }
          }
          if (flag == false) {
            result += this._repeat_classic_list.length - this._repeat_classic_indexes[t];
          }
          break;
        }
      }
    }

    if (this._repeat_ai_list.length > 0) {
      for (var t = min_rating; t <= max_rating; t += 100) {
        if (this._repeat_ai_indexes[t] || this._repeat_ai_indexes[t] == 0) {
          var flag = false;
          for (var i = max_rating + 100; i <= 2900; i += 100) {
            if (this._repeat_ai_indexes[i]) {
              result += this._repeat_ai_indexes[i] - this._repeat_ai_indexes[t];
              flag = true;
              break;
            }
          }
          if (flag == false) {
            result += this._repeat_ai_list.length - this._repeat_ai_indexes[t];
          }
          break;
        }
      }
    }

    if (this._repeat_endgame_list.length > 0) {
      for (var t = min_rating; t <= max_rating; t += 100) {
        if (this._repeat_endgame_indexes[t] || this._repeat_endgame_indexes[t] == 0) {
          var flag = false;
          for (var i = max_rating + 100; i <= 2900; i += 100) {
            if (this._repeat_endgame_indexes[i]) {
              result += this._repeat_endgame_indexes[i] - this._repeat_endgame_indexes[t];
              flag = true;
              break;
            }
          }
          if (flag == false) {
            result += this._repeat_endgame_list.length - this._repeat_endgame_indexes[t];
          }
          break;
        }
      }
    }

    result += this._number_of_loaded_in_repeat_list;
    this._last_list_length = result;

  },


  get_rating_indexes_from_list: function(list) {
    if (!list || list.length == 0) return {};
    var result = {};
    result[list[0].rating] = 0;
    if (list.length < 2) return result;
    for (var i = 1; i < list.length; ++i) {
      if (list[i].rating != list[i - 1].rating) {
        result[list[i].rating] = i;
      }
    }
    return result;
  },


  move_item_to_attempted: function(tsumego_id, tsumego_type, tsumego_rating) {

    var tsumego_baseline = this.get_rating_baseline(Number(tsumego_rating));
    if (tsumego_type == "classic") {
      var current_list = this._classic_list;
      var current_indexes = this._classic_indexes;
      var current_full_list = this._full_updated_classic_list;
      var current_full_indexes = this._full_updated_classic_indexes;
      var current_attempted_list = this._attempted_classic_list;
      var current_attempted_indexes = this._attempted_classic_indexes;
    } else if (tsumego_type == "ai") {
      var current_list = this._ai_list;
      var current_indexes = this._ai_indexes;
      var current_full_list = this._full_updated_ai_list;
      var current_full_indexes = this._full_updated_ai_indexes;
      var current_attempted_list = this._attempted_ai_list;
      var current_attempted_indexes = this._attempted_ai_indexes;
    } else if (tsumego_type == "endgame") {
      var current_list = this._endgame_list;
      var current_indexes = this._endgame_indexes;
      var current_full_list = this._full_updated_endgame_list;
      var current_full_indexes = this._full_updated_endgame_indexes;
      var current_attempted_list = this._attempted_endgame_list;
      var current_attempted_indexes = this._attempted_endgame_indexes;
    } else {
      return false;
    }
    const types = ["classic", "ai", "endgame", "total"];

    // Check if tsumego already in attempted list:
    var start_index = 0;
    var first_outside_index = current_attempted_list.length;
    if (current_attempted_indexes[tsumego_baseline]) {
      start_index = current_attempted_indexes[tsumego_baseline];
      for (var i = tsumego_baseline + 100; i < 3000; i += 100) {
        if (current_attempted_indexes[i]) {
          first_outside_index = current_attempted_indexes[i];
          break;
        }
      }
    }
    var item_index =  -1;
    for (var i = start_index; i < first_outside_index; ++i) {
      if (current_attempted_list[i].id == tsumego_id) {
        item_index = i;
        break;
      }
    }
    if (item_index != -1) {
      // Tsumego already in attempted list:
      return;
    }

    var start_index = 0;
    var first_outside_index = current_list.length;
    if (current_indexes[tsumego_baseline]) {
      start_index = current_indexes[tsumego_baseline];
      for (var i = tsumego_baseline + 100; i < 3000; i += 100) {
        if (current_indexes[i]) {
          first_outside_index = current_indexes[i];
          break;
        }
      }
    }
    var item_index =  -1;
    for (var i = start_index; i < first_outside_index; ++i) {
      if (current_list[i].id == tsumego_id) {
        item_index = i;
        break;
      }
    }

    if (item_index != -1) {

      // Add to the correct attempted list, and at the correct index
      var suitable_index = current_attempted_list.length;
      for (var i = current_list[item_index].rating; i < 3000; i += 100) {
        if (current_attempted_indexes[i] || current_attempted_indexes[i] == 0) {
          suitable_index = current_attempted_indexes[i];
          break;
        }
      }
      // Note: Insert so that "suitable_index" will be the index of the inserted item:
      if (suitable_index == current_attempted_list.length) {
        if (tsumego_type == "classic") {
          this._attempted_classic_list.push(current_list[item_index]);
        } else if (tsumego_type == "ai") {
          this._attempted_ai_list.push(current_list[item_index]);
        } else if (tsumego_type == "endgame") {
          this._attempted_endgame_list.push(current_list[item_index]);
        }
      } else {
        if (tsumego_type == "classic") {
          this._attempted_classic_list = current_attempted_list.slice(0, suitable_index).concat([current_list[item_index]].concat(current_attempted_list.slice(suitable_index)));
        } else if (tsumego_type == "ai") {
          this._attempted_ai_list = current_attempted_list.slice(0, suitable_index).concat([current_list[item_index]].concat(current_attempted_list.slice(suitable_index)));
        } else if (tsumego_type == "endgame") {
          this._attempted_endgame_list = current_attempted_list.slice(0, suitable_index).concat([current_list[item_index]].concat(current_attempted_list.slice(suitable_index)));
        }
      }
      // Increment all attempted_indexes above inserted index:
      for (var i = 0; i < 3000; i += 100) {
        if (current_attempted_indexes[i] > suitable_index) {
          current_attempted_indexes[i]++;
        }
      }
      // If tsumego rating do not exist in index object, insert it:
      if (!current_attempted_indexes[current_list[item_index].rating] && current_attempted_indexes[current_list[item_index].rating] != 0) {
        current_attempted_indexes[current_list[item_index].rating] = suitable_index;
      }

      for (category of current_list[item_index].categories) {
        var id = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[STATIC_CATEGORIES.indexOf(category)];
        this._attempted_content_count[types[current_list[item_index].type]][id][this.get_rating_baseline(current_list[item_index].rating)] += 1;
        this._attempted_content_count.total[id][this.get_rating_baseline(current_list[item_index].rating)] += 1;
        this._public_content_count[types[current_list[item_index].type]][id][this.get_rating_baseline(current_list[item_index].rating)] -= 1;
        this._public_content_count.total[id][this.get_rating_baseline(current_list[item_index].rating)] -= 1;
      }
      for (tag of current_list[item_index].tags) {
        var n = STATIC_TAGS.indexOf(tag);
        var id = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[(n - (n % 26)) / 26] + "abcdefghijklmnopqrstuvwxyz"[n % 26];
        this._attempted_content_count[types[current_list[item_index].type]][id][this.get_rating_baseline(current_list[item_index].rating)] += 1;
        this._attempted_content_count.total[id][this.get_rating_baseline(current_list[item_index].rating)] += 1;
        this._public_content_count[types[current_list[item_index].type]][id][this.get_rating_baseline(current_list[item_index].rating)] -= 1;
        this._public_content_count.total[id][this.get_rating_baseline(current_list[item_index].rating)] -= 1;
      }

      current_list.splice(item_index, 1);

      // Decrement all indexes above "item_index":
      for (var i = 0; i < 3000; i += 100) {
        if (current_indexes[i] && current_indexes[i] > item_index) {
          current_indexes[i] -= 1;
        }
      }

      // Delete all current_indexes which doesn't have any tsumego left:
      for (var i = 0; i < 3000; i += 100) {
        if ((current_indexes[i] || current_indexes[i] == 0)) {
          if (current_indexes[i] > current_list.length - 1 || current_list[current_indexes[i]].rating != i) {
            delete(current_indexes[i]);
          }
        }
      }

      // For visitors: save attempted id to local storage:
      if (global.player.get_verified() == false) {
        var attempted_string = "";
        if (cookie_handler._storage.attempted) {
          attempted_string = cookie_handler.get_data_value("attempted");
          attempted_string += ";"
        }
        cookie_handler.update_data("attempted", attempted_string + tsumego_id);
      }
    }

    var start_index = 0;
    var first_outside_index = current_full_list.length;
    if (current_full_indexes[tsumego_baseline]) {
      start_index = current_full_indexes[tsumego_baseline];
      for (var i = tsumego_baseline + 100; i < 3000; i += 100) {
        if (current_full_indexes[i]) {
          first_outside_index = current_full_indexes[i];
          break;
        }
      }
    }
    var item_index =  -1;
    for (var i = start_index; i < first_outside_index; ++i) {
      if (current_full_list[i].id == tsumego_id) {
        item_index = i;
        break;
      }
    }
    if (item_index != -1) {
      current_full_list.splice(item_index, 1);
      // Decrement all indexes above "item_index":
      for (var i = 0; i < 3000; i += 100) {
        if (current_full_indexes[i] && current_full_indexes[i] > item_index) {
          current_full_indexes[i] -= 1;
        }
      }
      // Delete all current_indexes which doesn't have any tsumego left:
      for (var i = 0; i < 3000; i += 100) {
        if ((current_full_indexes[i] || current_full_indexes[i] == 0)) {
          if (current_full_indexes[i] > current_full_list.length - 1 || current_full_list[current_full_indexes[i]].rating != i) {
            delete(current_full_indexes[i]);
          }
        }
      }
    }

  },


  copy_item_to_failed: function(tsumego_id, tsumego_type, tsumego_rating) {
    var tsumego_baseline = this.get_rating_baseline(Number(tsumego_rating));
    if (tsumego_type == "classic") {
      var current_attempted_list = this._attempted_classic_list;
      var current_attempted_indexes = this._attempted_classic_indexes;
      var current_failed_list = this._failed_classic_list;
      var current_failed_indexes = this._failed_classic_indexes;
    } else if (tsumego_type == "ai") {
      var current_attempted_list = this._attempted_ai_list;
      var current_attempted_indexes = this._attempted_ai_indexes;
      var current_failed_list = this._failed_ai_list;
      var current_failed_indexes = this._failed_ai_indexes;
    } else if (tsumego_type == "endgame") {
      var current_attempted_list = this._attempted_endgame_list;
      var current_attempted_indexes = this._attempted_endgame_indexes;
      var current_failed_list = this._failed_endgame_list;
      var current_failed_indexes = this._failed_endgame_indexes;
    }

    // Check if tsumego exist in attempted list:
    var start_index = 0;
    var first_outside_index = current_attempted_list.length;
    if (current_attempted_indexes[tsumego_baseline]) {
      start_index = current_attempted_indexes[tsumego_baseline];
      for (var i = tsumego_baseline + 100; i < 3000; i += 100) {
        if (current_attempted_indexes[i]) {
          first_outside_index = current_attempted_indexes[i];
          break;
        }
      }
    }
    var item_index =  -1;
    for (var i = start_index; i < first_outside_index; ++i) {
      if (current_attempted_list[i].id == tsumego_id) {
        item_index = i;
        break;
      }
    }
    if (item_index != -1) {

      // Add to the correct attempted list, and at the correct index
      var suitable_index = current_failed_list.length;
      for (var i = current_attempted_list[item_index].rating; i < 3000; i += 100) {
        if (current_failed_indexes[i] || current_failed_indexes[i] == 0) {
          suitable_index = current_failed_indexes[i];
          break;
        }
      }
      // Note: Insert so that "suitable_index" will be the index of the inserted item:
      if (suitable_index == current_failed_list.length) {
        if (tsumego_type == "classic") {
          this._failed_classic_list.push(current_attempted_list[item_index]);
        } else if (tsumego_type == "ai") {
          this._failed_ai_list.push(current_attempted_list[item_index]);
        } else if (tsumego_type == "endgame") {
          this._failed_endgame_list.push(current_attempted_list[item_index]);
        }
      } else {
        if (tsumego_type == "classic") {
          this._failed_classic_list = current_failed_list.slice(0, suitable_index).concat([current_attempted_list[item_index]].concat(current_failed_list.slice(suitable_index)));
        } else if (tsumego_type == "ai") {
          this._failed_ai_list = current_failed_list.slice(0, suitable_index).concat([current_attempted_list[item_index]].concat(current_failed_list.slice(suitable_index)));
        } else if (tsumego_type == "endgame") {
          this._failed_endgame_list = current_failed_list.slice(0, suitable_index).concat([current_attempted_list[item_index]].concat(current_failed_list.slice(suitable_index)));
        }
      }

      // Increment all attempted_indexes above inserted index:
      for (var i = 0; i < 3000; i += 100) {
        if (current_failed_indexes[i] > suitable_index) {
          current_failed_indexes[i]++;
        }
      }
      // If tsumego rating do not exist in index object, insert it:
      if (!current_failed_indexes[current_attempted_list[item_index].rating] && current_failed_indexes[current_attempted_list[item_index].rating] != 0) {
        current_failed_indexes[current_attempted_list[item_index].rating] = suitable_index;
      }

      // For visitors: save failed to local storage
      if (global.player.get_verified() == false) {
        var failed_string = "";
        if (cookie_handler._storage.failed) {
          failed_string = cookie_handler.get_data_value("failed");
          failed_string += ";"
        }
        cookie_handler.update_data("failed", failed_string + tsumego_id);
      }
    }
  },


  tsumego_in_failed: function(tsumego_id, tsumego_type, tsumego_rating) {
    var tsumego_baseline = this.get_rating_baseline(Number(tsumego_rating));
    if (tsumego_type == "classic") {
      var current_failed_list = this._failed_classic_list;
      var current_failed_indexes = this._failed_classic_indexes;
    } else if (tsumego_type == "ai") {
      var current_failed_list = this._failed_ai_list;
      var current_failed_indexes = this._failed_ai_indexes;
    } else if (tsumego_type == "endgame") {
      var current_failed_list = this._failed_endgame_list;
      var current_failed_indexes = this._failed_endgame_indexes;
    }
    // Check if tsumego exist in attempted list:
    var start_index = 0;
    var first_outside_index = current_failed_list.length;
    if (current_failed_indexes[tsumego_baseline]) {
      start_index = current_failed_indexes[tsumego_baseline];
      for (var i = tsumego_baseline + 100; i < 3000; i += 100) {
        if (current_failed_indexes[i]) {
          first_outside_index = current_failed_indexes[i];
          break;
        }
      }
    }
    var item_index =  -1;
    for (var i = start_index; i < first_outside_index; ++i) {
      if (current_failed_list[i].id == tsumego_id) {
        item_index = i;
        break;
      }
    }
    if (item_index != -1) {
      return true;
    } else {
      return false;
    }
  },


  remove_from_failed: function(tsumego_id, tsumego_type, tsumego_rating) {
    var tsumego_baseline = this.get_rating_baseline(Number(tsumego_rating));
    if (tsumego_type == "classic") {
      var current_failed_list = this._failed_classic_list;
      var current_failed_indexes = this._failed_classic_indexes;
    } else if (tsumego_type == "ai") {
      var current_failed_list = this._failed_ai_list;
      var current_failed_indexes = this._failed_ai_indexes;
    } else if (tsumego_type == "endgame") {
      var current_failed_list = this._failed_endgame_list;
      var current_failed_indexes = this._failed_endgame_indexes;
    }
    // TODO: Use manual index (current_failed_indexes) instead of findIndex()
    var item_index = current_failed_list.findIndex((element) => element.id == tsumego_id);
    if (item_index != -1) {
      current_failed_list.splice(item_index, 1);
      // Decrement all attempted_indexes above removed index:
      for (var i = 0; i < 3000; i += 100) {
        if (current_failed_indexes[i] > item_index) { // Todo: Should this be > or >= ?
          current_failed_indexes[i]--;
        }
      }
    }
  },


  re_insert_popped_list_in_repeat_list: function() {
    while (this._popped_from_repeat_in_player_mode.length) {
      var item = this._popped_from_repeat_in_player_mode.pop();
      if (item.type == 0) {
        var current_repeat_list = this._repeat_classic_list;
        var current_repeat_indexes = this._repeat_classic_indexes;
      } else if (item.type == 1) {
        var current_repeat_list = this._repeat_ai_list;
        var current_repeat_indexes = this._repeat_ai_indexes;
      } else if (item.type == 2) {
        var current_repeat_list = this._repeat_endgame_list;
        var current_repeat_indexes = this._repeat_endgame_indexes;
      }
      // Add to the correct repeat list, and at the correct index
      var suitable_index = current_repeat_list.length;
      for (var i = item.rating; i < 3000; i += 100) {
        if (current_repeat_indexes[i] || current_repeat_indexes[i] == 0) {
          suitable_index = current_repeat_indexes[i];
          break;
        }
      }
      // Note: Insert so that "suitable_index" will be the index of the inserted item:
      if (suitable_index == current_repeat_list.length) {
        if (item.type == 0) {
          this._repeat_classic_list.push(item);
        } else if (item.type == 1) {
          this._repeat_ai_list.push(item);
        } else if (item.type == 2) {
          this._repeat_endgame_list.push(item);
        }
      } else {
        if (item.type == 0) {
          this._repeat_classic_list = current_repeat_list.slice(0, suitable_index).concat([item].concat(current_repeat_list.slice(suitable_index)));
        } else if (item.type == 1) {
          this._repeat_ai_list = current_repeat_list.slice(0, suitable_index).concat([item].concat(current_repeat_list.slice(suitable_index)));
        } else if (item.type == 2) {
          this._repeat_endgame_list = current_repeat_list.slice(0, suitable_index).concat([item].concat(current_repeat_list.slice(suitable_index)));
        }
      }
      // Increment all repeat_indexes above inserted index:
      for (var i = 0; i < 3000; i += 100) {
        if (current_repeat_indexes[i] > suitable_index) {
          current_repeat_indexes[i]++;
        }
      }
      // If tsumego rating does not exist in index object, insert it:
      if (!current_repeat_indexes[item.rating] && current_repeat_indexes[item.rating] != 0) {
        current_repeat_indexes[item.rating] = suitable_index;
      }
    }
  },


  next_item: function() {
    var result = null;
    if (this._full_updated_classic_list.length == 0 && this._full_updated_ai_list.length == 0 && this._full_updated_endgame_list.length == 0 && this._repeat_classic_list.length == 0 && this._repeat_ai_list.length == 0 && this._repeat_endgame_list.length == 0) {
      return result;
    }
    var last_type = this._last_type;
    if (last_type == "classic") {
      var priority_list = ["ai", "endgame", "classic"];
    } else if (last_type == "ai") {
      var priority_list = ["endgame", "classic", "ai"];
    } else {
      var priority_list = ["classic", "ai", "endgame"];
    }
    while (priority_list.length > 0) {
      var priority = priority_list.splice(0, 1)[0];
      if (priority == "classic") {
        var full_list = this._full_updated_classic_list;
        var full_indexes = this._full_updated_classic_indexes;
        var repeat_list = this._repeat_classic_list;
        var repeat_indexes = this._repeat_classic_indexes;
      } else if (priority == "ai") {
        var full_list = this._full_updated_ai_list;
        var full_indexes = this._full_updated_ai_indexes;
        var repeat_list = this._repeat_ai_list;
        var repeat_indexes = this._repeat_ai_indexes;
      } else if (priority == "endgame") {
        var full_list = this._full_updated_endgame_list;
        var full_indexes = this._full_updated_endgame_indexes;
        var repeat_list = this._repeat_endgame_list;
        var repeat_indexes = this._repeat_endgame_indexes;
      }

      var min_rating = 0;
      var max_rating = 2900;
      if (this._current_rating_settings) {
        if (this._current_rating_settings.type == "any") {
          // Any (show as close as possible to player rank)
          min_rating = this.get_rating_baseline(Number(global.player.get_rating()));
          if (min_rating < 0) min_rating = 0;
          max_rating = this.get_rating_baseline(Number(global.player.get_rating()));
          if (max_rating > 2900) max_rating = 2900;
        } else if (this._current_rating_settings.type == "player") {
          // Player (show any index within rating span, following player rank)
          min_rating = this.get_rating_baseline(Number(global.player.get_rating())) - this._current_rating_settings.delta;
          if (min_rating < 0) min_rating = 0;
          max_rating = this.get_rating_baseline(Number(global.player.get_rating())) + this._current_rating_settings.delta;
          if (max_rating > 2900) max_rating = 2900;
        } else {
          // Only / Span (show any within span, using the selected baseline)
          min_rating = this.get_rating_baseline(this._current_rating_settings.baseline) - this._current_rating_settings.delta;
          if (min_rating < 0) min_rating = 0;
          max_rating = this.get_rating_baseline(this._current_rating_settings.baseline) + this._current_rating_settings.delta;
          if (max_rating > 2900) max_rating = 2900;
        }
      }

      // If repeat_list.length and random 33% or no full list: Use random index from repeat list
      if (repeat_list.length > 0) {
        var min_index = 0;
        var max_index = repeat_list.length - 1;
        var index_to_use = 0;
        if (this._current_rating_settings) {
          if (repeat_indexes[min_rating] || repeat_indexes[min_rating] == 0) {
            min_index = repeat_indexes[min_rating];
          } else {
            for (var i = min_rating; i >= 0; i -= 100) {
              if (repeat_indexes[i] || repeat_indexes[i] == 0) {
                min_index = repeat_indexes[i];
                break;
              }
            }
          }
          if (repeat_indexes[max_rating + 100]) {
            max_index = repeat_indexes[max_rating + 100] - 1;
          } else {
            for (var i = max_rating + 100; i <= 2900; ++i) {
              if (repeat_indexes[i] || repeat_indexes[i] == 0) {
                max_index = repeat_indexes[i];
                break;
              }
            }
          }
          if (min_index == max_index) {
            if (repeat_list[min_index].rating >= min_rating && repeat_list[min_index].rating <= max_rating) {
              index_to_use = min_index;
            } else if (this._current_rating_settings.type == "any") {
              index_to_use = min_index;
            } else {
              index_to_use = -1;
            }
          } else {
            var random_index = min_index + Math.floor(Math.random() * ((max_index - min_index) + 1));
            if (repeat_list[random_index].rating >= min_rating && repeat_list[random_index].rating <= max_rating) {
              index_to_use = random_index;
            } else if (this._current_rating_settings.type == "any") {
              index_to_use = random_index;
            } else {
              index_to_use = -1;
            }
          }
        } else {
          index_to_use = Math.floor(Math.random() * full_list.length);
        }

        var random_number = Math.floor(Math.random() * 3);
        var full_list_is_empty = true;
        // If type == "player", check if full_list contains any tsumego with correct rating
        if (this._current_rating_settings && this._current_rating_settings.type == "player") {
          for (item of full_list) {
            if (item.rating >= min_rating && item.rating <= max_rating) {
              full_list_is_empty = false;
              break;
            }
          }
        } else {
          full_list_is_empty = (full_list.length == 0);
        }
        if (index_to_use != -1 && (random_number == 1 || full_list_is_empty == true)) {
          var list_item = repeat_list[index_to_use];
          var item_to_return = {"categories": list_item.categories, "db": list_item.db, "id": list_item.id, "rating": list_item.rating, "tags": list_item.tags, "type": list_item.type};

          this._number_of_loaded_in_repeat_list += 1;
          if (this._current_rating_settings && this._current_rating_settings.type == "player") {
            this._popped_from_repeat_in_player_mode.push(repeat_list[index_to_use]);
          }
          repeat_list.splice(index_to_use, 1);
          // Decrement all indexes above removed index:
          for (var i = 0; i < 3000; i += 100) {
            if (repeat_indexes[i] && repeat_indexes[i] > index_to_use) {
              repeat_indexes[i] -= 1;
            }
          }
          // Delete all current_indexes which doesn't have any tsumego left:
          for (var i = 0; i < 3000; i += 100) {
            if ((repeat_indexes[i] || repeat_indexes[i] == 0)) {
              if (repeat_indexes[i] > repeat_list.length - 1 || repeat_list[repeat_indexes[i]].rating != i) {
                delete(repeat_indexes[i]);
              }
            }
          }
          this._last_type = priority;
          return item_to_return;
        }

      }

      // If full_list, use random index from there
      if (full_list.length > 0) {
        if (this._current_rating_settings) {

          // Find min and max index:
          var min_index = 0;
          var max_index = full_list.length - 1;
          if (full_indexes[min_rating]) {
            min_index = full_indexes[min_rating];
          } else {
            // TODO: The following is looking both up and down. If any "span" mode: make sure min or max is not outside of span?
            for (var i = 0; i <= Math.max(2900 - min_rating, min_rating); i += 100) {
              if ((min_rating - i >= 0) && (full_indexes[min_rating - i] || full_indexes[min_rating - i] == 0)) {
                min_index = full_indexes[min_rating - i];
                break;
              }
              if ((min_rating + i <= 2900) && (full_indexes[min_rating + i] || full_indexes[min_rating + i] == 0)) {
                min_index = full_indexes[min_rating + i];
                break;
              }
            }
          }
          if ((full_indexes[max_rating] || full_indexes[max_rating] == 0) && full_indexes[max_rating + 100]) {
            max_index = full_indexes[max_rating + 100] - 1;
          } else {
            // TODO: The following is looking both up and down. If any "span" mode: make sure min or max is not outside of span?
            for (var i = 0; i <= Math.max(2900 - max_rating, max_rating); i += 100) {
              if ((max_rating + i <= 2900) && (full_indexes[max_rating + i] || full_indexes[max_rating + i] == 0)) {
                // Find next existing higher rating:
                var next_rating_index = -1;
                for (t = max_rating + i + 100; t <= 2900; t += 100) {
                  if (full_indexes[t] || full_indexes[t] == 0) {
                    next_rating_index = full_indexes[t];
                    break;
                  }
                }
                // If no existing higher rating, use max index
                if (next_rating_index == -1) {
                  next_rating_index = full_list.length;
                }
                max_index = next_rating_index - 1;
                break;
              }
              if ((max_rating - i >= 0) && (full_indexes[max_rating - i] || full_indexes[max_rating - i] == 0)) {
                // Find next existing higher rating:
                var next_rating_index = -1;
                for (t = max_rating - i + 100; t <= 2900; t += 100) {
                  if (full_indexes[t] || full_indexes[t] == 0) {
                    next_rating_index = full_indexes[t];
                    break;
                  }
                }
                // If no existing higher rating, use max index
                if (next_rating_index == -1) {
                  next_rating_index = full_list.length;
                }
                max_index = next_rating_index - 1;
                break;
              }
            }
          }
          if (min_index == max_index) {
            if (this._current_rating_settings.type != "player" || (full_list[min_index].rating >= min_rating && full_list[min_index].rating <= max_rating)) {
              this._last_type = priority;
              return full_list[min_index];
            }
          } else {
            var random_index = min_index + Math.floor(Math.random() * ((max_index - min_index) + 1));
            if (this._current_rating_settings.type != "player" || (full_list[random_index].rating >= min_rating && full_list[random_index].rating <= max_rating)) {
              this._last_type = priority;
              return full_list[random_index];
            }
          }
        } else {
          this._last_type = priority;
          return full_list[Math.floor(Math.random() * full_list.length)];
        }
      }
    }
    return result;
  },


  copy_array: function(arr) {
    var result = [];
    for (var i = 0; i < arr.length; i += 1) {
      result.push(arr[i]);
    }
    return result;
  },


};



